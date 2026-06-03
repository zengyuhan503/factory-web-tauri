use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::process::Stdio;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command;
use tokio::time::{sleep, Duration};

/// SFR 分析结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SfrResult {
    pub device_grade: String,
    pub device_mean_avg50: f64,
    pub device_std_avg50: f64,
    pub mean_avg50_min: f64,
    pub cam_std_max: f64,
    pub cameras: Vec<SfrCameraResult>,
    pub image_dir: PathBuf,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SfrCameraResult {
    pub image: String,
    pub cam: String,
    pub v50: f64,
    pub h50: f64,
    pub avg50: f64,
}

pub struct SfrRunner {
    serial: String,
    resource_dir: PathBuf,
}

impl SfrRunner {
    pub fn new(serial: String, resource_dir: PathBuf) -> Self {
        Self {
            serial,
            resource_dir,
        }
    }

    /// 从设备拉取清晰度标定图片到本地目录
    /// 目录: {work_dir}/sfr/
    pub async fn pull_sfr_files(
        &self,
        work_dir: &std::path::Path,
        _cpu_id: &str,
        on_log: impl Fn(&str),
    ) -> Result<PathBuf, crate::error::CalibError> {
        let pull_target = work_dir.join("sfr");

        // 清空旧目录（仅当前设备目录，防止旧文件残留导致误判）
        if pull_target.exists() {
            if let Err(e) = tokio::fs::remove_dir_all(&pull_target).await {
                let msg = format!(
                    "清空当前设备目录 {:?} 失败: {}。为防止旧文件残留导致误判，终止拉取。",
                    pull_target, e
                );
                on_log(&msg);
                log::error!("[SFR/pull] {}", msg);
                return Err(crate::error::CalibError::SfrFailed(msg));
            }
            let msg = format!("已清空当前设备目录 {:?}", pull_target);
            on_log(&msg);
            log::info!("[SFR/pull] {}", msg);
            // 等待文件系统同步
            sleep(Duration::from_millis(2000)).await;
        }

        // 创建目录
        if let Err(e) = tokio::fs::create_dir_all(&pull_target).await {
            let msg = format!("创建目录 {:?} 失败: {}", pull_target, e);
            on_log(&msg);
            log::error!("[SFR/pull] {}", msg);
            return Err(crate::error::CalibError::SfrFailed(msg));
        }

        let pull_target_str = pull_target.to_str().unwrap_or(".");

        // 尝试多个可能的设备路径
        let candidate_paths = [
            "/sdcard/snapshot",
            "/storage/emulated/0/snapshot",
            "/mnt/sdcard/snapshot",
        ];

        // 先用 adb shell ls 探测有效路径
        let mut valid_remote_path: Option<String> = None;
        for path in &candidate_paths {
            let ls_cmd = Command::new("adb")
                .args(["-s", &self.serial, "shell", "ls", path])
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .output()
                .await;

            match ls_cmd {
                Ok(output) => {
                    let stdout = String::from_utf8_lossy(&output.stdout);
                    let stderr = String::from_utf8_lossy(&output.stderr);
                    on_log(&format!("[SFR/pull] 探测路径 {}: stdout={}, stderr={}", path, stdout.trim(), stderr.trim()));

                    if output.status.success() && !stdout.trim().is_empty() && !stdout.contains("No such file") {
                        let file_count = stdout.lines().count();
                        on_log(&format!("[SFR/pull] 路径 {} 有效，包含 {} 个条目", path, file_count));
                        log::info!("[SFR/pull] 路径 {} 有效，包含 {} 个条目", path, file_count);
                        valid_remote_path = Some(format!("{}/.", path));
                        break;
                    }
                }
                Err(e) => {
                    on_log(&format!("[SFR/pull] 探测路径 {} 失败: {}", path, e));
                }
            }
        }

        let remote_path = match valid_remote_path {
            Some(p) => p,
            None => {
                let msg = "无法找到设备上的 snapshot 目录，尝试的路径: /sdcard/snapshot, /storage/emulated/0/snapshot, /mnt/sdcard/snapshot".to_string();
                on_log(&msg);
                log::error!("[SFR/pull] {}", msg);
                return Err(crate::error::CalibError::SfrFailed(msg));
            }
        };

        // 使用 adb -s serial 指定设备拉取
        let mut cmd = Command::new("adb");
        cmd.arg("-s")
            .arg(&self.serial)
            .args(["pull", &remote_path, pull_target_str])
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        on_log(&format!("[SFR] adb -s {} pull {} {}", self.serial, remote_path, pull_target_str));
        log::info!("[SFR] 执行命令: adb -s {} pull {} {}", self.serial, remote_path, pull_target_str);

        let output = cmd.output().await.map_err(|e| {
            let msg = format!("adb pull 命令执行失败: {}", e);
            crate::error::CalibError::SfrFailed(msg)
        })?;

        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        on_log(&format!("[SFR/pull] stdout: {}", stdout));
        on_log(&format!("[SFR/pull] stderr: {}", stderr));

        if !output.status.success() {
            let msg = format!("adb pull 失败: {} {}", stdout, stderr);
            log::error!("[SFR/pull] {}", msg);
            return Err(crate::error::CalibError::SfrFailed(msg));
        }

        // 验证本地是否确实有文件（不依赖 stdout 字符串匹配，避免 "10 files" 误判 "0 files"）
        let local_files: Vec<_> = std::fs::read_dir(&pull_target)
            .ok()
            .map(|rd| rd.filter_map(|e| e.ok()).collect())
            .unwrap_or_default();

        if local_files.is_empty() {
            let msg = format!(
                "adb pull 报告成功但本地目录 {:?} 为空，远程路径: {}",
                pull_target, remote_path
            );
            on_log(&msg);
            log::error!("[SFR/pull] {}", msg);
            return Err(crate::error::CalibError::SfrFailed(msg));
        }

        on_log(&format!("[SFR/pull] 成功拉取 {} 个文件到 {:?}", local_files.len(), pull_target));
        log::info!("[SFR/pull] 文件拉取成功到 {:?}, 共 {} 个文件", pull_target, local_files.len());
        // 等待文件完全落盘
        sleep(Duration::from_millis(1000)).await;
        Ok(pull_target)
    }

