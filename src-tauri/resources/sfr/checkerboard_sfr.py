#!/usr/bin/env python3
"""
棋盘格 SFR (Spatial Frequency Response) 分析
基于 ISO 12233 斜边法，在棋盘格边缘上计算 SFR/MTF。

用法:
  python checkerboard_sfr.py use6/
  python checkerboard_sfr.py image.png --json results.json
"""

# 调用示例（可直接复制到终端）:
# 1) 分析单张图像（默认仅输出终端结果、metrics CSV，可选 JSON）
#    python checkerboard_sfr.py image.png
#
# 2) 分析目录下全部图像
#    python checkerboard_sfr.py use6/
#
# 3) 指定输出目录 + 导出 JSON
#    python checkerboard_sfr.py use6/ --output-dir out --json results.json
#
# 4) 显式生成单图结果（_sfr.png / _overlay.png）
#    python checkerboard_sfr.py use6/ --plot
#
# 5) 显式生成单图结果 + 批量对比图（sfr_comparison.png）
#    python checkerboard_sfr.py use6/ --plot --batch-plot
#
# 6) 指定棋盘角点规格提示（加速并提高稳定性）
#    python checkerboard_sfr.py use6/ --pattern-hint 9x9
#    python checkerboard_sfr.py use6/ --pattern-hint 9x9,8x9
#
# 7) 左右分隔模式（每张图拆成 L/R 两个任务）
#    python checkerboard_sfr.py use6/ --split-lr
#
# 8) 仅处理文件名以 rgb 开头的图像
#    python checkerboard_sfr.py use6/ --only-rgb
#
# 9) 指定检测 ROI（按图像比例裁剪检测区域）
#    python checkerboard_sfr.py use6/ --detect-roi 0.1,0.2,0.9,0.9
#
# 10) 检测失败时保存调试图
#     python checkerboard_sfr.py use6/ --dump-fail-debug --output-dir debug_out
#
# 11) 自定义超采样和检测降采样上限
#     python checkerboard_sfr.py use6/ --oversampling 4 --detect-max-side 3000

import os
import sys
import json
import argparse
import time
import numpy as np
import cv2
from scipy import ndimage, signal
from concurrent.futures import ThreadPoolExecutor, as_completed

print("[startup] 正在加载 checkerboard_sfr 基础依赖...", flush=True)

_PLOT_MODULE = None
_PLOT_USE_CHINESE = False


def get_pyplot():
    """按需导入 matplotlib.pyplot，避免脚本启动阶段长时间无输出。"""
    global _PLOT_MODULE
    if _PLOT_MODULE is None:
        print("[startup] 正在加载 matplotlib.pyplot...", flush=True)
        import matplotlib.pyplot as plt_module

        _PLOT_MODULE = plt_module
    return _PLOT_MODULE


def startup_log(message, enabled=False):
    """输出启动阶段调试信息。"""
    if enabled:
        print(f"[startup] {message}", flush=True)


def plot_text(chinese, english):
    """根据当前绘图语言返回中英文文案。"""
    return chinese if _PLOT_USE_CHINESE else english

# ─── 中文字体 ───

def setup_chinese_font(enabled=False):
    """跨平台中文字体配置，默认关闭，按需启用。"""
    import platform
    import warnings

    if not enabled:
        return False
    
    system = platform.system()
    font_path = None
    
    # Windows 系统
    if system == 'Windows':
        windows_fonts = [
            'C:\\Windows\\Fonts\\simhei.ttf',        # 黑体（推荐）
            'C:\\Windows\\Fonts\\msyh.ttf',          # 微软雅黑
            'C:\\Windows\\Fonts\\simsun.ttf',        # 宋体
            'C:\\Windows\\Fonts\\msyhbd.ttf',        # 微软雅黑粗体
        ]
        for fp in windows_fonts:
            if os.path.exists(fp):
                font_path = fp
                break
    
    # macOS 系统
    elif system == 'Darwin':
        macos_fonts = [
            '/System/Library/Fonts/PingFang.ttc',
            '/Library/Fonts/Arial Unicode.ttf',
            '/Library/Fonts/STHeiti Light.ttc',
        ]
        for fp in macos_fonts:
            if os.path.exists(fp):
                font_path = fp
                break
    
    # Linux 系统
    else:
        linux_fonts = [
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        ]
        for fp in linux_fonts:
            if os.path.exists(fp):
                font_path = fp
                break
    
    # 尝试加载找到的字体
    if font_path:
        try:
            plt = get_pyplot()
            from matplotlib import font_manager
            font_manager.fontManager.addfont(font_path)
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            plt.rcParams['font.size'] = 10
            return True
        except Exception as e:
            print(f"  警告: 字体加载失败 {font_path}: {e}")
    
        # 无论是否加载字体成功，都禁用相关警告
        plt = get_pyplot()
    plt.rcParams['axes.unicode_minus'] = False
    warnings.filterwarnings('ignore', message='Glyph.*missing from font')
    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
    
    return False


# ─── 棋盘格检测 ───

_CB_MIN_SQ = 8  # 最小合理方格边长(px)，过滤假匹配
_SB_CALL_LOGGED = False


def to_gray_u8(img):
    """将任意通道/位深图像转换为灰度 uint8，便于稳定棋盘检测与SFR计算。"""
    if img is None:
        return None

    if img.ndim == 3:
        # 兼容 RGB/RGBA/BGR/BGRA：OpenCV 读取通常是 BGR/BGRA
        if img.shape[2] == 4:
            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    if gray.dtype == np.uint8:
        return gray

    gray = gray.astype(np.float64)
    finite = np.isfinite(gray)
    if not np.any(finite):
        return None

    vals = gray[finite]
    lo = np.percentile(vals, 1.0)
    hi = np.percentile(vals, 99.0)
    if hi <= lo:
        lo = np.min(vals)
        hi = np.max(vals)
    if hi <= lo:
        return np.zeros_like(gray, dtype=np.uint8)

    norm = (gray - lo) / (hi - lo)
    norm = np.clip(norm, 0.0, 1.0)
    return (norm * 255.0 + 0.5).astype(np.uint8)


def crop_lr_half(gray_u8, split_half=None):
    """按左右等分裁剪灰度图；split_half 为 'L' 或 'R'。"""
    if split_half is None:
        return gray_u8
    if gray_u8 is None or gray_u8.ndim != 2:
        return None

    h, w = gray_u8.shape
    if w < 2:
        return None

    half_w = w // 2
    if half_w < 1:
        return None

    if split_half == 'L':
        return gray_u8[:, :half_w]
    if split_half == 'R':
        return gray_u8[:, w - half_w:]
    return None


def parse_pattern_hint(text):
    """解析 pattern hint 字符串，如 '9x9' 或 '9x9,8x9'。"""
    if not text:
        return None
    pairs = []
    for part in text.split(','):
        p = part.strip().lower().replace('*', 'x')
        if 'x' not in p:
            continue
        a, b = p.split('x', 1)
        try:
            cols = int(a)
            rows = int(b)
        except ValueError:
            continue
        if cols >= 3 and rows >= 3:
            pairs.append((cols, rows))
    return pairs or None


def make_image_key(image_path, with_ext=True):
    """生成稳定图像键名：目录名_文件名。"""
    dname = os.path.basename(os.path.dirname(image_path))
    fname = os.path.basename(image_path) if with_ext else os.path.splitext(os.path.basename(image_path))[0]
    key = f"{dname}_{fname}" if dname else fname
    return key.replace(' ', '_')


def build_image_tasks(image_paths, split_lr=False):
    """构建分析任务列表；split_lr=True 时每张图拆成左右两半任务。"""
    tasks = []
    for img_path in image_paths:
        base_key = make_image_key(img_path, with_ext=True)
        base_name = os.path.basename(img_path)
        if not split_lr:
            tasks.append({
                'id': base_key,
                'path': img_path,
                'split_half': None,
                'display_name': base_name,
            })
            continue

        for side in ('L', 'R'):
            tasks.append({
                'id': f"{base_key}_{side}",
                'path': img_path,
                'split_half': side,
                'display_name': f"{base_name}[{side}]",
            })
    return tasks


