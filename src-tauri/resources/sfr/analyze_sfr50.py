#!/usr/bin/env python3
"""
设备级 SFR50 清晰度评估。
输入：sfr_metrics.csv（6个摄像头的 SFR50 数据）
输出：sfr50_summary.csv（设备级评估结果）

判级规则：
- 每个摄像头的 mean_avg50 >= --mean-avg50-min-pass
- 6个摄像头的 mean_avg50 标准差 <= --cam-std-max-pass

用法示例：
    python analyze_sfr50.py --input sfr_metrics.csv --summary sfr50_summary.csv --mean-avg50-min-pass 0.18 --cam-std-max-pass 0.05
"""

from __future__ import annotations

import argparse
import csv
import math
import os
from statistics import mean, median, stdev
from typing import Dict, List, Optional


# 判级阈值默认值
DEFAULT_MEAN_AVG50_MIN_PASS = 0.18
DEFAULT_CAM_STD_MAX_PASS = 0.05


def parse_float(v: str) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.upper() == "N/A":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def safe_mean(vals: List[float]) -> Optional[float]:
    return mean(vals) if vals else None


def safe_std(vals: List[float]) -> float:
    if len(vals) <= 1:
        return 0.0
    return stdev(vals)


def detect_outliers(values: List[float]) -> List[int]:
    """返回离群值下标，优先使用 MAD，退化到 z-score。"""
    if len(values) < 3:
        return []

    med = median(values)
    abs_dev = [abs(x - med) for x in values]
    mad = median(abs_dev)

    out = []
    if mad > 1e-12:
        for i, x in enumerate(values):
            mz = 0.6745 * (x - med) / mad
            if abs(mz) > 3.5:
                out.append(i)
        return out

    std = safe_std(values)
    if std <= 1e-12:
        return []

    mu = mean(values)
    for i, x in enumerate(values):
        z = (x - mu) / std
        if abs(z) > 2.0:
            out.append(i)
    return out


def fmt(v: Optional[float], nd: int = 6) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "N/A"
    return f"{v:.{nd}f}"


def load_rows(csv_path: str) -> List[dict]:
    """读取 metrics CSV，每行是一个摄像头（图片）。"""
    rows = []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            image = r.get("image", "")
            # 用图片文件名（不含扩展名）作为摄像头标识
            cam = image.rsplit(".", 1)[0] if image else "unknown"
            
            v50 = parse_float(r.get("V-SFR50", ""))
            h50 = parse_float(r.get("H-SFR50", ""))
            vals = [x for x in (v50, h50) if x is not None]
            avg50 = mean(vals) if vals else None

            rows.append({
                "image": image,
                "cam": cam,
                "v50": v50,
                "h50": h50,
                "avg50": avg50,
            })
    return rows


def grade_device(
    cam_means: Dict[str, float],
    mean_avg50_min_pass: float = DEFAULT_MEAN_AVG50_MIN_PASS,
    cam_std_max_pass: float = DEFAULT_CAM_STD_MAX_PASS,
) -> str:
    """
    设备级判级：基于 6 个摄像头的数据。
    条件1：每个摄像头的 mean_avg50 >= threshold
    条件2：6 个摄像头的 mean_avg50 标准差 <= threshold
    """
    # 条件1：检查每个摄像头
    for cam, mean_val in cam_means.items():
        if mean_val is None:
            return "不合格"
        if mean_val < mean_avg50_min_pass:
            return "不合格"
    
    # 条件2：检查摄像头间差异
    cam_mean_values = [v for v in cam_means.values() if v is not None]
    if len(cam_mean_values) > 1:
        cam_mean_std = safe_std(cam_mean_values)
        if cam_mean_std > cam_std_max_pass:
            return "不合格"
    
    return "合格"


