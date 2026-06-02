use crate::adapters::adb::list_devices;

#[tauri::command]
pub async fn get_connected_devices() -> Result<Vec<String>, String> {
    let devices = list_devices().await.map_err(|e| e.to_string())?;
    Ok(devices.into_iter().map(|d| d.serial).collect())
}
