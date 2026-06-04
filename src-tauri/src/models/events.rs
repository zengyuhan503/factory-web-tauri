use crate::error::CalibError;
use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StepEvent {
    pub slot_id: u8,
    pub step: String,
    pub step_name: String,
    pub progress: u8,
    pub hint: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogEvent {
    pub slot_id: u8,
    pub message: String,
    pub level: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompleteEvent {
    pub slot_id: u8,
    pub success: bool,
    pub message: String,
    pub oss_url: Option<String>,
}

/// 结构化错误事件，提供友好的错误展示
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorEvent {
    pub slot_id: u8,
    /// 错误码，如 "C003"
    pub code: String,
    /// 给用户看的简短错误说明
    pub message: String,
    /// 详细技术信息（可为空）
    pub detail: Option<String>,
    /// 建议的解决方案
    pub suggestion: String,
    /// 是否为产线操作问题（非系统bug）
    pub is_operational: bool,
}

impl ErrorEvent {
    pub fn from_calib_error(slot_id: u8, err: &CalibError) -> Self {
        Self {
            slot_id,
            code: err.code().to_string(),
            message: err.user_message(),
            detail: err.detail(),
            suggestion: err.suggestion().to_string(),
            is_operational: err.is_operational_error(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceConnectedEvent {
    pub slot_id: u8,
    pub serial: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceDisconnectedEvent {
    pub slot_id: u8,
}

pub fn emit_step_event(slot_id: u8, step: &str, step_name: &str, progress: u8, hint: &str) -> Value {
    serde_json::json!({
        "slot_id": slot_id,
        "step": step,
        "step_name": step_name,
        "progress": progress,
        "hint": hint,
    })
}

pub fn emit_complete_event(slot_id: u8, success: bool, message: &str, oss_url: Option<&str>) -> Value {
    serde_json::json!({
        "slot_id": slot_id,
        "success": success,
        "message": message,
        "oss_url": oss_url,
    })
}

pub fn emit_error_event(slot_id: u8, message: &str) -> Value {
    serde_json::json!({
        "slot_id": slot_id,
        "message": message,
    })
}
