use serde::{Deserialize, Serialize};
use thiserror::Error;

/// 标定错误枚举
///
/// 错误码体系:
/// - Axxx: ADB/设备连接错误
/// - Bxxx: 文件/路径/数量错误
/// - Cxxx: 标定算法/验证错误
/// - Dxxx: 系统/环境错误
/// - Exxx: 网络/上传错误
/// - Zxxx: 其他/未知错误
#[derive(Error, Debug, Clone, Serialize, Deserialize)]
pub enum CalibError {
    // === A: ADB/设备连接 ===
    #[error("设备未连接，请检查USB线和设备状态")]
    DeviceNotFound,

    #[error("设备连接超时，请重新插拔设备")]
    DeviceTimeout,

    #[error("设备未授权USB调试，请在设备上允许USB调试")]
    DeviceUnauthorized,

    #[error("ADB服务异常: {0}")]
    AdbServerError(String),

    #[error("ADB命令执行失败: {0}")]
    AdbCommandFailed(String),

    #[error("设备在测试过程中离线: {0}")]
    DeviceOffline(String),

    // === B: 文件/路径/数量 ===
    #[error("标定结果文件数量超限 (当前{current}个，上限{limit}个)，请清理历史文件")]
    FileLimitExceeded { limit: u32, current: usize },

    #[error("标定结果文件缺失: {0}")]
    CalibrationFileMissing(String),

    #[error("数据集路径不存在: {0}")]
    DatasetNotFound(String),

    #[error("标定详情压缩包不存在: {0}")]
    ZipFileNotFound(String),

    #[error("工作目录创建失败: {0}")]
    WorkDirCreateFailed(String),

    #[error("标定结果XML解析失败: {0}")]
    XmlParseFailed(String),

    // === C: 标定算法/验证 ===
    #[error("从设备拉取标定数据失败，请检查设备连接")]
    DatasetPullFailed,

    #[error("标定板检测失败: {detail}")]
    TargetDetectionFailed { detail: String },

    #[error("标定板尺寸偏差过大 (实测误差{actual:.3}mm，容差{tolerance:.3}mm)，请检查标定板")]
    TargetMeasurementError { actual: f64, tolerance: f64 },

    #[error("摄像头标定重投影误差过大，请检查拍摄图片质量")]
    ReprojectionErrorExceeded,

    #[error("摄像头标定计算失败: {0}")]
    CamCalibrationFailed(String),

    #[error("标定文件格式转换失败")]
    YamlConvertFailed,

    #[error("摄像头覆盖率验证未通过: {0}")]
    CoverageVerifyFailed(String),

    #[error("标定参数超出合格阈值: {0}")]
    ThresholdExceeded(String),

    #[error("高通标定判定未通过: {0}")]
    CheckResultFailed(String),

    #[error("清晰度标定验证未通过: {0}")]
    SfrVerifyFailed(String),

    // === D: 系统/环境 ===
    #[error("配置参数错误: {0}")]
    ConfigError(String),

    #[error("Python运行环境未找到: {0}")]
    PythonNotFound(String),

    #[error("CPU ID获取失败: {0}")]
    CpuIdFailed(String),

    // === E: 网络/上传 ===
    #[error("推送标定文件到设备失败: {0}")]
    PushFailed(String),

    #[error("设备重启失败: {0}")]
    RebootFailed(String),

    #[error("设备重启后启动超时，请检查设备状态")]
    BootTimeout,

    #[error("标定结果上传失败: {0}")]
    OssUploadFailed(String),

    #[error("标定结果上报失败: {0}")]
    ApiReportFailed(String),

    // === Z: 其他 ===
    #[error("标定测试已取消")]
    Cancelled,

    #[error("发生未知错误，请联系技术支持")]
    Unknown(String),
}

