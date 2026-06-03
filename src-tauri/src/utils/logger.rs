use log::{error, info, warn};
use std::fs::OpenOptions;
use std::io::{BufWriter, Write};
use std::path::PathBuf;
use std::sync::Mutex;

/// 设备测试日志记录器
/// 每个设备测试对应一个独立的日志文件，命名格式: {cpu_id}_{yyyy-MM-dd-HH-mm-ss}.log
pub struct DeviceTestLogger {
    writer: Mutex<BufWriter<std::fs::File>>,
    log_path: PathBuf,
}

impl DeviceTestLogger {
    /// 创建新的设备测试日志记录器
    ///
    /// # Arguments
    /// * `cpu_id` - 设备CPU ID，用于日志文件名
    /// * `serial` - 设备序列号，当cpu_id获取失败时用作fallback文件名
    ///
    /// 日志文件路径: logs/{cpu_id}_{yyyy-MM-dd-HH-mm-ss}.log
    pub fn new(cpu_id: &str, serial: &str) -> Self {
        let log_dir = std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|p| p.join("logs")))
            .unwrap_or_else(|| PathBuf::from("logs"));
        std::fs::create_dir_all(&log_dir).ok();

        let filename = if cpu_id.is_empty() {
            format!("{}_{}.log", serial, chrono::Local::now().format("%Y-%m-%d-%H-%M-%S"))
        } else {
            format!("{}_{}.log", cpu_id, chrono::Local::now().format("%Y-%m-%d-%H-%M-%S"))
        };

        let log_path = log_dir.join(&filename);

        let file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&log_path)
            .expect("无法创建日志文件");

        let writer = Mutex::new(BufWriter::new(file));

        let logger = Self { writer, log_path };

        logger.info(&format!("========================================"));
        logger.info(&format!("设备标定测试日志"));
        logger.info(&format!("CPU ID: {}", cpu_id));
        logger.info(&format!("Serial: {}", serial));
        logger.info(&format!("开始时间: {}", chrono::Local::now().format("%Y-%m-%d %H:%M:%S")));
        logger.info(&format!("========================================"));

        logger
    }

    fn write_log(&self, level: &str, message: &str) {
        let timestamp = chrono::Local::now().format("%Y-%m-%d %H:%M:%S%.3f");
        let line = format!("[{}] [{}] {}\n", timestamp, level, message);

        if let Ok(mut writer) = self.writer.lock() {
            let _ = writer.write_all(line.as_bytes());
            let _ = writer.flush();
        }

        // 同时输出到标准日志
        match level {
            "ERROR" => log::error!("{}", message),
            "WARN" => log::warn!("{}", message),
            "DEBUG" => log::debug!("{}", message),
            _ => log::info!("{}", message),
        }
    }

    pub fn info(&self, message: &str) {
        self.write_log("INFO", message);
    }

    pub fn warn(&self, message: &str) {
        self.write_log("WARN", message);
    }

    pub fn error(&self, message: &str) {
        self.write_log("ERROR", message);
    }

    pub fn debug(&self, message: &str) {
        self.write_log("DEBUG", message);
    }

    /// 记录Python脚本的原始输出
    pub fn python_log(&self, message: &str) {
        self.write_log("PYTHON", message);
    }

    /// 记录标定步骤开始
    pub fn step_start(&self, step_name: &str, step_index: u8) {
        self.info(&format!(
            "[步骤开始] {} (序号: {})",
            step_name, step_index
        ));
    }

    /// 记录标定步骤结束
    pub fn step_end(&self, step_name: &str, success: bool) {
        let status = if success { "成功" } else { "失败" };
        self.info(&format!("[步骤结束] {} - 结果: {}", step_name, status));
    }

    /// 记录关键操作（如文件推送、重启等）
    pub fn action(&self, action_name: &str, detail: &str) {
        self.info(&format!("[操作] {} - {}", action_name, detail));
    }

    /// 记录最终结果
    pub fn result(&self, success: bool, message: &str) {
        let status = if success { "通过" } else { "未通过" };
        self.info(&format!("========================================"));
        self.info(&format!("[最终结果] {} - {}", status, message));
        self.info(&format!("结束时间: {}", chrono::Local::now().format("%Y-%m-%d %H:%M:%S")));
        self.info(&format!("========================================"));
    }

    /// 记录详细的错误信息，包括错误类型和上下文
    pub fn log_error(&self, err: &crate::error::CalibError) {
        self.error(&format!("[错误] {}", err));
        // 对于特定错误类型，记录额外上下文
        match err {
            crate::error::CalibError::Adb(adb_err) => {
                self.error(&format!("[错误详情] ADB操作失败: {}", adb_err));
            }
            crate::error::CalibError::StepFailed { step, message } => {
                self.error(&format!("[错误详情] 步骤 '{}' 失败: {}", step, message));
            }
            crate::error::CalibError::CheckFailed(msg) => {
                self.error(&format!("[错误详情] 高通标定判定失败: {}", msg));
            }
            crate::error::CalibError::VerifyFailed(msg) => {
                self.error(&format!("[错误详情] 覆盖率验证失败: {}", msg));
            }
            crate::error::CalibError::ThresholdExceeded => {
                self.error(&format!("[错误详情] 标定参数超出阈值限制"));
            }
            crate::error::CalibError::PushFailed(path) => {
                self.error(&format!("[错误详情] 文件推送失败，路径: {}", path));
            }
            crate::error::CalibError::OssUpload(msg) => {
                self.error(&format!("[错误详情] OSS上传失败: {}", msg));
            }
            crate::error::CalibError::ApiReport(msg) => {
                self.error(&format!("[错误详情] API上报失败: {}", msg));
            }
            crate::error::CalibError::DeviceOffline(serial) => {
                self.error(&format!("[错误详情] 设备 {} 在测试过程中离线", serial));
            }
            crate::error::CalibError::RebootFailed(msg) => {
                self.error(&format!("[错误详情] 设备重启失败: {}", msg));
            }
            crate::error::CalibError::BootTimeout => {
                self.error(&format!("[错误详情] 设备重启后启动超时"));
            }
            crate::error::CalibError::SfrFailed(msg) => {
                self.error(&format!("[错误详情] 清晰度标定验证失败: {}", msg));
            }
            crate::error::CalibError::CalibrationFileMissing(path) => {
                self.error(&format!("[错误详情] 标定结果文件缺失: {}", path));
            }
            crate::error::CalibError::XmlParseFailed(msg) => {
                self.error(&format!("[错误详情] XML解析失败: {}", msg));
            }
            crate::error::CalibError::DatasetNotFound(path) => {
                self.error(&format!("[错误详情] 数据集路径不存在: {}", path));
            }
            crate::error::CalibError::ZipFileNotFound(path) => {
                self.error(&format!("[错误详情] 压缩包不存在: {}", path));
            }
            crate::error::CalibError::FileLimitExceeded { limit, current } => {
                self.error(&format!(
                    "[错误详情] 标定文件数量超限: 上限 {}, 当前 {}",
                    limit, current
                ));
            }
            _ => {}
        }
    }

    pub fn log_path(&self) -> &PathBuf {
        &self.log_path
    }
}

