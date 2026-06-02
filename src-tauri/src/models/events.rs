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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorEvent {
    pub slot_id: u8,
    pub message: String,
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
