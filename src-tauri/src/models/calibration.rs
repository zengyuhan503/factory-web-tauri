use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CalibStep {
    Idle = 0,
    SfrPull = 1,
    SfrAnalyze = 2,
    SfrReport = 3,
    DevicePull = 4,
    CamCali = 5,
    ConvertYaml = 6,
    VerifyCoverage = 7,
    CheckResult = 8,
    PushAndUpload = 9,
    Complete = 10,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CalibStatus {
    Idle,
    Running,
    Success,
    Error,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalibResult {
    pub success: bool,
    pub message: String,
    pub oss_url: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerifyData {
    pub dof: Option<Vec<f64>>,
    pub rgb: Option<Vec<f64>>,
    pub tof: Option<Vec<f64>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CheckResultData {
    pub status: CheckStatus,
    pub failures: Vec<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CheckStatus {
    Pass,
    Fail,
    Error,
}

impl CalibStep {
    pub fn display_name(&self) -> &'static str {
        match self {
            CalibStep::Idle => "待开始",
            CalibStep::SfrPull => "清晰度文件拉取",
            CalibStep::SfrAnalyze => "清晰度标定验证",
            CalibStep::SfrReport => "清晰度报告生成",
            CalibStep::DevicePull => "拉取设备数据",
            CalibStep::CamCali => "摄像头标定计算",
            CalibStep::ConvertYaml => "标定文件转换",
            CalibStep::VerifyCoverage => "覆盖率验证",
            CalibStep::CheckResult => "高通标定判定",
            CalibStep::PushAndUpload => "推送并上传",
            CalibStep::Complete => "完成",
        }
    }

    pub fn progress(&self) -> u8 {
        match self {
            CalibStep::Idle => 0,
            CalibStep::SfrPull => 8,
            CalibStep::SfrAnalyze => 15,
            CalibStep::SfrReport => 20,
            CalibStep::DevicePull => 25,
            CalibStep::CamCali => 40,
            CalibStep::ConvertYaml => 55,
            CalibStep::VerifyCoverage => 70,
            CalibStep::CheckResult => 85,
            CalibStep::PushAndUpload => 95,
            CalibStep::Complete => 100,
        }
    }

    pub fn hint(&self) -> &'static str {
        match self {
            CalibStep::Idle => "请连接设备后点击启动",
            CalibStep::SfrPull => "正在从设备拉取清晰度标定文件...",
            CalibStep::SfrAnalyze => "正在进行清晰度标定文件验证...",
            CalibStep::SfrReport => "正在生成清晰度验证报告...",
            CalibStep::DevicePull => "正在从设备拉取标定原始数据...",
            CalibStep::CamCali => "正在进行摄像头标定计算，请耐心等待...",
            CalibStep::ConvertYaml => "正在转换标定文件格式...",
            CalibStep::VerifyCoverage => "正在验证摄像头覆盖率...",
            CalibStep::CheckResult => "正在进行高通标定结果判定...",
            CalibStep::PushAndUpload => "正在推送标定文件并上传...",
            CalibStep::Complete => "标定完成",
        }
    }
}
