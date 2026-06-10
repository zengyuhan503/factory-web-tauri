pub mod adapters;
pub mod commands;
pub mod error;
pub mod models;
pub mod services;
pub mod state;
pub mod utils;

use state::AppState;
use tauri::Manager;

pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let app_state = AppState::new(9);
            app.manage(app_state.clone());

            // 注册 start_device_test 事件监听器（绕过 invoke 参数反序列化问题）
            let slots = app_state.slots.clone();
            let app_handle_for_event = app.handle().clone();
            app.listen_global("start_device_test", move |event| {
                if let Some(payload) = event.payload() {
                    if let Ok(json) = serde_json::from_str::<serde_json::Value>(payload) {
                        let slot_id = json.get("slot_id").and_then(|v| v.as_u64()).map(|v| v as u8);
                        let config_val = json.get("config").cloned();
                        if let (Some(slot_id), Some(config_val)) = (slot_id, config_val) {
                            if let Ok(config) = serde_json::from_value::<crate::models::DeviceConfig>(config_val) {
                                let slots_clone = slots.clone();
                                let app_handle_clone = app_handle_for_event.clone();
                                tauri::async_runtime::spawn(async move {
                                    let pool = crate::services::CalibrationPool::new(slots_clone);
                                    if let Err(e) = pool.start_slot(slot_id, config, app_handle_clone.clone()).await {
                                        log::error!("start_device_test event handler error: {}", e);
                                        let _ = app_handle_clone.emit_all("device:error", serde_json::json!({
                                            "slot_id": slot_id,
                                            "code": "Z002",
                                            "message": e,
                                            "detail": null,
                                            "suggestion": "请检查设备连接状态后重试",
                                            "is_operational": true,
                                        }));
                                    }
                                });
                            } else {
                                let _ = app_handle_for_event.emit_all("device:error", serde_json::json!({
                                    "slot_id": slot_id,
                                    "code": "Z002",
                                    "message": "配置解析失败",
                                    "detail": null,
                                    "suggestion": "请检查配置参数后重试",
                                    "is_operational": true,
                                }));
                            }
                        }
                    }
                }
            });

            let app_handle = app.handle().clone();
            let device_manager = services::DeviceManager::new(app_state.slots.clone());
            tauri::async_runtime::spawn(async move {
                device_manager.start_polling(app_handle).await;
            });

            // 生产模式：将资源从系统目录复制到用户工作目录（解决 /usr/lib/ 无写权限问题）
            #[cfg(not(debug_assertions))]
            {
                let work_dir = utils::paths::get_work_base_dir();
                let user_resources = work_dir.join("resources");
                if !user_resources.join("ProcessCal").exists() {
                    // 使用硬编码路径，不依赖 resource_dir()（避免 identifier/name 不匹配问题）
                    let system_resources = std::path::PathBuf::from("/usr/lib/skyworthxr-calib/resources");
                    if system_resources.exists() {
                        log::info!("首次启动，复制资源到用户目录: {:?} -> {:?}", system_resources, user_resources);
                        if let Err(e) = std::fs::create_dir_all(&work_dir) {
                            log::warn!("创建工作目录失败: {}", e);
                        }
                        if let Err(e) = utils::paths::copy_dir_recursive(&system_resources, &user_resources) {
                            log::warn!("复制资源目录失败: {}", e);
                        } else {
                            // 设置 XRCalib 执行权限
                            let xrcalib = user_resources.join("tools").join("qvr_calib").join("XRCalib");
                            if xrcalib.exists() {
                                let _ = std::process::Command::new("chmod")
                                    .arg("+x")
                                    .arg(&xrcalib)
                                    .output();
                            }
                            log::info!("资源复制完成");
                        }
                    } else {
                        log::warn!("系统资源目录不存在: {:?}", system_resources);
                    }
                }
            }

            // Linux 桌面快捷方式（首次启动自动创建）
            utils::create_linux_desktop_shortcut_if_needed();

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::start_device_test,
            commands::get_slot_status,
            commands::get_connected_devices,
            commands::save_config,
            commands::load_config,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
