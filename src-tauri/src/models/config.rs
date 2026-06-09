use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub is_rgb: bool,
    pub is_tof: bool,
    pub qvr_type: String,
    pub file_max: u32,
    pub verify_dof: Option<f64>,
    pub verify_rgb: Option<f64>,
    pub verify_tof: Option<f64>,
    pub slot_count: u8,
    pub enable_sfr: bool,
    pub sfr_mean_avg50_min: Option<f64>,
    pub sfr_cam_std_max: Option<f64>,
    pub detection_rate_threshold: Option<f64>,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            is_rgb: false,
            is_tof: false,
            qvr_type: "1".to_string(),
            file_max: 200,
            verify_dof: Some(95.0),
            verify_rgb: Some(95.0),
            verify_tof: Some(95.0),
            slot_count: 4,
            enable_sfr: true,
            sfr_mean_avg50_min: Some(0.18),
            sfr_cam_std_max: Some(0.05),
            detection_rate_threshold: Some(20.0),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceConfig {
    pub is_rgb: bool,
    pub is_tof: bool,
    pub qvr_type: String,
    pub file_max: u32,
    pub thresholds: ThresholdConfig,
    pub enable_sfr: bool,
    pub sfr_mean_avg50_min: Option<f64>,
    pub sfr_cam_std_max: Option<f64>,
    pub detection_rate_threshold: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThresholdConfig {
    pub dof: Option<f64>,
    pub rgb: Option<f64>,
    pub tof: Option<f64>,
}

impl Default for ThresholdConfig {
    fn default() -> Self {
        Self {
            dof: Some(95.0),
            rgb: Some(95.0),
            tof: Some(95.0),
        }
    }
}
