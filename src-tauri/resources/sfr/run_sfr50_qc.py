#!/usr/bin/env python3
r"""
串联执行棋盘格 SFR 计算与 SFR50 判级，直接给出“正常/不正常”结果。

流程:
1. 调用 checkerboard_sfr.py 生成/更新 metrics CSV。
2. 调用 analyze_sfr50.py 中的统计逻辑对 metrics CSV 做判级。
3. 对外返回退出码，便于产线或上层脚本直接判断。

退出码:
- 0: 正常（checkerboard_sfr 执行成功，且设备判级为"合格"）
- 2: 不正常（存在图像分析失败，或设备判级为"不合格"）
- 1: 执行错误（参数错误、脚本调用失败、输出文件缺失等）
- 3: 存在至少一张图片未检出棋盘格（或无有效 SFR 结果）

用法示例:
1) 基本用法：指定图片目录和棋盘格提示
   python run_sfr50_qc.py E:\BaiduNetdiskDownload\data\6cam --pattern-hint 9x9

2) 指定 metrics 和 summary 输出路径
   python run_sfr50_qc.py E:\BaiduNetdiskDownload\data\6cam --pattern-hint 9x9 --metrics-csv sfr_metrics.csv --summary sfr50_summary.csv

3) 自定义判级阈值
   python run_sfr50_qc.py E:\BaiduNetdiskDownload\data\6cam --pattern-hint 9x9 --mean-avg50-min-pass 0.18 --cam-std-max-pass 0.05
"""

import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# 确保能找到同目录下的模块（analyze_sfr50.py）
sys.path.insert(0, str(Path(__file__).parent))

import analyze_sfr50 as sfr50


NORMAL_GRADES = {"合格"}

EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_ABNORMAL = 2
EXIT_CHESSBOARD_MISSING = 3


def collect_input_images(inputs: List[str]) -> List[str]:
    """展开输入路径，收集所有图片文件。"""
    image_paths: List[str] = []
    allowed_suffixes = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}

    for item in inputs:
        path = Path(item)
        if path.is_dir():
            for child in sorted(path.iterdir()):
                if not child.is_file():
                    continue
                if child.suffix.lower() not in allowed_suffixes:
                    continue
                image_paths.append(str(child))
        elif path.is_file():
            if path.suffix.lower() not in allowed_suffixes:
                continue
            image_paths.append(str(path))
        else:
            print(f"警告: 输入不存在，已跳过: {path}")

    return image_paths


def build_checkerboard_command(args: argparse.Namespace, image_args: List[str]) -> List[str]:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    checkerboard_script = os.path.join(script_dir, "checkerboard_sfr.py")

    cmd = [
        sys.executable,
        checkerboard_script,
        *image_args,
        "--metrics-csv",
        args.metrics_csv,
        "--no-plot",
        "--no-batch-plot",
    ]

    if args.pattern_hint:
        cmd.extend(["--pattern-hint", args.pattern_hint])
    if args.detect_max_side is not None:
        cmd.extend(["--detect-max-side", str(args.detect_max_side)])
    if args.oversampling is not None:
        cmd.extend(["--oversampling", str(args.oversampling)])
    if args.detect_roi:
        cmd.extend(["--detect-roi", args.detect_roi])
    if args.output_dir:
        cmd.extend(["--output-dir", args.output_dir])
    if args.only_rgb:
        cmd.append("--only-rgb")
    if args.split_lr:
        cmd.append("--split-lr")
    if args.dump_fail_debug:
        cmd.append("--dump-fail-debug")

    if not image_args:
        raise FileNotFoundError("未找到图片文件")

    return cmd


def count_metrics_rows(csv_path: str) -> int:
    """统计 metrics CSV 的数据行数（不含表头）。"""
    path = Path(csv_path)
    if not path.exists() or path.stat().st_size == 0:
        return 0

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return sum(1 for _ in reader)


def run_checkerboard_stage(args: argparse.Namespace) -> Tuple[int, int, int, int]:
    image_args = collect_input_images(args.images)
    cmd = build_checkerboard_command(args, image_args)
    expected_tasks = len(image_args) * (2 if args.split_lr else 1)
    rows_before = count_metrics_rows(args.metrics_csv)

    print("\n=== 阶段 1/2: 执行棋盘格 SFR 分析 ===")
    print("命令:", " ".join(cmd))
    result = subprocess.run(cmd, check=False)
    print(f"checkerboard_sfr.py 退出码: {result.returncode}")
    rows_after = count_metrics_rows(args.metrics_csv)
    added_rows = max(0, rows_after - rows_before)
    missing_count = max(0, expected_tasks - added_rows)

    print(f"阶段1期望任务数: {expected_tasks}")
    print(f"阶段1新增有效结果行数: {added_rows}")
    print(f"阶段1未检出棋盘格(或无有效SFR)数量: {missing_count}")
    return result.returncode, expected_tasks, added_rows, missing_count


def run_sfr50_stage(args: argparse.Namespace):
    print("\n=== 阶段 2/2: 执行 SFR50 统计判级 ===")

    if not os.path.exists(args.metrics_csv):
        raise FileNotFoundError(f"metrics CSV 不存在: {args.metrics_csv}")

    rows = sfr50.load_rows(args.metrics_csv)
    if not rows:
        raise RuntimeError("未读取到有效 SFR50 数据，请检查 metrics CSV 内容")

    device_result, cam_details = sfr50.analyze(
        rows,
        mean_avg50_min_pass=args.mean_avg50_min_pass,
        cam_std_max_pass=args.cam_std_max_pass,
    )
    sfr50.write_summary_csv(args.summary, device_result, cam_details)

    print(f"\n汇总表已写入: {args.summary}")
    print(f"设备判级: {device_result['grade']}")
    print(f"设备 mean_avg50: {sfr50.fmt(device_result['device_mean_avg50'], 4)}")
    print(f"相机间 std_avg50: {device_result['device_std_avg50']:.6f}")

    return device_result, cam_details


