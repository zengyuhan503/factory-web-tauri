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

            let app_handle = app.handle().clone();
            let device_manager = services::DeviceManager::new(app_state.slots.clone());
            tauri::async_runtime::spawn(async move {
                device_manager.start_polling(app_handle).await;
            });

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
