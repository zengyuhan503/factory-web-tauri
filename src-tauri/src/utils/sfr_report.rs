use crate::adapters::sfr_runner::SfrResult;
use std::path::Path;

/// SFR 验证报告数据（用于 JSON 序列化）
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SfrReportData {
    pub sn: String,
    pub cpu_id: String,
    pub generated_at: String,
    pub sfr: SfrData,
    pub result: SfrOverallResult,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SfrData {
    pub health_status: String,
    pub mean_avg50_min_pass: f64,
    pub cam_std_max_pass: f64,
    pub device_grade: String,
    pub device_mean_avg50: f64,
    pub device_std_avg50: f64,
    pub cameras: Vec<SfrCameraReport>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SfrCameraReport {
    pub image: String,
    pub cam: String,
    pub v50: f64,
    pub h50: f64,
    pub avg50: f64,
    pub pass: bool,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SfrOverallResult {
    pub sfr_ok: String,
    pub overall: String,
    pub failures: Vec<String>,
}

impl SfrReportData {
    pub fn from_result(
        sn: &str,
        cpu_id: &str,
        result: &SfrResult,
    ) -> Self {
        let mean_pass = result.device_mean_avg50 >= result.mean_avg50_min;
        let std_pass = result.device_std_avg50 <= result.cam_std_max;
        let sfr_ok = mean_pass && std_pass;
        let health_status = if sfr_ok { "PASS" } else { "FAIL" };

        let mut failures = Vec::new();
        if !mean_pass {
            failures.push(format!(
                "设备清晰度均值不足: {:.4} < 阈值 {:.4}",
                result.device_mean_avg50, result.mean_avg50_min
            ));
        }
        if !std_pass {
            failures.push(format!(
                "摄像头间差异过大: {:.6} > 阈值 {:.4}",
                result.device_std_avg50, result.cam_std_max
            ));
        }

        let cameras: Vec<SfrCameraReport> = result
            .cameras
            .iter()
            .map(|c| SfrCameraReport {
                image: c.image.clone(),
                cam: c.cam.clone(),
                v50: c.v50,
                h50: c.h50,
                avg50: c.avg50,
                pass: c.avg50 >= result.mean_avg50_min,
            })
            .collect();

        // 如果有单个摄像头未通过，也加入失败原因
        for cam in &cameras {
            if !cam.pass {
                failures.push(format!(
                    "摄像头 {} 清晰度不足: AVG50={:.4} < 阈值 {:.4}",
                    cam.cam, cam.avg50, result.mean_avg50_min
                ));
            }
        }

        Self {
            sn: sn.to_string(),
            cpu_id: cpu_id.to_string(),
            generated_at: chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
            sfr: SfrData {
                health_status: health_status.to_string(),
                mean_avg50_min_pass: result.mean_avg50_min,
                cam_std_max_pass: result.cam_std_max,
                device_grade: result.device_grade.clone(),
                device_mean_avg50: result.device_mean_avg50,
                device_std_avg50: result.device_std_avg50,
                cameras,
            },
            result: SfrOverallResult {
                sfr_ok: health_status.to_string(),
                overall: if sfr_ok { "PASS" } else { "FAIL" }.to_string(),
                failures,
            },
        }
    }
}

/// 生成 SFR 验证 JSON 报告
pub fn generate_json_report(
    report: &SfrReportData,
    output_dir: &Path,
) -> Result<String, String> {
    let json_path = output_dir.join("sfr_report.json");
    let json = serde_json::to_string_pretty(report).map_err(|e| e.to_string())?;
    std::fs::write(&json_path, json).map_err(|e| e.to_string())?;
    Ok(json_path.to_string_lossy().to_string())
}

/// 生成 SFR 验证 Text 报告
pub fn generate_text_report(
    report: &SfrReportData,
    output_dir: &Path,
) -> Result<String, String> {
    let txt_path = output_dir.join("sfr_report.txt");
    let mut content = String::new();

    content.push_str("========================================\n");
    content.push_str("        SFR 清晰度验证报告\n");
    content.push_str("========================================\n\n");

    content.push_str(&format!("设备序列号: {}\n", report.sn));
    content.push_str(&format!("CPU ID: {}\n", report.cpu_id));
    content.push_str(&format!("生成时间: {}\n\n", report.generated_at));

    let status_str = if report.result.overall == "PASS" {
        "[PASS]"
    } else {
        "[FAIL]"
    };
    content.push_str(&format!("整体结果: {}\n\n", status_str));

    content.push_str("---------- 验证配置 ----------\n");
    content.push_str(&format!(
        "清晰度均值阈值 (mean_avg50_min): {:.4}\n",
        report.sfr.mean_avg50_min_pass
    ));
    content.push_str(&format!(
        "摄像头间标准差阈值 (cam_std_max): {:.4}\n\n",
        report.sfr.cam_std_max_pass
    ));

    content.push_str("---------- 验证结果 ----------\n");
    content.push_str(&format!("健康状态: {}\n", report.sfr.health_status));
    content.push_str(&format!("设备判级: {}\n", report.sfr.device_grade));
    content.push_str(&format!(
        "设备 mean_avg50: {:.4} {}\n",
        report.sfr.device_mean_avg50,
        if report.sfr.device_mean_avg50 >= report.sfr.mean_avg50_min_pass {
            "[OK]"
        } else {
            "[FAIL]"
        }
    ));
    content.push_str(&format!(
        "设备 std_avg50: {:.6} {}\n\n",
        report.sfr.device_std_avg50,
        if report.sfr.device_std_avg50 <= report.sfr.cam_std_max_pass {
            "[OK]"
        } else {
            "[FAIL]"
        }
    ));

    if !report.result.failures.is_empty() {
        content.push_str("---------- 失败原因 ----------\n");
        for (i, f) in report.result.failures.iter().enumerate() {
            content.push_str(&format!("  {}. {}\n", i + 1, f));
        }
        content.push('\n');
    }

    content.push_str("---------- 各摄像头详情 ----------\n");
    for cam in &report.sfr.cameras {
        content.push_str(&format!("\n摄像头: {}\n", cam.cam));
        content.push_str(&format!("  图片: {}\n", cam.image));
        content.push_str(&format!(
            "  V-SFR50: {:.4} {}\n",
            cam.v50,
            if cam.v50 >= report.sfr.mean_avg50_min_pass {
                "[OK]"
            } else {
                "[LOW]"
            }
        ));
        content.push_str(&format!(
            "  H-SFR50: {:.4} {}\n",
            cam.h50,
            if cam.h50 >= report.sfr.mean_avg50_min_pass {
                "[OK]"
            } else {
                "[LOW]"
            }
        ));
        content.push_str(&format!(
            "  AVG50: {:.4} {}\n",
            cam.avg50,
            if cam.pass { "[PASS]" } else { "[FAIL]" }
        ));
    }

    content.push_str("\n========================================\n");
    content.push_str(&format!("\nSFR 检查结果: {}\n", report.result.sfr_ok));
    content.push_str("========================================\n");

    std::fs::write(&txt_path, content).map_err(|e| e.to_string())?;
    Ok(txt_path.to_string_lossy().to_string())
}

/// 生成 SFR 验证 PDF 报告（调用 Python 脚本，支持中文和图片）
pub fn generate_pdf_report(
    report: &SfrReportData,
    output_dir: &Path,
    resource_dir: &Path,
) -> Result<String, String> {
    // 确保 JSON 报告已写入（Python 脚本读取 JSON）
    let json_path = output_dir.join("sfr_report.json");
    let json = serde_json::to_string_pretty(report).map_err(|e| e.to_string())?;
    std::fs::write(&json_path, json).map_err(|e| e.to_string())?;

    let script_path = resource_dir.join("sfr").join("generate_sfr_report.py");
    let img_dir = output_dir; // 报告和图片统一在 sfr/ 目录下

    // 检查 Python 脚本是否存在（开发模式下可能未同步到 target/debug/resources，回退到源码目录）
    let script_path = if script_path.exists() {
        script_path
    } else {
        let fallback = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("resources")
            .join("sfr")
            .join("generate_sfr_report.py");
        if fallback.exists() {
            fallback
        } else {
            return Err(format!(
                "PDF 生成脚本不存在: {} 且回退路径也不存在",
                script_path.to_string_lossy()
            ));
        }
    };

    // 调用 Python 脚本生成 PDF
    let output = std::process::Command::new("python3")
        .arg(&script_path)
        .arg(&json_path)
        .arg(output_dir)
        .arg(&img_dir)
        .output()
        .map_err(|e| format!("执行 Python PDF 生成脚本失败: {}", e))?;

    let stderr = String::from_utf8_lossy(&output.stderr);
    let stdout = String::from_utf8_lossy(&output.stdout);

    if !output.status.success() {
        return Err(format!(
            "Python PDF 生成失败 (exit={}): stderr={} stdout={}",
            output.status.code().unwrap_or(-1),
            stderr,
            stdout
        ));
    }

    // 最后一行 stdout 是生成的 PDF 路径
    let pdf_path = stdout.lines().last().unwrap_or("").trim();
    if pdf_path.is_empty() {
        return Err(format!(
            "Python 脚本未返回 PDF 路径。stdout: {} stderr: {}",
            stdout, stderr
        ));
    }

    Ok(pdf_path.to_string())
}