def analyze(
    rows: List[dict],
    mean_avg50_min_pass: float = DEFAULT_MEAN_AVG50_MIN_PASS,
    cam_std_max_pass: float = DEFAULT_CAM_STD_MAX_PASS,
) -> tuple[dict, List[dict]]:
    """
    设备级评估：所有输入的 rows 作为一个设备的多个摄像头。
    
    返回：
    - device_result: dict 包含设备级信息（判级、整体均值等）
    - cam_details: list[dict] 每个摄像头的详细信息
    """
    # 为每个摄像头计算指标
    cam_metrics = {}  # {cam: {mean_avg50, std_avg50, ...}}
    cam_rows_map = {}  # {cam: [rows]}
    
    for row in rows:
        cam = row["cam"]
        if cam not in cam_rows_map:
            cam_rows_map[cam] = []
        cam_rows_map[cam].append(row)
    
    # 计算每个摄像头的统计
    for cam in sorted(cam_rows_map.keys()):
        cam_data = cam_rows_map[cam]
        avg50_vals = [r["avg50"] for r in cam_data if r["avg50"] is not None]
        
        mean_avg50 = safe_mean(avg50_vals)
        std_avg50 = safe_std(avg50_vals)
        
        cam_metrics[cam] = {
            "mean_avg50": mean_avg50,
            "std_avg50": std_avg50,
            "n_samples": len(avg50_vals),
        }
    
    # 设备级判级
    cam_means = {cam: metrics["mean_avg50"] for cam, metrics in cam_metrics.items()}
    
    grade = grade_device(
        cam_means,
        mean_avg50_min_pass=mean_avg50_min_pass,
        cam_std_max_pass=cam_std_max_pass,
    )
    
    # 计算设备级汇总
    mean_vals = [m for m in cam_means.values() if m is not None]
    device_mean_avg50 = safe_mean(mean_vals) if mean_vals else None
    device_std_avg50 = safe_std(mean_vals) if len(mean_vals) > 1 else 0.0
    
    device_result = {
        "cam_count": len(cam_metrics),
        "device_mean_avg50": device_mean_avg50,
        "device_std_avg50": device_std_avg50,
        "grade": grade,
    }
    
    # 构建每个摄像头的详细信息
    cam_details = []
    for cam in sorted(cam_rows_map.keys()):
        cam_row = cam_rows_map[cam][0] if cam_rows_map[cam] else {}
        cam_details.append({
            "image": cam_row.get("image", cam),
            "cam": cam,
            "v50": cam_row.get("v50"),
            "h50": cam_row.get("h50"),
            "avg50": cam_row.get("avg50"),
            "mean_avg50": cam_metrics[cam]["mean_avg50"],
            "std_avg50": cam_metrics[cam]["std_avg50"],
            "n_samples": cam_metrics[cam]["n_samples"],
        })
    
    return device_result, cam_details


def write_summary_csv(path: str, device_result: dict, cam_details: List[dict]):
    """输出设备级评估结果（每行一个摄像头）。"""
    fields = [
        "image",
        "cam",
        "v50",
        "h50",
        "avg50",
        "mean_avg50",
        "std_avg50",
        "n_samples",
        "device_mean_avg50",
        "device_std_avg50",
        "device_grade",
    ]
    
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        
        for cam_detail in cam_details:
            row = {
                "image": cam_detail["image"],
                "cam": cam_detail["cam"],
                "v50": fmt(cam_detail["v50"]),
                "h50": fmt(cam_detail["h50"]),
                "avg50": fmt(cam_detail["avg50"]),
                "mean_avg50": fmt(cam_detail["mean_avg50"]),
                "std_avg50": f"{cam_detail['std_avg50']:.6f}",
                "n_samples": cam_detail["n_samples"],
                "device_mean_avg50": fmt(device_result["device_mean_avg50"]),
                "device_std_avg50": f"{device_result['device_std_avg50']:.6f}",
                "device_grade": device_result["grade"],
            }
            w.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="设备级 SFR50 清晰度评估")
    parser.add_argument("--input", default="sfr_metrics.csv", help="输入 CSV 路径")
    parser.add_argument("--summary", default="sfr50_summary.csv", help="输出汇总表路径")
    parser.add_argument(
        "--mean-avg50-min-pass",
        type=float,
        default=DEFAULT_MEAN_AVG50_MIN_PASS,
        help="每个摄像头 mean_avg50 的最低阈值",
    )
    parser.add_argument(
        "--cam-std-max-pass",
        type=float,
        default=DEFAULT_CAM_STD_MAX_PASS,
        help="多个摄像头间 mean_avg50 标准差的最大阈值",
    )
    args = parser.parse_args()

    if not os.path.exists(args.input):
        raise FileNotFoundError(f"输入文件不存在: {args.input}")

    rows = load_rows(args.input)
    if not rows:
        raise RuntimeError("未读取到有效数据，请检查 metrics CSV")

    device_result, cam_details = analyze(
        rows,
        mean_avg50_min_pass=args.mean_avg50_min_pass,
        cam_std_max_pass=args.cam_std_max_pass,
    )

    write_summary_csv(args.summary, device_result, cam_details)
    print(f"汇总表已写入: {args.summary}")
    print(f"设备判级: {device_result['grade']}")
    print(f"设备 mean_avg50: {fmt(device_result['device_mean_avg50'], 4)}")
    print(f"相机间 std_avg50: {device_result['device_std_avg50']:.6f}")


if __name__ == "__main__":
    main()
