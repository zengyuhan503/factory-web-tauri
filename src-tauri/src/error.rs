use thiserror::Error;

#[derive(Error, Debug)]
pub enum CalibError {
    #[error("ADB错误: {0}")]
    Adb(#[from] AdbError),

    #[error("Python脚本执行错误: {0}")]
    Python(String),

    #[error("设备未连接")]
    DeviceNotFound,

    #[error("设备连接超时")]
    DeviceTimeout,

    #[error("设备离线: {0}")]
    DeviceOffline(String),

    #[error("标定步骤失败 [{step}]: {message}")]
    StepFailed { step: String, message: String },

    #[error("覆盖率验证失败: {0}")]
    VerifyFailed(String),

    #[error("清晰度标定验证失败: {0}")]
    SfrFailed(String),

    #[error("阈值检查未通过")]
    ThresholdExceeded,

    #[error("高通标定判定失败: {0}")]
    CheckFailed(String),

    #[error("文件推送失败: {0}")]
    PushFailed(String),

    #[error("OSS上传失败: {0}")]
    OssUpload(String),

    #[error("API上报失败: {0}")]
    ApiReport(String),

    #[error("标定被取消")]
    Cancelled,

    #[error("配置文件错误: {0}")]
    Config(String),

    #[error("Python环境未找到: {0}")]
    PythonNotFound(String),

    #[error("数据集路径不存在: {0}")]
    DatasetNotFound(String),

    #[error("标定结果文件解析失败: {0}")]
    XmlParseFailed(String),

    #[error("标定文件缺失: {0}")]
    CalibrationFileMissing(String),

    #[error("设备重启失败: {0}")]
    RebootFailed(String),

    #[error("设备启动超时")]
    BootTimeout,

    #[error("工作目录创建失败: {0}")]
    WorkDirCreateFailed(String),

    #[error("文件数量超限: 上限 {limit}, 当前 {current}")]
    FileLimitExceeded { limit: u32, current: usize },

    #[error("标定详情压缩包不存在: {0}")]
    ZipFileNotFound(String),

    #[error("CPU ID 获取失败: {0}")]
    CpuIdFailed(String),

    #[error("未知错误: {0}")]
    Unknown(String),
}

#[derive(Error, Debug)]
pub enum AdbError {
    #[error("设备未连接")]
    DeviceNotFound,

    #[error("无可用设备")]
    NoDevices,

    #[error("设备未授权 (unauthorized)")]
    DeviceUnauthorized,

    #[error("ADB权限不足")]
    PermissionDenied,

    #[error("ADB命令执行超时")]
    Timeout,

    #[error("ADB服务异常: {0}")]
    ServerError(String),

    #[error("ADB Shell执行失败: {0}")]
    ShellFailed(String),

    #[error("文件推送失败: {0}")]
    PushFailed(String),

    #[error("文件拉取失败: {0}")]
    PullFailed(String),

    #[error("命令执行失败: {0}")]
    CommandFailed(String),

    #[error("CPU ID 获取失败: {0}")]
    CpuIdFailed(String),

    #[error("未知ADB错误: {0}")]
    Unknown(String),
}

impl From<std::io::Error> for AdbError {
    fn from(err: std::io::Error) -> Self {
        let msg = err.to_string().to_lowercase();
        if msg.contains("no devices")
            || msg.contains("device not found")
            || msg.contains("device '(null)'")
        {
            AdbError::DeviceNotFound
        } else if msg.contains("unauthorized") {
            AdbError::DeviceUnauthorized
        } else if msg.contains("no permissions") || msg.contains("permission denied") {
            AdbError::PermissionDenied
        } else if msg.contains("adb server") || msg.contains("cannot connect to daemon") {
            AdbError::ServerError(err.to_string())
        } else {
            AdbError::Unknown(err.to_string())
        }
    }
}
