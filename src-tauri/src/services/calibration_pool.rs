use crate::adapters::adb::AdbExecutor;
use crate::models::events::ErrorEvent;
use crate::models::{DeviceConfig, DeviceSlot, SlotResult, SlotStatus};
use crate::services::calibration_engine::CalibrationEngine;
use crate::utils::logger::DeviceTestLogger;
use crate::utils::paths::get_resource_dir;
use std::sync::Arc;
use tauri::Manager;
use tokio::sync::Mutex;

pub struct CalibrationPool {
    slots: Arc<Mutex<Vec<DeviceSlot>>>,
}

impl CalibrationPool {
    pub fn new(slots: Arc<Mutex<Vec<DeviceSlot>>>) -> Self {
        Self { slots }
    }

    pub async fn start_slot(
        &self,
        slot_id: u8,
        config: DeviceConfig,
        app: tauri::AppHandle,
    ) -> Result<(), String> {
        let mut slots = self.slots.lock().await;
        let slot = slots
            .get_mut(slot_id as usize)
            .ok_or("无效槽位编号")?;

        if slot.status != SlotStatus::Connected {
            return Err("设备未连接或正在运行".to_string());
        }

        let serial = slot
            .serial
            .clone()
            .ok_or("槽位无设备")?;

        // 获取或重试获取 CPU ID
        let cpu_id = if let Some(ref id) = slot.cpu_id {
            id.clone()
        } else {
            // 如果在 device_manager 中未能获取，在此重试
            let adb = AdbExecutor::new(serial.clone());
            match adb.get_cpu_id().await {
                Ok(id) => {
                    let id = id.trim().to_string();
                    slot.cpu_id = Some(id.clone());
                    // 通知前端更新 CPU ID 显示
                    let _ = app.emit_all(
                        "device:connected",
                        serde_json::json!({
                            "slot_id": slot_id,
                            "serial": serial,
                            "cpu_id": id,
                        }),
                    );
                    id
                }
                Err(e) => {
                    log::warn!("[槽位{}] 测试启动时获取 CPU ID 失败: {}", slot_id, e);
                    String::new() // 空字符串作为 fallback，logger 会使用 serial
                }
            }
        };

        // 创建设备测试日志记录器
        let logger = DeviceTestLogger::new(&cpu_id, &serial);
        logger.info(&format!("[槽位{}] 测试启动", slot_id));
        logger.info(&format!("配置 - RGB: {}, TOF: {}, QVR类型: {}",
            config.is_rgb, config.is_tof, config.qvr_type));

        slot.status = SlotStatus::Running;
        slot.progress = 0;
        slot.step_name = "初始化中...".to_string();
        slot.hint = "准备开始标定".to_string();
        slot.result = SlotResult::Pending;

        let resource_dir = get_resource_dir(&app);
        let engine = CalibrationEngine::new(slot_id, serial.clone(), cpu_id.clone(), config, resource_dir, Some(logger));
        let slots_clone = self.slots.clone();

        // 标定结束后自动恢复槽位的辅助函数
        let slots_clone_for_reset = slots_clone.clone();
        let schedule_reset = move |app_handle: tauri::AppHandle| {
            let serial_clone = serial.clone();
            let slots_clone2 = slots_clone_for_reset.clone();
            let slot_id = slot_id;
            tokio::spawn(async move {
                tokio::time::sleep(tokio::time::Duration::from_secs(10)).await;

                let adb = AdbExecutor::new(serial_clone.clone());
                let still_connected = adb.is_connected().await;

                let mut slots = slots_clone2.lock().await;
                if let Some(slot) = slots.get_mut(slot_id as usize) {
                    if still_connected {
                        log::info!("[槽位{}] 设备 {} 仍在连接，10秒后恢复为可测试状态", slot_id, serial_clone);
                        slot.status = SlotStatus::Connected;
                        slot.progress = 0;
                        slot.step_name = "已连接".to_string();
                        slot.hint = "点击启动按钮开始标定".to_string();
                        slot.result = SlotResult::Pending;
                        // 保留 cpu_id 和 serial
                    } else {
                        log::info!("[槽位{}] 设备 {} 已断开，10秒后重置为空槽位", slot_id, serial_clone);
                        slot.serial = None;
                        slot.cpu_id = None;
                        slot.status = SlotStatus::Empty;
                        slot.progress = 0;
                        slot.step_name = "待连接".to_string();
                        slot.hint = "".to_string();
                        slot.result = SlotResult::Pending;
                    }
                    let _ = app_handle.emit_all(
                        "device:reset",
                        serde_json::json!({
                            "slot_id": slot_id,
                            "status": if still_connected { "connected" } else { "empty" },
                            "serial": if still_connected { slot.serial.as_deref() } else { None },
                            "cpu_id": slot.cpu_id.as_deref(),
                        }),
                    );
                }
            });
        };

        // 在独立 task 中运行
        tokio::spawn(async move {
            match engine.run(app.clone()).await {
                Ok(_result) => {
                    let mut slots = slots_clone.lock().await;
                    if let Some(slot) = slots.get_mut(slot_id as usize) {
                        slot.status = SlotStatus::Success;
                        slot.progress = 100;
                        slot.step_name = "完成".to_string();
                        slot.hint = "标定成功".to_string();
                        slot.result = SlotResult::Pass;
                    }
                    // 标定成功也10秒后恢复
                    schedule_reset(app);
                }
                Err(e) => {
                    log::error!("[槽位{}] 标定失败 [{}]: {}", slot_id, e.code(), e.user_message());
                    let mut slots = slots_clone.lock().await;
                    if let Some(slot) = slots.get_mut(slot_id as usize) {
                        slot.status = SlotStatus::Error;
                        slot.step_name = format!("失败 [{}]", e.code());
                        slot.hint = e.user_message();
                        slot.result = SlotResult::Fail {
                            reason: e.user_message(),
                        };
                    }

                    let error_event = ErrorEvent::from_calib_error(slot_id, &e);
                    let _ = app.emit_all("device:error", error_event);
                    // 标定失败10秒后恢复
                    schedule_reset(app);
                }
            }
        });

        Ok(())
    }
}
