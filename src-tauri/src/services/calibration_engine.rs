use crate::adapters::adb::AdbExecutor;
use crate::adapters::http_client::OssUploader;
use crate::adapters::python_runner::{CheckStatus, CheckResultDetail, PythonRunner};
use crate::error::AdbError;
use crate::adapters::sfr_runner::SfrRunner;
use crate::models::{CalibResult, CalibStep, DeviceConfig, ThresholdConfig};
use crate::utils::logger::DeviceTestLogger;
use crate::utils::paths::get_device_work_dir;
use crate::utils::verify::verify_coverage;
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
        println!("等待设备连接...");
        self.log_action("ADB", "等待设备连接");
        self.adb
            .wait_for_device(30000)
            .await
            .map_err(|e| e.to_calib_error())?;
        self.log_info("设备已连接并就绪");

        let work_dir = get_device_work_dir(&self.cpu_id);
        self.log_action("文件系统", &format!("创建工作目录: {:?}", work_dir));
        std::fs::create_dir_all(&work_dir).map_err(|e| {
            crate::error::CalibError::WorkDirCreateFailed(e.to_string())
        })?;

        // 2. 文件数量检查
        println!("检查标定文件数量上限: {}", self.config.file_max);
        self.log_info(&format!("检查标定文件数量上限: {}", self.config.file_max));
        self.check_file_limit().await?;

        // 3. SFR 清晰度标定验证（可选）
        if self.config.enable_sfr {
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
            println!("开始清晰度分析...");
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
                        let err = crate::error::CalibError::SfrVerifyFailed(msg);
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
            println!("开始生成清晰度验证报告...");
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
        } else {
            self.log_info("SFR 清晰度测试已关闭，跳过清晰度验证步骤");
        }

        // 4. DevicePull
        println!("开始拉取数据集...");
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
        println!("dataset_path: {}", dataset_path);

        // 4. CAM Cali
        println!("dataset_path 开始摄像头标定...");
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
                let _ = self.generate_calib_failure_report(&e, &dataset_path, &app).await;
                return Err(e);
            }
        }

        // 5. ConvertSlamYaml
        println!("开始转换 SLAM YAML 文件...");
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
                let _ = self.generate_calib_failure_report(&e, &dataset_path, &app).await;
                return Err(e);
            }
        }

        // 6. VerifyCoverage
        println!("开始验证数据...");
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
                let err = crate::error::CalibError::CoverageVerifyFailed(e.clone());
                self.log_calib_error(&err);
                let _ = self.generate_calib_failure_report(&err, &dataset_path, &app).await;
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

        let (threshold_ok, failures) = crate::utils::verify::check_thresholds_detail(
            &verify_data, &thresholds, self.config.is_rgb, self.config.is_tof,
        );

        if !threshold_ok {
            let mut detail = String::from("覆盖率验证未通过:");
            for f in &failures {
                detail.push_str(&format!(
                    "\n  - {} 摄像头 [{}] 覆盖率 {:.1}% < 阈值 {:.1}%",
                    f.camera_type, f.camera_name, f.coverage, f.threshold
                ));
            }
            self.log_error(&detail);
            let err = crate::error::CalibError::ThresholdExceeded(detail);
            self.log_calib_error(&err);
            let _ = self.generate_calib_failure_report(&err, &dataset_path, &app).await;
            return Err(err);
        }
        self.log_info("阈值检查通过");

        // 7. CheckResult
        println!("开始检查标定结果...");
        self.log_step_start(CalibStep::CheckResult);
        self.emit_step(CalibStep::CheckResult, &app).await;
        let check_detail = match self.run_check_result_detail(&dataset_path, &app).await {
            Ok(detail) => {
                let success = detail.status == CheckStatus::Pass;
                self.log_step_end(CalibStep::CheckResult, success);
                detail
            }
            Err(e) => {
                self.log_step_end(CalibStep::CheckResult, false);
                self.log_calib_error(&e);
                // 尝试生成失败报告
                let _ = self.generate_calib_failure_report(&e, &dataset_path, &app).await;
                return Err(e);
            }
        };

        // 7.5 生成标定报告（无论通过/失败都生成）
        let report_result = self
            .generate_calib_report(&check_detail,
                &dataset_path,
                &app,
            )
            .await;
        match report_result {
            Ok(_) => self.log_info("标定报告生成完成"),
            Err(e) => self.log_warn(&format!("标定报告生成失败（非致命）: {}", e)),
        }

        match check_detail.status {
            CheckStatus::Pass => {
                self.log_info("高通标定判定通过");
            }
            CheckStatus::Fail => {
                let msg = if check_detail.failures.is_empty() {
                    "高通标定判定失败".to_string()
                } else {
                    format!("高通标定判定失败: {}", check_detail.failures.join("; "))
                };
                self.log_error(&msg);
                let err = crate::error::CalibError::CheckResultFailed(msg);
                self.log_calib_error(&err);
                return Err(err);
            }
            CheckStatus::Error => {
                let msg = "标定结果判定执行错误".to_string();
                self.log_error(&msg);
                let err = crate::error::CalibError::CheckResultFailed(msg);
                self.log_calib_error(&err);
                return Err(err);
            }
        }

        // 8. PushAndUpload
        println!("开始上传标定结果...");
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
            .await?;

        Ok(result)
    }

    /// 确保标定工具 XRCalib 有执行权限
    async fn ensure_calib_tool_executable(&self) {
        let xrcalib_path = self.resource_dir.join("tools").join("qvr_calib").join("XRCalib");
        if xrcalib_path.exists() {
            match tokio::process::Command::new("chmod")
                .arg("+x")
                .arg(&xrcalib_path)
                .output()
                .await
            {
                Ok(o) if o.status.success() => {
                    self.log_info(&format!("已设置标定工具执行权限: {:?}", xrcalib_path));
                }
                Ok(o) => {
                    let err = String::from_utf8_lossy(&o.stderr);
                    self.log_warn(&format!("设置标定工具权限失败: {}", err));
                }
                Err(e) => {
                    self.log_warn(&format!("无法执行 chmod: {}", e));
                }
            }
        } else {
            self.log_warn(&format!("标定工具不存在: {:?}", xrcalib_path));
        }
    }

    async fn run_cam_cali(
        &self,
        dataset_path: &str,
        app: &tauri::AppHandle,
    ) -> Result<(), crate::error::CalibError> {
        // 调用前先确保标定工具有执行权限
        self.ensure_calib_tool_executable().await;

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
            .await?;

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
            .await?;

        Ok(())
    }

    async fn run_check_result_detail(
        &self,
        dataset_path: &str,
        app: &tauri::AppHandle,
    ) -> Result<crate::adapters::python_runner::CheckResultDetail, crate::error::CalibError> {
        let runner = PythonRunner::new(self.serial.clone(), self.resource_dir.clone());
        let slot_id = self.slot_id;
        let app_clone = app.clone();
        let logger_arc = self.logger.clone();

        let result = runner
            .run_check_result_detail(dataset_path, move |log| {
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
            .await?;

        Ok(result)
    }

    async fn push_and_upload(
        &self,
        _dataset_path: &str,
        _serial: &str,
    ) -> Result<String, crate::error::CalibError> {
        // 推送 calib 目录到设备（独立步骤）
        // 注意：calib 报告目录在 get_device_work_dir(cpu_id)/calib，不是在 dataset_path 父目录下
        let calib_dir_local = crate::utils::paths::get_device_work_dir(&self.cpu_id).join("calib");
        let calib_dir_remote = "/sdcard/qc/calib";
        self.log_action("文件推送", &format!("推送 calib 目录到 {}", calib_dir_remote));

        if let Err(e) = self.adb.shell(&format!("mkdir -p {}", calib_dir_remote), 15000).await {
            let err = crate::error::CalibError::PushFailed(format!("创建设备目录失败: {}", e));
            self.log_calib_error(&err);
            return Err(err);
        }

        if calib_dir_local.exists() {
            // 使用 /./ 推送目录内容，避免在目标路径下多创建一层 calib 目录
            let calib_source = format!("{}/.", calib_dir_local.to_string_lossy());
            match self.adb.push(&calib_source, calib_dir_remote, 60000).await {
                Ok(_) => {
                    self.log_info("calib 目录推送成功");
                }
                Err(e) => {
                    let err = crate::error::CalibError::PushFailed(
                        format!("push高通标定文件失败，请检查或者重测: {}", e)
                    );
                    self.log_calib_error(&err);
                    return Err(err);
                }
            }
        } else {
            self.log_warn(&format!("本地 calib 目录不存在: {}", calib_dir_local.display()));
        }

        // 推送 device_calibration.xml（从 calib/ 报告目录读取，不从 resources/qvrdataset 读取）
        let xml_path = calib_dir_local.join("device_calibration.xml");
        self.log_action("文件推送", &format!("推送 {} 到 /data/local/tmp", xml_path.display()));
        if xml_path.exists() {
            match self.adb.push(&xml_path.to_string_lossy(), "/data/local/tmp", 30000).await {
                Ok(_) => {
                    self.log_info(&format!("标定文件推送成功: {}", xml_path.display()));
                }
                Err(e) => {
                    let err = crate::error::CalibError::PushFailed(e.to_string());
                    self.log_calib_error(&err);
                    return Err(err);
                }
            }
        } else {
            self.log_warn(&format!("标定文件不存在: {}", xml_path.display()));
            return Err(crate::error::CalibError::CalibrationFileMissing(xml_path.to_string_lossy().to_string()));
        }

        // 等待文件完全写入设备存储
        self.log_info("等待设备文件系统同步...");
        sleep(Duration::from_millis(500)).await;

        // sync
        self.log_action("ADB", "执行 sync 命令");
        self.adb
            .shell("sync", 15000)
            .await
            .map_err(|e| e.to_calib_error())?;
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
                    AdbError::Timeout => crate::error::CalibError::BootTimeout,
                    _ => e.to_calib_error(),
                };
                self.log_calib_error(&err);
                return Err(err);
            }
        }

        // 压缩标定结果目录
        // 压缩的是 CalibratResult/{cpu_id}/ 整个目录（包含 calib/ 报告和 qvrdataset/ 数据）
        let work_dir = crate::utils::paths::get_device_work_dir(&self.cpu_id);
        let zip_path_buf = work_dir.join("calibDetails.zip");
        let exclude_vec: Vec<String> = if self.config.enable_sfr {
            vec![]
        } else {
            vec!["sfr".to_string()]
        };

        // 统计待压缩文件数量和大小，帮助排查卡顿问题
        let (file_count, total_size) = count_files_recursive(&work_dir, &exclude_vec)
            .unwrap_or((0, 0));
        self.log_info(&format!(
            "待压缩: {} 个文件/目录, 总大小约 {:.1} MB",
            file_count, total_size as f64 / (1024.0 * 1024.0)
        ));

        self.log_action("压缩", &format!("开始压缩 {:?} 到 calibDetails.zip (enable_sfr={})", work_dir, self.config.enable_sfr));

        // 使用 spawn_blocking 避免阻塞 tokio async worker 线程
        let work_dir_clone = work_dir.clone();
        let zip_path_clone = zip_path_buf.clone();
        let compress_result = tokio::task::spawn_blocking(move || {
            let exclude_refs: Vec<&str> = exclude_vec.iter().map(|s| s.as_str()).collect();
            let mut logs = Vec::new();
            let result = zip_directory_blocking(
                &work_dir_clone, &zip_path_clone, &exclude_refs,
                |log| logs.push(log.to_string()),
            );
            (result, logs)
        }).await.map_err(|e| crate::error::CalibError::Unknown(format!("压缩任务中断: {}", e)))?;

        for log in compress_result.1 {
            self.log_info(&log);
        }

        match compress_result.0 {
            Ok(file_count) => {
                self.log_info(&format!("压缩完成: {:?} (共 {} 个文件)", zip_path_buf, file_count));
            }
            Err(e) => {
                self.log_warn(&format!("压缩失败: {}", e));
                return Err(crate::error::CalibError::Unknown(format!("压缩标定目录失败: {}", e)));
            }
        }

        // 上传 OSS
        let time = chrono::Local::now().format("%Y-%m-%d-%H-%M-%S").to_string();
        let zip_path = zip_path_buf.to_string_lossy().to_string();
        let file_name = format!("{}-{}.zip", self.cpu_id, time);

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
                let err = crate::error::CalibError::OssUploadFailed(e.to_string());
                self.log_calib_error(&err);
                return Err(err);
            }
        };

        // API 上报
        let brand = self.config.qvr_type.parse::<i32>().unwrap_or(0);
        self.log_action("API上报", &format!("上报标定结果, brand={}", brand));
        match self
            .oss
            .report_to_api(&oss_url, &self.cpu_id, &time, brand)
            .await
        {
            Ok(_) => {
                self.log_info("API上报成功");
            }
            Err(e) => {
                let err = crate::error::CalibError::ApiReportFailed(e.to_string());
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
        _app: &tauri::AppHandle,
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

        // 确保目标目录存在
        let sfr_remote_dir = "/sdcard/qc/sharpness";
        if let Err(e) = self.adb.shell(&format!("mkdir -p {}", sfr_remote_dir), 15000).await {
            self.log_warn(&format!("创建 {} 目录失败: {}", sfr_remote_dir, e));
        }

        // 推送 JSON
        match self.adb.push(&json_path, sfr_remote_dir, 30000).await {
            Ok(_) => self.log_info("SFR JSON 报告已推送"),
            Err(e) => self.log_warn(&format!("推送 JSON 失败: {}", e)),
        }

        // 推送 Text
        match self.adb.push(&txt_path, sfr_remote_dir, 30000).await {
            Ok(_) => self.log_info("SFR Text 报告已推送"),
            Err(e) => self.log_warn(&format!("推送 Text 失败: {}", e)),
        }

        // 推送 PDF
        match self.adb.push(&pdf_path, sfr_remote_dir, 30000).await {
            Ok(_) => self.log_info("SFR PDF 报告已推送"),
            Err(e) => self.log_warn(&format!("推送 PDF 失败: {}", e)),
        }

        // 推送图片（分析报告生成的标注图）
        for cam in &report.sfr.cameras {
            let img_path = image_dir.join(&cam.image);
            if img_path.exists() {
                match self.adb.push(
                    img_path.to_str().unwrap(), sfr_remote_dir, 30000).await {
                    Ok(_) => {}
                    Err(e) => self.log_warn(&format!("推送图片 {} 失败: {}", cam.image, e)),
                }
            }
        }

        // 推送原始清晰度测试图片
        self.log_action("ADB", "推送 SFR 原始图片到设备");
        let image_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"];
        let mut pushed_count = 0;
        if let Ok(entries) = std::fs::read_dir(image_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_file() {
                    let ext = path.extension()
                        .and_then(|e| e.to_str())
                        .unwrap_or("")
                        .to_lowercase();
                    if image_extensions.iter().any(|&e| e.trim_start_matches('.') == ext) {
                        match self.adb.push(
                            path.to_str().unwrap_or(""), sfr_remote_dir, 30000).await {
                            Ok(_) => pushed_count += 1,
                            Err(e) => self.log_warn(&format!("推送原始图片 {:?} 失败: {}", path.file_name().unwrap_or_default(), e)),
                        }
                    }
                }
            }
        }
        self.log_info(&format!("SFR 原始图片推送完成: {} 张", pushed_count));

        Ok(())
    }

    /// 复制标定相关原始文件到报告目录（PDF 生成成功后调用）
    fn copy_calib_source_files(&self, dataset_path: &str, report_dir: &Path) {
        // 源文件可能在 dataset_path 或其父目录中
        let source_dirs: Vec<std::path::PathBuf> = vec![
            dataset_path.into(),
            std::path::Path::new(dataset_path)
                .parent()
                .map(|p| p.to_path_buf())
                .unwrap_or_else(|| dataset_path.into()),
        ];

        let files_to_copy = [
            ("Calib.log", true),
            ("device_calibration.xml", true),
            ("parsed_report.txt", false), // 可选
            ("calibDetails.zip", false),  // 可选
        ];

        for (filename, required) in &files_to_copy {
            let mut copied = false;
            for src_dir in &source_dirs {
                let src = src_dir.join(filename);
                if src.exists() {
                    let dst = report_dir.join(filename);
                    match std::fs::copy(&src, &dst) {
                        Ok(_) => {
                            self.log_info(&format!(
                                "已复制 {} 到报告目录",
                                filename
                            ));
                            copied = true;
                            break;
                        }
                        Err(e) => {
                            self.log_warn(&format!(
                                "复制 {} 失败: {}",
                                filename, e
                            ));
                        }
                    }
                }
            }
            if !copied && *required {
                self.log_warn(&format!(
                    "未找到源文件: {}（ searched in {:?} ）",
                    filename, source_dirs
                ));
            }
        }
    }

    /// 生成标定报告（JSON + TXT + PDF）
    async fn generate_calib_report(
        &self,
        check_detail: &CheckResultDetail,
        dataset_path: &str,
        _app: &tauri::AppHandle,
    ) -> Result<(), String> {
        let work_dir = get_device_work_dir(&self.cpu_id);
        let report_dir = work_dir.join("calib");
        std::fs::create_dir_all(&report_dir).map_err(|e| e.to_string())?;

        // 从 parse_calib.py 的 JSON 构建报告数据
        let calib_detail = if let Some(ref json) = check_detail.json_data {
            serde_json::from_value::<crate::utils::calib_report::CalibDetail>(json.clone())
                .map_err(|e| format!("解析标定 JSON 失败: {}", e))?
        } else {
            return Err("标定 JSON 数据不存在".to_string());
        };

        let report = crate::utils::calib_report::CalibReportData {
            sn: self.serial.clone(),
            cpu_id: self.cpu_id.clone(),
            generated_at: chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
            calib: calib_detail,
            result: crate::utils::calib_report::CalibOverallResult {
                overall: if check_detail.status == CheckStatus::Pass {
                    "PASS".to_string()
                } else {
                    "FAIL".to_string()
                },
                failures: check_detail.failures.clone(),
            },
        };

        // 生成 JSON 报告
        match crate::utils::calib_report::generate_json_report(&report, &report_dir,
        ) {
            Ok(path) => self.log_info(&format!("标定 JSON 报告已生成: {}", path)),
            Err(e) => self.log_warn(&format!("生成 JSON 失败: {}", e)),
        }

        // 生成 TXT 报告
        match crate::utils::calib_report::generate_text_report(&report, &report_dir,
        ) {
            Ok(path) => self.log_info(&format!("标定 TXT 报告已生成: {}", path)),
            Err(e) => self.log_warn(&format!("生成 TXT 失败: {}", e)),
        }

        // 生成 PDF 报告
        match crate::utils::calib_report::generate_pdf_report(
            &report, &report_dir, &self.resource_dir,
        ) {
            Ok(path) => {
                self.log_info(&format!("标定 PDF 报告已生成: {}", path));
                // PDF 生成成功后，复制原始标定文件到报告目录
                self.copy_calib_source_files(dataset_path, &report_dir);
            }
            Err(e) => self.log_warn(&format!("生成 PDF 失败: {}", e)),
        }

        self.log_info(&format!("标定报告目录: {:?}", report_dir));
        Ok(())
    }

    /// 在标定流程失败时生成简化报告
    async fn generate_calib_failure_report(
        &self,
        error: &crate::error::CalibError,
        dataset_path: &str,
        _app: &tauri::AppHandle,
    ) -> Result<(), String> {
        let work_dir = get_device_work_dir(&self.cpu_id);

        // 尝试运行 parse_calib.py 获取已有数据
        let runner = PythonRunner::new(self.serial.clone(), self.resource_dir.clone());
        let json_data = runner
            .run_check_result_detail(dataset_path, |_log| {})
            .await
            .ok()
            .and_then(|d| d.json_data);

        // 构造报告
        let report = if let Some(json) = json_data {
            // 使用已有数据
            let calib_detail =
                serde_json::from_value::<crate::utils::calib_report::CalibDetail>(json)
                    .map_err(|e| e.to_string())?;
            crate::utils::calib_report::CalibReportData {
                sn: self.serial.clone(),
                cpu_id: self.cpu_id.clone(),
                generated_at: chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
                calib: calib_detail,
                result: crate::utils::calib_report::CalibOverallResult {
                    overall: "FAIL".to_string(),
                    failures: vec![error.to_string()],
                },
            }
        } else {
            // 没有任何数据，生成极简报告
            crate::utils::calib_report::CalibReportData {
                sn: self.serial.clone(),
                cpu_id: self.cpu_id.clone(),
                generated_at: chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
                calib: crate::utils::calib_report::CalibDetail {
                    device_uid: self.cpu_id.clone(),
                    cameras: serde_json::Value::Object(serde_json::Map::new()),
                    imu: serde_json::Value::Object(serde_json::Map::new()),
                    log_data: serde_json::Value::Object(serde_json::Map::new()),
                    consistency: vec![],
                    xml_missing_checks: vec![],
                    results: crate::utils::calib_report::CalibResults {
                        intrinsic: vec![],
                        extrinsic: vec![],
                        consistency: vec![],
                        imu_bias: vec![],
                        xml_checks: vec![],
                    },
                    overall: "FAIL".to_string(),
                    fail_codes: vec![],
                },
                result: crate::utils::calib_report::CalibOverallResult {
                    overall: "FAIL".to_string(),
                    failures: vec![error.to_string()],
                },
            }
        };

        // 生成报告
        let report_dir = work_dir.join("calib");
        let _ = std::fs::create_dir_all(&report_dir);

        let _ = crate::utils::calib_report::generate_json_report(&report, &report_dir,
        );
        let _ = crate::utils::calib_report::generate_text_report(&report, &report_dir,
        );
        match crate::utils::calib_report::generate_pdf_report(
            &report, &report_dir, &self.resource_dir,
        ) {
            Ok(_) => {
                // PDF 生成成功后，复制原始标定文件到报告目录
                self.copy_calib_source_files(dataset_path, &report_dir);
            }
            Err(_) => {}
        }

        self.log_info(&format!("失败标定报告已生成: {:?}", report_dir));
        Ok(())
    }
}

