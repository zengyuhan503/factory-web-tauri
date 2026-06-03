use crate::adapters::adb::AdbExecutor;
use crate::adapters::http_client::OssUploader;
use crate::adapters::python_runner::{CheckStatus, PythonRunner};
use crate::adapters::sfr_runner::SfrRunner;
use crate::models::{CalibResult, CalibStep, DeviceConfig, ThresholdConfig};
use crate::utils::logger::DeviceTestLogger;
use crate::utils::paths::get_device_work_dir;
use crate::utils::verify::{check_thresholds, verify_coverage};
use std::path::Path;
use std::sync::Arc;
use tauri::Manager;
use tokio::time::{sleep, Duration};

pub struct CalibrationEngine {
    slot_id: u8,
    serial: String,
    cpu_id: String,
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
        cpu_id: String,
        config: DeviceConfig,
        resource_dir: std::path::PathBuf,
        logger: Option<DeviceTestLogger>,
    ) -> Self {
        Self {
            slot_id,
            serial: serial.clone(),
            cpu_id,
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

        let work_dir = get_device_work_dir(&self.cpu_id);
        self.log_action("文件系统", &format!("创建工作目录: {:?}", work_dir));
        std::fs::create_dir_all(&work_dir).map_err(|e| {
            crate::error::CalibError::WorkDirCreateFailed(e.to_string())
        })?;

        // 2. 文件数量检查
        self.log_info(&format!("检查标定文件数量上限: {}", self.config.file_max));
        self.check_file_limit().await?;

        // 3. SFR 清晰度标定验证
        // 3.1 SfrPull - 拉取清晰度标定文件
        self.log_step_start(CalibStep::SfrPull);
        self.emit_step(CalibStep::SfrPull, &app).await;
        let sfr_runner = SfrRunner::new(serial.clone(), self.resource_dir.clone());
        let sfr_image_dir = match sfr_runner
            .pull_sfr_files(&work_dir, &self.cpu_id, |log| {
                let _ = app.emit_all(
                    "device:log",
                    serde_json::json!({
                        "slot_id": self.slot_id,
                        "message": log,
                        "level": "info",
                    }),
                );
                if let Some(ref logger) = self.logger {
                    logger.python_log(log);
                }
            })
            .await
        {
            Ok(dir) => {
                self.log_step_end(CalibStep::SfrPull, true);
                self.log_info(&format!("SFR 文件拉取成功: {:?}", dir));
                dir
            }
            Err(e) => {
                self.log_step_end(CalibStep::SfrPull, false);
                self.log_calib_error(&e);
                return Err(e);
            }
        };

        // 3.2 SfrAnalyze - 运行清晰度分析
        self.log_step_start(CalibStep::SfrAnalyze);
        self.emit_step(CalibStep::SfrAnalyze, &app).await;
        let sfr_mean_min = self.config.sfr_mean_avg50_min.unwrap_or(0.18);
        let sfr_std_max = self.config.sfr_cam_std_max.unwrap_or(0.05);
        let sfr_result = match sfr_runner
            .analyze_sfr(
                &sfr_image_dir,
                sfr_mean_min,
                sfr_std_max,
                |log| {
                    let _ = app.emit_all(
                        "device:log",
                        serde_json::json!({
                            "slot_id": self.slot_id,
                            "message": log,
                            "level": "info",
                        }),
                    );
                    if let Some(ref logger) = self.logger {
                        logger.python_log(log);
                    }
                },
            )
            .await
        {
            Ok(result) => {
                // 检查 SFR 结果是否真正合格（脚本可能返回 Ok 但结果不合格）
                let sfr_pass = result.device_mean_avg50 >= sfr_mean_min
                    && result.device_std_avg50 <= sfr_std_max;

                if !sfr_pass {
                    let msg = format!(
                        "SFR 清晰度验证未通过: mean_avg50={:.4}(阈值≥{:.4}), std_avg50={:.6}(阈值≤{:.4}), 判级={}",
                        result.device_mean_avg50, sfr_mean_min,
                        result.device_std_avg50, sfr_std_max,
                        result.device_grade
                    );
                    self.log_error(&msg);
                    self.log_step_end(CalibStep::SfrAnalyze, false);
                    let err = crate::error::CalibError::SfrFailed(msg);
                    self.log_calib_error(&err);
                    return Err(err);
                }

                self.log_step_end(CalibStep::SfrAnalyze, true);
                self.log_info("清晰度标定验证通过");
                result
            }
            Err(e) => {
                self.log_step_end(CalibStep::SfrAnalyze, false);
                self.log_calib_error(&e);
                return Err(e);
            }
        };

        // 3.3 SfrReport - 生成清晰度验证报告（无论成功失败都生成）
        self.log_step_start(CalibStep::SfrReport);
        self.emit_step(CalibStep::SfrReport, &app).await;
        let report = crate::utils::sfr_report::SfrReportData::from_result(
            &self.serial,
            &self.cpu_id,
            &sfr_result,
        );
        match self.generate_and_push_sfr_report(&report, &sfr_image_dir, &work_dir, &app,
        ).await {
            Ok(_) => {
                self.log_step_end(CalibStep::SfrReport, true);
                self.log_info("清晰度验证报告生成并推送完成");
            }
            Err(e) => {
                self.log_warn(&format!("清晰度验证报告生成失败（非致命）: {}", e));
                self.log_step_end(CalibStep::SfrReport, false);
                // 报告生成失败不阻断后续流程
            }
        }

        // 4. DevicePull
        self.log_step_start(CalibStep::DevicePull);
        self.emit_step(CalibStep::DevicePull, &app).await;
        let dataset_path = match self.run_device_pull(&app).await {
            Ok(path) => {
                self.log_step_end(CalibStep::DevicePull, true);
                self.log_info(&format!("数据集路径: {}", path));
                self.log_info("等待文件系统同步...");
                sleep(Duration::from_millis(1000)).await;
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
                self.log_info("等待标定结果落盘...");
                sleep(Duration::from_millis(1000)).await;
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
                self.log_info("等待 YAML 文件写入完成...");
                sleep(Duration::from_millis(500)).await;
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
        let _ = app.emit_all(
            "device:step",
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
        let _ = app.emit_all(
            "device:complete",
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
                    let _ = app_clone.emit_all(
                        "device:log",
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
                    let _ = app_clone.emit_all(
                        "device:log",
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
                let _ = app_clone.emit_all(
                    "device:log",
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
                let _ = app_clone.emit_all(
                    "device:log",
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

        // 等待文件完全写入设备存储
        self.log_info("等待设备文件系统同步...");
        sleep(Duration::from_millis(500)).await;

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

    /// 生成 SFR 报告并推回设备
    async fn generate_and_push_sfr_report(
        &self,
        report: &crate::utils::sfr_report::SfrReportData,
        image_dir: &std::path::Path,
        work_dir: &std::path::Path,
        app: &tauri::AppHandle,
    ) -> Result<(), String> {
        // 报告统一输出到 sfr 子目录中
        let report_dir = work_dir.join("sfr");

        // 生成 JSON 报告
        let json_path = crate::utils::sfr_report::generate_json_report(report, &report_dir)
            .map_err(|e| format!("生成 JSON 失败: {}", e))?;
        self.log_info(&format!("SFR JSON 报告已生成: {}", json_path));

        // 生成 Text 报告
        let txt_path = crate::utils::sfr_report::generate_text_report(report, &report_dir)
            .map_err(|e| format!("生成 Text 失败: {}", e))?;
        self.log_info(&format!("SFR Text 报告已生成: {}", txt_path));

        // 生成 PDF 报告
        let pdf_path = crate::utils::sfr_report::generate_pdf_report(report, &report_dir, &self.resource_dir)
            .map_err(|e| format!("生成 PDF 失败: {}", e))?;
        self.log_info(&format!("SFR PDF 报告已生成: {}", pdf_path));

        // 等待报告文件完全落盘
        self.log_info("等待报告文件写入完成...");
        sleep(Duration::from_millis(500)).await;

        // 推回设备
        self.log_action("ADB", "推送 SFR 报告到设备");

        // 推送 JSON
        match self.adb.push(&json_path, "/sdcard/snapshot/", 30000).await {
            Ok(_) => self.log_info("SFR JSON 报告已推送"),
            Err(e) => self.log_warn(&format!("推送 JSON 失败: {}", e)),
        }

        // 推送 Text
        match self.adb.push(&txt_path, "/sdcard/snapshot/", 30000).await {
            Ok(_) => self.log_info("SFR Text 报告已推送"),
            Err(e) => self.log_warn(&format!("推送 Text 失败: {}", e)),
        }

        // 推送 PDF
        match self.adb.push(&pdf_path, "/sdcard/snapshot/", 30000).await {
            Ok(_) => self.log_info("SFR PDF 报告已推送"),
            Err(e) => self.log_warn(&format!("推送 PDF 失败: {}", e)),
        }

        // 推送图片
        for cam in &report.sfr.cameras {
            let img_path = image_dir.join(&cam.image);
            if img_path.exists() {
                match self.adb.push(
                    img_path.to_str().unwrap(), "/sdcard/snapshot/", 30000).await {
                    Ok(_) => {}
                    Err(e) => self.log_warn(&format!("推送图片 {} 失败: {}", cam.image, e)),
                }
            }
        }

        Ok(())
    }
}
