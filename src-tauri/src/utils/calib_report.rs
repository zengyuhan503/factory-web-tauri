use std::path::Path;

/// 标定报告数据（对标 SfrReportData）
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CalibReportData {
    pub sn: String,
    pub cpu_id: String,
    pub generated_at: String,
    pub calib: CalibDetail,
    pub result: CalibOverallResult,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CalibDetail {
    pub device_uid: String,
    pub cameras: serde_json::Value,
    pub imu: serde_json::Value,
    pub log_data: serde_json::Value,
    pub consistency: Vec<ConsistencyItem>,
    pub xml_missing_checks: Vec<String>,
    pub results: CalibResults,
    pub overall: String,
    pub fail_codes: Vec<i32>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ConsistencyItem {
    pub label: String,
    pub fl_diff_pct: f64,
    pub pp_shift_str: String,
    pub ok: bool,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CalibResults {
    pub intrinsic: Vec<IntrinsicResult>,
    pub extrinsic: Vec<ExtrinsicResult>,
    pub consistency: Vec<ConsistencyResult>,
    pub imu_bias: Vec<ImuBiasResult>,
    pub xml_checks: Vec<XmlCheckResult>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct IntrinsicResult {
    pub camera: String,
    pub rms: f64,
    pub threshold: f64,
    pub result: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ExtrinsicResult {
    pub stage: String,
    pub rms: f64,
    pub threshold: f64,
    pub strict_less: bool,
    pub result: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ConsistencyResult {
    pub label: String,
    pub fl_diff_pct: f64,
    pub pp_shift_str: String,
    pub result: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ImuBiasResult {
    pub item: String,
    pub value: f64,
    pub threshold: f64,
    pub result: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct XmlCheckResult {
    pub item: String,
    pub exists: bool,
    pub result: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CalibOverallResult {
    pub overall: String,
    pub failures: Vec<String>,
}

impl CalibReportData {
    /// 从 parse_calib.py 输出的 JSON 构建报告数据
    pub fn from_json(
        sn: &str,
        cpu_id: &str,
        json: &serde_json::Value,
        failures: Vec<String>,
    ) -> Result<Self, String> {
        let calib_detail: CalibDetail =
            serde_json::from_value(json.clone()).map_err(|e| e.to_string())?;

        let overall = calib_detail.overall.clone();

        Ok(Self {
            sn: sn.to_string(),
            cpu_id: cpu_id.to_string(),
            generated_at: chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
            calib: calib_detail,
            result: CalibOverallResult { overall, failures },
        })
    }
}

/// 生成标定 JSON 报告
pub fn generate_json_report(
    report: &CalibReportData,
    output_dir: &Path,
) -> Result<String, String> {
    let json_path = output_dir.join("calib_report.json");
    let json = serde_json::to_string_pretty(report).map_err(|e| e.to_string())?;
    std::fs::write(&json_path, json).map_err(|e| e.to_string())?;
    Ok(json_path.to_string_lossy().to_string())
}

/// 生成标定 Text 报告
pub fn generate_text_report(
    report: &CalibReportData,
    output_dir: &Path,
) -> Result<String, String> {
    let txt_path = output_dir.join("calib_report.txt");
    let mut content = String::new();

    let sep = "=".repeat(60);
    let dash = "-".repeat(60);

    // 标题
    content.push_str(&sep);
    content.push('\n');
    content.push_str("              VR 设备标定验证报告\n");
    content.push_str(&sep);
    content.push_str("\n\n");

    // 头部信息
    content.push_str(&format!("设备序列号: {}\n", report.sn));
    content.push_str(&format!("CPU ID: {}\n", report.cpu_id));
    content.push_str(&format!("生成时间: {}\n", report.generated_at));
    let overall_str = if report.result.overall == "PASS" {
        "[PASS]"
    } else {
        "[FAIL]"
    };
    content.push_str(&format!("整体结果: {}\n\n", overall_str));

    // 一、设备基本信息
    content.push_str(&dash);
    content.push_str("\n一、设备基本信息\n");
    content.push_str(&dash);
    content.push('\n');
    content.push_str(&format!("  设备 UID  : {}\n", report.calib.device_uid));

    // 标定耗时
    if let Some(ct) = report.calib.log_data.get("calibration_time") {
        if let Some(det_s) = ct.get("detection_s").and_then(|v| v.as_f64()) {
            let cal_s = ct.get("calibration_s").and_then(|v| v.as_f64()).unwrap_or(0.0);
            let total = ct.get("total_s").and_then(|v| v.as_f64()).unwrap_or(det_s + cal_s);
            content.push_str(&format!(
                "  标定耗时  : 检测 {:.1}s + 优化 {:.1}s = {:.1}s\n",
                det_s, cal_s, total
            ));
        }
    }
    content.push_str(&format!(
        "  摄像头数量 : {}\n",
        if let Some(cams) = report.calib.cameras.as_object() {
            cams.len()
        } else {
            0
        }
    ));

    // 二、摄像头内参
    content.push('\n');
    content.push_str(&dash);
    content.push_str("\n二、摄像头内参\n");
    content.push_str(&dash);
    content.push('\n');
    content.push_str(&format!(
        "  {:<18} {:>10} {:>12} {:>22} {:>24} {:>8}\n",
        "摄像头", "分辨率", "焦距(px)", "主点(px)", "模型", "快门"
    ));
    content.push_str(&format!("  {}\n", "-".repeat(96)));

    if let Some(cams) = report.calib.cameras.as_object() {
        let mut cam_names: Vec<&String> = cams.keys().collect();
        cam_names.sort_by_key(|name| {
            cams[*name]
                .get("id")
                .and_then(|v| v.as_i64())
                .unwrap_or(999) as i32
        });
        for name in cam_names {
            if let Some(cam) = cams[name].as_object() {
                let size = cam.get("size").and_then(|v| v.as_array());
                let fl = cam.get("focal_length").and_then(|v| v.as_array());
                let pp = cam.get("principal_point").and_then(|v| v.as_array());
                let model = cam
                    .get("model")
                    .and_then(|v| v.as_str())
                    .unwrap_or("N/A");
                let is_rolling = cam
                    .get("is_rolling_shutter")
                    .and_then(|v| v.as_bool())
                    .unwrap_or(false);
                let shutter = if is_rolling { "Rolling" } else { "Global" };

                if let (Some(size), Some(fl), Some(pp)) = (size, fl, pp) {
                    let w = size.get(0).and_then(|v| v.as_f64()).unwrap_or(0.0) as i32;
                    let h = size.get(1).and_then(|v| v.as_f64()).unwrap_or(0.0) as i32;
                    let fl_val = fl.get(0).and_then(|v| v.as_f64()).unwrap_or(0.0);
                    let pp_x = pp.get(0).and_then(|v| v.as_f64()).unwrap_or(0.0);
                    let pp_y = pp.get(1).and_then(|v| v.as_f64()).unwrap_or(0.0);
                    content.push_str(&format!(
                        "  {:<18} {}x{:<4} {:>12.2} ({:.1}, {:.1}){:>10} {:>24} {:>8}\n",
                        name, w, h, fl_val, pp_x, pp_y, "", model, shutter
                    ));
                }
            }
        }
    }

    // 三、标定板检测率
    content.push('\n');
    content.push_str(&dash);
    content.push_str("\n三、标定板检测率\n");
    content.push_str(&dash);
    content.push('\n');
    content.push_str(&format!(
        "  {:<18} {:>12} {:>12} {:>14} {:>10}\n",
        "摄像头", "A板", "B板", "综合检测率", "评级"
    ));
    content.push_str(&format!("  {}\n", "-".repeat(70)));

    if let Some(det) = report.calib.log_data.get("detection").and_then(|v| v.as_object()) {
        if let Some(cams) = report.calib.cameras.as_object() {
            let mut cam_names: Vec<&String> = cams.keys().collect();
            cam_names.sort_by_key(|name| {
                cams[*name]
                    .get("id")
                    .and_then(|v| v.as_i64())
                    .unwrap_or(999) as i32
            });
            for name in cam_names {
                if let Some(d) = det.get(name).and_then(|v| v.as_object()) {
                    let targets: Vec<&String> = d.keys().collect();
                    let det_a = d
                        .get(targets.get(0).unwrap_or(&&String::new()).as_str())
                        .and_then(|v| v.as_array());
                    let det_b = d
                        .get(targets.get(1).unwrap_or(&&String::new()).as_str())
                        .and_then(|v| v.as_array());

                    let (a_found, a_total) = if let Some(arr) = det_a {
                        (
                            arr.get(0).and_then(|v| v.as_i64()).unwrap_or(0) as i32,
                            arr.get(1).and_then(|v| v.as_i64()).unwrap_or(0) as i32,
                        )
                    } else {
                        (0, 0)
                    };
                    let (b_found, b_total) = if let Some(arr) = det_b {
                        (
                            arr.get(0).and_then(|v| v.as_i64()).unwrap_or(0) as i32,
                            arr.get(1).and_then(|v| v.as_i64()).unwrap_or(0) as i32,
                        )
                    } else {
                        (0, 0)
                    };

                    let total_det = a_found + b_found;
                    let total_all = a_total + b_total;
                    let rate = if total_all > 0 {
                        (total_det as f64 / total_all as f64) * 100.0
                    } else {
                        0.0
                    };

                    let rating = if rate >= 60.0 {
                        "[**] EXCELLENT"
                    } else if rate >= 45.0 {
                        "[OK] GOOD"
                    } else if rate >= 30.0 {
                        "[--] ACCEPTABLE"
                    } else {
                        "[!!] POOR"
                    };

                    content.push_str(&format!(
                        "  {:<18} {:>4}/{:<6} {:>4}/{:<6} {:>13.1}%  {}\n",
                        name, a_found, a_total, b_found, b_total, rate, rating
                    ));
                }
            }
        }
    }

    // 四、内参标定精度 (RMS 残差)
    content.push('\n');
    content.push_str(&dash);
    content.push_str("\n四、内参标定精度 (RMS 残差)\n");
    content.push_str(&dash);
    content.push('\n');
    content.push_str(&format!(
        "  {:<18} {:>10} {:>10} {:>10} {:>14} {:>10}\n",
        "摄像头", "残差(px)", "约束数", "离群点%", "合格阈值(px)", "结果"
    ));
    content.push_str(&format!("  {}\n", "-".repeat(76)));

    for item in &report.calib.results.intrinsic {
        let icon = if item.result == "PASS" { "[OK]" } else { "[!!]" };
        content.push_str(&format!(
            "  {:<18} {:>10.4} {:>10} {:>9.3}%  {:>12.2}  {} {}\n",
            item.camera,
            item.rms,
            "", // constraints not in IntrinsicResult
            0.0,
            item.threshold,
            icon,
            item.result
        ));
    }

    // 五、联合标定精度
    content.push('\n');
    content.push_str(&dash);
    content.push_str("\n五、联合标定精度 (外参 + IMU)\n");
    content.push_str(&dash);
    content.push('\n');
    content.push_str(&format!(
        "  {:<55} {:>10} {:>16}\n",
        "阶段", "RMS(px)", "结果"
    ));
    content.push_str(&format!("  {}\n", "-".repeat(85)));

    for item in &report.calib.results.extrinsic {
        let display = if item.stage.len() > 55 {
            format!("{}...", &item.stage[..52])
        } else {
            item.stage.clone()
        };
        if item.stage == "Full-Extrinsics+Intrinsics-Extrinsics" {
            let icon = if item.result == "PASS" { "[OK]" } else { "[!!]" };
            content.push_str(&format!(
                "  {:<55} {:>10.4} {} {} (阈值 {} {})\n",
                display,
                item.rms,
                icon,
                item.result,
                if item.strict_less { "<" } else { "<=" },
                item.threshold
            ));
        } else {
            let rating = if item.rms <= 0.5 {
                "[**] EXCELLENT"
            } else if item.rms <= 0.8 {
                "[OK] GOOD"
            } else if item.rms <= 1.5 {
                "[--] ACCEPTABLE"
            } else {
                "[!!] POOR"
            };
            content.push_str(&format!(
                "  {:<55} {:>10.4} {}\n",
                display, item.rms, rating
            ));
        }
    }

    // 六、外参几何关系
    content.push('\n');
    content.push_str(&dash);
    content.push_str("\n六、外参几何关系 (相对 trackingA)\n");
    content.push_str(&dash);
    content.push('\n');
    content.push_str(&format!(
        "  {:<18} {:>10} {:>10} {:>16}\n",
        "摄像头", "基线(mm)", "主轴夹角", "角分辨率(px/°)"
    ));
    content.push_str(&format!("  {}\n", "-".repeat(60)));

    if let Some(ext) = report.calib.log_data.get("extrinsic").and_then(|v| v.as_object()) {
        if let Some(bl) = ext.get("baselines").and_then(|v| v.as_object()) {
            for name in ["trackingB", "ctrl-trackingA", "ctrl-trackingB", "rgb-left", "rgb-right"] {
                if let Some(b) = bl.get(name).and_then(|v| v.as_object()) {
                    let baseline = b.get("baseline_m").and_then(|v| v.as_f64()).unwrap_or(0.0) * 1000.0;
                    let angle = b.get("angle_deg").and_then(|v| v.as_f64()).unwrap_or(0.0);
                    let ppd = b.get("pixels_per_deg").and_then(|v| v.as_f64()).unwrap_or(0.0);
                    content.push_str(&format!(
                        "  {:<18} {:>10.1} {:>9.1}° {:>16.2}\n",
                        name, baseline, angle, ppd
                    ));
                }
            }
        }
    }

    // 七、摄像头一致性
    content.push('\n');
    content.push_str(&dash);
    content.push_str("\n七、摄像头一致性分析\n");
    content.push_str(&dash);
    content.push('\n');
    content.push_str(&format!(
        "  {:<24} {:>10} {:>16} {:>10}\n",
        "对比组", "焦距差%", "主点偏移(px)", "评级"
    ));
    content.push_str(&format!("  {}\n", "-".repeat(66)));

    for item in &report.calib.results.consistency {
        let icon = if item.result == "PASS" { "[OK]" } else { "[!!]" };
        let label = item.label.clone();
        // 简化标签
        let label = if label.contains("trackingA") && label.contains("trackingB") {
            "Tracking 组"
        } else if label.contains("ctrl-trackingA") && label.contains("ctrl-trackingB") {
            "Ctrl-Tracking 组"
        } else if label.contains("rgb-left") && label.contains("rgb-right") {
            "RGB 组"
        } else {
            &label
        };
        content.push_str(&format!(
            "  {:<24} {:>9.3}% {:>16} {} {}\n",
            label, item.fl_diff_pct, item.pp_shift_str, icon, item.result
        ));
    }

    // 八、IMU 标定结果
    content.push('\n');
    content.push_str(&dash);
    content.push_str("\n八、IMU 标定结果\n");
    content.push_str(&dash);
    content.push('\n');

    if let Some(imu) = report.calib.imu.as_object() {
        if let Some(v) = imu.get("moving_accel_noise").and_then(|v| v.as_f64()) {
            content.push_str(&format!("  加速度计噪声 : {:.6}\n", v));
        }
        if let Some(v) = imu.get("moving_gyro_noise").and_then(|v| v.as_f64()) {
            content.push_str(&format!("  陀螺仪噪声   : {:.6}\n", v));
        }
        if let Some(v) = imu.get("delta").and_then(|v| v.as_f64()) {
            content.push_str(&format!("  时间对齐     : {:.3} ms\n", v * 1000.0));
        }
        if let Some(ab) = imu.get("aBias").and_then(|v| v.as_array()) {
            let vals: Vec<f64> = ab.iter().filter_map(|v| v.as_f64()).collect();
            if vals.len() == 3 {
                content.push_str(&format!(
                    "  Accel bias   : ({:.4}, {:.4}, {:.4})\n",
                    vals[0], vals[1], vals[2]
                ));
            }
        }
        if let Some(wb) = imu.get("wBias").and_then(|v| v.as_array()) {
            let vals: Vec<f64> = wb.iter().filter_map(|v| v.as_f64()).collect();
            if vals.len() == 3 {
                content.push_str(&format!(
                    "  Gyro bias    : ({:.6}, {:.6}, {:.6})\n",
                    vals[0], vals[1], vals[2]
                ));
            }
        }
    }

    // 各摄像头时间对齐
    content.push('\n');
    content.push_str("  各摄像头时间对齐:\n");
    if let Some(cams) = report.calib.cameras.as_object() {
        let mut cam_names: Vec<&String> = cams.keys().collect();
        cam_names.sort_by_key(|name| {
            cams[*name]
                .get("id")
                .and_then(|v| v.as_i64())
                .unwrap_or(999) as i32
        });
        for name in cam_names {
            if let Some(ta) = cams[name]
                .get("time_alignment")
                .and_then(|v| v.as_f64())
            {
                content.push_str(&format!("    {:<18} delta = {:.4} ms\n", name, ta * 1000.0));
            }
        }
    }

    // 九、警告 & 异常
    content.push('\n');
    content.push_str(&dash);
    content.push_str("\n九、警告 & 异常\n");
    content.push_str(&dash);
    content.push('\n');

    let has_warnings = if let Some(warnings) = report.calib.log_data.get("warnings").and_then(|v| v.as_array()) {
        if !warnings.is_empty() {
            for warn in warnings.iter().take(10) {
                if let Some(text) = warn.as_str() {
                    content.push_str(&format!("  WARNING: {}\n", text));
                }
            }
            if warnings.len() > 10 {
                content.push_str(&format!("  ... 共 {} 条警告\n", warnings.len()));
            }
            true
        } else {
            false
        }
    } else {
        false
    };

    let has_special = if let Some(checks) = report.calib.log_data.get("special_checks").and_then(|v| v.as_array()) {
        if !checks.is_empty() {
            for check in checks {
                if let Some(text) = check.as_str() {
                    content.push_str(&format!("  CHECK: {}\n", text));
                }
            }
            true
        } else {
            false
        }
    } else {
        false
    };

    let has_xml_missing = !report.calib.xml_missing_checks.is_empty();
    if has_xml_missing {
        for item in &report.calib.xml_missing_checks {
            content.push_str(&format!("  WARNING: {}\n", item));
        }
    }

    if !has_warnings && !has_special && !has_xml_missing {
        content.push_str("  无警告\n");
    }

    // 十、失败原因
    content.push('\n');
    content.push_str(&dash);
    content.push_str("\n十、失败原因\n");
    content.push_str(&dash);
    content.push('\n');

    if report.result.failures.is_empty() {
        content.push_str("  （无）\n");
    } else {
        for (i, f) in report.result.failures.iter().enumerate() {
            content.push_str(&format!("  {}. {}\n", i + 1, f));
        }
    }

    // 十一、总结
    content.push('\n');
    content.push_str(&dash);
    content.push_str("\n十一、总结\n");
    content.push_str(&dash);
    content.push('\n');
    content.push_str(&format!("  总评            : {}\n", report.result.overall));

    // 联合标定残差
    if let Some(ext) = report.calib.log_data.get("extrinsic").and_then(|v| v.as_object()) {
        if let Some(rms) = ext
            .get("CalibrateIMU-robust-Trajectory-Extrinsics-Intrinsics-Full")
            .and_then(|v| v.as_object())
            .and_then(|v| v.get("rms"))
            .and_then(|v| v.as_f64())
        {
            content.push_str(&format!("  联合标定残差     : {:.4} px\n", rms));
        }
    }

    // 最弱摄像头
    let mut worst_cam = "N/A";
    let mut worst_rms = 0.0;
    for item in &report.calib.results.intrinsic {
        if item.rms > worst_rms {
            worst_rms = item.rms;
            worst_cam = &item.camera;
        }
    }
    content.push_str(&format!(
        "  内参最弱摄像头   : {} ({:.4} px)\n",
        worst_cam, worst_rms
    ));

    // 检测率最低
    if let Some(det) = report.calib.log_data.get("detection").and_then(|v| v.as_object()) {
        let mut worst_det_cam = "N/A";
        let mut worst_rate = 100.0;
        for (cam_name, d) in det {
            if let Some(dobj) = d.as_object() {
                let mut total_det = 0;
                let mut total_all = 0;
                for (_, v) in dobj {
                    if let Some(arr) = v.as_array() {
                        total_det += arr.get(0).and_then(|v| v.as_i64()).unwrap_or(0) as i32;
                        total_all += arr.get(1).and_then(|v| v.as_i64()).unwrap_or(0) as i32;
                    }
                }
                let rate = if total_all > 0 {
                    (total_det as f64 / total_all as f64) * 100.0
                } else {
                    0.0
                };
                if rate < worst_rate {
                    worst_rate = rate;
                    worst_det_cam = cam_name;
                }
            }
        }
        content.push_str(&format!(
            "  检测率最低摄像头 : {} ({:.1}%)\n",
            worst_det_cam, worst_rate
        ));
    }

    content.push('\n');
    content.push_str(&sep);
    content.push('\n');

    std::fs::write(&txt_path, content).map_err(|e| e.to_string())?;
    Ok(txt_path.to_string_lossy().to_string())
}

/// 生成标定 PDF 报告（调用 Python 脚本）
pub fn generate_pdf_report(
    report: &CalibReportData,
    output_dir: &Path,
    resource_dir: &Path,
) -> Result<String, String> {
    // 确保 JSON 报告已写入
    let json_path = output_dir.join("calib_report.json");
    let json = serde_json::to_string_pretty(report).map_err(|e| e.to_string())?;
    std::fs::write(&json_path, json).map_err(|e| e.to_string())?;

    let script_path = resource_dir.join("CheckResult").join("generate_calib_report.py");

    // 检查脚本是否存在（开发模式回退）
    let script_path = if script_path.exists() {
        script_path
    } else {
        let fallback = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("resources")
            .join("CheckResult")
            .join("generate_calib_report.py");
        if fallback.exists() {
            fallback
        } else {
            return Err(format!(
                "PDF 生成脚本不存在: {} 且回退路径也不存在",
                script_path.to_string_lossy()
            ));
        }
    };

    // 调用 Python 脚本
    let python_cmd = if std::process::Command::new("python3.12")
        .arg("--version")
        .output()
        .is_ok()
    {
        "python3.12"
    } else {
        "python3"
    };

    let output = std::process::Command::new(python_cmd)
        .arg(&script_path)
        .arg(&json_path)
        .arg(output_dir)
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
