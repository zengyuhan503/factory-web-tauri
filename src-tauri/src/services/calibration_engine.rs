use crate::adapters::adb::AdbExecutor;
use crate::adapters::http_client::OssUploader;
use crate::adapters::python_runner::{CheckStatus, PythonRunner};
use crate::models::{CalibResult, CalibStep, DeviceConfig, ThresholdConfig};
use crate::utils::logger::DeviceTestLogger;
use crate::utils::paths::get_device_work_dir;
use crate::utils::verify::{check_thresholds, verify_coverage};
use std::path::Path;
use std::sync::Arc;
use tauri::Emitter;
use tokio::time::{sleep, Duration};

pub struct CalibrationEngine {
    slot_id: u8,
    serial: String,
    config: DeviceConfig,
    resource_dir: std::path::PathBuf,
    adb: AdbExecutor,
    oss: OssUploader,
    logger: Option<Arc<DeviceTestLogger>>,
}

impl CalibrationEngine {
    pub fn new(
        slot_id: u8,
        serial: String,
        config: DeviceConfig,
        resource_dir: std::path::PathBuf,
        logger: Option<DeviceTestLogger>,
    ) -> Self {
        Self {
            slot_id,
            serial: serial.clone(),
            config,
            resource_dir,
            adb: AdbExecutor::new(serial),
            oss: OssUploader::new(),
            logger: logger.map(Arc::new),
        }
    }

    fn log_info(&self, message: &str) {
        if let Some(ref logger) = self.logger {
            logger.info(message);
        }
    }

    fn log_warn(&self, message: &str) {
        if let Some(ref logger) = self.logger {
            logger.warn(message);
        }
    }

    fn log_error(&self, message: &str) {
        if let Some(ref logger) = self.logger {
            logger.error(message);
        }
    }

    fn log_action(&self, action_name: &str, detail: &str) {
        if let Some(ref logger) = self.logger {
            logger.action(action_name, detail);
        }
    }

    fn log_python(&self, message: &str) {
        if let Some(ref logger) = self.logger {
            logger.python_log(message);
        }
    }

    fn log_step_start(&self, step: CalibStep) {
        if let Some(ref logger) = self.logger {
            logger.step_start(step.display_name(), step as u8);
        }
    }

    fn log_step_end(&self, step: CalibStep, success: bool) {
        if let Some(ref logger) = self.logger {
            logger.step_end(step.display_name(), success);
        }
    }

    fn log_calib_error(&self, err: &crate::error::CalibError) {
        if let Some(ref logger) = self.logger {
            logger.log_error(err);
        }
    }

    fn log_result(&self, success: bool, message: &str) {
        if let Some(ref logger) = self.logger {
            logger.result(success, message);
        }
    }