/// 兼容旧版 DeviceLogger，保留原有接口
pub struct DeviceLogger {
    log_dir: PathBuf,
}

impl DeviceLogger {
    pub fn new() -> Self {
        let log_dir = std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|p| p.join("logs")))
            .unwrap_or_else(|| PathBuf::from("logs"));
        std::fs::create_dir_all(&log_dir).ok();
        std::fs::create_dir_all(log_dir.join("device")).ok();
        std::fs::create_dir_all(log_dir.join("error")).ok();
        Self { log_dir }
    }

    pub fn log_device(&self, serial: &str, level: &str, message: &str) {
        let file_path = self.log_dir.join("device").join(format!("{}.log", serial));
        let timestamp = chrono::Local::now().format("%Y-%m-%d %H:%M:%S");
        let line = format!("[{}] [{}] {}\n", timestamp, level, message);

        if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(&file_path) {
            let _ = file.write_all(line.as_bytes());
        }

        match level {
            "ERROR" => error!("[{}] {}", serial, message),
            "WARN" => warn!("[{}] {}", serial, message),
            _ => info!("[{}] {}", serial, message),
        }
    }

    pub fn info(&self, serial: &str, message: &str) {
        self.log_device(serial, "INFO", message);
    }

    pub fn warn(&self, serial: &str, message: &str) {
        self.log_device(serial, "WARN", message);
    }

    pub fn error(&self, serial: &str, message: &str) {
        self.log_device(serial, "ERROR", message);
    }
}
