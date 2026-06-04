use crate::models::VerifyData;
use regex::Regex;

pub fn verify_coverage(
    device_pull_path: &str,
    is_rgb: bool,
    is_tof: bool,
) -> Result<VerifyData, String> {
    let index = device_pull_path.rfind('/').ok_or("无效路径")?;
    let log_path = format!("{}/Calib.log", &device_pull_path[..index + 1]);

    let contents = std::fs::read_to_string(&log_path)
        .map_err(|e| format!("读取 Calib.log 失败: {}", e))?;

    let labels = vec![
        ("dof", vec!["trackingA", "trackingB", "ctrl-trackingA", "ctrl-trackingB"]),
        ("rgb", if is_rgb { vec!["rgb-right", "rgb-left"] } else { vec![] }),
        ("tof", if is_tof { vec!["depth"] } else { vec![] }),
    ];

    let mut result = VerifyData {
        dof: None,
        rgb: None,
        tof: None,
    };

    for (key, names) in labels {
        if names.is_empty() {
            continue;
        }

        let mut values = Vec::new();
        for name in names {
            let pattern = format!(r"Coverage in {}:\s+((?:AR DEBUG:\s[01X]+\s*)+)", regex::escape(name));
            let re = Regex::new(&pattern).map_err(|e| e.to_string())?;

            if let Some(captures) = re.captures(&contents) {
                let matched = captures.get(1).map(|m| m.as_str()).unwrap_or("");
                let bits: String = matched
                    .split('\n')
                    .map(|line| line.trim().trim_start_matches("AR DEBUG: "))
                    .filter(|line| !line.is_empty())
                    .collect();

                let total = bits.len();
                let zero_count = bits.matches('0').count();
                let x_count = bits.matches('X').count();
                let percentage = 100.0 - ((zero_count + x_count) as f64 / total as f64) * 100.0;
                values.push(percentage);
            } else {
                values.push(0.0);
            }
        }

        match key {
            "dof" => result.dof = Some(values),
            "rgb" => result.rgb = Some(values),
            "tof" => result.tof = Some(values),
            _ => {}
        }
    }

    Ok(result)
}

/// 覆盖率检查失败的单项信息
#[derive(Debug, Clone)]
pub struct CoverageFailure {
    pub camera_type: String,
    pub camera_name: String,
    pub coverage: f64,
    pub threshold: f64,
}

/// 检查阈值，返回 (是否通过, 失败项列表)
/// 失败项包含具体的摄像头名称、覆盖率和阈值
pub fn check_thresholds_detail(
    results: &VerifyData,
    thresholds: &crate::models::ThresholdConfig,
    is_rgb: bool,
    is_tof: bool,
) -> (bool, Vec<CoverageFailure>) {
    let mut failures = Vec::new();

    let camera_names = vec![
        ("dof", vec!["trackingA", "trackingB", "ctrl-trackingA", "ctrl-trackingB"]),
        ("rgb", if is_rgb { vec!["rgb-right", "rgb-left"] } else { vec![] }),
        ("tof", if is_tof { vec!["depth"] } else { vec![] }),
    ];

    for (ctype, names) in camera_names {
        if names.is_empty() {
            continue;
        }
        let (values, threshold) = match ctype {
            "dof" => (&results.dof, thresholds.dof),
            "rgb" => (&results.rgb, thresholds.rgb),
            "tof" => (&results.tof, thresholds.tof),
            _ => continue,
        };

        if let (Some(vals), Some(th)) = (values, threshold) {
            for (i, &v) in vals.iter().enumerate() {
                if v < th {
                    failures.push(CoverageFailure {
                        camera_type: match ctype {
                            "dof" => "6DOF",
                            "rgb" => "RGB",
                            "tof" => "TOF",
                            _ => ctype,
                        }.to_string(),
                        camera_name: names.get(i).unwrap_or(&"未知").to_string(),
                        coverage: v,
                        threshold: th,
                    });
                }
            }
        }
    }

    (failures.is_empty(), failures)
}

pub fn check_thresholds(results: &VerifyData, thresholds: &crate::models::ThresholdConfig) -> bool {
    fn check_array(arr: &Option<Vec<f64>>, threshold: Option<f64>) -> bool {
        match (arr, threshold) {
            (Some(arr), Some(th)) => arr.iter().all(|&v| v >= th),
            (Some(_), None) => true,
            (None, _) => true,
        }
    }

    check_array(&results.dof, thresholds.dof)
        && check_array(&results.rgb, thresholds.rgb)
        && check_array(&results.tof, thresholds.tof)
}