    pub async fn run(
        &self,
        app: tauri::AppHandle,
    ) -> Result<CalibResult, crate::error::CalibError> {
        let serial = self.serial.clone();
        self.log_info(&format!("[槽位{}] 开始标定流程，设备: {}", self.slot_id, serial));

        // 1. 等待设备
        self.log_action("ADB", "等待设备连接");
        self.adb
            .wait_for_device(30000)
            .await
            .map_err(crate::error::CalibError::Adb)?;
        self.log_info("设备已连接并就绪");

        let work_dir = get_device_work_dir(&serial);
        self.log_action("文件系统", &format!("创建工作目录: {:?}", work_dir));
        std::fs::create_dir_all(&work_dir).map_err(|e| {
            crate::error::CalibError::WorkDirCreateFailed(e.to_string())
        })?;

        // 2. 文件数量检查
        self.log_info(&format!("检查标定文件数量上限: {}", self.config.file_max));
        self.check_file_limit().await?;

        // 3. DevicePull
        self.log_step_start(CalibStep::DevicePull);
        self.emit_step(CalibStep::DevicePull, &app).await;
        let dataset_path = match self.run_device_pull(&app).await {
            Ok(path) => {
                self.log_step_end(CalibStep::DevicePull, true);
                self.log_info(&format!("数据集路径: {}", path));
                path
            }
            Err(e) => {
                self.log_step_end(CalibStep::DevicePull, false);
                self.log_calib_error(&e);
                return Err(e);
            }
        };

        // 4. CAM Cali
        self.log_step_start(CalibStep::CamCali);
        self.emit_step(CalibStep::CamCali, &app).await;
        match self.run_cam_cali(&dataset_path, &app).await {
            Ok(_) => {
                self.log_step_end(CalibStep::CamCali, true);
            }
            Err(e) => {
                self.log_step_end(CalibStep::CamCali, false);
                self.log_calib_error(&e);
                return Err(e);
            }
        }

        // 5. ConvertSlamYaml
        self.log_step_start(CalibStep::ConvertYaml);
        self.emit_step(CalibStep::ConvertYaml, &app).await;
        match self.run_convert_yaml(&dataset_path, &app).await {
            Ok(_) => {
                self.log_step_end(CalibStep::ConvertYaml, true);
            }
            Err(e) => {
                self.log_step_end(CalibStep::ConvertYaml, false);
                self.log_calib_error(&e);
                return Err(e);
            }
        }

        // 6. VerifyCoverage
        self.log_step_start(CalibStep::VerifyCoverage);
        self.emit_step(CalibStep::VerifyCoverage, &app).await;
        let verify_data = match verify_coverage(&dataset_path, self.config.is_rgb, self.config.is_tof) {
            Ok(data) => {
                self.log_step_end(CalibStep::VerifyCoverage, true);
                self.log_info(&format!("覆盖率验证数据: {:?}", data));
                data
            }
            Err(e) => {
                self.log_step_end(CalibStep::VerifyCoverage, false);
                let err = crate::error::CalibError::VerifyFailed(e.clone());
                self.log_calib_error(&err);
                return Err(err);
            }
        };

        let thresholds = ThresholdConfig {
            dof: self.config.thresholds.dof,
            rgb: self.config.thresholds.rgb,
            tof: self.config.thresholds.tof,
        };

        self.log_info(&format!("阈值配置 - DOF: {:?}, RGB: {:?}, TOF: {:?}",
            thresholds.dof, thresholds.rgb, thresholds.tof));

        if !check_thresholds(&verify_data, &thresholds) {
            self.log_error("标定参数超出阈值限制");
            let err = crate::error::CalibError::ThresholdExceeded;
            self.log_calib_error(&err);
            return Err(err);
        }
        self.log_info("阈值检查通过");

        // 7. CheckResult
        self.log_step_start(CalibStep::CheckResult);
        self.emit_step(CalibStep::CheckResult, &app).await;
        let check_result = match self.run_check_result(&dataset_path, &app).await {
            Ok(result) => {
                self.log_step_end(CalibStep::CheckResult, true);
                result
            }
            Err(e) => {
                self.log_step_end(CalibStep::CheckResult, false);
                self.log_calib_error(&e);
                return Err(e);
            }
        };

        match check_result.status {
            CheckStatus::Pass => {
                self.log_info("高通标定判定通过");
            }
            CheckStatus::Fail => {
                let msg = if check_result.failures.is_empty() {
                    "高通标定判定失败".to_string()
                } else {
                    format!("高通标定判定失败: {}", check_result.failures.join("; "))
                };
                self.log_error(&msg);
                let err = crate::error::CalibError::CheckFailed(msg);
                self.log_calib_error(&err);
                return Err(err);
            }
            CheckStatus::Error => {
                let msg = "标定结果判定执行错误".to_string();
                self.log_error(&msg);
                let err = crate::error::CalibError::CheckFailed(msg);
                self.log_calib_error(&err);
                return Err(err);
            }
        }

        // 8. PushAndUpload
        self.log_step_start(CalibStep::PushAndUpload);
        self.emit_step(CalibStep::PushAndUpload, &app).await;
        let oss_url = match self.push_and_upload(&dataset_path, &serial).await {
            Ok(url) => {
                self.log_step_end(CalibStep::PushAndUpload, true);
                url
            }
            Err(e) => {
                self.log_step_end(CalibStep::PushAndUpload, false);
                self.log_calib_error(&e);
                return Err(e);
            }
        };

        // 完成
        self.log_step_start(CalibStep::Complete);
        self.emit_step(CalibStep::Complete, &app).await;
        self.emit_complete(true, &oss_url, &app).await;
        self.log_result(true, &format!("标定成功，OSS链接: {}", oss_url));

        Ok(CalibResult {
            success: true,
            message: "标定成功".to_string(),
            oss_url: Some(oss_url),
        })
    }

