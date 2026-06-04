use crate::error::{parse_python_calib_error, CalibError};
use std::path::PathBuf;
use std::process::Stdio;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command;

pub struct PythonRunner {
    python_path: String,
    resource_dir: PathBuf,
    serial: String,
}

#[derive(Debug, Clone)]
pub struct PythonResult {
    pub logs: Vec<String>,
    pub result: String,
    pub exit_code: i32,
}

impl PythonRunner {
    pub fn new(serial: String, resource_dir: PathBuf) -> Self {
        let python_path = if cfg!(target_os = "linux") {
            "python3".to_string()
        } else {
            "python".to_string()
        };
        Self {
            python_path,
            resource_dir,
            serial,
        }
    }

    pub async fn run(
        &self,
        script_name: &str,
        args: &[&str],
        on_log: impl Fn(&str),
    ) -> Result<PythonResult, CalibError> {
        let script_path = self.resource_dir.join("ProcessCal").join(script_name);

        let mut child = Command::new(&self.python_path)
            .arg(&script_path)
            .args(args)
            .env("ANDROID_SERIAL", &self.serial)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| CalibError::PythonNotFound(format!("启动 Python 失败: {}", e)))?;

        let mut logs = Vec::new();
        let mut result = String::new();
        let mut _resolved = false;

        // 读取 stdout
        if let Some(stdout) = child.stdout.take() {
            let reader = BufReader::new(stdout);
            let mut lines = reader.lines();
            while let Ok(Some(line)) = lines.next_line().await {
                logs.push(line.clone());

                if line.contains("status:ok") {
                    if let Some(path_idx) = line.find("path:") {
                        result = line[path_idx + 5..].to_string();
                    }
                    _resolved = true;
                    on_log(&line);
                } else if line.contains("status:error") {
                    // 收集剩余日志用于错误解析
                    let mut error_logs = logs.clone();
                    while let Ok(Some(remaining)) = lines.next_line().await {
                        error_logs.push(remaining.clone());
                        on_log(&remaining);
                    }
                    // 也读取 stderr
                    if let Some(stderr) = child.stderr.take() {
                        let reader = BufReader::new(stderr);
                        let mut err_lines = reader.lines();
                        while let Ok(Some(err_line)) = err_lines.next_line().await {
                            error_logs.push(err_line);
                        }
                    }
                    let _ = child.wait().await;
                    return Err(parse_python_calib_error(script_name, &error_logs));
                } else {
                    on_log(&line);
                }
            }
        }

        // 读取 stderr（某些脚本将 status:ok 输出到 stderr）
        if let Some(stderr) = child.stderr.take() {
            let reader = BufReader::new(stderr);
            let mut lines = reader.lines();
            while let Ok(Some(line)) = lines.next_line().await {
                logs.push(line.clone());

                if line.contains("status:ok") {
                    if let Some(path_idx) = line.find("path:") {
                        result = line[path_idx + 5..].to_string();
                    }
                    _resolved = true;
                    on_log(&line);
                } else if line.contains("status:error") {
                    on_log(&line);
                } else {
                    on_log(&line);
                }
            }
        }

        let status = child
            .wait()
            .await
            .map_err(|e| CalibError::Unknown(format!("等待进程结束失败: {}", e)))?;

        let exit_code = status.code().unwrap_or(-1);
        let has_ok = logs.iter().any(|l| l.contains("status:ok"));

        log::info!(
            "[PythonRunner] {} exit_code={} resolved={} has_ok={}",
            script_name, exit_code, _resolved, has_ok
        );

        // 如果脚本已明确返回 status:ok，忽略 exit code（某些脚本 exit code 非 0 但有成功输出）
        if exit_code != 0 && !has_ok {
            log::warn!(
                "[PythonRunner] {} 失败，未检测到 status:ok，日志:\n{}",
                script_name,
                logs.join("\n")
            );
            return Err(parse_python_calib_error(script_name, &logs));
        }

        if has_ok {
            log::info!(
                "[PythonRunner] {} 成功，result='{}'",
                script_name,
                result
            );
        }

