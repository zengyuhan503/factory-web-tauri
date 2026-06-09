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

    // 尝试完整解析，兼容旧版配置（缺少字段时使用默认值）
    match serde_json::from_str::<AppConfig>(&json) {
        Ok(config) => Ok(config),
        Err(_) => {
            // 旧版配置缺少新字段，尝试部分解析后合并默认值
            let mut config = AppConfig::default();

            if let Ok(value) = serde_json::from_str::<serde_json::Value>(&json) {
                if let Some(v) = value.get("is_rgb").and_then(|v| v.as_bool()) {
                    config.is_rgb = v;
                }
                if let Some(v) = value.get("is_tof").and_then(|v| v.as_bool()) {
                    config.is_tof = v;
                }
                if let Some(v) = value.get("qvr_type").and_then(|v| v.as_str()) {
                    config.qvr_type = v.to_string();
                }
                if let Some(v) = value.get("file_max").and_then(|v| v.as_u64()) {
                    config.file_max = v as u32;
                }
                if let Some(v) = value.get("verify_dof").and_then(|v| v.as_f64()) {
                    config.verify_dof = Some(v);
                }
                if let Some(v) = value.get("verify_rgb").and_then(|v| v.as_f64()) {
                    config.verify_rgb = Some(v);
                }
                if let Some(v) = value.get("verify_tof").and_then(|v| v.as_f64()) {
                    config.verify_tof = Some(v);
                }
                if let Some(v) = value.get("slot_count").and_then(|v| v.as_u64()) {
                    config.slot_count = v as u8;
                }
                if let Some(v) = value.get("enable_sfr").and_then(|v| v.as_bool()) {
                    config.enable_sfr = v;
                }
                if let Some(v) = value.get("sfr_mean_avg50_min").and_then(|v| v.as_f64()) {
                    config.sfr_mean_avg50_min = Some(v);
                }
                if let Some(v) = value.get("sfr_cam_std_max").and_then(|v| v.as_f64()) {
                    config.sfr_cam_std_max = Some(v);
                }
                if let Some(v) = value.get("detection_rate_threshold").and_then(|v| v.as_f64()) {
                    config.detection_rate_threshold = Some(v);
                }
            }

            // 保存更新后的配置（带新字段）
            let _ = std::fs::write(&config_path, serde_json::to_string_pretty(&config).unwrap());

            Ok(config)
        }
    }
}