// =============================================================================
// 独立模块函数（不依赖 CalibrationEngine，可在 spawn_blocking 中调用）
// =============================================================================

/// 递归统计目录下的文件数量和总字节数，排除指定子目录
fn count_files_recursive(dir: &std::path::Path, exclude_dirs: &[impl AsRef<str>]) -> Result<(usize, u64), String> {
    let mut count = 0usize;
    let mut total = 0u64;
    for entry in std::fs::read_dir(dir).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let path = entry.path();
        let name = entry.file_name().to_string_lossy().to_string();

        if exclude_dirs.iter().any(|ex| name == ex.as_ref()) {
            continue;
        }

        if path.is_file() {
            count += 1;
            if let Ok(meta) = path.metadata() {
                total += meta.len();
            }
        } else if path.is_dir() {
            count += 1; // 目录也算一个条目
            let (sub_count, sub_total) = count_files_recursive(&path, exclude_dirs)?;
            count += sub_count;
            total += sub_total;
        }
    }
    Ok((count, total))
}

/// 将目录压缩为 zip 文件，可排除指定子目录和 zip 文件本身
/// 返回压缩的文件数量
fn zip_directory_blocking(
    src_dir: &std::path::Path,
    zip_path: &std::path::Path,
    exclude_dirs: &[&str],
    mut log_callback: impl FnMut(&str),
) -> Result<usize, String> {
    let file = std::fs::File::create(zip_path)
        .map_err(|e| format!("创建 zip 文件失败: {}", e))?;
    // 使用 Option 包装 ZipWriter，出错时手动处理，避免 Drop 中的 debug_assert panic
    let mut zip: Option<zip::ZipWriter<std::fs::File>> = Some(zip::ZipWriter::new(file));

    // 使用 Stored（不压缩只打包）+ 最低压缩级别 fallback，最大限度提升速度
    let options = zip::write::FileOptions::<()>::default()
        .compression_method(zip::CompressionMethod::Stored);

    let exclude_zip = zip_path.file_name()
        .map(|n| n.to_string_lossy().to_string());

    let mut file_count = 0usize;

    // 添加文件到 zip
    {
        let z = zip.as_mut().unwrap();
        if let Err(e) = zip_add_entries_blocking(
            z, src_dir, src_dir, options, exclude_dirs, exclude_zip.as_deref(),
            &mut log_callback, &mut file_count,
        ) {
            let _ = std::mem::ManuallyDrop::new(zip.take().unwrap());
            let _ = std::fs::remove_file(zip_path);
            return Err(e);
        }
    }

    // 完成 zip 写入
    let z = zip.take().unwrap();
    match z.finish() {
        Ok(_) => Ok(file_count),
        Err(e) => {
            let _ = std::fs::remove_file(zip_path);
            Err(format!("完成 zip 写入失败: {}", e))
        }
    }
}