    /// 运行 SFR 分析脚本，返回结构化结果
    pub async fn analyze_sfr(
        &self,
        image_dir: &std::path::Path,
        mean_avg50_min: f64,
        cam_std_max: f64,
        on_log: impl Fn(&str),
    ) -> Result<SfrResult, crate::error::CalibError> {
        let sfr_dir = self.resource_dir.join("sfr");
        let run_sfr_path = sfr_dir.join("run_sfr50_qc.py");

        if !run_sfr_path.exists() {
            let msg = format!(
                "run_sfr50_qc.py 不存在: {}",
                run_sfr_path.to_string_lossy()
            );
            on_log(&msg);
            log::error!("[SFR/analyze] {}", msg);
            return Err(crate::error::CalibError::SfrFailed(msg));
        }

        let image_dir_str = image_dir.to_str().unwrap_or(".");
        let mean_str = format!("{}", mean_avg50_min);
        let std_str = format!("{}", cam_std_max);

        let mut child = Command::new("python3")
            .arg(&run_sfr_path)
            .arg(image_dir_str)
            .arg("--pattern-hint")
            .arg("9x9")
            .arg("--mean-avg50-min-pass")
            .arg(&mean_str)
            .arg("--cam-std-max-pass")
            .arg(&std_str)
            .env("ANDROID_SERIAL", &self.serial)
            .env("PYTHONIOENCODING", "utf-8")
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| {
                let msg = format!("启动 SFR Python 脚本失败: {}", e);
                crate::error::CalibError::SfrFailed(msg)
            })?;

        let mut logs = Vec::new();

        // 读取 stdout
        if let Some(stdout) = child.stdout.take() {
            let reader = BufReader::new(stdout);
            let mut lines = reader.lines();
            while let Ok(Some(line)) = lines.next_line().await {
                logs.push(line.clone());
                on_log(&line);
            }
        }

        // 读取 stderr
        if let Some(stderr) = child.stderr.take() {
            let reader = BufReader::new(stderr);
            let mut lines = reader.lines();
            while let Ok(Some(line)) = lines.next_line().await {
                logs.push(line.clone());
                on_log(&line);
            }
        }

        let status = child
            .wait()
            .await
            .map_err(|e| {
                let msg = format!("等待 SFR 进程结束失败: {}", e);
                crate::error::CalibError::SfrFailed(msg)
            })?;

        let exit_code = status.code().unwrap_or(3);

        log::info!(
            "[SFR/analyze] 进程结束 exit_code={}",
            exit_code
        );

