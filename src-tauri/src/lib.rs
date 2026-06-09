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
                        if let (Some(slot_id), Some(config_val)) = (
                            json.get("slot_id").and_then(|v| v.as_u64()).map(|v| v as u8),
                            json.get("config").cloned()
                        ) {
                            if let Ok(config) = serde_json::from_value::<crate::models::DeviceConfig>(config_val) {
                                let slots_clone = slots.clone();
                                let app_handle_clone = app_handle_for_event.clone();
                                tauri::async_runtime::spawn(async move {
                                    let pool = crate::services::CalibrationPool::new(slots_clone);
                                    if let Err(e) = pool.start_slot(slot_id, config, app_handle_clone).await {
                                        log::error!("start_device_test event handler error: {}", e);
                                    }
                                });
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