fn zip_add_entries_blocking(
    zip: &mut zip::ZipWriter<std::fs::File>,
    base: &std::path::Path,
    current: &std::path::Path,
    options: zip::write::FileOptions<()>,
    exclude_dirs: &[&str],
    exclude_file: Option<&str>,
    log_callback: &mut dyn FnMut(&str),
    file_count: &mut usize,
) -> Result<(), String> {
    for entry in std::fs::read_dir(current).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let path = entry.path();
        let name = path.strip_prefix(base).map_err(|e| e.to_string())?;
        let name_str = name.to_string_lossy().to_string();

        if exclude_dirs.iter().any(|ex| name_str.starts_with(ex)) {
            continue;
        }

        if let Some(exclude) = exclude_file {
            if name_str == exclude {
                continue;
            }
        }

        if path.is_file() {
            *file_count += 1;

            // 大文件时输出进度日志，帮助排查卡顿
            if let Ok(metadata) = path.metadata() {
                let size_mb = metadata.len() as f64 / (1024.0 * 1024.0);
                if size_mb > 50.0 {
                    log_callback(&format!("正在压缩大文件 {} ({:.1} MB)...", name_str, size_mb)
                    );
                }
            }

            zip.start_file(name_str, options).map_err(|e| e.to_string())?;
            let mut f = std::fs::File::open(&path).map_err(|e| e.to_string())?;
            std::io::copy(&mut f, zip).map_err(|e| e.to_string())?;
        } else if path.is_dir() {
            if name != std::path::Path::new("") {
                zip.add_directory(name_str.clone(), options).map_err(|e| e.to_string())?;
            }
            zip_add_entries_blocking(
                zip, base, &path, options, exclude_dirs, exclude_file,
                log_callback, file_count,
            )?;
        }
    }
    Ok(())
}
