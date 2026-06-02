use crate::models::AppConfig;
use crate::state::AppState;
use std::path::PathBuf;

fn get_config_path() -> PathBuf {
    PathBuf::from("config.json")
}

#[tauri::command]
pub async fn save_config(
    config: AppConfig,
    state: tauri::State<'_, AppState>,
) -> Result<(), String> {
    let mut cfg = state.config.lock().await;
    *cfg = config.clone();

    let config_path = get_config_path();
    if let Some(parent) = config_path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }

    let json = serde_json::to_string_pretty(&config).map_err(|e| e.to_string())?;
    std::fs::write(&config_path, json).map_err(|e| e.to_string())?;

    Ok(())
}

#[tauri::command]
pub async fn load_config() -> Result<AppConfig, String> {
    let config_path = get_config_path();

    if !config_path.exists() {
        return Ok(AppConfig::default());
    }

    let json = std::fs::read_to_string(&config_path).map_err(|e| e.to_string())?;
    let config: AppConfig = serde_json::from_str(&json).map_err(|e| e.to_string())?;
    Ok(config)
}
