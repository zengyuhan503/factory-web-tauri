use crate::models::DeviceConfig;
use crate::services::CalibrationPool;
use crate::state::AppState;

#[tauri::command]
pub async fn start_device_test(
    slot_id: u8,
    config: DeviceConfig,
    app: tauri::AppHandle,
    state: tauri::State<'_, AppState>,
) -> Result<(), String> {
    let pool = CalibrationPool::new(state.slots.clone());
    pool.start_slot(slot_id, config, app).await
}

#[tauri::command]
pub async fn get_slot_status(
    state: tauri::State<'_, AppState>,
) -> Result<Vec<crate::models::DeviceSlot>, String> {
    let slots = state.slots.lock().await;
    Ok(slots.clone())
}
