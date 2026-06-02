#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VQ920 XR 设备标定结果解析脚本
解析 device_calibration.xml 和 Calib.log，输出结构化标定报告

退出码约定（供外部脚本/产线判断）：
- 0: 正常（报告生成成功，且总评为 PASS）
- 2: 不正常（报告生成成功，但存在多项失败）
- 20: 不正常（内参 RMS 超阈值）
- 21: 不正常（Full-Extrinsics+Intrinsics-Extrinsics RMS 超阈值）
- 22: 不正常（联合标定 RMS 超阈值）
- 23: 不正常（加速度计 bias 超阈值）
- 24: 不正常（陀螺仪 bias 超阈值）
- 25: 不正常（缺少 IMUNoise 节点）
- 26: 不正常（IMUNoise 缺少必填字段）
- 27: 不正常（检测率低于合格阈值）
- 10: 输入目录不存在
- 11: 缺少 device_calibration.xml
- 12: 缺少 Calib.log
- 13: XML 解析失败
- 14: Log 解析失败
- 15: 报告写入失败
- 19: 其他未分类执行错误
"""

import xml.etree.ElementTree as ET
import re
import math
import os
import sys
import argparse


# ────────────────────────────── 阈值配置 ──────────────────────────────
THRESHOLDS = {
    "intrinsic_rms_tracking": 0.5,   # Tracking (灰度) 摄像头内参 RMS 合格上限 (px)
    "intrinsic_rms_rgb": 1.3,         # RGB 摄像头内参 RMS 合格上限 (px)
    "full_extrinsics_intrinsics_rms_max": 0.5,  # Full-Extrinsics+Intrinsics-Extrinsics 阶段 RMS 合格上限 (严格小于)
    "joint_rms": {  # 联合标定 RMS (px)
        "excellent": 0.50,
        "good": 0.80,
        "acceptable": 1.50,
    },
    "detection_rate": {  # 标定板检测率 (%)
        "excellent": 60,
        "good": 45,
        "acceptable": 30,
    },
    "focal_length_diff_pct": 2.0,  # 同组焦距差异阈值 (%)
    "principal_point_shift_pct": 3.0,  # 同组主点偏移阈值 (% of image size)
    "outlier_pct": 0.1,  # 离群点比例阈值 (%)
    "accel_bias_max": 0.6,   # 加速度计 bias 分量绝对值上限
    "gyro_bias_max": 0.06,   # 陀螺仪 bias 分量绝对值上限
}


# 退出码定义
EXIT_OK = 0  # 正常：报告生成成功，且总评 PASS
EXIT_FAIL = 2  # 不正常：存在多项业务失败（组合失败）
EXIT_FAIL_INTRINSIC_RMS = 20  # 不正常：至少一个相机内参 RMS 超阈值
EXIT_FAIL_FULL_EXT_RMS = 21  # 不正常：Full-Extrinsics+Intrinsics-Extrinsics RMS 超阈值
EXIT_FAIL_JOINT_RMS = 22  # 不正常：联合标定 RMS 超阈值
EXIT_FAIL_ACCEL_BIAS = 23  # 不正常：加速度计 bias 超阈值
EXIT_FAIL_GYRO_BIAS = 24  # 不正常：陀螺仪 bias 超阈值
EXIT_FAIL_IMUNOISE_NODE_MISSING = 25  # 不正常：XML 缺少 IMUNoise 节点
EXIT_FAIL_IMUNOISE_FIELD_MISSING = 26  # 不正常：IMUNoise 缺少必填字段
EXIT_FAIL_DETECTION_RATE = 27  # 不正常：至少一个相机检测率低于合格阈值
EXIT_DIR_NOT_FOUND = 10  # 执行错误：输入目录不存在
EXIT_XML_MISSING = 11  # 执行错误：缺少 device_calibration.xml
EXIT_LOG_MISSING = 12  # 执行错误：缺少 Calib.log
EXIT_XML_PARSE_ERROR = 13  # 执行错误：XML 解析失败
EXIT_LOG_PARSE_ERROR = 14  # 执行错误：Log 解析失败
EXIT_REPORT_WRITE_ERROR = 15  # 执行错误：报告写入失败
EXIT_UNKNOWN_ERROR = 19  # 执行错误：其他未分类异常


def intrinsic_rms_limit(cam_name: str) -> float:
    """返回该相机内参 RMS 合格上限（px）：rgb-* 相机用宽松阈值，tracking 相机用严格阈值。"""
    if "rgb" in cam_name.lower():
        return THRESHOLDS["intrinsic_rms_rgb"]
    return THRESHOLDS["intrinsic_rms_tracking"]


def rating(value, thresholds, lower_is_better=True):
    """根据阈值给出评级: excellent / good / acceptable / poor"""
    if lower_is_better:
        if value <= thresholds["excellent"]:
            return "EXCELLENT"
        elif value <= thresholds["good"]:
            return "GOOD"
        elif value <= thresholds["acceptable"]:
            return "ACCEPTABLE"
        else:
            return "POOR"
    else:
        if value >= thresholds["excellent"]:
            return "EXCELLENT"
        elif value >= thresholds["good"]:
            return "GOOD"
        elif value >= thresholds["acceptable"]:
            return "ACCEPTABLE"
        else:
            return "POOR"


def rating_icon(level):
    icons = {"EXCELLENT": "[**]", "GOOD": "[OK]", "ACCEPTABLE": "[--]", "POOR": "[!!]"}
    return icons.get(level, "[??]")


# ─────────────────────────── XML 解析 ────────────────────────────────
def parse_xml(xml_path):
    """解析 device_calibration.xml"""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    device_uid = root.attrib.get("deviceUID", "unknown")

    cameras = {}
    for cam_elem in root.findall("Camera"):
        name = cam_elem.attrib.get("cam_name") or cam_elem.attrib.get("name")
        cam_id = int(cam_elem.attrib.get("id", -1))

        calib = cam_elem.find("Calibration")
        size = list(map(float, calib.attrib["size"].split()))
        pp = list(map(float, calib.attrib["principal_point"].split()))
        fl = list(map(float, calib.attrib["focal_length"].split()))
        model = calib.attrib.get("model", "")
        rd = list(map(float, calib.attrib["radial_distortion"].split()))
        dist_limit = float(calib.attrib.get("distortion_limit", "0"))
        undist_limit = float(calib.attrib.get("undistortion_limit", "0"))

        rig = cam_elem.find("Rig")
        translation = list(map(float, rig.attrib["translation"].split()))
        rotation = list(map(float, rig.attrib["rowMajorRotationMat"].split()))

        rs_elem = cam_elem.find("RollingShutter")
        is_rolling = rs_elem is not None and rs_elem.attrib.get("isRollingShutter") == "true"
        linetime = float(rs_elem.attrib["linetime"]) if rs_elem is not None else None

        ta_elem = cam_elem.find("TimeAlignment")
        time_delta = float(ta_elem.attrib["delta"]) if ta_elem is not None else None

        cd = cam_elem.find("CaptureDetails")
        capture = {k: int(cd.attrib[k]) for k in cd.attrib} if cd is not None else {}

        vig = cam_elem.find("VignettingCorrection")
        vignette = None
        if vig is not None:
            vignette = {
                "center": list(map(float, vig.attrib["center"].split())),
                "coeffs": list(map(float, vig.attrib["coeffs"].split())),
            }

        cameras[name] = {
            "id": cam_id,
            "size": size,
            "principal_point": pp,
            "focal_length": fl,
            "model": model,
            "radial_distortion": rd,
            "distortion_limit": dist_limit,
            "undistortion_limit": undist_limit,
            "translation": translation,
            "rotation": rotation,
            "is_rolling_shutter": is_rolling,
            "linetime": linetime,
            "time_alignment": time_delta,
            "capture_details": capture,
            "vignetting": vignette,
        }

    # IMU / SFConfig
    sf = root.find("SFConfig")
    imu = {}
    xml_missing_checks = []
    if sf is not None:
        si = sf.find("Stateinit")
        if si is not None:
            imu["ombc"] = list(map(float, si.attrib["ombc"].split()))
            imu["tbc"] = list(map(float, si.attrib["tbc"].split()))
            imu["aBias"] = list(map(float, si.attrib["aBias"].split()))
            imu["wBias"] = list(map(float, si.attrib["wBias"].split()))
            imu["delta"] = float(si.attrib.get("delta", 0))
        noise = sf.find("IMUNoise")
        if noise is not None:
            # 必检项(默认): 只要求移动状态噪声字段。
            # stationaryAccelNoise / stationaryGyroNoise 改为可选，不再作为默认失败项。
            required_noise_fields = {
                "movingAccelNoise": "movingAccelNoise",
                "movingGyroNoise": "movingGyroNoise",
            }
            for attr_name, display_name in required_noise_fields.items():
                if attr_name not in noise.attrib:
                    xml_missing_checks.append(
                        f"device_calibration.xml 缺少 IMUNoise 字段: {display_name}"
                    )

            if "movingAccelNoise" in noise.attrib:
                imu["moving_accel_noise"] = float(noise.attrib["movingAccelNoise"])
            if "movingGyroNoise" in noise.attrib:
                imu["moving_gyro_noise"] = float(noise.attrib["movingGyroNoise"])
            if "stationaryAccelNoise" in noise.attrib:
                imu["stationary_accel_noise"] = float(noise.attrib["stationaryAccelNoise"])
            if "stationaryGyroNoise" in noise.attrib:
                imu["stationary_gyro_noise"] = float(noise.attrib["stationaryGyroNoise"])
        else:
            xml_missing_checks.append("device_calibration.xml 缺少 IMUNoise 节点")

    # 从 XML 尾部注释中提取检测率等统计
    detection_from_xml = {}
    calib_time_info = {}
    target_ar_error = {}
    try:
        with open(xml_path, "r") as f:
            content = f.read()
        comment_match = re.search(r"<!--Device ID.*?-->", content, re.DOTALL)
        if comment_match:
            comment_text = comment_match.group()
            # 解析检测率
            for m in re.finditer(
                r"Target (XRCalib-\w+) detected in camera ([\w-]+) (\d+)/(\d+) times",
                comment_text,
            ):
                target, cam, detected, total = m.groups()
                if cam not in detection_from_xml:
                    detection_from_xml[cam] = {}
                detection_from_xml[cam][target] = (int(detected), int(total))
            # 解析标定时间
            m = re.search(
                r"Calibration time (.+?)(?:\n|$)",
                comment_text,
            )
            if m:
                calib_time_line = m.group(1).strip()
            m = re.search(
                r"Pattern detection time ([0-9.]+)s, calibration time ([0-9.]+)s, total ([0-9.]+)s",
                comment_text,
            )
            if m:
                calib_time_info = {
                    "detection_s": float(m.group(1)),
                    "calibration_s": float(m.group(2)),
                    "total_s": float(m.group(3)),
                }
            # 解析 AR error
            for m in re.finditer(r"(XRCalib-\w+):([0-9.]+)", comment_text):
                target_ar_error[m.group(1)] = float(m.group(2))
    except Exception:
        pass

    return (
        device_uid,
        cameras,
        imu,
        detection_from_xml,
        calib_time_info,
        target_ar_error,
        xml_missing_checks,
    )


# ─────────────────────────── Log 解析 ────────────────────────────────
def parse_log(log_path):
    """解析 Calib.log 中的关键指标"""
    results = {
        "detection": {},
        "selection": {},
        "intrinsic": {},
        "extrinsic": {},
        "warnings": [],
        "special_checks": [],
        "calibration_time": {},
        "target_ar_error": {},
    }

    with open(log_path, "r", errors="replace") as f:
        content = f.read()

    # Pattern detection
    det_pattern = re.compile(
        r"Target (XRCalib-\w+) detected in camera ([\w-]+) (\d+)/(\d+) times"
    )
    for m in det_pattern.finditer(content):
        target, cam, detected, total = m.groups()
        if cam not in results["detection"]:
            results["detection"][cam] = {}
        results["detection"][cam][target] = (int(detected), int(total))

    # Pattern selection
    sel_pattern = re.compile(
        r"([\w-]+)[\s-]Remove redundant detections: Selected (\d+)/(\d+) timestamps"
    )
    for m in sel_pattern.finditer(content):
        cam, selected, total = m.groups()
        results["selection"][cam] = (int(selected), int(total))

    # Intrinsic calibration
    # 先找离群点信息
    outlier_blocks = re.findall(
        r"(\d+)/(\d+) target prior estimations failed; (\d+)/(\d+) outlier dot detections removed \(([0-9.]+)%\)",
        content,
    )

    intrin_pattern = re.compile(
        r"Full-([\w-]+) (\d+) constraints, (\d+) vbles, (\d+) free vbles, ([0-9.]+) pixels RMS residual"
    )
    intrin_matches = list(intrin_pattern.finditer(content))
    for i, m in enumerate(intrin_matches):
        cam = m.group(1)
        constraints = int(m.group(2))
        rms = float(m.group(5))
        outlier_info = outlier_blocks[i * 2] if i * 2 < len(outlier_blocks) else None
        outlier_pct = float(outlier_info[4]) if outlier_info else 0
        results["intrinsic"][cam] = {
            "constraints": constraints,
            "rms": rms,
            "outlier_pct": outlier_pct,
        }

    # Extrinsic / IMU calibration
    # Note: stage name may contain '+' (e.g. Full-Extrinsics+Intrinsics-Extrinsics),
    # so [\w+\-] is used. When a stage appears multiple times the last match wins
    # (dict key overwrite), which gives the final-pass RMS as required.
    ext_pattern = re.compile(
        r"(CalibrateIMU[\w-]+|Full-Extrinsics[\w+\-]+) (\d+) constraints, (\d+) vbles, (\d+) free vbles, ([0-9.]+) pixels RMS residual"
    )
    for m in ext_pattern.finditer(content):
        stage = m.group(1)
        rms = float(m.group(5))
        results["extrinsic"][stage] = {
            "constraints": int(m.group(2)),
            "rms": rms,
        }

    # Baseline info
    baseline_pattern = re.compile(
        r"([\w-]+) after extrinsic optimization: Baseline.*?([0-9.]+)m;.*?([0-9.]+) degrees.*?([0-9.]+) pixels/degree"
    )
    for m in baseline_pattern.finditer(content):
        cam = m.group(1)
        if "baselines" not in results["extrinsic"]:
            results["extrinsic"]["baselines"] = {}
        results["extrinsic"]["baselines"][cam] = {
            "baseline_m": float(m.group(2)),
            "angle_deg": float(m.group(3)),
            "pixels_per_deg": float(m.group(4)),
        }

    # Warnings
    warn_pattern = re.compile(r"AR WARNING: (.+)")
    for m in warn_pattern.finditer(content):
        results["warnings"].append(m.group(1))

    # XRCalib 特定检查项
    # 示例: Minimum angular acceleration is 14.967816 rad/s²; recommended minimum is 15
    min_ang_accel_pattern = re.compile(
        r"Minimum angular acceleration is\s+[0-9.]+\s+rad/s(?:²|\^2);\s+recommended minimum is\s+[0-9.]+"
    )
    for m in min_ang_accel_pattern.finditer(content):
        results["special_checks"].append(m.group(0))

    # # 示例: Too few measurements to calculate IMU0 Accel noise when stationary
    # imu_noise_pattern = re.compile(
    #     r"Too few measurements to calculate IMU\d+\s+Accel noise when stationary"
    # )
    # for m in imu_noise_pattern.finditer(content):
    #     results["special_checks"].append(m.group(0))

    # Calibration time
    time_pattern = re.compile(
        r"Pattern detection time ([0-9.]+)s, calibration time ([0-9.]+)s, total ([0-9.]+)s"
    )
    m = time_pattern.search(content)
    if m:
        results["calibration_time"] = {
            "detection_s": float(m.group(1)),
            "calibration_s": float(m.group(2)),
            "total_s": float(m.group(3)),
        }

    # Target AR error
    ar_pattern = re.compile(r"(XRCalib-\w+):([0-9.]+)")
    for m in ar_pattern.finditer(content):
        results["target_ar_error"][m.group(1)] = float(m.group(2))

    return results


# ─────────────────────────── 报告生成 ────────────────────────────────
def rotation_matrix_to_angles(R_flat):
    """3x3 行主序旋转矩阵 → 欧拉角 (度)"""
    R = [R_flat[i * 3 : (i + 1) * 3] for i in range(3)]
    ry = math.degrees(math.asin(max(-1, min(1, R[0][2]))))
    rz = math.degrees(math.atan2(-R[0][1], R[0][0]))
    rx = math.degrees(math.atan2(-R[1][2], R[2][2]))
    return rx, ry, rz


def vec_norm(v):
    return math.sqrt(sum(x * x for x in v))


def angle_between_axes(R1_flat, R2_flat):
    """计算两个相机主轴之间的夹角 (度)"""
    # 主轴 = Z 轴 = 旋转矩阵第三列
    z1 = [R1_flat[2], R1_flat[5], R1_flat[8]]
    z2 = [R2_flat[2], R2_flat[5], R2_flat[8]]
    dot = sum(a * b for a, b in zip(z1, z2))
    cos_a = max(-1, min(1, abs(dot)))
    return math.degrees(math.acos(cos_a))


def collect_bias_violations(imu):
    """收集 IMU bias 超阈值项。"""
    bias_violations = []
    ab_max = THRESHOLDS["accel_bias_max"]
    wb_max = THRESHOLDS["gyro_bias_max"]

    if "aBias" in imu:
        for i, v in enumerate(imu["aBias"]):
            if abs(v) > ab_max:
                bias_violations.append(
                    f"Accel bias[{i}] = {v:.4f} 超阈值 ±{ab_max}"
                )

    if "wBias" in imu:
        for i, v in enumerate(imu["wBias"]):
            if abs(v) > wb_max:
                bias_violations.append(
                    f"Gyro bias[{i}] = {v:.6f} 超阈值 ±{wb_max}"
                )

    return bias_violations


def calc_detection_rate(cam_det_data):
    """计算单个摄像头的综合检测率（%）。
    cam_det_data: {target_name: (detected, total), ...}
    """
    total_det = sum(v[0] for v in cam_det_data.values())
    total_all = sum(v[1] for v in cam_det_data.values())
    return (total_det / total_all * 100) if total_all > 0 else 0.0


def collect_detection_rate_failures(det):
    """收集检测率低于阈值的摄像头。
    返回: [(cam_name, rate), ...]
    """
    failures = []
    threshold = THRESHOLDS["detection_rate"]["acceptable"]
    for cam_name in det:
        rate = calc_detection_rate(det[cam_name])
        if rate < threshold:
            failures.append((cam_name, rate))
    return failures


def collect_failure_codes(log_data, imu, xml_missing_checks=None):
    """收集失败原因对应的退出码。"""
    fail_codes = []
    intrin = log_data.get("intrinsic", {})
    ext = log_data.get("extrinsic", {})
    det = log_data.get("detection", {})
    xml_missing_checks = xml_missing_checks or []

    # 1) 内参 RMS 超阈值
    if any(intrin[cam]["rms"] > intrinsic_rms_limit(cam) for cam in intrin):
        fail_codes.append(EXIT_FAIL_INTRINSIC_RMS)

    # 2) Full-Extrinsics+Intrinsics-Extrinsics 阶段 RMS 超阈值
    full_ext_rms = ext.get("Full-Extrinsics+Intrinsics-Extrinsics", {}).get("rms", "N/A")
    if isinstance(full_ext_rms, float) and full_ext_rms >= THRESHOLDS["full_extrinsics_intrinsics_rms_max"]:
        fail_codes.append(EXIT_FAIL_FULL_EXT_RMS)

    # 3) 联合标定 RMS 超阈值
    joint_rms = ext.get("CalibrateIMU-robust-Trajectory-Extrinsics-Intrinsics-Full", {}).get("rms", "N/A")
    if isinstance(joint_rms, float) and joint_rms > THRESHOLDS["joint_rms"]["acceptable"]:
        fail_codes.append(EXIT_FAIL_JOINT_RMS)

    # 4) IMU bias 超阈值（区分 accel / gyro）
    accel_bias_fail = any(abs(v) > THRESHOLDS["accel_bias_max"] for v in imu.get("aBias", []))
    gyro_bias_fail = any(abs(v) > THRESHOLDS["gyro_bias_max"] for v in imu.get("wBias", []))
    if accel_bias_fail:
        fail_codes.append(EXIT_FAIL_ACCEL_BIAS)
    if gyro_bias_fail:
        fail_codes.append(EXIT_FAIL_GYRO_BIAS)

    # 5) IMUNoise 缺失（节点 / 字段）
    if any("缺少 IMUNoise 节点" in item for item in xml_missing_checks):
        fail_codes.append(EXIT_FAIL_IMUNOISE_NODE_MISSING)
    if any("缺少 IMUNoise 字段" in item for item in xml_missing_checks):
        fail_codes.append(EXIT_FAIL_IMUNOISE_FIELD_MISSING)

    # 6) 检测率低于合格阈值
    det_rate_failures = collect_detection_rate_failures(det)
    if det_rate_failures:
        fail_codes.append(EXIT_FAIL_DETECTION_RATE)

    # 去重并保持顺序
    dedup = []
    for code in fail_codes:
        if code not in dedup:
            dedup.append(code)
    return dedup


def evaluate_overall_status(log_data, imu, xml_missing_checks=None):
    """返回总体状态字符串: PASS / FAIL。"""
    return "PASS" if not collect_failure_codes(log_data, imu, xml_missing_checks) else "FAIL"


def resolve_status_and_exit_code(log_data, imu, xml_missing_checks=None):
    """统一计算总评与退出码，确保 PASS 仅在 EXIT_OK 时成立。"""
    fail_codes = collect_failure_codes(log_data, imu, xml_missing_checks)
    if not fail_codes:
        exit_code = EXIT_OK
    elif len(fail_codes) == 1:
        exit_code = fail_codes[0]
    else:
        exit_code = EXIT_FAIL

    overall = "PASS" if exit_code == EXIT_OK else "FAIL"
    return overall, fail_codes, exit_code


def generate_report(device_uid, cameras, imu, log_data, xml_missing_checks=None):
    """生成结构化标定报告"""
    lines = []
    sep = "=" * 72

    def w(text=""):
        lines.append(text)

    def section(title):
        w()
        w(sep)
        w(f"  {title}")
        w(sep)

    def subsection(title):
        w()
        w(f"--- {title} ---")

    # ── 基本信息 ──
    section("设备基本信息")
    w(f"  设备 UID  : {device_uid}")
    ct = log_data["calibration_time"]
    if ct:
        w(f"  标定耗时  : 检测 {ct['detection_s']:.1f}s + 优化 {ct['calibration_s']:.1f}s = {ct['total_s']:.1f}s")
    ar = log_data["target_ar_error"]
    if ar:
        w(f"  标定板 AR 误差上限 : {', '.join(f'{k}: {v:.5f}' for k, v in ar.items())}")
    w(f"  摄像头数量 : {len(cameras)}")

    # ── 摄像头内参 ──
    section("摄像头内参")
    w(f"  {'摄像头':<18} {'分辨率':>10} {'焦距(px)':>12} {'主点(px)':>22} {'模型':>22} {'快门':>6}")
    w("  " + "-" * 96)
    for name in sorted(cameras, key=lambda n: cameras[n]["id"]):
        c = cameras[name]
        w_val, h_val = c["size"]
        fl = c["focal_length"][0]
        pp = c["principal_point"]
        shutter = "Rolling" if c["is_rolling_shutter"] else "Global"
        w(f"  {name:<18} {int(w_val)}x{int(h_val):>4} {fl:>12.2f} ({pp[0]:.1f}, {pp[1]:.1f}){'':>8} {c['model']:>22} {shutter:>6}")

    # ── 标定板检测率 ──
    section("标定板检测率 & 清晰度评估")
    w(f"  {'摄像头':<18} {'A板':>12} {'B板':>12} {'综合检测率':>12} {'合格阈值':>12} {'结果':>10}")
    w("  " + "-" * 80)
    det = log_data["detection"]
    det_rate_threshold = THRESHOLDS["detection_rate"]["acceptable"]
    for name in sorted(cameras, key=lambda n: cameras[n]["id"]):
        if name in det:
            d = det[name]
            targets = sorted(d.keys())
            det_a = d.get(targets[0], (0, 0)) if len(targets) > 0 else (0, 0)
            det_b = d.get(targets[1], (0, 0)) if len(targets) > 1 else (0, 0)
            rate = calc_detection_rate(d)
            ok = rate >= det_rate_threshold
            icon = "[OK]" if ok else "[!!]"
            result = "PASS" if ok else "FAIL"
            w(f"  {name:<18} {det_a[0]:>4}/{det_a[1]:<4} {det_b[0]:>4}/{det_b[1]:<4} {rate:>10.1f}%  {det_rate_threshold:>10.1f}%  {icon} {result}")

    # ── 内参精度 ──
    section("内参标定精度 (RMS 残差)")
    w(f"  {'摄像头':<18} {'残差(px)':>10} {'约束数':>10} {'离群点%':>10} {'合格阈值(px)':>14} {'结果':>8}")
    w("  " + "-" * 72)
    intrin = log_data["intrinsic"]
    for name in sorted(cameras, key=lambda n: cameras[n]["id"]):
        if name in intrin:
            d = intrin[name]
            lim = intrinsic_rms_limit(name)
            ok = d["rms"] <= lim
            icon = "[OK]" if ok else "[!!]"
            result = "PASS" if ok else "FAIL"
            w(f"  {name:<18} {d['rms']:>10.4f} {d['constraints']:>10} {d['outlier_pct']:>9.3f}%  {lim:>12.2f}  {icon} {result}")

    # ── 联合标定精度 ──
    section("联合标定精度 (外参 + IMU)")
    ext = log_data["extrinsic"]
    w(f"  {'阶段':<55} {'RMS(px)':>10} {'评级':>10}")
    w("  " + "-" * 80)
    for stage in [
        "CalibrateIMU-robust-biasConstraint-Trajectory-Extrinsics-RSPrior",
        "Full-Extrinsics+Intrinsics-Extrinsics",
        "CalibrateIMU-robust-Trajectory-Extrinsics-Intrinsics-Full",
    ]:
        if stage in ext:
            rms = ext[stage]["rms"]
            display = stage[:52] + "..." if len(stage) > 55 else stage
            if stage == "Full-Extrinsics+Intrinsics-Extrinsics":
                lim = THRESHOLDS["full_extrinsics_intrinsics_rms_max"]
                ok = rms < lim
                icon = "[OK]" if ok else "[!!]"
                result = "PASS" if ok else "FAIL"
                w(f"  {display:<55} {rms:>10.4f} {icon} {result} (阈值 < {lim})")
            else:
                r = rating(rms, THRESHOLDS["joint_rms"])
                w(f"  {display:<55} {rms:>10.4f} {rating_icon(r)} {r}")

    # ── 外参几何 ──
    subsection("外参几何关系 (相对 trackingA)")
    bl = ext.get("baselines", {})
    w(f"  {'摄像头':<18} {'基线(mm)':>10} {'主轴夹角':>10} {'角分辨率(px/°)':>16}")
    w("  " + "-" * 60)
    for name in ["trackingB", "ctrl-trackingA", "ctrl-trackingB", "rgb-left", "rgb-right"]:
        if name in bl:
            b = bl[name]
            w(f"  {name:<18} {b['baseline_m']*1000:>10.1f} {b['angle_deg']:>9.1f}° {b['pixels_per_deg']:>14.2f}")

    # ── 一致性分析 ──
    section("摄像头一致性分析")

    pairs = [
        ("trackingA", "trackingB", "Tracking 组"),
        ("ctrl-trackingA", "ctrl-trackingB", "Ctrl-Tracking 组"),
        ("rgb-left", "rgb-right", "RGB 组"),
    ]

    w(f"  {'对比组':<24} {'焦距差%':>10} {'主点偏移(px)':>16} {'评级':>10}")
    w("  " + "-" * 66)

    issues = []
    for n1, n2, label in pairs:
        if n1 not in cameras or n2 not in cameras:
            continue
        c1, c2 = cameras[n1], cameras[n2]
        fl1, fl2 = c1["focal_length"][0], c2["focal_length"][0]
        fl_diff_pct = abs(fl1 - fl2) / ((fl1 + fl2) / 2) * 100

        pp1, pp2 = c1["principal_point"], c2["principal_point"]
        pp_shift = (abs(pp1[0] - pp2[0]), abs(pp1[1] - pp2[1]))

        # 主点偏移占图像尺寸比例
        img_size = max(c1["size"])
        pp_shift_pct = math.sqrt(pp_shift[0] ** 2 + pp_shift[1] ** 2) / img_size * 100

        consistency = "GOOD"
        if fl_diff_pct > THRESHOLDS["focal_length_diff_pct"]:
            consistency = "POOR"
            issues.append(f"{n1} vs {n2}: 焦距差异 {fl_diff_pct:.2f}% 超过阈值 {THRESHOLDS['focal_length_diff_pct']}%")
        if pp_shift_pct > THRESHOLDS["principal_point_shift_pct"]:
            consistency = "ACCEPTABLE" if consistency == "GOOD" else consistency
            issues.append(f"{n1} vs {n2}: 主点偏移 {pp_shift_pct:.2f}% 超过阈值 {THRESHOLDS['principal_point_shift_pct']}%")

        r = rating_icon(consistency)
        w(f"  {label:<24} {fl_diff_pct:>9.3f}% ({pp_shift[0]:.1f}, {pp_shift[1]:.1f}){'':>4} {r} {consistency}")

    # 同组内参残差对比
    subsection("同组残差一致性")
    for n1, n2, label in pairs:
        if n1 in intrin and n2 in intrin:
            rms1, rms2 = intrin[n1]["rms"], intrin[n2]["rms"]
            diff = abs(rms1 - rms2)
            w(f"  {label}: {n1}={rms1:.4f}px, {n2}={rms2:.4f}px, 差值={diff:.4f}px")

    # ── IMU ──
    section("IMU 标定结果")
    if imu:
        w(f"  加速度计噪声 : {imu.get('moving_accel_noise', 'N/A')}")
        w(f"  陀螺仪噪声   : {imu.get('moving_gyro_noise', 'N/A')}")
        w(f"  时间对齐     : {imu.get('delta', 'N/A') * 1000:.3f} ms" if "delta" in imu else "")
        if "aBias" in imu:
            ab = imu["aBias"]
            ab_max = THRESHOLDS["accel_bias_max"]
            ab_ok = all(abs(v) <= ab_max for v in ab)
            ab_flag = "" if ab_ok else f"  [!!] 超阈值 (限 ±{ab_max})"
            w(f"  Accel bias   : ({ab[0]:.4f}, {ab[1]:.4f}, {ab[2]:.4f}){ab_flag}")
        if "wBias" in imu:
            wb = imu["wBias"]
            wb_max = THRESHOLDS["gyro_bias_max"]
            wb_ok = all(abs(v) <= wb_max for v in wb)
            wb_flag = "" if wb_ok else f"  [!!] 超阈值 (限 ±{wb_max})"
            w(f"  Gyro bias    : ({wb[0]:.6f}, {wb[1]:.6f}, {wb[2]:.6f}){wb_flag}")

    # 各摄像头时间对齐
    subsection("各摄像头时间对齐")
    for name in sorted(cameras, key=lambda n: cameras[n]["id"]):
        c = cameras[name]
        if c["time_alignment"] is not None:
            w(f"  {name:<18} delta = {c['time_alignment']*1000:.4f} ms")

    # ── 警告信息 ──
    section("警告 & 异常")
    special_checks = log_data.get("special_checks", [])
    xml_missing_checks = xml_missing_checks or []

    # IMU bias 超阈值检查
    bias_violations = collect_bias_violations(imu)

    if special_checks:
        w("  XRCalib 关键检查命中:")
        for item in special_checks:
            w(f"  CHECK: {item}")

    if xml_missing_checks:
        if special_checks:
            w()
        w("  XML 必检项缺失:")
        for item in xml_missing_checks:
            w(f"  WARNING: {item}")

    if bias_violations:
        if special_checks or xml_missing_checks:
            w()
        w("  IMU Bias 超阈值:")
        for item in bias_violations:
            w(f"  WARNING: {item}")

    if log_data["warnings"]:
        if special_checks:
            w()
        for warn in log_data["warnings"][:10]:
            w(f"  WARNING: {warn}")
        if len(log_data["warnings"]) > 10:
            w(f"  ... 共 {len(log_data['warnings'])} 条警告")
    elif not special_checks and not xml_missing_checks and not bias_violations:
        w("  无警告")

    # ── 总评 ──
    section("总结 & 建议")

    # 找最弱摄像头
    worst_intrinsic_cam = max(intrin, key=lambda k: intrin[k]["rms"]) if intrin else "N/A"
    worst_intrinsic_rms = intrin[worst_intrinsic_cam]["rms"] if worst_intrinsic_cam in intrin else 0

    worst_det_cam = None
    worst_det_rate = 100
    for cam_name in det:
        rate = calc_detection_rate(det[cam_name])
        if rate < worst_det_rate:
            worst_det_rate = rate
            worst_det_cam = cam_name

    joint_rms = ext.get("CalibrateIMU-robust-Trajectory-Extrinsics-Intrinsics-Full", {}).get("rms", "N/A")
    full_ext_rms = ext.get("Full-Extrinsics+Intrinsics-Extrinsics", {}).get("rms", "N/A")

    overall, fail_codes, _ = resolve_status_and_exit_code(log_data, imu, xml_missing_checks)

    # 收集检测率失败详情，用于总评显示
    det_rate_failures = collect_detection_rate_failures(det)

    w(f"  总评            : {overall}")
    w(f"  联合标定残差     : {joint_rms:.4f} px" if isinstance(joint_rms, float) else f"  联合标定残差     : {joint_rms}")
    w(f"  内参最弱摄像头   : {worst_intrinsic_cam} ({worst_intrinsic_rms:.4f} px)")
    w(f"  检测率最低摄像头 : {worst_det_cam} ({worst_det_rate:.1f}%)")

    if det_rate_failures:
        w()
        w("  检测率不合格:")
        for cam_name, rate in det_rate_failures:
            w(f"    - {cam_name}: {rate:.1f}% (阈值 {THRESHOLDS['detection_rate']['acceptable']}%)")

    if issues:
        w()
        w("  关注事项:")
        for issue in issues:
            w(f"    - {issue}")

    w()
    return "\n".join(lines)


# ─────────────────────────── 主入口 ──────────────────────────────────
def main():
    """主函数。

    返回值约定：
    - 0: 正常（PASS）
    - 2: 不正常（存在多项失败）
    - 20: 不正常（内参 RMS 超阈值）
    - 21: 不正常（Full-Extrinsics+Intrinsics-Extrinsics RMS 超阈值）
    - 22: 不正常（联合标定 RMS 超阈值）
    - 23: 不正常（加速度计 bias 超阈值）
    - 24: 不正常（陀螺仪 bias 超阈值）
    - 25: 不正常（缺少 IMUNoise 节点）
    - 26: 不正常（IMUNoise 缺少必填字段）
    - 27: 不正常（检测率低于合格阈值）
    - 10: 输入目录不存在
    - 11: 缺少 device_calibration.xml
    - 12: 缺少 Calib.log
    - 13: XML 解析失败
    - 14: Log 解析失败
    - 15: 报告写入失败
    - 19: 其他未分类执行错误
    """
    parser = argparse.ArgumentParser(
        description="VQ920 XR 设备标定结果解析脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 在脚本同目录查找文件（默认）
  python parse_calib.py
  
  # 在指定目录查找文件
  python parse_calib.py --dir ./calib_results
  python parse_calib.py --dir E:/device_calib/batch1
        """
    )
    parser.add_argument(
        "--dir",
        type=str,
        default=None,
        help="指定包含 device_calibration.xml 和 Calib.log 的目录。默认为脚本所在目录"
    )
    args = parser.parse_args()

    # 确定工作目录
    if args.dir:
        work_dir = os.path.abspath(args.dir)
    else:
        work_dir = os.path.dirname(os.path.abspath(__file__))

    if not os.path.isdir(work_dir):
        print(f"错误: 输入目录不存在 {work_dir}")
        return EXIT_DIR_NOT_FOUND

    xml_path = os.path.join(work_dir, "device_calibration.xml")
    log_path = os.path.join(work_dir, "Calib.log")

    if not os.path.exists(xml_path):
        print(f"错误: 找不到 {xml_path}")
        return EXIT_XML_MISSING
    if not os.path.exists(log_path):
        print(f"错误: 找不到 {log_path}")
        return EXIT_LOG_MISSING

    print(f"解析 XML : {xml_path}")
    try:
        (
            device_uid,
            cameras,
            imu,
            det_from_xml,
            calib_time_xml,
            ar_error_xml,
            xml_missing_checks,
        ) = parse_xml(xml_path)
    except Exception as exc:
        print(f"XML 解析失败: {exc}")
        return EXIT_XML_PARSE_ERROR

    print(f"解析 Log : {log_path}")
    try:
        log_data = parse_log(log_path)
    except Exception as exc:
        print(f"Log 解析失败: {exc}")
        return EXIT_LOG_PARSE_ERROR

    # 用 XML 注释中的检测率补充 log 中可能缺失的数据
    if det_from_xml and not log_data["detection"]:
        log_data["detection"] = det_from_xml
    if calib_time_xml and not log_data["calibration_time"]:
        log_data["calibration_time"] = calib_time_xml
    if ar_error_xml and not log_data["target_ar_error"]:
        log_data["target_ar_error"] = ar_error_xml

    try:
        report = generate_report(device_uid, cameras, imu, log_data, xml_missing_checks)
        print(report)

        report_path = os.path.join(work_dir, "parsed_report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n报告已保存至: {report_path}")
    except OSError as exc:
        print(f"报告写入失败: {exc}")
        return EXIT_REPORT_WRITE_ERROR
    except Exception as exc:
        print(f"执行错误: {exc}")
        return EXIT_UNKNOWN_ERROR

    # 成功执行后按统一规则返回：仅 EXIT_OK 记为 PASS
    overall, fail_codes, exit_code = resolve_status_and_exit_code(log_data, imu, xml_missing_checks)
    print(f"\nCALIB_PARSE_STATUS={overall}")
    if fail_codes:
        print(f"FAIL_CODES={','.join(str(c) for c in fail_codes)}")
    print(f"EXIT_CODE={exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
