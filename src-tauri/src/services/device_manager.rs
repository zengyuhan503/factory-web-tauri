use crate::adapters::adb::AdbExecutor;
use crate::adapters::adb::list_devices;
use crate::models::{DeviceSlot, SlotStatus};
use std::sync::Arc;
use tauri::Emitter;
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

                    // 检查已连接设备是否还在
                    for slot in slots_guard.iter_mut() {
                        if let Some(ref serial) = slot.serial {
                            let still_connected = devices.iter().any(|d| d.serial == *serial);
                            if !still_connected {
                                log::warn!("槽位 {} 设备 {} 断开", slot.slot_id, serial);
                                slot.serial = None;
                                slot.cpu_id = None;
                                slot.status = SlotStatus::Empty;
                                slot.progress = 0;
                                slot.step_name = "待连接".to_string();
                                slot.hint = "".to_string();
                                slot.result = crate::models::SlotResult::Pending;

                                let _ = app.emit(
                                    &format!("device:{}:disconnected", slot.slot_id),
                                    (),
                                );
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
                                    // 尝试获取 CPU ID
                                    let cpu_id = {
                                        let adb = AdbExecutor::new(device.serial.clone());
                                        match adb.get_cpu_id().await {
                                            Ok(id) => {
                                                let id = id.trim().to_string();
                                                if !id.is_empty() {
                                                    log::info!("设备 {} CPU ID: {}", device.serial, id);
                                                    Some(id)
                                                } else {
                                                    log::warn!("设备 {} CPU ID 为空", device.serial);
                                                    None
                                                }
                                            }
                                            Err(e) => {
                                                log::warn!("获取设备 {} CPU ID 失败: {}", device.serial, e);
                                                None
                                            }
                                        }
                                    };

                                    slot.serial = Some(device.serial.clone());
                                    slot.cpu_id = cpu_id.clone();
                                    slot.status = SlotStatus::Connected;
                                    slot.step_name = "已连接".to_string();
                                    slot.hint = "点击启动按钮开始标定".to_string();

                                    let _ = app.emit(
                                        &format!("device:{}:connected", slot.slot_id),
                                        serde_json::json!({
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
