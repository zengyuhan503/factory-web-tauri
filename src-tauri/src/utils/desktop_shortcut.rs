/// 在 Linux 用户桌面创建应用快捷方式（.desktop 文件）
/// 仅在首次启动时执行，通过标记文件避免重复创建
pub fn create_linux_desktop_shortcut_if_needed() {
    #[cfg(target_os = "linux")]
    {
        use std::fs;
        use std::path::PathBuf;

        const DESKTOP_FLAG_FILE: &str = ".skycalib_desktop_created";

        let home_dir = match std::env::var("HOME") {
            Ok(v) => PathBuf::from(v),
            Err(_) => {
                log::warn!("无法获取 HOME 环境变量，跳过桌面快捷方式创建");
                return;
            }
        };

        let config_dir = home_dir.join(".config/skycalib-tauri");
        let flag_file = config_dir.join(DESKTOP_FLAG_FILE);

        if flag_file.exists() {
            return;
        }

        let desktop_dir = home_dir.join("Desktop");
        if !desktop_dir.exists() {
            let desktop_zh = home_dir.join("桌面");
            if desktop_zh.exists() {
                let _ = create_desktop_file(&desktop_zh);
            } else {
                log::warn!("未找到桌面目录，跳过桌面快捷方式创建");
                return;
            }
        } else {
            let _ = create_desktop_file(&desktop_dir);
        }

        let _ = fs::create_dir_all(&config_dir);
        let _ = fs::write(&flag_file, "1");
    }
}

#[cfg(target_os = "linux")]
fn create_desktop_file(desktop_dir: &std::path::PathBuf) -> std::io::Result<()> {
    use std::fs;

    let desktop_content = r#"[Desktop Entry]
Name=SkyCalib VR设备标定工具
Exec=/usr/bin/skyworthxr-skycalib
Type=Application
Icon=skyworthxr-skycalib
Categories=Development;
Terminal=false
"#;

    let desktop_file = desktop_dir.join("skyworthxr-skycalib.desktop");
    fs::write(&desktop_file, desktop_content)?;

    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mut permissions = fs::metadata(&desktop_file)?.permissions();
        permissions.set_mode(0o755);
        fs::set_permissions(&desktop_file, permissions)?;
    }

    log::info!("已在桌面创建快捷方式: {}", desktop_file.display());
    Ok(())
}
