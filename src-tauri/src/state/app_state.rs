use crate::models::{AppConfig, DeviceSlot};
use std::sync::Arc;
use tokio::sync::Mutex;

#[derive(Clone)]
pub struct AppState {
    pub slots: Arc<Mutex<Vec<DeviceSlot>>>,
    pub config: Arc<Mutex<AppConfig>>,
}

impl AppState {
    pub fn new(slot_count: u8) -> Self {
        let mut slots = Vec::with_capacity(slot_count as usize);
        for i in 0..slot_count {
            slots.push(DeviceSlot::new(i));
        }

        Self {
            slots: Arc::new(Mutex::new(slots)),
            config: Arc::new(Mutex::new(AppConfig::default())),
        }
    }
}