    async fn emit_step(&self, step: CalibStep, app: &tauri::AppHandle) {
        let _ = app.emit(
            &format!("device:{}:step", self.slot_id),
            serde_json::json!({
                "slot_id": self.slot_id,
                "step": format!("{:?}", step),
                "step_name": step.display_name(),
                "progress": step.progress(),
                "hint": step.hint(),
            }),
        );
    }

    async fn emit_complete(&self, success: bool, oss_url: &str, app: &tauri::AppHandle) {
        let _ = app.emit(
            &format!("device:{}:complete", self.slot_id),
            serde_json::json!({
                "slot_id": self.slot_id,
                "success": success,
                "message": if success { "标定成功" } else { "标定失败" },
                "oss_url": oss_url,
            }),
        );
    }

    async fn check_file_limit(&self) -> Result<(), crate::error::CalibError> {
        let base_dir = crate::utils::paths::get_calib_result_base_dir();
        if let Ok(entries) = std::fs::read_dir(&base_dir) {
            let count = entries.count();
            if count > self.config.file_max as usize {
                self.log_error(&format!(
                    "标定文件数量超过上限 {}，当前 {}",
                    self.config.file_max, count
                ));
                return Err(crate::error::CalibError::FileLimitExceeded {
                    limit: self.config.file_max,
                    current: count,
                });
            }
            self.log_info(&format!("当前标定文件数量: {}/{}" , count, self.config.file_max));
        }
        Ok(())
    }

    async fn run_device_pull(
        &self,
        app: &tauri::AppHandle,
    ) -> Result<String, crate::error::CalibError> {
        let runner = PythonRunner::new(self.serial.clone(), self.resource_dir.clone());
        let slot_id = self.slot_id;
        let app_clone = app.clone();
        let logger_arc = self.logger.clone();

        let result = runner
            .run_device_pull(
                self.config.is_rgb,
                &self.config.qvr_type,
                move |log| {
                    let _ = app_clone.emit(
                        &format!("device:{}:log", slot_id),
                        serde_json::json!({
                            "slot_id": slot_id,
                            "message": log,
                            "level": "info",
                        }),
                    );
                    if let Some(ref logger) = logger_arc {
                        logger.python_log(log);
                    }
                },
            )
            .await
            .map_err(crate::error::CalibError::Python)?;

        Ok(result)
    }

    async fn run_cam_cali(
        &self,
        dataset_path: &str,
        app: &tauri::AppHandle,
    ) -> Result<(), crate::error::CalibError> {
        let runner = PythonRunner::new(self.serial.clone(), self.resource_dir.clone());
        let slot_id = self.slot_id;
        let app_clone = app.clone();
        let logger_arc = self.logger.clone();

        runner
            .run_cam_cali(
                self.config.is_rgb,
                &self.config.qvr_type,
                dataset_path,
                move |log| {
                    let _ = app_clone.emit(
                        &format!("device:{}:log", slot_id),
                        serde_json::json!({
                            "slot_id": slot_id,
                            "message": log,
                            "level": "info",
                        }),
                    );
                    if let Some(ref logger) = logger_arc {
                        logger.python_log(log);
                    }
                },
            )
            .await
            .map_err(crate::error::CalibError::Python)?;

        Ok(())
    }

    async fn run_convert_yaml(
        &self,
        dataset_path: &str,
        app: &tauri::AppHandle,
    ) -> Result<(), crate::error::CalibError> {
        let runner = PythonRunner::new(self.serial.clone(), self.resource_dir.clone());
        let slot_id = self.slot_id;
        let app_clone = app.clone();
        let logger_arc = self.logger.clone();

        runner
            .run_convert_yaml(dataset_path, move |log| {
                let _ = app_clone.emit(
                    &format!("device:{}:log", slot_id),
                    serde_json::json!({
                        "slot_id": slot_id,
                        "message": log,
                        "level": "info",
                    }),
                );
                if let Some(ref logger) = logger_arc {
                    logger.python_log(log);
                }
            })
            .await
            .map_err(crate::error::CalibError::Python)?;

        Ok(())
    }

