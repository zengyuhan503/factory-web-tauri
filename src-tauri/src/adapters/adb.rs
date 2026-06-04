use crate::error::AdbError;
use std::time::Duration;
use tokio::process::Command;
use tokio::time::timeout;

pub struct AdbExecutor {
    serial: String,
}

impl AdbExecutor {
    pub fn new(serial: String) -> Self {
        Self { serial }
    }

    fn build_cmd(&self, args: &[&str]) -> Command {
        let mut cmd = Command::new("adb");
        cmd.arg("-s").arg(&self.serial);
        cmd.args(args);
        cmd
    }

    pub async fn exec(&self, args: &[&str], timeout_ms: u64) -> Result<String, AdbError> {
        let mut cmd = self.build_cmd(args);
        let output = timeout(
            Duration::from_millis(timeout_ms),
            cmd.output(),
        )
        .await
        .map_err(|_| AdbError::Timeout)??;

        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        if !output.status.success() {
            let err_str = format!("{}\n{}", stdout, stderr);
            return Err(AdbError::CommandFailed(err_str));
        }

        if stderr.to_lowercase().contains("error:") {
            return Err(AdbError::CommandFailed(stderr.to_string()));
        }

        Ok(stdout.trim().to_string())
    }

    pub async fn shell(&self, cmd_str: &str, timeout_ms: u64) -> Result<String, AdbError> {
        self.exec(&["shell", cmd_str], timeout_ms).await
    }

    pub async fn push(&self, local: &str, remote: &str, timeout_ms: u64) -> Result<String, AdbError> {
        self.exec(&["push", local, remote], timeout_ms).await
    }

    pub async fn pull(&self, remote: &str, local: &str, timeout_ms: u64) -> Result<String, AdbError> {
        self.exec(&["pull", remote, local], timeout_ms).await
    }

    pub async fn reboot(&self, timeout_ms: u64) -> Result<String, AdbError> {
        self.exec(&["reboot"], timeout_ms).await
    }

    pub async fn wait_for_device(&self, timeout_ms: u64) -> Result<(), AdbError> {
        self.exec(&["wait-for-device"], timeout_ms).await?;
        Ok(())
    }

    pub async fn wait_for_boot(&self, timeout_ms: u64, max_retries: u32) -> Result<(), AdbError> {
        for _ in 0..max_retries {
            match self.shell("getprop sys.boot_completed", timeout_ms).await {
                Ok(output) if output.trim() == "1" => return Ok(()),
                Ok(_) => tokio::time::sleep(Duration::from_secs(1)).await,
                Err(AdbError::DeviceNotFound) => return Err(AdbError::DeviceNotFound),
                Err(_) => tokio::time::sleep(Duration::from_secs(1)).await,
            }
        }
        Err(AdbError::Timeout)
    }

    pub async fn is_connected(&self) -> bool {
        match self.exec(&["devices"], 5000).await {
            Ok(output) => output.contains(&self.serial),
            Err(_) => false,
        }
    }

    pub async fn get_cpu_id(&self) -> Result<String, AdbError> {
        self.shell("cat /sys/devices/soc0/serial_number", 10000).await
    }

    pub async fn get_android_version(&self) -> Result<String, AdbError> {
        let version = self.shell("getprop ro.build.version.release", 10000).await?;
        Ok(version.replace("\r\n", "").trim().to_string())
    }

    pub async fn get_product_model(&self) -> Result<String, AdbError> {
        let model = self.shell("getprop ro.product.model", 10000).await?;
        Ok(model.trim().to_string())
    }

    pub async fn get_command_prefix(&self) -> Result<String, AdbError> {
        match self.shell("ls /system/bin/sxrmmi", 10000).await {
            Ok(_) => Ok("sxr".to_string()),
            Err(_) => Ok("ssnwt".to_string()),
        }
    }

    pub async fn get_camera_type(&self, prefix: &str) -> Result<String, AdbError> {
        let cam = self.shell(&format!("getprop persist.{}.camname", prefix), 10000).await?;
        let cam = cam.trim().to_string();
        if cam == "tracking" {
            Ok("gray".to_string())
        } else {
            Ok(cam)
        }
    }
}

pub async fn list_devices() -> Result<Vec<DeviceInfo>, AdbError> {
    let output = Command::new("adb")
        .arg("devices")
        .arg("-l")
        .output()
        .await
        .map_err(|e| AdbError::Unknown(e.to_string()))?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let mut devices = Vec::new();

    for line in stdout.lines().skip(1) {
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() >= 2 && parts[1] == "device" {
            let serial = parts[0].to_string();
            let mut product = None;
            let mut usb = None;

            for part in parts.iter().skip(2) {
                if part.starts_with("product:") {
                    product = Some(part[8..].to_string());
                } else if part.starts_with("usb:") {
                    usb = Some(part[4..].to_string());
                }
            }

            devices.push(DeviceInfo {
                serial,
                product,
                usb,
            });
        }
    }

    Ok(devices)
}

#[derive(Debug, Clone)]
pub struct DeviceInfo {
    pub serial: String,
    pub product: Option<String>,
    pub usb: Option<String>,
}
