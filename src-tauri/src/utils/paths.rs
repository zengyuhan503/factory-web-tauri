use std::path::PathBuf;
use tauri::Manager;

pub fn get_calib_result_base_dir() -> PathBuf {
    PathBuf::from("/home/ssnwt/work/skycalib/CalibratResult")
}

pub fn get_device_work_dir(serial: &str) -> PathBuf {
    get_calib_result_base_dir().join(serial)
}

pub fn get_resource_dir(app_handle: &tauri::AppHandle) -> PathBuf {
    app_handle.path_resolver().resource_dir().unwrap_or_else(|| PathBuf::from("."))
}
