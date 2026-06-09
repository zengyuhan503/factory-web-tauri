use std::path::PathBuf;

/// 获取可执行文件所在目录（开发模式下为 target/debug/）
fn get_exe_dir() -> PathBuf {
    std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(PathBuf::from))
        .unwrap_or_else(|| PathBuf::from("."))
}

pub fn get_calib_result_base_dir() -> PathBuf {
    #[cfg(debug_assertions)]
    {
        // 开发模式：放在 target/debug/CalibratResult/ 下
        get_exe_dir().join("CalibratResult")
    }
    #[cfg(not(debug_assertions))]
    {
        PathBuf::from("/home/ssnwt/work/skycalib/CalibratResult")
    }
}

pub fn get_device_work_dir(cpu_id: &str) -> PathBuf {
    get_calib_result_base_dir().join(cpu_id)
}

pub fn get_resource_dir(_app_handle: &tauri::AppHandle) -> PathBuf {
    #[cfg(debug_assertions)]
    {
        // 开发模式：优先使用 target/debug/resources/，不存在则回退到源码目录
        let debug_resources = get_exe_dir().join("resources");
        if debug_resources.exists() {
            debug_resources
        } else {
            PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("resources")
        }
    }
    #[cfg(not(debug_assertions))]
    {
        let base = _app_handle.path_resolver().resource_dir().unwrap_or_else(|| PathBuf::from("."));
        // .deb 安装后资源可能在 resource_dir/resources/ 下，探测并自动适配
        let with_resources = base.join("resources");
        if with_resources.exists() {
            with_resources
        } else {
            base
        }
    }
}