impl CalibError {
    /// 错误码，用于快速定位问题
    pub fn code(&self) -> &'static str {
        match self {
            CalibError::DeviceNotFound => "A001",
            CalibError::DeviceTimeout => "A002",
            CalibError::DeviceUnauthorized => "A003",
            CalibError::AdbServerError(_) => "A004",
            CalibError::AdbCommandFailed(_) => "A005",
            CalibError::DeviceOffline(_) => "A006",
            CalibError::FileLimitExceeded { .. } => "B001",
            CalibError::CalibrationFileMissing(_) => "B002",
            CalibError::DatasetNotFound(_) => "B003",
            CalibError::ZipFileNotFound(_) => "B004",
            CalibError::WorkDirCreateFailed(_) => "B005",
            CalibError::XmlParseFailed(_) => "B006",
            CalibError::DatasetPullFailed => "C001",
            CalibError::TargetDetectionFailed { .. } => "C002",
            CalibError::TargetMeasurementError { .. } => "C003",
            CalibError::ReprojectionErrorExceeded => "C004",
            CalibError::CamCalibrationFailed(_) => "C005",
            CalibError::YamlConvertFailed => "C006",
            CalibError::CoverageVerifyFailed(_) => "C007",
            CalibError::ThresholdExceeded(_) => "C008",
            CalibError::CheckResultFailed(_) => "C009",
            CalibError::SfrVerifyFailed(_) => "C010",
            CalibError::ConfigError(_) => "D001",
            CalibError::PythonNotFound(_) => "D002",
            CalibError::CpuIdFailed(_) => "D003",
            CalibError::PushFailed(_) => "E001",
            CalibError::RebootFailed(_) => "E002",
            CalibError::BootTimeout => "E003",
            CalibError::OssUploadFailed(_) => "E004",
            CalibError::ApiReportFailed(_) => "E005",
            CalibError::Cancelled => "Z001",
            CalibError::Unknown(_) => "Z002",
        }
    }

    /// 给产线操作人员看的简短错误说明（不含技术细节）
    pub fn user_message(&self) -> String {
        match self {
            CalibError::DeviceNotFound => "设备未连接，请检查USB线".to_string(),
            CalibError::DeviceTimeout => "设备连接超时，请重新插拔设备".to_string(),
            CalibError::DeviceUnauthorized => "设备未授权，请在设备上允许USB调试".to_string(),
            CalibError::AdbServerError(_) => "ADB服务异常，请重启ADB服务".to_string(),
            CalibError::AdbCommandFailed(_) => "ADB命令执行失败".to_string(),
            CalibError::DeviceOffline(_) => "设备在测试中离线，请检查USB连接".to_string(),
            CalibError::FileLimitExceeded { .. } => {
                "标定结果文件过多，请清理历史文件".to_string()
            }
            CalibError::CalibrationFileMissing(_) => {
                "标定结果文件缺失，标定流程未完成".to_string()
            }
            CalibError::DatasetNotFound(_) => "数据集路径不存在".to_string(),
            CalibError::ZipFileNotFound(_) => "标定结果压缩包不存在".to_string(),
            CalibError::WorkDirCreateFailed(_) => "创建工作目录失败，请检查磁盘空间".to_string(),
            CalibError::XmlParseFailed(_) => "标定结果文件解析失败".to_string(),
            CalibError::DatasetPullFailed => "从设备拉取数据失败，请检查设备连接".to_string(),
            CalibError::TargetDetectionFailed { .. } => {
                "标定板检测失败，请检查拍摄图片".to_string()
            }
            CalibError::TargetMeasurementError { actual, tolerance } => {
                format!(
                    "标定板尺寸偏差过大 (误差{:.3}mm > 容差{:.3}mm)，请检查标定板",
                    actual, tolerance
                )
            }
            CalibError::ReprojectionErrorExceeded => {
                "标定重投影误差过大，请检查拍摄图片质量".to_string()
            }
            CalibError::CamCalibrationFailed(detail) => {
                if detail.is_empty() {
                    "摄像头标定计算失败".to_string()
                } else {
                    format!("摄像头标定失败: {}", detail)
                }
            }
            CalibError::YamlConvertFailed => "标定文件转换失败".to_string(),
            CalibError::CoverageVerifyFailed(detail) => {
                format!("覆盖率验证未通过: {}", detail)
            }
            CalibError::ThresholdExceeded(detail) => {
                format!("标定参数不合格: {}", detail)
            }
            CalibError::CheckResultFailed(detail) => {
                format!("高通标定判定未通过: {}", detail)
            }
            CalibError::SfrVerifyFailed(detail) => {
                format!("清晰度验证未通过: {}", detail)
            }
            CalibError::ConfigError(_) => "配置参数错误".to_string(),
            CalibError::PythonNotFound(_) => "Python运行环境未找到".to_string(),
            CalibError::CpuIdFailed(_) => "设备识别失败".to_string(),
            CalibError::PushFailed(_) => "推送文件到设备失败".to_string(),
            CalibError::RebootFailed(_) => "设备重启失败".to_string(),
            CalibError::BootTimeout => "设备重启后未正常启动".to_string(),
            CalibError::OssUploadFailed(_) => "标定结果上传失败".to_string(),
            CalibError::ApiReportFailed(_) => "标定结果上报失败".to_string(),
            CalibError::Cancelled => "标定测试已取消".to_string(),
            CalibError::Unknown(_) => "发生未知错误，请联系技术支持".to_string(),
        }
    }

    /// 给技术人员看的详细错误信息
    pub fn detail(&self) -> Option<String> {
        match self {
            CalibError::AdbServerError(msg)
            | CalibError::AdbCommandFailed(msg)
            | CalibError::DeviceOffline(msg)
            | CalibError::CalibrationFileMissing(msg)
            | CalibError::DatasetNotFound(msg)
            | CalibError::ZipFileNotFound(msg)
            | CalibError::WorkDirCreateFailed(msg)
            | CalibError::XmlParseFailed(msg)
            | CalibError::ConfigError(msg)
            | CalibError::PythonNotFound(msg)
            | CalibError::CpuIdFailed(msg)
            | CalibError::PushFailed(msg)
            | CalibError::RebootFailed(msg)
            | CalibError::OssUploadFailed(msg)
            | CalibError::ApiReportFailed(msg)
            | CalibError::Unknown(msg)
            | CalibError::CamCalibrationFailed(msg)
            | CalibError::CoverageVerifyFailed(msg)
            | CalibError::ThresholdExceeded(msg)
            | CalibError::CheckResultFailed(msg)
            | CalibError::SfrVerifyFailed(msg) => Some(msg.clone()),
            CalibError::TargetDetectionFailed { detail } => Some(detail.clone()),
            CalibError::TargetMeasurementError { actual, tolerance } => Some(format!(
                "标定板测量误差 {:.3}mm 超过容差 {:.3}mm",
                actual, tolerance
            )),
            CalibError::FileLimitExceeded { limit, current } => Some(format!(
                "文件数量 {}/{} 超过上限",
                current, limit
            )),
            _ => None,
        }
    }

    /// 建议的解决方案
    pub fn suggestion(&self) -> &'static str {
        match self {
            CalibError::DeviceNotFound
            | CalibError::DeviceTimeout
            | CalibError::DeviceOffline(_) => "请检查USB线是否松动，重新插拔设备后重试",

            CalibError::DeviceUnauthorized => "请在设备弹出的USB调试授权对话框中点击\"允许\"",

            CalibError::AdbServerError(_) => "请执行 `adb kill-server && adb start-server` 后重试",

            CalibError::AdbCommandFailed(_) => "请检查ADB环境是否正常",

            CalibError::FileLimitExceeded { .. } => "请清理 /home/ssnwt/work/skycalib/CalibratResult/ 目录下的历史文件",

            CalibError::CalibrationFileMissing(_) => "标定流程未完成即终止，请重新执行标定",

            CalibError::DatasetNotFound(_) | CalibError::DatasetPullFailed => {
                "请检查设备连接状态，确认设备上有标定数据"
            }

            CalibError::WorkDirCreateFailed(_) => "请检查磁盘空间和目录权限",

            CalibError::TargetDetectionFailed { .. }
            | CalibError::ReprojectionErrorExceeded => {
                "请检查: 1) 拍摄图片是否清晰 2) 标定板是否完整出现在画面中 3) 光照是否充足"
            }

            CalibError::TargetMeasurementError { .. } => {
                "请检查: 1) 标定板是否变形或损坏 2) 标定板尺寸是否准确 3) 重新测量标定板实际尺寸"
            }

            CalibError::CamCalibrationFailed(_) => {
                "请检查拍摄数据集质量，确认所有摄像头图片均包含完整的标定板"
            }

            CalibError::YamlConvertFailed => "请检查标定结果文件是否完整",

            CalibError::CoverageVerifyFailed(_) => {
                "请检查摄像头安装位置，确认所有摄像头视角覆盖标定区域"
            }

            CalibError::ThresholdExceeded(_) => "标定参数未达到合格标准，请检查设备硬件",

            CalibError::CheckResultFailed(_) => "高通标定判定未通过，请根据具体失败项排查",

            CalibError::SfrVerifyFailed(_) => "请检查摄像头清晰度，确认镜头无污损、对焦正确",

            CalibError::ConfigError(_) => "请检查配置参数是否有效",

            CalibError::PythonNotFound(_) => "请确保系统已安装 python3",

            CalibError::PushFailed(_) | CalibError::RebootFailed(_) | CalibError::BootTimeout => {
                "请检查设备连接状态，确认设备未在测试中断开"
            }

            CalibError::OssUploadFailed(_) | CalibError::ApiReportFailed(_) => {
                "请检查网络连接，确认可访问OSS和API服务"
            }

            CalibError::Cancelled => "测试被取消，如需重新测试请点击启动按钮",

            _ => "请联系技术支持排查",
        }
    }

    /// 判断是否为产线操作问题（非系统bug）
    pub fn is_operational_error(&self) -> bool {
        matches!(
            self,
            CalibError::DeviceNotFound
                | CalibError::DeviceTimeout
                | CalibError::DeviceUnauthorized
                | CalibError::DeviceOffline(_)
                | CalibError::FileLimitExceeded { .. }
                | CalibError::TargetDetectionFailed { .. }
                | CalibError::TargetMeasurementError { .. }
                | CalibError::ReprojectionErrorExceeded
                | CalibError::CamCalibrationFailed(_)
                | CalibError::CoverageVerifyFailed(_)
                | CalibError::ThresholdExceeded(_)
                | CalibError::CheckResultFailed(_)
                | CalibError::SfrVerifyFailed(_)
        )
    }
}