    async fn run_check_result(
        &self,
        dataset_path: &str,
        app: &tauri::AppHandle,
    ) -> Result<crate::adapters::python_runner::CheckResult, crate::error::CalibError> {
        let runner = PythonRunner::new(self.serial.clone(), self.resource_dir.clone());
        let slot_id = self.slot_id;
        let app_clone = app.clone();
        let logger_arc = self.logger.clone();

        let result = runner
            .run_check_result(dataset_path, move |log| {
                let _ = app_clone.emit(
                    &format!("device:{}:log", slot_id),
                    serde_json::json!({
                        "slot_id": slot_id,
                        "message": log,
                        "level": "info",
                    }),
                );
                if let Some(ref logger) = logger_arc {
                    logger.python_log(log);
                }
            })
            .await
            .map_err(crate::error::CalibError::Python)?;

        Ok(result)
    }

    async fn push_and_upload(
        &self,
        dataset_path: &str,
        serial: &str,
    ) -> Result<String, crate::error::CalibError> {
        let dir = Path::new(dataset_path)
            .parent()
            .map(|p| p.to_string_lossy().to_string())
            .unwrap_or_else(|| dataset_path.to_string());

        // 推送 device_calibration.xml
        let xml_path = format!("{}/device_calibration.xml", dir);
        self.log_action("文件推送", &format!("推送 {} 到 /data/local/tmp", xml_path));
        if Path::new(&xml_path).exists() {
            match self.adb.push(&xml_path, "/data/local/tmp", 30000).await {
                Ok(_) => {
                    self.log_info(&format!("标定文件推送成功: {}", xml_path));
                }
                Err(e) => {
                    let err = crate::error::CalibError::PushFailed(e.to_string());
                    self.log_calib_error(&err);
                    return Err(err);
                }
            }
        } else {
            self.log_warn(&format!("标定文件不存在: {}", xml_path));
            return Err(crate::error::CalibError::CalibrationFileMissing(xml_path));
        }

        // sync
        self.log_action("ADB", "执行 sync 命令");
        self.adb
            .shell("sync", 15000)
            .await
            .map_err(crate::error::CalibError::Adb)?;
        self.log_info("sync 完成");

        // reboot
        self.log_action("ADB", "执行 reboot 命令");
        match self.adb.reboot(15000).await {
            Ok(_) => {
                self.log_info("设备重启命令已发送");
            }
            Err(e) => {
                let err = crate::error::CalibError::RebootFailed(e.to_string());
                self.log_calib_error(&err);
                return Err(err);
            }
        }

        sleep(Duration::from_secs(2)).await;

        // wait for boot
        self.log_action("ADB", "等待设备重启完成");
        match self.adb.wait_for_boot(15000, 300).await {
            Ok(_) => {
                self.log_info("设备重启完成");
            }
            Err(e) => {
                let err = match e {
                    crate::error::AdbError::Timeout => crate::error::CalibError::BootTimeout,
                    _ => crate::error::CalibError::Adb(e),
                };
                self.log_calib_error(&err);
                return Err(err);
            }
        }

        // 上传 OSS
        let time = chrono::Local::now().format("%Y-%m-%d-%H-%M-%S").to_string();
        let zip_path = format!("{}/calibDetails.zip", dir);
        let file_name = format!("{}-{}.zip", serial, time);

        self.log_action("OSS上传", &format!("准备上传 {} 到 OSS", zip_path));

        if !Path::new(&zip_path).exists() {
            let err = crate::error::CalibError::ZipFileNotFound(zip_path);
            self.log_calib_error(&err);
            return Err(err);
        }

        let oss_url = match self
            .oss
            .upload_file(&zip_path, "calibDetails/", &file_name)
            .await
        {
            Ok(url) => {
                self.log_info(&format!("OSS上传成功: {}", url));
                url
            }
            Err(e) => {
                let err = crate::error::CalibError::OssUpload(e.to_string());
                self.log_calib_error(&err);
                return Err(err);
            }
        };

        // API 上报
        let brand = self.config.qvr_type.parse::<i32>().unwrap_or(0);
        self.log_action("API上报", &format!("上报标定结果, brand={}", brand));
        match self
            .oss
            .report_to_api(&oss_url, serial, &time, brand)
            .await
        {
            Ok(_) => {
                self.log_info("API上报成功");
            }
            Err(e) => {
                let err = crate::error::CalibError::ApiReport(e.to_string());
                self.log_calib_error(&err);
                return Err(err);
            }
        }

        Ok(oss_url)
    }
}
