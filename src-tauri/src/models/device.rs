use serde::{Deserialize, Serialize, Serializer, Deserializer};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceInfo {
    pub serial: String,
    pub cpu_id: String,
    pub android_version: String,
    pub product_model: Option<String>,
    pub usb_port: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SlotStatus {
    Empty,
    Connected,
    Running,
    Success,
    Error,
}

#[derive(Debug, Clone)]
pub enum SlotResult {
    Pending,
    Pass,
    Fail { reason: String },
}

impl Serialize for SlotResult {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where S: Serializer,
    {
        let s = match self {
            SlotResult::Pending => "pending",
            SlotResult::Pass => "pass",
            SlotResult::Fail { .. } => "fail",
        };
        serializer.serialize_str(s)
    }
}

impl<'de> Deserialize<'de> for SlotResult {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where D: Deserializer<'de>,
    {
        let s = String::deserialize(deserializer)?;
        match s.as_str() {
            "pending" => Ok(SlotResult::Pending),
            "pass" => Ok(SlotResult::Pass),
            "fail" => Ok(SlotResult::Fail { reason: String::new() }),
            _ => Err(serde::de::Error::custom("invalid slot result")),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceSlot {
    pub slot_id: u8,
    pub serial: Option<String>,
    pub cpu_id: Option<String>,
    pub status: SlotStatus,
    pub progress: u8,
    pub step_name: String,
    pub hint: String,
    pub result: SlotResult,
}

impl Default for DeviceSlot {
    fn default() -> Self {
        Self {
            slot_id: 0,
            serial: None,
            cpu_id: None,
            status: SlotStatus::Empty,
            progress: 0,
            step_name: "待连接".to_string(),
            hint: "".to_string(),
            result: SlotResult::Pending,
        }
    }
}

impl DeviceSlot {
    pub fn new(slot_id: u8) -> Self {
        Self {
            slot_id,
            ..Default::default()
        }
    }

    pub fn reset(&mut self) {
        self.status = SlotStatus::Empty;
        self.progress = 0;
        self.step_name = "待连接".to_string();
        self.hint = "".to_string();
        self.result = SlotResult::Pending;
    }
}