/// 从Python脚本输出中解析标定错误
///
/// 这个函数负责将原始的Python日志解析为结构化的 CalibError，
/// 避免将大量原始日志直接展示给用户。
pub fn parse_python_calib_error(script_name: &str, logs: &[String]) -> CalibError {
    let full_log = logs.join("\n");

    match script_name {
        "ProcessCam.py" => {
            // 标定工具缺少执行权限
            if full_log.contains("PermissionError")
                && full_log.contains("Permission denied")
            {
                if let Some(path_start) = full_log.find("Permission denied: '") {
                    let path = &full_log[path_start + 20..];
                    if let Some(path_end) = path.find('\'') {
                        let tool_path = &path[..path_end];
                        return CalibError::CamCalibrationFailed(format!(
                            "标定工具缺少执行权限: {}，请执行 chmod +x {}",
                            tool_path, tool_path
                        ));
                    }
                }
                return CalibError::CamCalibrationFailed(
                    "标定工具缺少执行权限，请执行 chmod +x".to_string()
                );
            }

            // 标定板测量误差过大
            if let Some(caps) = regex::Regex::new(
                r"measurement error of\s+([\d.]+)mm\s*>\s*tolerance\s+([\d.]+)mm",
            )
            .unwrap()
            .captures(&full_log)
            {
                let actual = caps[1].parse().unwrap_or(0.0);
                let tolerance = caps[2].parse().unwrap_or(0.1);
                return CalibError::TargetMeasurementError { actual, tolerance };
            }

            // 标定板检测失败（特征点不足等）
            if full_log.contains("detection failed")
                || full_log.contains("no corners")
                || full_log.contains("failed to detect")
                || full_log.contains("Checkerboard detection")
                || full_log.contains("not enough images")
            {
                let detail = extract_python_error_message(&full_log)
                    .unwrap_or_else(|| "标定板特征点检测失败".to_string());
                return CalibError::TargetDetectionFailed { detail };
            }

            // 重投影误差过大
            if full_log.contains("reprojection error")
                || full_log.contains("RMS")
                || full_log.contains("residual too large")
            {
                return CalibError::ReprojectionErrorExceeded;
            }

            // 通用标定失败，优先提取 status:error + 后面的中文描述
            let reason = extract_python_error_message(&full_log)
                .unwrap_or_else(|| "标定算法执行失败".to_string());
            CalibError::CamCalibrationFailed(reason)
        }

        "DevicePull.py" => {
            let reason = extract_failure_reason(&full_log)
                .unwrap_or_else(|| "从设备拉取标定数据失败".to_string());
            if reason.len() < 50 {
                CalibError::DatasetPullFailed
            } else {
                CalibError::CamCalibrationFailed(format!("数据拉取: {}", reason))
            }
        }

        "ConvertSlamYaml.py" => CalibError::YamlConvertFailed,

        "parse_calib.py" => {
            let reason = extract_failure_reason(&full_log)
                .unwrap_or_else(|| "标定结果判定失败".to_string());
            CalibError::CheckResultFailed(reason)
        }

        _ => {
            let reason = if full_log.len() > 200 {
                format!("{}...", &full_log[..200])
            } else {
                full_log
            };
            CalibError::Unknown(format!("{} 执行失败: {}", script_name, reason))
        }
    }
}

