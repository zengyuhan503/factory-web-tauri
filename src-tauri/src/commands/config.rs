use crate::models::AppConfig;
use crate::state::AppState;
use tauri_plugin_store::StoreExt;

#[tauri::command]
pub async fn save_config(
    config: AppConfig,
    app: tauri::AppHandle,
    state: tauri::State<'_, AppState>,
) -> Result<(), String> {
    let mut cfg = state.config.lock().await;
    *cfg = config;

    let store = app.store("config.json").map_err(|e| e.to_string())?;
    store.set("config", serde_json::to_value(&*cfg).map_err(|e| e.to_string())?);
    store.save().map_err(|e| e.to_string())?;

    Ok(())
}

#[tauri::command]
pub async fn load_config(
    app: tauri::AppHandle,
    state: tauri::State<'_, AppState>,
) -> Result<AppConfig, String> {
    let store = app.store("config.json").map_err(|e| e.to_string())?;

    if let Some(value) = store.get("config") {
        let config: AppConfig =
            serde_json::from_value(value).map_err(|e| e.to_string())?;
        let mut cfg = state.config.lock().await;
        *cfg = config.clone();
        Ok(config)
    } else {
        Ok(AppConfig::default())
    }
}