def resolve_csv_paths(inputs: List[str], metrics_csv: Optional[str], summary_csv: Optional[str], outliers_csv: Optional[str]) -> Tuple[str, str, str]:
    """
    根据输入的图片路径确定 CSV 输出路径。
    如果 CSV 参数是 None，则使用第一个图片路径所在的目录作为默认输出目录。
    """
    output_dir = None

    # 找出第一个有效的目录或文件所在目录
    for item in inputs:
        path = Path(item)
        if path.is_dir():
            output_dir = str(path.absolute())
            break
        elif path.is_file():
            output_dir = str(path.parent.absolute())
            break

    # 如果找到了一个有效目录，使用它作为默认输出路径
    if output_dir:
        metrics_csv = metrics_csv or os.path.join(output_dir, "sfr_metrics.csv")
        summary_csv = summary_csv or os.path.join(output_dir, "sfr50_summary.csv")
        outliers_csv = outliers_csv or os.path.join(output_dir, "sfr50_outliers.csv")
    else:
        # 备选：使用当前目录
        metrics_csv = metrics_csv or "sfr_metrics.csv"
        summary_csv = summary_csv or "sfr50_summary.csv"
        outliers_csv = outliers_csv or "sfr50_outliers.csv"

    return metrics_csv, summary_csv, outliers_csv


def decide_exit_code(checkerboard_exit: int, device_result: dict, missing_count: int) -> int:
    if checkerboard_exit == 0 and missing_count > 0:
        device_result["grade"] = "不合格"
        print("\n最终结果: 不正常")
        print(f"- 存在未检出棋盘格的图像数量: {missing_count}")
        print(f"- 设备判级: {device_result['grade']}")
        print(f"- 设备 mean_avg50: {sfr50.fmt(device_result['device_mean_avg50'], 4)}")
        print(f"- 相机间 std_avg50: {device_result['device_std_avg50']:.6f}")
        return EXIT_CHESSBOARD_MISSING

    if checkerboard_exit == 0 and device_result["grade"] in NORMAL_GRADES:
        print("\n最终结果: 正常")
        return EXIT_OK

    device_result["grade"] = "不合格"
    print("\n最终结果: 不正常")
    if checkerboard_exit != 0:
        print(f"- 棋盘格分析阶段存在异常，退出码: {checkerboard_exit}")
    print(f"- 设备判级: {device_result['grade']}")
    print(f"- 设备 mean_avg50: {sfr50.fmt(device_result['device_mean_avg50'], 4)}")
    print(f"- 相机间 std_avg50: {device_result['device_std_avg50']:.6f}")
    return EXIT_ABNORMAL


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="串联 checkerboard_sfr.py 和 analyze_sfr50.py，直接输出多摄像头清晰度是否正常"
    )
    parser.add_argument("images", nargs="+", help="图像文件或目录")
    parser.add_argument("--pattern-hint", default=None, help="可选棋盘格角点提示，如 9x9 或 9x9,8x9")
    parser.add_argument("--oversampling", type=int, default=4, help="ESF 超采样因子")
    parser.add_argument("--detect-max-side", type=int, default=3000, help="棋盘检测最大边长")
    parser.add_argument("--detect-roi", default=None, help="检测前裁剪 ROI，格式 x1,y1,x2,y2 的比例")
    parser.add_argument("--output-dir", default=None, help="checkerboard_sfr.py 输出目录")
    parser.add_argument("--metrics-csv", default=None, help="SFR 指标 CSV 路径（默认：图片所在目录或当前目录）")
    parser.add_argument("--summary", default=None, help="SFR50 汇总输出路径（默认：图片所在目录或当前目录）")
    parser.add_argument("--outliers", default=None, help="SFR50 离群点输出路径（默认：图片所在目录或当前目录）")
    parser.add_argument(
        "--mean-avg50-min-pass",
        type=float,
        default=sfr50.DEFAULT_MEAN_AVG50_MIN_PASS,
        help="判为合格时 mean_avg50 的最低阈值",
    )
    parser.add_argument(
        "--cam-std-max-pass",
        type=float,
        default=sfr50.DEFAULT_CAM_STD_MAX_PASS,
        help="6 个摄像头间 mean_avg50 的最大标准差（摄像头一致性）",
    )
    parser.add_argument("--only-rgb", action="store_true", help="仅处理文件名以 rgb 开头的图像")
    parser.add_argument("--split-lr", action="store_true", help="将每张输入图像按左右等分后分别计算 SFR")
    parser.add_argument("--dump-fail-debug", action="store_true", help="检测失败时保存调试图")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # 根据图片目录自动确定 CSV 输出路径
    metrics_csv, summary_csv, outliers_csv = resolve_csv_paths(
        args.images,
        args.metrics_csv,
        args.summary,
        args.outliers,
    )
    args.metrics_csv = metrics_csv
    args.summary = summary_csv
    args.outliers = outliers_csv

    try:
        checkerboard_exit, _expected_tasks, _added_rows, missing_count = run_checkerboard_stage(args)
        device_result, _cam_details = run_sfr50_stage(args)
    except Exception as exc:
        print(f"\n执行错误: {exc}")
        return EXIT_RUNTIME_ERROR

    return decide_exit_code(checkerboard_exit, device_result, missing_count)


if __name__ == "__main__":
    sys.exit(main())