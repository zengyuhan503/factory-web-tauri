use crate::models::{CalibStatus, CalibStep, SlotStatus};

pub struct SlotState {
    pub status: SlotStatus,
    pub calib_status: CalibStatus,
    pub current_step: CalibStep,
    pub progress: u8,
    pub step_name: String,
    pub hint: String,
    pub cancel_token: Option<tokio_util::sync::CancellationToken>,
}

impl SlotState {
    pub fn new() -> Self {
        Self {
            status: SlotStatus::Empty,
            calib_status: CalibStatus::Idle,
            current_step: CalibStep::Idle,
            progress: 0,
            step_name: "待连接".to_string(),
            hint: "".to_string(),
            cancel_token: None,
        }
    }

    pub fn reset(&mut self) {
        self.status = SlotStatus::Empty;
        self.calib_status = CalibStatus::Idle;
        self.current_step = CalibStep::Idle;
        self.progress = 0;
        self.step_name = "待连接".to_string();
        self.hint = "".to_string();
        self.cancel_token = None;
    }

    pub fn transition_to(&mut self, step: CalibStep) {
        self.current_step = step;
        self.progress = step.progress();
        self.step_name = step.display_name().to_string();
        self.hint = step.hint().to_string();
        self.calib_status = CalibStatus::Running;
    }

    pub fn set_error(&mut self, message: &str) {
        self.calib_status = CalibStatus::Error;
        self.status = SlotStatus::Error;
        self.hint = message.to_string();
    }

    pub fn set_success(&mut self) {
        self.calib_status = CalibStatus::Success;
        self.status = SlotStatus::Success;
        self.progress = 100;
        self.step_name = "完成".to_string();
        self.hint = "标定完成".to_string();
    }

    pub fn is_cancelled(&self) -> bool {
        self.cancel_token
            .as_ref()
            .map(|t| t.is_cancelled())
            .unwrap_or(false)
    }
}
