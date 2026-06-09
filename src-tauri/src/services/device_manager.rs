use crate::adapters::adb::AdbExecutor;
use crate::adapters::adb::list_devices;
use crate::models::{DeviceSlot, SlotStatus};
use std::sync::Arc;
use tauri::Manager;
use tokio::sync::Mutex;
use tokio::time::{sleep, Duration};

pub struct DeviceManager {
    slots: Arc<Mutex<Vec<DeviceSlot>>>,
}

impl DeviceManager {
    pub fn new(slots: Arc<Mutex<Vec<DeviceSlot>>>) -> Self {
        Self { slots }
    }

    pub async fn start_polling(&self, app: tauri::AppHandle) {
        let slots = self.slots.clone();

        tokio::spawn(async move {
            loop {
                let devices = list_devices().await.unwrap_or_default();

                {
                    let mut slots_guard = slots.lock().await;

                    // 检查已连接设备是否还在，以及是否需要重试获取 CPU ID
                    for slot in slots_guard.iter_mut() {
                        if let Some(ref serial) = slot.serial {
                            let still_connected = devices.iter().any(|d| d.serial == *serial);
                            if !still_connected {
                                // 如果设备正在主动 reboot，跳过断开检测（reboot 期间的断连是正常的）
                                if slot.rebooting {
                                    continue;
                                }

                                // 如果槽位正在运行标定流程，发送错误事件并将状态改为 Error
                                if slot.status == SlotStatus::Running {
                                    if !slot.disconnect_notified {
                                        log::warn!("槽位 {} 设备 {} 在标定过程中断开", slot.slot_id, serial);
                                        slot.disconnect_notified = true;
                                        slot.status = SlotStatus::Error;
                                        slot.step_name = "失败 [A006]".to_string();
                                        slot.hint = "设备在测试中离线，请检查USB连接".to_string();
                                        slot.result = crate::models::SlotResult::Fail {
                                            reason: "设备在测试中离线".to_string(),
                                        };
                                        let _ = app.emit_all(
                                            "device:error",
                                            serde_json::json!({
                                                "slot_id": slot.slot_id,
                                                "code": "A006",
                                                "message": "设备在测试中离线，请检查USB连接",
                                                "detail": format!("设备 {} 在标定过程中断开连接", serial),
                                                "suggestion": "请检查USB线是否松动，重新插拔设备后重试",
                                                "is_operational": true,
                                            }),
                                        );
                                    }
                                    continue;
                                }

                                // 如果槽位是 Error 或 Success 状态，说明标定刚结束，schedule_reset 会在 10 秒后处理恢复。
                                // 此时不清空 serial，避免设备重启期间被分配到其他槽位。
                                if slot.status == SlotStatus::Error || slot.status == SlotStatus::Success {
                                    log::warn!("槽位 {} 设备 {} 断开（状态 {:?}），等待 schedule_reset 处理", slot.slot_id, serial, slot.status);
                                    continue;
                                }

                                log::warn!("槽位 {} 设备 {} 断开", slot.slot_id, serial);
                                slot.serial = None;
                                slot.cpu_id = None;
                                slot.status = SlotStatus::Empty;
                                slot.progress = 0;
                                slot.step_name = "待连接".to_string();
                                slot.hint = "".to_string();
                                slot.result = crate::models::SlotResult::Pending;
                                slot.disconnect_notified = false;

                                let _ = app.emit_all(
                                    "device:disconnected",
                                    serde_json::json!({
                                        "slot_id": slot.slot_id,
                                    }),
                                );
                            } else if slot.cpu_id.is_none() && slot.status != SlotStatus::Running {
                                // 设备仍在连接但 CPU ID 未获取到，重试获取
                                let adb = AdbExecutor::new(serial.clone());
                                match adb.get_cpu_id().await {
                                    Ok(id) => {
                                        let id = id.trim().to_string();
                                        if !id.is_empty() {
                                            log::info!("槽位 {} 设备 {} 重试获取 CPU ID 成功: {}", slot.slot_id, serial, id);
                                            slot.cpu_id = Some(id.clone());
                                            let _ = app.emit_all(
                                                "device:connected",
                                                serde_json::json!({
                                                    "slot_id": slot.slot_id,
                                                    "serial": serial,
                                                    "cpu_id": id,
                                                }),
                                            );
                                        }
                                    }
                                    Err(_) => {
                                        // 获取失败，下次轮询再试
                                    }
                                }
                            }
                        }
                    }

                    // 分配新设备到空槽位
                    for device in devices {
                        let already_assigned = slots_guard
                            .iter()
                            .any(|s| s.serial.as_ref() == Some(&device.serial));

                        if !already_assigned {
                            for slot in slots_guard.iter_mut() {
                                if slot.status == SlotStatus::Empty {
                                    // 尝试获取 CPU ID，失败时重试一次
                                    let mut cpu_id = None;
                                    let adb = AdbExecutor::new(device.serial.clone());
                                    for attempt in 1..=2 {
                                        match adb.get_cpu_id().await {
                                            Ok(id) => {
                                                let id = id.trim().to_string();
                                                if !id.is_empty() {
                                                    log::info!("设备 {} 第{}次获取 CPU ID 成功: {}", device.serial, attempt, id);
                                                    cpu_id = Some(id);
                                                    break;
                                                } else {
                                                    log::warn!("设备 {} 第{}次获取 CPU ID 为空", device.serial, attempt);
                                                }
                                            }
                                            Err(e) => {
                                                log::warn!("设备 {} 第{}次获取 CPU ID 失败: {}", device.serial, attempt, e);
                                            }
                                        }
                                        if attempt == 1 {
                                            sleep(Duration::from_secs(1)).await;
                                        }
                                    }

                                    slot.serial = Some(device.serial.clone());
                                    slot.cpu_id = cpu_id.clone();
                                    slot.status = SlotStatus::Connected;
                                    slot.step_name = "已连接".to_string();
                                    slot.hint = "点击启动按钮开始标定".to_string();
                                    slot.disconnect_notified = false;

                                    let _ = app.emit_all(
                                        "device:connected",
                                        serde_json::json!({
                                            "slot_id": slot.slot_id,
                                            "serial": device.serial,
                                            "cpu_id": cpu_id,
                                        }),
                                    );
                                    break;
                                }
                            }
                        }
                    }
                }

                sleep(Duration::from_secs(2)).await;
            }
        });
    }
}