        // 解析 sfr50_summary.csv
        let summary_csv = image_dir.join("sfr50_summary.csv");
        let sfr_result = Self::parse_sfr_summary(&summary_csv, mean_avg50_min, cam_std_max, image_dir.to_path_buf())
            .map_err(|e| crate::error::CalibError::SfrFailed(format!("解析 SFR 汇总表失败: {}", e)))?;
        println!("exit_code: {}", exit_code);
        match exit_code {
            0 => {
                on_log("[SFR] 清晰度标定验证通过");
                log::info!("[SFR] 清晰度标定验证通过");
                Ok(sfr_result)
            }
            2 => {
                // 根据解析结果构造详细的失败原因
                let mut details = Vec::new();

                if sfr_result.device_mean_avg50 < mean_avg50_min {
                    details.push(format!(
                        "设备清晰度均值不足: {:.4} < 阈值 {:.4}",
                        sfr_result.device_mean_avg50, mean_avg50_min
                    ));
                }
                if sfr_result.device_std_avg50 > cam_std_max {
                    details.push(format!(
                        "摄像头一致性差: std={:.6} > 阈值 {:.4}",
                        sfr_result.device_std_avg50, cam_std_max
                    ));
                }
                for cam in &sfr_result.cameras {
                    if cam.avg50 < mean_avg50_min {
                        details.push(format!(
                            "摄像头 {} 清晰度不足: AVG50={:.4}",
                            cam.cam, cam.avg50
                        ));
                    }
                }

                let msg = if details.is_empty() {
                    "清晰度验证未通过: 棋盘格检测异常，请检查图片拍摄质量".to_string()
                } else {
                    format!("清晰度验证未通过: {}", details.join("; "))
                };
                on_log(&format!("[SFR] {}", msg));
                log::error!("[SFR] {}", msg);
                Err(crate::error::CalibError::SfrFailed(msg))
            }
            3 => {
                let msg = "存在至少一张图片未检出棋盘格（或无有效 SFR 结果）".to_string();
                on_log(&format!("[SFR] {}", msg));
                log::error!("[SFR] {}", msg);
                Err(crate::error::CalibError::SfrFailed(msg))
            }
            _ => {
                let full_output = logs.join("\n");
                let msg = format!(
                    "SFR 分析执行失败 exit_code={} {}",
                    exit_code,
                    if full_output.is_empty() {
                        String::new()
                    } else {
                        format!("({})", full_output)
                    }
                );
                log::error!("[SFR/analyze] {}", msg);
                Err(crate::error::CalibError::SfrFailed(msg))
            }
        }
    }

    /// 解析 sfr50_summary.csv
    fn parse_sfr_summary(
        csv_path: &std::path::Path,
        mean_avg50_min: f64,
        cam_std_max: f64,
        image_dir: PathBuf,
    ) -> Result<SfrResult, String> {
        if !csv_path.exists() {
            return Err(format!("汇总表不存在: {}", csv_path.to_string_lossy()));
        }

        let content = std::fs::read_to_string(csv_path)
            .map_err(|e| format!("读取汇总表失败: {}", e))?;

        let mut rdr = csv::Reader::from_reader(content.as_bytes());
        let mut cameras = Vec::new();
        let mut device_grade = String::new();
        let mut device_mean_avg50 = 0.0;
        let mut device_std_avg50 = 0.0;

        for result in rdr.records() {
            let record = result.map_err(|e| format!("解析 CSV 行失败: {}", e))?;
            if record.len() < 11 {
                continue;
            }

            let image = record.get(0).unwrap_or("").to_string();
            let cam = record.get(1).unwrap_or("").to_string();
            let v50: f64 = record.get(2).unwrap_or("0").parse().unwrap_or(0.0);
            let h50: f64 = record.get(3).unwrap_or("0").parse().unwrap_or(0.0);
            let avg50: f64 = record.get(4).unwrap_or("0").parse().unwrap_or(0.0);

            cameras.push(SfrCameraResult {
                image: image.clone(),
                cam,
                v50,
                h50,
                avg50,
            });

            // 从最后一行读取设备级数据
            if let Some(grade) = record.get(10) {
                device_grade = grade.to_string();
            }
            if let Ok(v) = record.get(8).unwrap_or("0").parse::<f64>() {
                device_mean_avg50 = v;
            }
            if let Ok(v) = record.get(9).unwrap_or("0").parse::<f64>() {
                device_std_avg50 = v;
            }
        }

        Ok(SfrResult {
            device_grade,
            device_mean_avg50,
            device_std_avg50,
            mean_avg50_min,
            cam_std_max,
            cameras,
            image_dir,
        })
    }
}