def build_fail_debug_image(gray_u8, fail_info):
    """构建失败调试图：左侧增强图，右侧边缘强度图。"""
    if gray_u8 is None or gray_u8.ndim != 2:
        return None

    # 局部对比度增强，便于观察反光/模糊细节
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray_u8)

    # 梯度幅值图：反映可用于角点检测的边缘能量
    gx = cv2.Sobel(enhanced, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(enhanced, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    if np.max(mag) > 1e-9:
        mag_u8 = np.clip((mag / np.max(mag)) * 255.0, 0, 255).astype(np.uint8)
    else:
        mag_u8 = np.zeros_like(enhanced, dtype=np.uint8)

    left = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    right = cv2.applyColorMap(mag_u8, cv2.COLORMAP_INFERNO)
    panel = np.hstack([left, right])

    cv2.putText(panel, 'Enhanced', (16, 28), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (0, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(panel, 'Edge magnitude', (left.shape[1] + 16, 28), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (0, 255, 255), 2, cv2.LINE_AA)

    reason = fail_info.get('reason', 'unknown') if fail_info else 'unknown'
    stats_line = (
        f"std={fail_info.get('image_std', 0.0):.2f} "
        f"scale={fail_info.get('scale', 1.0):.3f} "
        f"hit={fail_info.get('matched_count', 0)} "
        f"miss={fail_info.get('not_found_count', 0)} "
        f"small={fail_info.get('filtered_small_square_count', 0)}"
    ) if fail_info else 'n/a'

    cv2.rectangle(panel, (8, panel.shape[0] - 74), (panel.shape[1] - 8, panel.shape[0] - 8),
                  (20, 20, 20), thickness=-1)
    cv2.putText(panel, f"Fail reason: {reason}", (16, panel.shape[0] - 44),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (230, 230, 230), 1, cv2.LINE_AA)
    cv2.putText(panel, stats_line, (16, panel.shape[0] - 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (230, 230, 230), 1, cv2.LINE_AA)

    return panel


def dump_fail_debug_image(image_path, gray_u8, fail_info, output_dir=None, image_label=None):
    """将失败调试图写盘，返回输出路径或 None。"""
    debug_img = build_fail_debug_image(gray_u8, fail_info)
    if debug_img is None:
        return None

    out_dir = output_dir or os.path.dirname(image_path) or '.'
    os.makedirs(out_dir, exist_ok=True)
    key = image_label if image_label else make_image_key(image_path, with_ext=False)
    key = key.replace(' ', '_').replace('\\', '_').replace('/', '_').replace(':', '_')
    out_path = os.path.join(out_dir, f"{key}_fail_debug.png")

    ok = cv2.imwrite(out_path, debug_img)
    return out_path if ok else None


def _find_chessboard_corners(det_img, pattern, flags):
    """优先使用更鲁棒的 SB 版本；失败则回退到传统接口。"""
    global _SB_CALL_LOGGED
    if hasattr(cv2, 'findChessboardCornersSB'):
        try:
            sb_flags = flags
            if hasattr(cv2, 'CALIB_CB_EXHAUSTIVE'):
                sb_flags |= cv2.CALIB_CB_EXHAUSTIVE
            if hasattr(cv2, 'CALIB_CB_ACCURACY'):
                sb_flags |= cv2.CALIB_CB_ACCURACY
            if hasattr(cv2, 'CALIB_CB_LARGER'):
                sb_flags |= cv2.CALIB_CB_LARGER
            if not _SB_CALL_LOGGED:
                print(f"  [Chessboard] 调用 findChessboardCornersSB(pattern={pattern}, exhaustive={'on' if hasattr(cv2, 'CALIB_CB_EXHAUSTIVE') else 'off'})")
                _SB_CALL_LOGGED = True
            variants = [det_img]
            # 遮挡/低对比场景下，增强后再试一次可提升命中率
            if det_img is not None and det_img.ndim == 2 and det_img.dtype == np.uint8:
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                variants.append(clahe.apply(det_img))

            for img_try in variants:
                ret, corners = cv2.findChessboardCornersSB(img_try, pattern, sb_flags)
                if ret:
                    return ret, corners
        except Exception:
            pass
    return cv2.findChessboardCorners(det_img, pattern, flags)


def _mask_bbox(mask, pts, pad=10):
    """按角点外接框在 mask 上涂黑，供下一轮重新搜索。"""
    if mask is None or pts is None or len(pts) == 0:
        return
    xs = pts[:, 0]
    ys = pts[:, 1]
    x0 = max(0, int(np.floor(np.min(xs))) - pad)
    y0 = max(0, int(np.floor(np.min(ys))) - pad)
    x1 = min(mask.shape[1] - 1, int(np.ceil(np.max(xs))) + pad)
    y1 = min(mask.shape[0] - 1, int(np.ceil(np.max(ys))) + pad)
    if x1 > x0 and y1 > y0:
        cv2.rectangle(mask, (x0, y0), (x1, y1), 0, thickness=-1)


def detect_checkerboard(image, max_side=3000, pattern_pairs=None, return_fail_info=False):
    """
    自动检测棋盘格，返回角点和相关信息。
    若存在多个可用候选，优先选择“面积最大且尽量居中”的棋盘格。
    同规格多棋盘时，采用掩模法反复搜索并收集所有候选。
    """
    flags = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.01)

    # 若给定 pattern hint，则只按 hint 尝试；否则走全范围自动搜索
    if pattern_pairs:
        pairs = pattern_pairs
    else:
        pairs = sorted(
            [(c, r) for c in range(3, 13) for r in range(3, 13)],
            key=lambda x: x[0] * x[1], reverse=True
        )

    det_base = image
    scale = 1.0
    h, w = image.shape[:2]
    img_min = float(np.min(image))
    img_max = float(np.max(image))
    img_std = float(np.std(image))
    if max_side and max(h, w) > max_side:
        scale = float(max_side) / float(max(h, w))
        det_base = cv2.resize(image, (int(round(w * scale)), int(round(h * scale))),
                              interpolation=cv2.INTER_AREA)

    det_h, det_w = det_base.shape[:2]
    det_mask = np.full((det_h, det_w), 255, dtype=np.uint8)

    fail_info = {
        'shape': (h, w),
        'detect_shape': det_base.shape[:2],
        'scale': scale,
        'attempted_patterns': len(pairs),
        'not_found_count': 0,
        'matched_count': 0,
        'candidate_count': 0,
        'mask_rounds': 0,
        'filtered_small_square_count': 0,
        'small_square_examples': [],
        'image_min': img_min,
        'image_max': img_max,
        'image_std': img_std,
        'reason': '',
    }

    best_result = None
    best_area = -1.0
    best_center_dist = float("inf")

    img_cx = w * 0.5
    img_cy = h * 0.5
    img_diag_half = max(1.0, 0.5 * np.hypot(w, h))

    # 掩模法：反复在剩余区域搜索同一/不同规格的棋盘格候选
    max_rounds = max(2, min(8, len(pairs) * 2))
    while fail_info['mask_rounds'] < max_rounds:
        progress = False
        fail_info['mask_rounds'] += 1

        masked_det = cv2.bitwise_and(det_base, det_base, mask=det_mask)

        for cols, rows in pairs:
            ret, corners = _find_chessboard_corners(masked_det, (cols, rows), flags)
            if not ret:
                fail_info['not_found_count'] += 1
                continue

            fail_info['matched_count'] += 1

            det_corners = corners.reshape(-1, 1, 2).astype(np.float32)
            det_pts = det_corners.reshape(-1, 2)

            # 用检测图上的外接框先做掩模，避免下一轮继续命中同一块棋盘
            bbox_w_det = float(np.max(det_pts[:, 0]) - np.min(det_pts[:, 0]))
            bbox_h_det = float(np.max(det_pts[:, 1]) - np.min(det_pts[:, 1]))
            bbox_pad = max(10, int(round(0.10 * max(bbox_w_det, bbox_h_det))))
            _mask_bbox(det_mask, det_pts, pad=bbox_pad)
            progress = True

            # 若检测在降采样图完成，则映射回原图后再做亚像素优化
            if scale != 1.0:
                corners = (det_corners / scale).astype(np.float32)
            else:
                corners = det_corners.astype(np.float32)
            corners = cv2.cornerSubPix(image, corners, (5, 5), (-1, -1), criteria)
            pts = corners.reshape(-1, 2)

            # 用欧氏距离估计方格尺寸，避免棋盘旋转/透视时 x/y 分量被低估。
            row_dists = []
            for r in range(rows):
                row_pts = pts[r * cols:(r + 1) * cols]
                if len(row_pts) > 1:
                    d = np.linalg.norm(np.diff(row_pts, axis=0), axis=1)
                    row_dists.extend(d.tolist())

            col_dists = []
            for c in range(cols):
                col_pts = pts[c::cols]
                if len(col_pts) > 1:
                    d = np.linalg.norm(np.diff(col_pts, axis=0), axis=1)
                    col_dists.extend(d.tolist())

            sx = float(np.median(row_dists)) if row_dists else 0.0
            sy = float(np.median(col_dists)) if col_dists else 0.0

            # 过滤方格太小的假匹配
            if sx < _CB_MIN_SQ or sy < _CB_MIN_SQ:
                fail_info['filtered_small_square_count'] += 1
                if len(fail_info['small_square_examples']) < 3:
                    fail_info['small_square_examples'].append({
                        'pattern': (cols, rows),
                        'sx': float(sx),
                        'sy': float(sy),
                    })
                continue

            # 评分策略：优先面积更大，其次更居中。
            board_cx = float(np.mean(pts[:, 0]))
            board_cy = float(np.mean(pts[:, 1]))
            center_dist = float(np.hypot(board_cx - img_cx, board_cy - img_cy))

            bbox_w = float(np.max(pts[:, 0]) - np.min(pts[:, 0]))
            bbox_h = float(np.max(pts[:, 1]) - np.min(pts[:, 1]))
            bbox_diag = float(np.hypot(bbox_w, bbox_h))
            bbox_area = float(bbox_w * bbox_h)

            result = {
                'corners': corners,
                'pts': pts,
                'pattern': (cols, rows),
                'square': (sx, sy),
                'detect_scale': scale,
                'center': (board_cx, board_cy),
                'center_dist': center_dist,
                'bbox_area': bbox_area,
                'bbox_diag': bbox_diag,
                'det_pts': det_pts,
                'det_bbox': (float(np.min(det_pts[:, 0])), float(np.min(det_pts[:, 1])),
                             float(np.max(det_pts[:, 0])), float(np.max(det_pts[:, 1]))),
            }

            fail_info['candidate_count'] += 1
            print(
                f"  候选#{fail_info['candidate_count']}: {cols}x{rows}，"
                f"面积≈{bbox_area:.0f}px^2，中心距={center_dist:.1f}px"
            )

            if (bbox_area > best_area) or (abs(bbox_area - best_area) < 1e-6 and center_dist < best_center_dist):
                best_area = bbox_area
                best_center_dist = center_dist
                best_result = result

        if not progress:
            break

    if best_result is not None:
        print(
            f"  棋盘格候选命中数: {fail_info['matched_count']}，"
            f"最终选用: {best_result['pattern'][0]}x{best_result['pattern'][1]}，"
            f"面积≈{best_result['bbox_area']:.0f}px^2，"
            f"中心距={best_result['center_dist']:.1f}px"
        )
        if return_fail_info:
            return best_result, fail_info
        return best_result

    if fail_info['matched_count'] == 0:
        if fail_info['image_std'] < 8:
            fail_info['reason'] = '所有候选规格均未找到角点，且图像对比度偏低'
        else:
            fail_info['reason'] = '所有候选规格均未找到角点'
    elif fail_info['filtered_small_square_count'] > 0:
        fail_info['reason'] = '检测到角点但被最小方格尺寸阈值过滤'
    else:
        fail_info['reason'] = '检测失败（未命中有效棋盘格）'

    if return_fail_info:
        return None, fail_info
    return None


# ─── ESF / SFR 计算 (ISO 12233) ───

def compute_edge_sfr(roi, oversampling=4):
    """
    在旋转校正的 ROI 中计算单条边的 SFR。

    ROI 中边缘应近似垂直（暗在左/右），用 Sobel X 定位后：
      ESF → LSF → Windowed FFT → SFR(MTF)

    返回 dict 或 None。
    """
    h, w = roi.shape
    if h < 10 or w < 10:
        return None

    # 定位边缘 — 使用 argmax 而非 find_peaks（边缘通常是梯度最高的位置，不一定是峰）
    sobel_x = cv2.Sobel(roi, cv2.CV_64F, 1, 0, ksize=3)
    grad_abs = np.abs(sobel_x)
    col_grad = np.mean(grad_abs, axis=0)
    col_smooth = ndimage.gaussian_filter1d(col_grad, sigma=3)

    edge_x = int(np.argmax(col_smooth))
    max_dist = min(w, h) / 3.0

    # 计算每行中边缘亚像素位置 → 求斜边角度
    row_pos, row_idx = [], []
    for y in range(0, h, max(1, h // 60)):
        row_g = grad_abs[y, :]
        if np.max(row_g) > 10:
            local_x = np.argmax(row_g)
            row_pos.append(local_x)
            row_idx.append(y)

    if len(row_pos) < 3:
        angle_rad = 0.0
    else:
        c = np.polyfit(row_idx, row_pos, 1)
        angle_rad = np.arctan(c[0])

    cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
    ys, xs = np.mgrid[0:h, 0:w]
    distances = (xs - edge_x) * cos_a - (ys - h / 2.0) * sin_a

    # 分 bin 构建 ESF
    dist_mask = np.abs(distances) <= max_dist
    bin_idx = np.round(distances * oversampling).astype(int)

    valid_bins = bin_idx[dist_mask]
    if len(valid_bins) < 50:
        return None

    b_min, b_max = valid_bins.min(), valid_bins.max()
    n_bins = b_max - b_min + 1
    if n_bins < 20:
        return None

    b_off = -b_min
    flat_roi = roi.ravel().astype(np.float64)
    flat_bins = (bin_idx + b_off).ravel()
    flat_mask = dist_mask.ravel()
    idx = np.where(flat_mask)[0]
    valid_bins_idx = flat_bins[idx]
    esf_sum = np.bincount(valid_bins_idx, weights=flat_roi[idx], minlength=n_bins)
    esf_cnt = np.bincount(valid_bins_idx, minlength=n_bins).astype(np.float64)

    mask = esf_cnt > 0
    if np.sum(mask) < 20:
        return None

    esf = np.full(n_bins, np.nan)
    esf[mask] = esf_sum[mask] / esf_cnt[mask]

    valid = ~np.isnan(esf)
    if np.sum(valid) < 20:
        return None

    vi = np.where(valid)[0]
    esf_interp = np.interp(np.arange(n_bins), vi, esf[valid])

    # 裁剪到过渡区域
    esf_grad = np.abs(np.gradient(esf_interp))
    gc = np.argmax(esf_grad)
    hw = min(n_bins // 4, 100 * oversampling)
    s, e = max(0, gc - hw), min(n_bins, gc + hw)
    esf_trim = esf_interp[s:e]
    if len(esf_trim) < 20:
        return None

    # LSF → 加窗 FFT → SFR
    lsf = np.gradient(esf_trim)
    win = np.hamming(len(lsf))
    lsf_w = lsf * win

    fft = np.fft.rfft(lsf_w)
    sfr = np.abs(fft)
    if sfr[0] < 1e-6:
        return None
    sfr_norm = sfr / sfr[0]
    freqs = np.fft.rfftfreq(len(lsf_w), d=1.0 / oversampling)

    # 计算 SFR at 各频率
    nyquist = 0.5
    sfr_values = {}
    for pct in [10, 20, 30, 50]:
        threshold = pct / 100.0
        val = None
        for i in range(1, len(sfr_norm)):
            if freqs[i] > nyquist:
                break
            if sfr_norm[i] <= threshold:
                f1, f2 = freqs[i - 1], freqs[i]
                m1, m2 = sfr_norm[i - 1], sfr_norm[i]
                val = f1 + (threshold - m1) * (f2 - f1) / (m2 - m1) if m2 != m1 else f1
                break
        if val is None:
            val = nyquist
        sfr_values[f'SFR{pct}'] = val

    # SFR at Nyquist
    nyq_idx = np.searchsorted(freqs, nyquist)
    if nyq_idx > 0 and nyq_idx < len(sfr_norm):
        sfr_values['SFR_Nyq'] = float(np.clip(sfr_norm[nyq_idx], 0, 1))
    else:
        sfr_values['SFR_Nyq'] = float(np.clip(sfr_norm[-1], 0, 1))

    esf_x = (np.arange(len(esf_trim)) + s - b_off) / oversampling

    return {
        'sfr': sfr_norm,
        'freqs': freqs,
        'esf': esf_trim,
        'esf_x': esf_x,
        'lsf': lsf_w,
        'sfr_values': sfr_values,
        'oversampling': oversampling,
    }


def extract_edge_roi(image, p1, p2, roi_size, rotate=False):
    """
    从棋盘格边 (p1→p2) 提取透视校正的 ROI。
    rotate=True 时旋转 90° 使边缘跳变沿 X 方向（适配 Sobel X）。
    """
    img_h, img_w = image.shape
    mid = (p1 + p2) / 2.0
    vec = p2 - p1
    elen = np.linalg.norm(vec)
    if elen < 5:
        return None

    d = vec / elen
    n = np.array([-d[1], d[0]])

    # 沿法线方向两侧对称采样，沿边缘方向取一小段用于透视变换
    e_a = d * min(elen / 2, 2)  # 小范围，确保边缘在 ROI 中部
    e_n = n * (roi_size / 2)

    src = np.array([
        mid - e_a - e_n, mid + e_a - e_n,
        mid + e_a + e_n, mid - e_a + e_n,
    ], dtype=np.float32)
    dst = np.array([[0, 0], [roi_size, 0], [roi_size, roi_size], [0, roi_size]], dtype=np.float32)

    M = cv2.getPerspectiveTransform(src, dst)
    roi = cv2.warpPerspective(image, M, (roi_size, roi_size),
                              flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    if roi.std() < 5:
        return None

    if rotate:
        roi = cv2.rotate(roi, cv2.ROTATE_90_CLOCKWISE)

    all_pts = src.reshape(-1, 2)
    rx = max(0, int(np.floor(all_pts[:, 0].min())))
    ry = max(0, int(np.floor(all_pts[:, 1].min())))
    rw = int(np.ceil(all_pts[:, 0].max())) - rx
    rh = int(np.ceil(all_pts[:, 1].max())) - ry

    return {
        'roi': roi,
        'rect': (rx, ry, rw, rh),
        'edge_center': (float(mid[0]), float(mid[1])),
        'edge_len': elen,
        'angle': np.degrees(np.arctan2(d[1], d[0])),
    }


# ─── 整体分析 ───

def analyze_image(image_path, oversampling=4, detect_max_side=3000, pattern_pairs=None,
                  dump_fail_debug=False, fail_debug_dir=None,
                  split_half=None, image_label=None, detect_roi=None):
    """
    分析单张棋盘格图像，返回 SFR 结果。
    """
    t0 = time.perf_counter()

    if not os.path.exists(image_path):
        print(f"  错误: 文件不存在: {image_path}")
        return None

    raw = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if raw is None:
        print(f"  错误: 无法读取: {image_path}")
        return None
    img = to_gray_u8(raw)
    if img is None:
        print(f"  错误: 图像数据无效: {image_path}")
        return None
    if split_half is not None:
        img = crop_lr_half(img, split_half=split_half)
        if img is None:
            print(f"  错误: 左右分隔失败: {image_path} (split={split_half})")
            return None
    t_load = time.perf_counter()

    h, w = img.shape
    display_name = image_label or os.path.basename(image_path)
    print(f"\n{'=' * 70}")
    print(f"  图像: {display_name}  ({w}x{h})")
    print(f"{'=' * 70}")

    # 若指定检测 ROI，先裁出子区域供检测，之后将角点坐标迁回原图
    roi_offset = (0, 0)
    detect_img = img
    if detect_roi is not None:
        try:
            x1f, y1f, x2f, y2f = detect_roi
            _h, _w = img.shape
            rx0 = max(0, int(round(x1f * _w)))
            ry0 = max(0, int(round(y1f * _h)))
            rx1 = min(_w, int(round(x2f * _w)))
            ry1 = min(_h, int(round(y2f * _h)))
            if rx1 > rx0 and ry1 > ry0:
                detect_img = img[ry0:ry1, rx0:rx1]
                roi_offset = (rx0, ry0)
                print(f"  检测ROI: x=[{rx0},{rx1}], y=[{ry0},{ry1}] ({rx1-rx0}x{ry1-ry0}px)")
        except Exception as _e:
            print(f"  警告: detect_roi 参数无效，将使用全图检测 ({_e})")

    cb, fail_info = detect_checkerboard(
        detect_img,
        max_side=detect_max_side,
        pattern_pairs=pattern_pairs,
        return_fail_info=True,
    )
    t_detect = time.perf_counter()
    # 将 ROI 子图坐标迁回原图坐标系
    if cb is not None and (roi_offset[0] != 0 or roi_offset[1] != 0):
        _off = np.array([roi_offset[0], roi_offset[1]], dtype=np.float32)
        cb['pts'] = cb['pts'] + _off
        cb['center'] = (cb['center'][0] + roi_offset[0], cb['center'][1] + roi_offset[1])
    if cb is None:
        print(f"  未检测到棋盘格 (检测耗时 {t_detect - t_load:.3f}s)")
        print(f"  失败原因: {fail_info.get('reason', '未知原因')}")
        print(
            f"  检测统计: 原图={fail_info['shape'][1]}x{fail_info['shape'][0]}, "
            f"检测图={fail_info['detect_shape'][1]}x{fail_info['detect_shape'][0]}, "
            f"scale={fail_info['scale']:.3f}, 候选={fail_info['attempted_patterns']}, "
            f"命中={fail_info['matched_count']}, 未命中={fail_info['not_found_count']}, "
            f"小方格过滤={fail_info['filtered_small_square_count']}"
        )
        print(
            f"  图像统计: min={fail_info['image_min']:.1f}, max={fail_info['image_max']:.1f}, "
            f"std={fail_info['image_std']:.2f}"
        )
        if fail_info['small_square_examples']:
            print("  小方格过滤样例:")
            for ex in fail_info['small_square_examples']:
                print(
                    f"    pattern={ex['pattern'][0]}x{ex['pattern'][1]}, "
                    f"sx={ex['sx']:.2f}, sy={ex['sy']:.2f}, 阈值={_CB_MIN_SQ}"
                )
        if dump_fail_debug:
            out_path = dump_fail_debug_image(
                image_path,
                img,
                fail_info,
                output_dir=fail_debug_dir,
                image_label=display_name,
            )
            if out_path:
                print(f"  失败调试图已保存: {out_path}")
            else:
                print("  警告: 失败调试图保存失败")
        return None

    pts = cb['pts']
    cols, rows = cb['pattern']
    sx, sy = cb['square']
    roi_size = max(30, int(min(sx, sy) * 1.5))

    print(f"  棋盘格: {cols}x{rows}, 方格≈{sx:.0f}x{sy:.0f}px, ROI={roi_size}px")
    if cb.get('detect_scale', 1.0) < 1.0:
        print(f"  检测降采样: {cb['detect_scale']:.3f}x (加速大图棋盘检测)")

    # 收集中心附近所有边缘（不用分 left/right/top/bottom，统一收集）
    center_col = (cols - 1) / 2.0
    center_row = (rows - 1) / 2.0
    cx, cy = pts[:, 0].mean(), pts[:, 1].mean()

    h_edges = []   # (p1, p2, direction='H', dist) — 水平边（row间），测垂直 SFR
    v_edges = []   # (p1, p2, direction='V', dist) — 垂直边（col间），测水平 SFR

    for r in range(rows - 1):
        for c in range(cols):
            p1, p2 = pts[r * cols + c], pts[(r + 1) * cols + c]
            mid = (p1 + p2) / 2
            dist = np.sqrt((mid[0] - cx) ** 2 + (mid[1] - cy) ** 2)
            h_edges.append((p1.copy(), p2.copy(), dist))

    for r in range(rows):
        for c in range(cols - 1):
            p1, p2 = pts[r * cols + c], pts[r * cols + c + 1]
            mid = (p1 + p2) / 2
            dist = np.sqrt((mid[0] - cx) ** 2 + (mid[1] - cy) ** 2)
            v_edges.append((p1.copy(), p2.copy(), dist))

    # 按距中心排序，取最近的 N 条
    max_dist = min(sx, sy) * (max(cols, rows) * 0.4)
    h_edges.sort(key=lambda e: e[2])
    v_edges.sort(key=lambda e: e[2])
    h_edges = [e for e in h_edges if e[2] < max_dist]
    v_edges = [e for e in v_edges if e[2] < max_dist]

    # 计算每条边的 SFR
    h_sfrs, v_sfrs = [], []
    h_edge_info, v_edge_info = [], []

    t_edge_start = time.perf_counter()
    for p1, p2, dist in h_edges:
        # 水平边（行间）：边缘向量垂直，跳变沿 Y 方向，需旋转 90°
        ed = extract_edge_roi(img, p1, p2, roi_size, rotate=True)
        if ed is None:
            continue
        result = compute_edge_sfr(ed['roi'], oversampling)
        if result is None:
            continue
        h_sfrs.append(result)
        h_edge_info.append({**ed, 'p1': p1.tolist(), 'p2': p2.tolist()})

    for p1, p2, dist in v_edges:
        # 垂直边（列间）：边缘向量水平，跳变沿 Y 方向，需旋转 90° 使边缘变为垂直
        ed = extract_edge_roi(img, p1, p2, roi_size, rotate=True)
        if ed is None:
            continue
        result = compute_edge_sfr(ed['roi'], oversampling)
        if result is None:
            continue
        v_sfrs.append(result)
        v_edge_info.append({**ed, 'p1': p1.tolist(), 'p2': p2.tolist()})

    t_sfr = time.perf_counter()
    print(f"  水平边 (测垂直 SFR): {len(h_sfrs)} 条有效")
    print(f"  垂直边 (测水平 SFR): {len(v_sfrs)} 条有效")

    if not h_sfrs and not v_sfrs:
        print("  无有效边缘")
        return None

    # 汇总：对 SFR 曲线取平均
    def avg_sfr(sfr_list):
        """对多条 SFR 曲线在公共频率网格上取平均。"""
        if not sfr_list:
            return None, None, None
        common = np.arange(0, 0.5, 0.005)
        interp_list = []
        for s in sfr_list:
            freqs = s['freqs']
            sfr = s['sfr']
            f_lo, f_hi = freqs[0], freqs[-1]
            mask = (common >= f_lo) & (common <= min(f_hi, 0.5))
            if not np.any(mask):
                continue
            interp_vals = np.interp(common[mask], freqs, sfr)
            full = np.full(len(common), np.nan)
            full[mask] = interp_vals
            interp_list.append(full)
        if not interp_list:
            return None, None, None

        stacked = np.array(interp_list)
        valid_count = np.sum(~np.isnan(stacked), axis=0)
        # 只在大多数曲线都有数据的频率上做平均
        threshold = max(1, len(interp_list) * 0.5)
        valid_mask = valid_count >= threshold

        avg = np.full(len(common), np.nan)
        if np.any(valid_mask):
            avg[valid_mask] = np.nanmean(stacked[:, valid_mask], axis=0)

        return common, avg, interp_list

    h_freq, h_avg, h_indiv = avg_sfr(h_sfrs)
    v_freq, v_avg, v_indiv = avg_sfr(v_sfrs)

    def get_metric(sfr_list, key):
        vals = [s['sfr_values'][key] for s in sfr_list if key in s['sfr_values']]
        return float(np.mean(vals)) if vals else None

    def interp_metric(freqs, sfr_curve, pct):
        """从平均 SFR 曲线上插值求 SFR{pct}。"""
        if freqs is None or len(freqs) < 2:
            return None
        threshold = pct / 100.0
        nyq = 0.5
        for i in range(1, len(sfr_curve)):
            if freqs[i] > nyq:
                break
            v = sfr_curve[i]
            vp = sfr_curve[i - 1]
            if v is None or np.isnan(v) or vp is None or np.isnan(vp):
                continue
            if v <= threshold:
                f1, f2 = freqs[i - 1], freqs[i]
                m1, m2 = vp, v
                return float(f1 + (threshold - m1) * (f2 - f1) / (m2 - m1)) if m2 != m1 else float(f1)
        return None

    # 打印结果
    metrics = {}
    for label, sfrs, freqs, avg_curve in [('垂直 SFR (水平边)', h_sfrs, h_freq, h_avg),
                                            ('水平 SFR (垂直边)', v_sfrs, v_freq, v_avg)]:
        if not sfrs:
            print(f"  {label}: 无数据")
            continue
        sfr10 = interp_metric(freqs, avg_curve, 10)
        sfr20 = interp_metric(freqs, avg_curve, 20)
        sfr50 = interp_metric(freqs, avg_curve, 50)
        # SFR at Nyquist: 直接从平均曲线插值，限制在 [0, 1]
        sfr_nyq = None
        if freqs is not None and len(avg_curve) >= 2:
            nyq_idx = np.searchsorted(freqs, 0.5)
            if 0 < nyq_idx < len(avg_curve):
                f_lo, f_hi = freqs[nyq_idx - 1], freqs[nyq_idx]
                v_lo, v_hi = avg_curve[nyq_idx - 1], avg_curve[nyq_idx]
                if f_hi > f_lo and not (np.isnan(v_lo) or np.isnan(v_hi)):
                    sfr_nyq = float(np.clip(
                        v_lo + (0.5 - f_lo) * (v_hi - v_lo) / (f_hi - f_lo), 0, 1))
            elif nyq_idx > 0:
                v = avg_curve[nyq_idx - 1]
                sfr_nyq = float(np.clip(v, 0, 1)) if not np.isnan(v) else None

        key_prefix = 'V' if label.startswith('垂直') else 'H'
        metrics[f'{key_prefix}_SFR10'] = sfr10
        metrics[f'{key_prefix}_SFR20'] = sfr20
        metrics[f'{key_prefix}_SFR50'] = sfr50
        metrics[f'{key_prefix}_SFR_Nyq'] = sfr_nyq

        print(f"\n  {label} ({len(sfrs)} 条边平均):")
        print(f"    SFR10 = {sfr10:.4f}" if sfr10 is not None else "    SFR10 = ≥Nyquist")
        print(f"    SFR20 = {sfr20:.4f}" if sfr20 is not None else "    SFR20 = ≥Nyquist")
        print(f"    SFR50 = {sfr50:.4f}" if sfr50 is not None else "    SFR50 = ≥Nyquist")
        print(f"    SFR @ Nyquist = {sfr_nyq:.4f}" if sfr_nyq is not None else "    SFR @ Nyquist = N/A")

    # 各向异性
    v50 = metrics.get('V_SFR50')
    h50 = metrics.get('H_SFR50')
    if v50 and h50 and v50 > 0:
        ratio = h50 / v50
        metrics['anisotropy'] = ratio
        print(f"\n  各向异性比 (H_SFR50 / V_SFR50): {ratio:.4f}")

    t_end = time.perf_counter()
    timing = {
        'load_s':   round(t_load   - t0,          3),
        'detect_s': round(t_detect - t_load,       3),
        'sfr_s':    round(t_sfr    - t_edge_start, 3),
        'total_s':  round(t_end    - t0,           3),
    }
    print(f"  耗时: 加载={timing['load_s']:.3f}s  检测={timing['detect_s']:.3f}s"
          f"  SFR计算={timing['sfr_s']:.3f}s  合计={timing['total_s']:.3f}s")

    return {
        'image_id': display_name,
        'source_image': image_path,
        'split_half': split_half,
        'pattern': list(cb['pattern']),
        'square': [round(sx, 1), round(sy, 1)],
        'cb_pts': cb['pts'].tolist(),
        'h_edges': len(h_sfrs),
        'v_edges': len(v_sfrs),
        'timing': timing,
        'h_freq': h_freq.tolist() if h_freq is not None else None,
        'h_avg': h_avg.tolist() if h_avg is not None else None,
        'h_indiv': [s['sfr'].tolist() for s in h_sfrs],
        'v_freq': v_freq.tolist() if v_freq is not None else None,
        'v_avg': v_avg.tolist() if v_avg is not None else None,
        'v_indiv': [s['sfr'].tolist() for s in v_sfrs],
        'h_edge_info': [{'center': e['edge_center'], 'len': round(e['edge_len'], 1),
                         'p1': e['p1'], 'p2': e['p2']}
                         for e in h_edge_info],
        'v_edge_info': [{'center': e['edge_center'], 'len': round(e['edge_len'], 1),
                         'p1': e['p1'], 'p2': e['p2']}
                         for e in v_edge_info],
        'metrics': {k: round(v, 6) if v is not None else None for k, v in metrics.items()},
    }


# ─── 绘图 ───

def plot_sfr(result, image_name, output_path=None):
    """绘制 SFR 曲线对比图。"""
    if result is None:
        return

    plt = get_pyplot()
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"{plot_text('SFR 分析', 'SFR Analysis')} - {image_name}", fontsize=14, fontweight='bold')

    m = result['metrics']

    # ── 左上: SFR 曲线（平均 + 单条） ──
    ax = axes[0, 0]
    for label, freq_key, avg_key, indiv_key, color in [
        (plot_text('垂直 SFR (水平边)', 'Vertical SFR (from horizontal edges)'), 'h_freq', 'h_avg', 'h_indiv', '#3498db'),
        (plot_text('水平 SFR (垂直边)', 'Horizontal SFR (from vertical edges)'), 'v_freq', 'v_avg', 'v_indiv', '#e67e22'),
    ]:
        freqs = result.get(freq_key)
        avg = result.get(avg_key)
        indiv = result.get(indiv_key)
        if freqs is None or avg is None:
            continue
        freqs = np.array(freqs)
        avg = np.array(avg)
        nyq = 0.5
        v = freqs <= nyq
        ax.plot(freqs[v], avg[v], color=color, linewidth=2, label=label, zorder=3)
        if indiv:
            f2 = freqs
            for s in indiv:
                s = np.array(s)
                n = min(len(f2), len(s))
                fv = f2[:n] <= nyq
                ax.plot(f2[:n][fv], s[:n][fv],
                        color=color, linewidth=0.5, alpha=0.3, zorder=2)

    ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.4, label='50%')
    ax.axhline(y=0.2, color='gray', linestyle='-.', alpha=0.4, label='20%')
    ax.axhline(y=0.1, color='gray', linestyle=':', alpha=0.3, label='10%')
    ax.set_xlabel('Spatial Frequency (cycles/pixel)')
    ax.set_ylabel('SFR (normalized)')
    ax.set_title('SFR Curves')
    ax.legend(fontsize=8, loc='upper right')
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlim(0, 0.5)
    ax.grid(True, alpha=0.3)

    # ── 右上: ESF 曲线（用第一条有效边的数据） ──
    ax = axes[0, 1]
    for label, key, color in [('Horizontal edge', 'h', '#3498db'), ('Vertical edge', 'v', '#e67e22')]:
        esf_list = []
        for s in (result.get('h_sfrs') or []):
            pass
        # 从 indiv 中取第一条边 — 直接用 compute_edge_sfr 存的 esf 不在 result 里
        # 用 avg 曲线代替: 画 SFR 即可
    ax.text(0.5, 0.5, 'ESF is available in per-edge analysis', ha='center', va='center',
            transform=ax.transAxes, color='gray', fontsize=10)

    # ── 左下: 柱状图 — SFR 指标对比 ──
    ax = axes[1, 0]
    labels = ['SFR10', 'SFR20', 'SFR50', 'SFR@Nyq']
    h_vals = [m.get('V_SFR10'), m.get('V_SFR20'), m.get('V_SFR50'), m.get('V_SFR_Nyq')]
    v_vals = [m.get('H_SFR10'), m.get('H_SFR20'), m.get('H_SFR50'), m.get('H_SFR_Nyq')]
    h_vals = [x if x else 0 for x in h_vals]
    v_vals = [x if x else 0 for x in v_vals]

    x = np.arange(len(labels))
    width = 0.3
    bars1 = ax.bar(x - width / 2, h_vals, width, label='Vertical SFR', color='#3498db', alpha=0.8)
    bars2 = ax.bar(x + width / 2, v_vals, width, label='Horizontal SFR', color='#e67e22', alpha=0.8)

    for bar in bars1:
        if bar.get_height() > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                    f'{bar.get_height():.3f}', ha='center', va='bottom', fontsize=7)
    for bar in bars2:
        if bar.get_height() > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                    f'{bar.get_height():.3f}', ha='center', va='bottom', fontsize=7)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel('cycles/pixel')
    ax.set_title('SFR Metrics')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(0, max(max(h_vals), max(v_vals)) * 1.25 if (h_vals or v_vals) else 0.5)

    # ── 右下: 文字汇总 ──
    ax = axes[1, 1]
    ax.axis('off')
    lines = [f"Checkerboard: {result['pattern'][0]}x{result['pattern'][1]}, "
             f"square~{result['square'][0]:.0f}x{result['square'][1]:.0f}px",
             f"Valid edges: horizontal {result['h_edges']}, vertical {result['v_edges']}",
             '']

    for label, prefix in [('Vertical direction', 'V'), ('Horizontal direction', 'H')]:
        s10 = m.get(f'{prefix}_SFR10')
        s20 = m.get(f'{prefix}_SFR20')
        s50 = m.get(f'{prefix}_SFR50')
        snyq = m.get(f'{prefix}_SFR_Nyq')
        if s10 is None:
            continue
        lines.append(f"  {label}:")
        lines.append(f"    SFR10  = {s10:.4f} cy/px")
        lines.append(f"    SFR20  = {s20:.4f} cy/px")
        lines.append(f"    SFR50  = {s50:.4f} cy/px")
        lines.append(f"    SFR@Nyq = {snyq:.4f}")
        lines.append('')

    ani = m.get('anisotropy')
    if ani is not None:
        lines.append(f"  Anisotropy (H/V): {ani:.4f}")

    # 清晰度判定 (基于 SFR20)
    avg_sfr20 = 0
    cnt = 0
    for prefix in ['V', 'H']:
        v = m.get(f'{prefix}_SFR20')
        if v is not None:
            avg_sfr20 += v
            cnt += 1
    if cnt > 0:
        avg_sfr20 /= cnt
        if avg_sfr20 >= 0.40:
            grade = 'Excellent'
        elif avg_sfr20 >= 0.30:
            grade = 'Good'
        elif avg_sfr20 >= 0.20:
            grade = 'Fair'
        else:
            grade = 'Poor'
        lines.append(f"\n  Mean SFR20 = {avg_sfr20:.4f} -> Sharpness: {grade}")

    ax.text(0.05, 0.95, '\n'.join(lines), transform=ax.transAxes,
            fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#f0f0f0', alpha=0.9))

    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"  SFR 图已保存: {output_path}")
    plt.close(fig)


def plot_overlay(image, result, output_path=None):
    """在图像上标注棋盘格和使用的边缘。"""
    if result is None:
        return

    plt = get_pyplot()
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    ax.imshow(image, cmap='gray')

    # 画所有检测到的角点（优先复用已缓存结果，避免重复检测）
    cb_pts = result.get('cb_pts')
    if cb_pts:
        pts = np.array(cb_pts)
        ax.plot(pts[:, 0], pts[:, 1], '.', color='#aaaaaa', markersize=2, zorder=3)
    else:
        cb = detect_checkerboard(image)
        if cb:
            pts = cb['pts']
            ax.plot(pts[:, 0], pts[:, 1], '.', color='#aaaaaa', markersize=2, zorder=3)

    # 画使用的边缘线
    for ei_list, color in [(result.get('h_edge_info', []), '#3498db'),
                           (result.get('v_edge_info', []), '#e67e22')]:
        for ei in ei_list:
            p1, p2 = ei['p1'], ei['p2']
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]],
                    color=color, linewidth=1.2, alpha=0.7, zorder=5)

    # 汇总文字
    m = result['metrics']
    lines = []
    for label, prefix in [('V-SFR20', 'V_SFR20'), ('H-SFR20', 'H_SFR20')]:
        v = m.get(prefix)
        if v:
            lines.append(f"{label}: {v:.4f}")
    ani = m.get('anisotropy')
    if ani:
        lines.append(f"H/V: {ani:.3f}")
    if lines:
        ax.text(image.shape[1] - 5, 5, '\n'.join(lines),
                fontsize=10, color='white', fontweight='bold', va='bottom', ha='right',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#2c3e50', alpha=0.85), zorder=8)

    ax.set_title(plot_text('棋盘格 SFR 边缘分布', 'Checkerboard SFR Edge Distribution'), fontsize=13)
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"  标注图已保存: {output_path}")
    plt.close(fig)


def print_batch_summary(all_results):
    """打印批量汇总表。"""
    print(f"\n{'─' * 110}")
    header = (f"  {'图像':<40}"
              f"{'V-SFR10':>9}{'V-SFR20':>9}{'V-SFR50':>9}{'V-Nyq':>9}"
              f"{'H-SFR10':>9}{'H-SFR20':>9}{'H-SFR50':>9}{'H-Nyq':>9}"
              f"{'H/V':>8}")
    print(header)
    print(f"{'─' * 110}")

    for item_id, result in all_results.items():
        display_name = item_id
        if result is not None:
            display_name = result.get('image_id', item_id)
        if result is None:
            print(f"  {display_name:<40}{'无结果':>80}")
            continue
        m = result['metrics']
        row = f"  {display_name:<40}"
        for k in ['V_SFR10', 'V_SFR20', 'V_SFR50', 'V_SFR_Nyq',
                   'H_SFR10', 'H_SFR20', 'H_SFR50', 'H_SFR_Nyq']:
            v = m.get(k)
            row += f"{v:>9.4f}" if v else f"{'N/A':>9}"
        ani = m.get('anisotropy')
        row += f"{ani:>8.4f}" if ani else f"{'N/A':>8}"
        print(row)

    print(f"{'─' * 110}")


def append_metrics_csv(all_results, csv_path):
    """将关键指标以逗号分隔格式写入文件（覆盖旧内容）。"""
    keys = ['V_SFR10', 'V_SFR20', 'V_SFR50', 'V_SFR_Nyq',
            'H_SFR10', 'H_SFR20', 'H_SFR50', 'H_SFR_Nyq', 'anisotropy']
    header = ['image', 'V-SFR10', 'V-SFR20', 'V-SFR50', 'V-Nyq',
              'H-SFR10', 'H-SFR20', 'H-SFR50', 'H-Nyq', 'H/V']

    appended = 0

    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write(','.join(header) + '\n')

        for item_id, result in all_results.items():
            if result is None:
                continue

            m = result.get('metrics', {})
            image_col = result.get('image_id', item_id)

            row = [image_col]
            for k in keys:
                v = m.get(k)
                row.append(f"{v:.6f}" if v is not None else 'N/A')

            f.write(','.join(row) + '\n')
            appended += 1

    print(f"\n指标已写入(覆盖模式): {csv_path}  (共 {appended} 行)")


# ─── Main ───

def main():
    parser = argparse.ArgumentParser(
         description='棋盘格 SFR (Spatial Frequency Response) 分析 — ISO 12233 斜边法',
        epilog="示例:\n"
               "  python checkerboard_sfr.py use6/\n"
               "  python checkerboard_sfr.py image.png --json out.json\n"
             "  python checkerboard_sfr.py image.png --plot\n"
             "  python checkerboard_sfr.py use6/ --plot --batch-plot\n",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('images', nargs='+', help='图像文件或目录')
    parser.add_argument('--oversampling', type=int, default=4, help='ESF 超采样因子 (默认 4)')
    parser.add_argument('--detect-max-side', type=int, default=3000,
                        help='棋盘检测最大边长像素；超出将先降采样检测后映射回原图 (默认 3000)')
    parser.add_argument('--pattern-hint', default=None,
                        help='可选棋盘格角点提示，如 9x9 或 9x9,8x9；可显著加速并提高稳定性')
    parser.add_argument('--json', metavar='FILE', help='导出 JSON')
    parser.add_argument('--metrics-csv', default='sfr_metrics.csv',
                        help='导出指标到逗号分隔CSV文件（覆盖写入，默认 sfr_metrics.csv）')
    parser.add_argument('--plot', action='store_true',
                        help='显式生成单图结果：_sfr.png 和 _overlay.png；默认关闭')
    parser.add_argument('--batch-plot', action='store_true',
                        help='显式生成批量对比图 sfr_comparison.png；默认关闭，且通常与 --plot 搭配使用')
    parser.add_argument('--no-batch-plot', action='store_true',
                        help=argparse.SUPPRESS)
    parser.add_argument('--no-plot', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--split-lr', action='store_true',
                        help='将每张输入图像按左右等分后分别计算 SFR')
    parser.add_argument('--only-rgb', action='store_true',
                        help='仅处理文件名以 rgb 开头的图像')
    parser.add_argument('--dump-fail-debug', action='store_true',
                        help='检测失败时自动保存增强+边缘强度调试图')
    parser.add_argument('--detect-roi', default=None,
                        help='检测前裁剪ROI，格式 x1_frac,y1_frac,x2_frac,y2_frac (0~1比例)，例如 0.1,0.2,0.9,0.9')
    parser.add_argument('--output-dir', default=None, help='输出目录')
    parser.add_argument('--verbose-startup', action='store_true', help='输出启动阶段调试日志，便于定位卡住位置')
    parser.add_argument('--enable-chinese-font', action='store_true', help='启用中文字体配置；默认关闭以避免启动阶段字体扫描卡顿')
    args = parser.parse_args()

    global _PLOT_USE_CHINESE
    _PLOT_USE_CHINESE = args.enable_chinese_font

    enable_single_plot = args.plot and not args.no_plot
    enable_batch_plot = args.batch_plot and not args.no_batch_plot

    startup_log('开始扫描输入图像...', enabled=args.verbose_startup)

    # 收集图像
    image_paths = []
    for path in args.images:
        if os.path.isdir(path):
            for f in sorted(os.listdir(path)):
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff')):
                    if not any(f.endswith(s) for s in ['_sfr.png', '_overlay.png', '_comparison.png',
                                                      '_mtf_curves.png', '_roi_overlay.png']):
                        if args.only_rgb and not f.lower().startswith('rgb'):
                            continue
                        image_paths.append(os.path.join(path, f))
        elif os.path.isfile(path):
            if args.only_rgb and not os.path.basename(path).lower().startswith('rgb'):
                continue
            image_paths.append(path)
        else:
            print(f"  警告: {path} 不存在")

    if not image_paths:
        print("未找到图像文件")
        sys.exit(1)

    output_dir = args.output_dir or os.path.dirname(image_paths[0]) or '.'
    startup_log(f'输入图像收集完成，共 {len(image_paths)} 张', enabled=args.verbose_startup)
    if args.enable_chinese_font:
        startup_log('开始配置中文字体...', enabled=args.verbose_startup)
    setup_chinese_font(enabled=args.enable_chinese_font)
    pattern_pairs = parse_pattern_hint(args.pattern_hint)

    def _parse_detect_roi(text):
        if not text:
            return None
        try:
            parts = [float(x.strip()) for x in text.split(',')]
            if len(parts) == 4:
                return tuple(parts)
        except ValueError:
            pass
        print(f"  警告: --detect-roi 格式错误，忽略: {text}")
        return None

    detect_roi = _parse_detect_roi(getattr(args, 'detect_roi', None))
    if detect_roi:
        print(f"使用检测ROI: {detect_roi}")
    if pattern_pairs:
        print(f"使用 pattern hint: {pattern_pairs}")

    print(f"\n棋盘格 SFR 分析程序")
    print(f"共 {len(image_paths)} 张图片, 超采样={args.oversampling}")

    tasks = build_image_tasks(image_paths, split_lr=args.split_lr)
    startup_log(f'分析任务构建完成，共 {len(tasks)} 个任务', enabled=args.verbose_startup)
    if args.split_lr:
        print(f"左右分隔模式: 开启 (任务数 {len(tasks)} = 图像数 {len(image_paths)} x 2)")

    all_results = {}
    all_json = {}

    # 并行分析阶段（I/O + 计算密集，线程数不超过4或图片数）
    def _analyze(task):
        result = analyze_image(
            task['path'],
            oversampling=args.oversampling,
            detect_max_side=args.detect_max_side,
            pattern_pairs=pattern_pairs,
            dump_fail_debug=args.dump_fail_debug,
            fail_debug_dir=output_dir,
            split_half=task['split_half'],
            image_label=task['id'],
            detect_roi=detect_roi,
        )
        return task, result

    workers = min(4, len(tasks))
    t_analysis_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {executor.submit(_analyze, t): t for t in tasks}
        done = 0
        total = len(tasks)
        for future in as_completed(future_map):
            task, result = future.result()
            task_id = task['id']
            all_results[task_id] = result
            all_json[task_id] = result
            done += 1
            status = 'OK' if result is not None else 'FAIL'
            print(f"  [阶段1进度] {done}/{total} {task['display_name']} {status}")
    t_analysis_end = time.perf_counter()
    print("阶段 1/4: 并行分析完成")

    # 绘图阶段（matplotlib 非线程安全，串行执行）
    t_plot_start = time.perf_counter()
    for task in tasks:
        result = all_results.get(task['id'])
        if enable_single_plot and result:
            base = task['id'].replace(' ', '_').replace('\\', '_').replace('/', '_').replace(':', '_')
            raw = cv2.imread(task['path'], cv2.IMREAD_UNCHANGED)
            img = to_gray_u8(raw)
            if img is None:
                print(f"  警告: 绘图阶段读取失败，跳过标注图: {task['path']}")
                continue
            if task['split_half'] is not None:
                img = crop_lr_half(img, split_half=task['split_half'])
                if img is None:
                    print(f"  警告: 绘图阶段左右分隔失败，跳过标注图: {task['display_name']}")
                    continue
            plot_sfr(result, base,
                     output_path=os.path.join(output_dir, f"{base}_sfr.png"))
            plot_overlay(img, result,
                         output_path=os.path.join(output_dir, f"{base}_overlay.png"))
    t_plot_end = time.perf_counter()
    print("阶段 2/4: 单图绘图完成")

    # 耗时汇总
    print(f"\n{'─' * 70}")
    print(f"  耗时汇总 (workers={workers})")
    print(f"{'─' * 70}")
    print(f"  {'图像':<40}{'加载':>8}{'检测':>8}{'SFR计算':>10}{'合计':>8}")
    print(f"  {'':─<40}{'':─>8}{'':─>8}{'':─>10}{'':─>8}")
    sum_total = 0.0
    for task in tasks:
        r = all_results.get(task['id'])
        if r and r.get('timing'):
            t = r['timing']
            name = task['display_name']
            sum_total += t['total_s']
            print(f"  {name:<40}{t['load_s']:>7.3f}s{t['detect_s']:>7.3f}s{t['sfr_s']:>9.3f}s{t['total_s']:>7.3f}s")
        else:
            print(f"  {task['display_name']:<40}{'失败':>37}")
    wall_analysis = t_analysis_end - t_analysis_start
    wall_plot = t_plot_end - t_plot_start
    print(f"  {'':─<40}{'':─>8}{'':─>8}{'':─>10}{'':─>8}")
    print(f"  {'各图合计(串行等效)':<40}{'':>26}{sum_total:>7.3f}s")
    print(f"  {'分析阶段实际挂钟时间':<40}{'':>26}{wall_analysis:>7.3f}s"
          f"  (并行加速比 {sum_total/wall_analysis:.2f}x)" if wall_analysis > 0 else "")
    print(f"  {'绘图阶段挂钟时间':<40}{'':>26}{wall_plot:>7.3f}s")
    print(f"  {'总挂钟时间':<40}{'':>26}{wall_analysis + wall_plot:>7.3f}s")
    print(f"{'─' * 70}")

    # 批量汇总
    if len(all_results) > 1:
        print(f"\n{'=' * 70}")
        print("  批量处理汇总")
        print(f"{'=' * 70}")
        print_batch_summary(all_results)

        if enable_batch_plot:
            # 批量柱状图
            plt = get_pyplot()
            img_names = [os.path.basename(p) for p, r in all_results.items() if r]
            h_vals = [all_results[p]['metrics'].get('V_SFR20', 0) or 0 for p in all_results if all_results[p]]
            v_vals = [all_results[p]['metrics'].get('H_SFR20', 0) or 0 for p in all_results if all_results[p]]
            if img_names:
                x = np.arange(len(img_names))
                w = 0.3
                fig, ax = plt.subplots(figsize=(max(10, len(img_names) * 3), 6))
                ax.bar(x - w / 2, h_vals, w, label='Vertical SFR20', color='#3498db', alpha=0.8)
                ax.bar(x + w / 2, v_vals, w, label='Horizontal SFR20', color='#e67e22', alpha=0.8)
                ax.set_ylabel('SFR20 (cycles/pixel)')
                ax.set_title('SFR20 Comparison')
                ax.set_xticks(x)
                ax.set_xticklabels(img_names, rotation=15, ha='right')
                ax.legend(fontsize=9)
                ax.grid(True, alpha=0.3, axis='y')
                plt.tight_layout()
                plt.savefig(os.path.join(output_dir, 'sfr_comparison.png'), dpi=150, bbox_inches='tight')
                print(f"  批量对比图已保存: sfr_comparison.png")
                plt.close(fig)
            print("阶段 3/4: 批量汇总完成")

    # 指标导出（逗号分隔，覆盖写入）
    append_metrics_csv(all_results, args.metrics_csv)
    print("阶段 4/4: 指标CSV写入完成")

    failed_count = sum(1 for result in all_results.values() if result is None)
    ok_count = len(all_results) - failed_count

    if args.json:
        # JSON 序列化：将 numpy 转为 list
        def serialize(obj):
            if isinstance(obj, (np.floating, np.integer)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, dict):
                return {k: serialize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [serialize(v) for v in obj]
            return obj

        json_path = args.json
        if args.output_dir and not os.path.isabs(args.json):
            json_path = os.path.join(args.output_dir, args.json)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(serialize(all_json), f, indent=2, ensure_ascii=False)
        print(f"\nJSON 已保存: {json_path}")

    if failed_count == 0:
        print(f"\n执行结果: 正常 (成功 {ok_count}/{len(all_results)})")
        return 0

    print(f"\n执行结果: 不正常 (成功 {ok_count}/{len(all_results)}, 失败 {failed_count})")
    return 2


if __name__ == '__main__':
    sys.exit(main())
