#[cfg(unix)]
use std::os::unix::fs::PermissionsExt;

fn main() {
    #[cfg(unix)]
    {
        let xrcalib = std::path::PathBuf::from("resources/tools/qvr_calib/XRCalib");
        if xrcalib.exists() {
            if let Ok(metadata) = std::fs::metadata(&xrcalib) {
                let mut perms = metadata.permissions();
                perms.set_mode(0o755);
                let _ = std::fs::set_permissions(&xrcalib, perms);
            }
        }
    }

    tauri_build::build()
}
