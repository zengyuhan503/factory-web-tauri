use std::path::PathBuf;

/// 统一工作基目录：开发和生产都使用 /home/ssnwt/work/skycalib/
pub fn get_work_base_dir() -> PathBuf {
    PathBuf::from("/home/ssnwt/work/skycalib")
}

/// 获取标定结果根目录
pub fn get_calib_result_base_dir() -> PathBuf {
    get_work_base_dir().join("CalibratResult")
}

/// 获取指定设备的标定工作目录
pub fn get_device_work_dir(cpu_id: &str) -> PathBuf {
    get_calib_result_base_dir().join(cpu_id)
}

/// 获取资源目录
/// 开发模式：使用 target/debug/resources/ 或源码目录
/// 生产模式：使用 /home/ssnwt/work/skycalib/resources/（应用启动时从系统目录复制）
pub fn get_resource_dir(_app_handle: &tauri::AppHandle) -> PathBuf {
    #[cfg(debug_assertions)]
    {
        let exe_dir = std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(PathBuf::from))
            .unwrap_or_else(|| PathBuf::from("."));
        let debug_resources = exe_dir.join("resources");
        if debug_resources.exists() {
            debug_resources
        } else {
            PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("resources")
        }
    }
    #[cfg(not(debug_assertions))]
    {
        get_work_base_dir().join("resources")
    }
}

/// 递归复制目录
pub fn copy_dir_recursive(src: &std::path::Path, dst: &std::path::Path) -> std::io::Result<()> {
    std::fs::create_dir_all(dst)?;
    for entry in std::fs::read_dir(src)? {
        let entry = entry?;
        let src_path = entry.path();
        let dst_path = dst.join(entry.file_name());
        if src_path.is_dir() {
            copy_dir_recursive(&src_path, &dst_path)?;
        } else {
            std::fs::copy(&src_path, &dst_path)?;
        }
    }
    Ok(())
}