        Ok(PythonResult {
            logs,
            result,
            exit_code,
        })
    }

    pub async fn run_device_pull(
        &self,
        is_rgb: bool,
        qvr_type: &str,
        on_log: impl Fn(&str),
    ) -> Result<String, CalibError> {
        let result = self
            .run(
                "DevicePull.py",
                &[if is_rgb { "1" } else { "0" }, qvr_type],
                on_log,
            )
            .await?;

        // DevicePull.py 的 result 是数据集路径
        Ok(result.result.trim().to_string())
    }

    pub async fn run_cam_cali(
        &self,
        is_rgb: bool,
        qvr_type: &str,
        device_path: &str,
        on_log: impl Fn(&str),
    ) -> Result<(), CalibError> {
        let path = device_path.trim_end_matches('/');
        self.run(
            "ProcessCam.py",
            &[path, if is_rgb { "1" } else { "0" }, qvr_type],
            on_log,
        )
        .await?;
        Ok(())
    }

    pub async fn run_convert_yaml(
        &self,
        device_path: &str,
        on_log: impl Fn(&str),
    ) -> Result<(), CalibError> {
        let path = device_path.trim_end_matches('/');
        self.run("ConvertSlamYaml.py", &[path], on_log).await?;
        Ok(())
    }

    pub async fn run_check_result(
        &self,
        device_path: &str,
        on_log: impl Fn(&str),
    ) -> Result<CheckResult, CalibError> {
        let dir = std::path::Path::new(device_path)
            .parent()
            .map(|p| p.to_string_lossy().to_string())
            .unwrap_or_else(|| device_path.to_string());

        let script_path = self.resource_dir.join("CheckResult").join("parse_calib.py");

        let mut child = Command::new(&self.python_path)
            .arg(&script_path)
            .args(&["--dir", &dir])
            .env("ANDROID_SERIAL", &self.serial)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| CalibError::Unknown(format!("启动 parse_calib.py 失败: {}", e)))?;

        let mut logs = Vec::new();

        if let Some(stdout) = child.stdout.take() {
            let reader = BufReader::new(stdout);
            let mut lines = reader.lines();
            while let Ok(Some(line)) = lines.next_line().await {
                logs.push(line.clone());
                on_log(&line);
            }
        }

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
            .map_err(|e| CalibError::Unknown(format!("等待进程结束失败: {}", e)))?;

        let full_output = logs.join("\n");

        // 解析状态
        let status = if full_output.contains("CALIB_PARSE_STATUS=PASS")
            || full_output.contains("总评            : PASS")
        {
            CheckStatus::Pass
        } else if full_output.contains("CALIB_PARSE_STATUS=FAIL")
            || full_output.contains("总评            : FAIL")
        {
            CheckStatus::Fail
        } else if status.code().unwrap_or(-1) != 0 {
            CheckStatus::Error
        } else {
            CheckStatus::Pass
        };

        // 解析失败原因
        let mut failures = Vec::new();
        if let Some(codes_match) = regex::Regex::new(r"FAIL_CODES=([\d,]+)")
            .unwrap()
            .captures(&full_output)
        {
            let codes: Vec<i32> = codes_match[1]
                .split(',')
                .filter_map(|c| c.trim().parse().ok())
                .collect();
            for code in codes {
                failures.push(match code {
                    20 => "摄像头内参 RMS 超阈值".to_string(),
                    21 => "Full-Extrinsics+Intrinsics-Extrinsics RMS 超阈值".to_string(),
                    22 => "联合标定 RMS 超阈值".to_string(),
                    23 => "IMU 加速度计 bias 超阈值".to_string(),
                    24 => "IMU 陀螺仪 bias 超阈值".to_string(),
                    25 => "标定文件 XML 缺少 IMUNoise 节点".to_string(),
                    26 => "标定文件 XML 中 IMUNoise 缺少必填字段".to_string(),
                    27 => "摄像头检测率低于合格阈值".to_string(),
                    2 => "标定结果存在多项失败".to_string(),
                    _ => format!("未知失败码: {}", code),
                });
            }
        }

        Ok(CheckResult { status, failures })
    }

    pub async fn run_check_result_detail(
        &self,
        device_path: &str,
        on_log: impl Fn(&str),
    ) -> Result<CheckResultDetail, CalibError> {
        let dir = std::path::Path::new(device_path)
            .parent()
            .map(|p| p.to_string_lossy().to_string())
            .unwrap_or_else(|| device_path.to_string());

        let script_path = self.resource_dir.join("CheckResult").join("parse_calib.py");

        let mut child = Command::new(&self.python_path)
            .arg(&script_path)
            .args(&["--dir", &dir])
            .arg("--json-output")
            .env("ANDROID_SERIAL", &self.serial)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| CalibError::Unknown(format!("启动 parse_calib.py 失败: {}", e)))?;

        let mut logs = Vec::new();
        let mut json_path: Option<String> = None;

        if let Some(stdout) = child.stdout.take() {
            let reader = BufReader::new(stdout);
            let mut lines = reader.lines();
            while let Ok(Some(line)) = lines.next_line().await {
                logs.push(line.clone());
                // 解析 JSON 路径
                if line.starts_with("JSON_PATH=") {
                    json_path = Some(line["JSON_PATH=".len()..].trim().to_string());
                }
                on_log(&line);
            }
        }

        if let Some(stderr) = child.stderr.take() {
            let reader = BufReader::new(stderr);
            let mut lines = reader.lines();
            while let Ok(Some(line)) = lines.next_line().await {
                logs.push(line.clone());
                if line.starts_with("JSON_PATH=") {
                    json_path = Some(line["JSON_PATH=".len()..].trim().to_string());
                }
                on_log(&line);
            }
        }

        let status = child
            .wait()
            .await
            .map_err(|e| CalibError::Unknown(format!("等待进程结束失败: {}", e)))?;

        let full_output = logs.join("\n");

        // 解析状态（与 run_check_result 相同的逻辑）
        let check_status = if full_output.contains("CALIB_PARSE_STATUS=PASS")
            || full_output.contains("总评            : PASS")
        {
            CheckStatus::Pass
        } else if full_output.contains("CALIB_PARSE_STATUS=FAIL")
            || full_output.contains("总评            : FAIL")
        {
            CheckStatus::Fail
        } else if status.code().unwrap_or(-1) != 0 {
            CheckStatus::Error
        } else {
            CheckStatus::Pass
        };

        // 解析失败原因
        let mut failures = Vec::new();
        if let Some(codes_match) = regex::Regex::new(r"FAIL_CODES=([\d,]+)")
            .unwrap()
            .captures(&full_output)
        {
            let codes: Vec<i32> = codes_match[1]
                .split(',')
                .filter_map(|c| c.trim().parse().ok())
                .collect();
            for code in codes {
                failures.push(match code {
                    20 => "摄像头内参 RMS 超阈值".to_string(),
                    21 => "Full-Extrinsics+Intrinsics-Extrinsics RMS 超阈值".to_string(),
                    22 => "联合标定 RMS 超阈值".to_string(),
                    23 => "IMU 加速度计 bias 超阈值".to_string(),
                    24 => "IMU 陀螺仪 bias 超阈值".to_string(),
                    25 => "标定文件 XML 缺少 IMUNoise 节点".to_string(),
                    26 => "标定文件 XML 中 IMUNoise 缺少必填字段".to_string(),
                    27 => "摄像头检测率低于合格阈值".to_string(),
                    2 => "标定结果存在多项失败".to_string(),
                    _ => format!("未知失败码: {}", code),
                });
            }
        }

        // 读取 JSON 数据
        let json_data = if let Some(path) = json_path {
            match tokio::fs::read_to_string(&path).await {
                Ok(content) => {
                    match serde_json::from_str::<serde_json::Value>(&content) {
                        Ok(data) => Some(data),
                        Err(e) => {
                            log::warn!("解析标定 JSON 报告失败: {}", e);
                            None
                        }
                    }
                }
                Err(e) => {
                    log::warn!("读取标定 JSON 报告失败: {}", e);
                    None
                }
            }
        } else {
            None
        };

        Ok(CheckResultDetail {
            status: check_status,
            failures,
            json_data,
            report_dir: dir,
        })
    }
}

#[derive(Debug, Clone)]
pub struct CheckResult {
    pub status: CheckStatus,
    pub failures: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct CheckResultDetail {
    pub status: CheckStatus,
    pub failures: Vec<String>,
    pub json_data: Option<serde_json::Value>,
    pub report_dir: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CheckStatus {
    Pass,
    Fail,
    Error,
}
