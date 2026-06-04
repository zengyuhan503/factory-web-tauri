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
    ) -> Result<PythonResult, String> {
        let script_path = self.resource_dir.join("ProcessCal").join(script_name);

        let mut child = Command::new(&self.python_path)
            .arg(&script_path)
            .args(args)
            .env("ANDROID_SERIAL", &self.serial)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| format!("启动 Python 失败: {}", e))?;

        let mut logs = Vec::new();
        let mut result = String::new();
        let mut resolved = false;

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
                    resolved = true;
                    on_log(&line);
                } else if line.contains("status:error") {
                    return Err(format!("Python 脚本错误: {}", line));
                } else {
                    on_log(&line);
                }
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
            .map_err(|e| format!("等待进程结束失败: {}", e))?;

        let exit_code = status.code().unwrap_or(-1);
        if exit_code != 0 {
            let full_log = logs.join("\n");
            return Err(format!(
                "Python 脚本退出码 {}: {}",
                exit_code,
                if full_log.is_empty() {
                    "无输出".to_string()
                } else {
                    full_log
                }
            ));
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
    ) -> Result<String, String> {
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
    ) -> Result<(), String> {
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
    ) -> Result<(), String> {
        let path = device_path.trim_end_matches('/');
        self.run("ConvertSlamYaml.py", &[path], on_log).await?;
        Ok(())
    }

    pub async fn run_check_result(
        &self,
        device_path: &str,
        on_log: impl Fn(&str),
    ) -> Result<CheckResult, String> {
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
            .map_err(|e| format!("启动 parse_calib.py 失败: {}", e))?;

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
            .map_err(|e| format!("等待进程结束失败: {}", e))?;

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
}

#[derive(Debug, Clone)]
pub struct CheckResult {
    pub status: CheckStatus,
    pub failures: Vec<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CheckStatus {
    Pass,
    Fail,
    Error,
}
