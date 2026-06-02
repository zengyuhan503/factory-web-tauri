use crate::adapters::adb::AdbExecutor;
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
        let engine = CalibrationEngine::new(slot_id, serial.clone(), config, resource_dir, Some(logger));
        let slots_clone = self.slots.clone();

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
                }
                Err(e) => {
                    log::error!("[槽位{}] 标定失败: {}", slot_id, e);
                    let mut slots = slots_clone.lock().await;
                    if let Some(slot) = slots.get_mut(slot_id as usize) {
                        slot.status = SlotStatus::Error;
                        slot.step_name = "失败".to_string();
                        slot.hint = e.to_string();
                        slot.result = SlotResult::Fail {
                            reason: e.to_string(),
                        };
                    }

                    let _ = app.emit_all(
                        &format!("device:{}:error", slot_id),
                        serde_json::json!({
                            "slot_id": slot_id,
                            "message": e.to_string(),
                        }),
                    );
                }
            }
        });

        Ok(())
    }
}