/// 从Python脚本输出中提取用户友好的错误信息
/// 优先提取 status:error + 后面的中文描述，其次提取 Failure reason
fn extract_python_error_message(log: &str) -> Option<String> {
    // 优先提取 "status:error + xxx"（Python脚本中的中文错误提示）
    if let Some(idx) = log.find("status:error +") {
        let start = idx + "status:error +".len();
        let rest = &log[start..];
        let reason = rest
            .lines()
            .map(|l| l.trim())
            .find(|l| !l.is_empty())
            .unwrap_or("");
        if !reason.is_empty() && reason.len() < 500 {
            return Some(reason.to_string());
        }
    }

    // 其次提取 "Failure reason: xxx"
    if let Some(idx) = log.find("Failure reason:") {
        let start = idx + "Failure reason:".len();
        let rest = &log[start..];
        let reason = rest
            .lines()
            .map(|l| l.trim())
            .find(|l| !l.is_empty())
            .unwrap_or("");
        if !reason.is_empty() && reason.len() < 500 {
            return Some(reason.to_string());
        }
    }

    extract_failure_reason(log)
}

/// 从Python输出中提取 Failure reason 或关键错误信息
fn extract_failure_reason(log: &str) -> Option<String> {
    // 尝试提取 "Failure reason: xxx"
    if let Some(idx) = log.find("Failure reason:") {
        let start = idx + "Failure reason:".len();
        let rest = &log[start..];
        let reason = rest
            .lines()
            .map(|l| l.trim())
            .find(|l| !l.is_empty())
            .unwrap_or("");
        if !reason.is_empty() && reason.len() < 500 {
            return Some(reason.to_string());
        }
    }

    // 尝试提取 "Error: xxx"
    if let Some(idx) = log.find("Error:") {
        let start = idx + "Error:".len();
        let rest = &log[start..];
        let reason = rest
            .lines()
            .map(|l| l.trim())
            .find(|l| !l.is_empty())
            .unwrap_or("");
        if !reason.is_empty() && reason.len() < 500 {
            return Some(reason.to_string());
        }
    }

    // 尝试提取 "Exception: xxx"
    if let Some(idx) = log.find("Exception:") {
        let start = idx + "Exception:".len();
        let rest = &log[start..];
        let reason = rest
            .lines()
            .map(|l| l.trim())
            .find(|l| !l.is_empty())
            .unwrap_or("");
        if !reason.is_empty() && reason.len() < 500 {
            return Some(reason.to_string());
        }
    }

    None
}

#[derive(Error, Debug, Clone, Serialize, Deserialize)]
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

impl AdbError {
    /// 将 AdbError 转换为对应的 CalibError
    pub fn to_calib_error(&self) -> CalibError {
        match self {
            AdbError::DeviceNotFound | AdbError::NoDevices => CalibError::DeviceNotFound,
            AdbError::DeviceUnauthorized => CalibError::DeviceUnauthorized,
            AdbError::PermissionDenied => CalibError::AdbCommandFailed("ADB权限不足".to_string()),
            AdbError::Timeout => CalibError::DeviceTimeout,
            AdbError::ServerError(msg) => CalibError::AdbServerError(msg.clone()),
            AdbError::ShellFailed(msg) => CalibError::AdbCommandFailed(msg.clone()),
            AdbError::PushFailed(msg) => CalibError::PushFailed(msg.clone()),
            AdbError::PullFailed(_msg) => CalibError::DatasetPullFailed,
            AdbError::CommandFailed(msg) => CalibError::AdbCommandFailed(msg.clone()),
            AdbError::CpuIdFailed(msg) => CalibError::CpuIdFailed(msg.clone()),
            AdbError::Unknown(msg) => CalibError::Unknown(msg.clone()),
        }
    }
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
