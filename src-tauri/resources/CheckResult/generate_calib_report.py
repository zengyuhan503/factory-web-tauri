#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calibration Report PDF Generator
Generate images using Pillow and save as PDF
"""

import json
import sys
import os
import re

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Error: Pillow not installed. Run: pip install Pillow", file=sys.stderr)
    sys.exit(1)


def _has_cjk(text):
    """Check if text contains CJK characters"""
    if not text:
        return False
    return bool(re.search(r'[一-鿿　-〿＀-￯]', str(text)))


def _translate_to_english(text):
    """Translate common Chinese failure/warning messages to English"""
    if not text or not _has_cjk(text):
        return text

    # Common Chinese -> English mappings for calibration reports
    mappings = {
        "摄像头标定精度不足，建议重新拍摄（确保标定板清晰、光线充足）": "Camera calibration accuracy insufficient. Re-shoot recommended (ensure clear calibration board and adequate lighting).",
        "摄像头相对位置标定不合格，请检查摄像头安装是否松动": "Camera relative position calibration failed. Check if camera mounting is loose.",
        "整体标定精度不合格，建议重新拍摄或检查设备硬件": "Overall calibration accuracy failed. Re-shoot or check device hardware.",
        "IMU传感器加速度偏差过大，设备可能需要返修": "IMU accelerometer bias too large. Device may need repair.",
        "IMU传感器陀螺仪偏差过大，设备可能需要返修": "IMU gyroscope bias too large. Device may need repair.",
        "标定结果文件缺少IMU噪声参数，请重新执行标定": "Calibration result missing IMU noise parameters. Please re-run calibration.",
        "标定结果文件IMU参数不完整，请重新执行标定": "Calibration result IMU parameters incomplete. Please re-run calibration.",
        "标定板检测率过低，请重新拍摄（确保标定板完整出现在画面中）": "Calibration board detection rate too low. Re-shoot recommended (ensure board fully visible).",
        "标定结果存在多项不合格": "Multiple calibration items failed.",
        "覆盖率": "coverage",
        "检测率": "detection rate",
        "阈值": "threshold",
        "不足": "insufficient",
        "失败": "failed",
        "错误": "error",
        "警告": "warning",
        "缺少": "missing",
        "相机": "camera",
        "摄像头": "camera",
        "建议": "suggest",
        "重新": "re-",
        "拍摄": "shoot",
        "检查": "check",
        "确保": "ensure",
        "清晰": "clear",
        "光线": "lighting",
        "充足": "adequate",
        "松动": "loose",
        "设备": "device",
        "硬件": "hardware",
        "需要": "need",
        "返修": "repair",
        "执行": "execute",
        "标定": "calibration",
        "结果": "result",
        "文件": "file",
        "参数": "parameters",
        "完整": "complete",
        "出现在": "appear in",
        "画面中": "frame",
        "多项": "multiple",
        "不合格": "failed",
        "精度": "accuracy",
        "偏差": "bias",
        "过大": "too large",
        "传感器": "sensor",
        "陀螺仪": "gyroscope",
        "加速度": "accelerometer",
        "噪声": "noise",
        "过低": "too low",
        "标定板": "calibration board",
        "检测": "detection",
        "画面": "frame",
    }

    result = str(text)
    # Try full phrase match first
    for cn, en in mappings.items():
        if len(cn) > 4:  # Only replace longer phrases first
            result = result.replace(cn, en)
    # Then word-by-word
    for cn, en in mappings.items():
        if len(cn) <= 4:
            result = result.replace(cn, en)

    # If still has CJK, replace remaining CJK chars with "?"
    if _has_cjk(result):
        result = re.sub(r'[一-鿿　-〿＀-￯]', '?', result)

    return result


def load_font(size):
    """Load font - English only, no CJK support needed"""
    candidates = [
        # Windows
        ("C:/Windows/Fonts/arial.ttf", 0),
        ("C:/Windows/Fonts/segoeui.ttf", 0),
        ("C:/Windows/Fonts/calibri.ttf", 0),
        ("C:/Windows/Fonts/tahoma.ttf", 0),
        # Linux - DejaVu (most common)
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0),
        ("/usr/share/fonts/dejavu/DejaVuSans.ttf", 0),
        # Linux - Liberation
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 0),
        ("/usr/share/fonts/liberation-sans/LiberationSans-Regular.ttf", 0),
        # macOS
        ("/Library/Fonts/Arial.ttf", 0),
        ("/System/Library/Fonts/Helvetica.ttc", 0),
    ]
    for path, index in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size, index=index)
            except Exception:
                continue

    # Fallback: scan system font directories
    scan_dirs = [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        os.path.expanduser("~/.fonts"),
    ]
    for scan_dir in scan_dirs:
        if not os.path.isdir(scan_dir):
            continue
        for root, _, files in os.walk(scan_dir):
            for fname in files:
                if fname.lower().endswith(('.ttf', '.ttc', '.otf')):
                    fpath = os.path.join(root, fname)
                    try:
                        return ImageFont.truetype(fpath, size)
                    except Exception:
                        continue

    print("Error: No suitable font found. Install TrueType fonts, e.g.:", file=sys.stderr)
    print("  Ubuntu/Debian: sudo apt-get install fonts-dejavu-core", file=sys.stderr)
    sys.exit(1)


def text_size(draw, text, font):
    """Calculate text size"""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def parse_color(color_str):
    """#RRGGBB -> (R, G, B)"""
    color_str = color_str.lstrip('#')
    return tuple(int(color_str[i:i+2], 16) for i in (0, 2, 4))


class ReportBuilder:
    """Report builder"""

    def __init__(self):
        # A4 @ 180 DPI
        self.DPI = 180
        self.MM_TO_PX = self.DPI / 25.4
        self.PAGE_W = int(210 * self.MM_TO_PX)
        self.PAGE_H = int(297 * self.MM_TO_PX)
        self.MARGIN = int(18 * self.MM_TO_PX)
        self.CONTENT_W = self.PAGE_W - 2 * self.MARGIN

        # Fonts
        self.font_title = load_font(36)
        self.font_header = load_font(24)
        self.font_body = load_font(18)
        self.font_small = load_font(15)
        self.font_tiny = load_font(13)

        # Colors
        self.C_GREEN = "#008800"
        self.C_RED = "#cc0000"
        self.C_ORANGE = "#cc8800"
        self.C_BLUE = "#1a3a6a"
        self.C_GRAY = "#666666"
        self.C_LIGHT_GRAY = "#f0f0f0"

        # Pages
        self.pages = []
        self.current_page_elements = []
        self.y = self.MARGIN

    def new_page(self):
        """Start new page"""
        if self.current_page_elements:
            self.pages.append(self.current_page_elements)
        self.current_page_elements = []
        self.y = self.MARGIN

    def check_page_break(self, needed_height):
        """Check if page break needed"""
        if self.y + needed_height > self.PAGE_H - self.MARGIN:
            self.new_page()
            return True
        return False

    def add_text(self, text, font, color="#333333", x=None, gap=12):
        """Add text"""
        if x is None:
            x = self.MARGIN
        temp_img = Image.new('RGB', (self.PAGE_W, 1), 'white')
        temp_draw = ImageDraw.Draw(temp_img)
        h = text_size(temp_draw, text, font)[1]

        self.check_page_break(h + gap)
        self.current_page_elements.append(("text", x, self.y, text, font, color))
        self.y += h + gap

    def add_line(self, color="#cccccc"):
        """Add horizontal line"""
        self.check_page_break(8)
        self.current_page_elements.append(("hline", self.MARGIN, self.y, self.PAGE_W - self.MARGIN, self.y, color))
        self.y += 8

    def add_section_title(self, title, font=None):
        """Add section title - no underline"""
        if font is None:
            font = self.font_header
        temp_img = Image.new('RGB', (self.PAGE_W, 1), 'white')
        temp_draw = ImageDraw.Draw(temp_img)
        h = text_size(temp_draw, title, font)[1]

        # Space before and after title, no underline
        self.check_page_break(h + 22)
        self.current_page_elements.append(("section", self.MARGIN, self.y + 10, title, font, self.C_BLUE))
        self.y += h + 22

    def add_table_row(self, columns, widths, font=None, colors=None, bg_color=None):
        """Add table row"""
        if font is None:
            font = self.font_small
        if colors is None:
            colors = ["#333333"] * len(columns)

        temp_img = Image.new('RGB', (self.PAGE_W, 1), 'white')
        temp_draw = ImageDraw.Draw(temp_img)
        max_h = max(text_size(temp_draw, str(c), font)[1] for c in columns)
        row_h = max_h + 16

        self.check_page_break(row_h + 4)

        x = self.MARGIN
        self.current_page_elements.append(("row", self.MARGIN, self.y, columns, widths, font, colors, bg_color, row_h))
        self.y += row_h + 4

    def add_table_header(self, columns, widths, font=None):
        """Add table header"""
        self.add_table_row(columns, widths, font, ["#333333"] * len(columns), "#e8e8e8")

    def add_spacer(self, height=14):
        """Add vertical spacer"""
        self.check_page_break(height)
        self.y += height

    def finalize(self):
        """Finalize last page"""
        if self.current_page_elements:
            self.pages.append(self.current_page_elements)

    def render(self, output_path):
        """Render all pages to PDF"""
        self.finalize()

        rendered_pages = []
        for page_elements in self.pages:
            img = Image.new('RGB', (self.PAGE_W, self.PAGE_H), 'white')
            draw = ImageDraw.Draw(img)

            for elem in page_elements:
                etype = elem[0]
                if etype == "text":
                    _, x, y, text, font, color = elem
                    draw.text((x, y), text, font=font, fill=parse_color(color))
                elif etype == "hline":
                    _, x1, y, x2, y2, color = elem
                    draw.line([(x1, y), (x2, y2)], fill=parse_color(color), width=1)
                elif etype == "section":
                    _, x, y, title, font, color = elem
                    draw.text((x, y), title, font=font, fill=parse_color(color))
                    # No underline
                elif etype == "row":
                    _, x, y, columns, widths, font, colors, bg_color, row_h = elem
                    if bg_color:
                        draw.rectangle([(x, y), (self.PAGE_W - self.MARGIN, y + row_h)],
                                       fill=parse_color(bg_color))
                    cx = x
                    for i, (col, width) in enumerate(zip(columns, widths)):
                        color = colors[i] if i < len(colors) else "#333333"
                        col_h = text_size(draw, str(col), font)[1]
                        vy = y + (row_h - col_h) // 2
                        draw.text((cx, vy), str(col), font=font, fill=parse_color(color))
                        cx += width

            rendered_pages.append(img)

        if not rendered_pages:
            return

        first = rendered_pages[0].convert('RGB')
        rest = [p.convert('RGB') for p in rendered_pages[1:]]
        first.save(output_path, "PDF", resolution=self.DPI, save_all=True, append_images=rest)
        print(output_path)


def result_color(result):
    if result == "PASS":
        return "#008800"
    elif result == "FAIL":
        return "#cc0000"
    return "#333333"


def rating_color(rate_pct, thresholds):
    if rate_pct >= thresholds["excellent"]:
        return "#008800"
    elif rate_pct >= thresholds["good"]:
        return "#008800"
    elif rate_pct >= thresholds["acceptable"]:
        return "#cc8800"
    return "#cc0000"


def build_report(report_data, builder):
    """Build report elements from JSON data"""
    calib = report_data.get("calib", {})
    result = report_data.get("result", {})

    overall = result.get("overall", "UNKNOWN")
    is_pass = overall == "PASS"

    # ========== Title ==========
    builder.add_text("VR Device Calibration Report", builder.font_title, builder.C_BLUE, gap=14)
    builder.add_line()

    # ========== Header Info ==========
    builder.add_spacer(10)
    builder.add_text(f"Serial Number: {report_data.get('sn', 'N/A')}", builder.font_body)
    builder.add_text(f"CPU ID: {report_data.get('cpu_id', 'N/A')}", builder.font_body)
    builder.add_text(f"Generated At: {report_data.get('generated_at', 'N/A')}", builder.font_body)
    builder.add_spacer(8)

    overall_text = f"Overall Result: [PASS]" if is_pass else f"Overall Result: [FAIL]"
    overall_color = builder.C_GREEN if is_pass else builder.C_RED
    builder.add_text(overall_text, builder.font_header, overall_color, gap=14)
    builder.add_line()

    # ========== 1. Device Information ==========
    builder.add_section_title("1. Device Information")
    builder.add_text(f"  Device UID  : {calib.get('device_uid', 'N/A')}", builder.font_body)

    log_data = calib.get("log_data", {})
    ct = log_data.get("calibration_time", {})
    if ct:
        det_s = ct.get("detection_s", 0)
        cal_s = ct.get("calibration_s", 0)
        total = ct.get("total_s", det_s + cal_s)
        builder.add_text(
            f"  Calibration Time  : Detection {det_s:.1f}s + Optimization {cal_s:.1f}s = {total:.1f}s",
            builder.font_body
        )

    cameras = calib.get("cameras", {})
    builder.add_text(f"  Camera Count : {len(cameras)}", builder.font_body)

    # ========== 2. Camera Intrinsics ==========
    builder.add_section_title("2. Camera Intrinsics")

    cam_headers = ["Camera", "Resolution", "Focal Length(px)", "Principal Point(px)", "Model", "Shutter"]
    cam_widths = [140, 100, 110, 140, 200, 80]
    builder.add_table_header(cam_headers, cam_widths, builder.font_small)

    cam_names = sorted(cameras.keys(), key=lambda n: cameras[n].get("id", 999))
    for name in cam_names:
        cam = cameras.get(name, {})
        size = cam.get("size", [0, 0])
        fl = cam.get("focal_length", [0])
        pp = cam.get("principal_point", [0, 0])
        model = cam.get("model", "N/A")
        is_rolling = cam.get("is_rolling_shutter", False)
        shutter = "Rolling" if is_rolling else "Global"

        w = int(size[0]) if size else 0
        h = int(size[1]) if len(size) > 1 else 0
        fl_val = fl[0] if fl else 0
        pp_x = pp[0] if pp else 0
        pp_y = pp[1] if len(pp) > 1 else 0

        row = [
            name,
            f"{w}x{h}",
            f"{fl_val:.2f}",
            f"({pp_x:.1f}, {pp_y:.1f})",
            model,
            shutter,
        ]
        builder.add_table_row(row, cam_widths, builder.font_tiny)

    # ========== 3. Target Detection Rate ==========
    builder.add_section_title("3. Target Detection Rate")

    det_headers = ["Camera", "Target A", "Target B", "Overall Rate", "Rating"]
    det_widths = [140, 100, 100, 120, 100]
    builder.add_table_header(det_headers, det_widths, builder.font_small)

    det_data = log_data.get("detection", {})
    for name in cam_names:
        if name in det_data:
            d = det_data[name]
            targets = sorted(d.keys())
            det_a = d.get(targets[0], [0, 0]) if targets else [0, 0]
            det_b = d.get(targets[1], [0, 0]) if len(targets) > 1 else [0, 0]
            total_det = det_a[0] + det_b[0]
            total_all = det_a[1] + det_b[1]
            rate = (total_det / total_all * 100) if total_all > 0 else 0

            if rate >= 60:
                rating_str = "[**] EXCELLENT"
                rcolor = builder.C_GREEN
            elif rate >= 45:
                rating_str = "[OK] GOOD"
                rcolor = builder.C_GREEN
            elif rate >= 30:
                rating_str = "[--] ACCEPTABLE"
                rcolor = builder.C_ORANGE
            else:
                rating_str = "[!!] POOR"
                rcolor = builder.C_RED

            row = [
                name,
                f"{det_a[0]}/{det_a[1]}",
                f"{det_b[0]}/{det_b[1]}",
                f"{rate:.1f}%",
                rating_str,
            ]
            colors = ["#333333"] * 4 + [rcolor]
            builder.add_table_row(row, det_widths, builder.font_tiny, colors)

    # ========== 4. Intrinsic Calibration Accuracy ==========
    builder.add_section_title("4. Intrinsic Calibration Accuracy (RMS Residual)")

    intrin_headers = ["Camera", "Residual(px)", "Threshold", "Result"]
    intrin_widths = [180, 120, 120, 100]
    builder.add_table_header(intrin_headers, intrin_widths, builder.font_small)

    for item in calib.get("results", {}).get("intrinsic", []):
        is_ok = item.get("result") == "PASS"
        icon = "[OK]" if is_ok else "[!!]"
        rcolor = builder.C_GREEN if is_ok else builder.C_RED
        row = [
            item.get("camera", "N/A"),
            f"{item.get('rms', 0):.4f}",
            f"{item.get('threshold', 0):.2f}",
            f"{icon} {item.get('result', 'N/A')}",
        ]
        colors = ["#333333", "#333333", "#333333", rcolor]
        builder.add_table_row(row, intrin_widths, builder.font_tiny, colors)

    # ========== 5. Joint Calibration Accuracy ==========
    builder.add_section_title("5. Joint Calibration Accuracy (Extrinsics + IMU)")

    ext_headers = ["Stage", "RMS(px)", "Result"]
    ext_widths = [420, 100, 100]
    builder.add_table_header(ext_headers, ext_widths, builder.font_small)

    for item in calib.get("results", {}).get("extrinsic", []):
        stage = item.get("stage", "N/A")
        display = stage[:50] + "..." if len(stage) > 53 else stage
        rms = item.get("rms", 0)
        is_ok = item.get("result") == "PASS"
        icon = "[OK]" if is_ok else "[!!]"
        rcolor = builder.C_GREEN if is_ok else builder.C_RED

        if stage == "Full-Extrinsics+Intrinsics-Extrinsics":
            result_text = f"{icon} {item.get('result', 'N/A')} (Threshold < {item.get('threshold', 0)})"
        else:
            if rms <= 0.5:
                result_text = "[**] EXCELLENT"
                rcolor = builder.C_GREEN
            elif rms <= 0.8:
                result_text = "[OK] GOOD"
                rcolor = builder.C_GREEN
            elif rms <= 1.5:
                result_text = "[--] ACCEPTABLE"
                rcolor = builder.C_ORANGE
            else:
                result_text = "[!!] POOR"
                rcolor = builder.C_RED

        row = [display, f"{rms:.4f}", result_text]
        colors = ["#333333", "#333333", rcolor]
        builder.add_table_row(row, ext_widths, builder.font_tiny, colors)

    # ========== 6. Extrinsic Geometry ==========
    builder.add_section_title("6. Extrinsic Geometry (Relative to trackingA)")

    ext_geom = log_data.get("extrinsic", {}).get("baselines", {})
    if ext_geom:
        bl_headers = ["Camera", "Baseline(mm)", "Principal Axis Angle", "Angular Resolution(px/deg)"]
        bl_widths = [160, 120, 120, 140]
        builder.add_table_header(bl_headers, bl_widths, builder.font_small)

        for name in ["trackingB", "ctrl-trackingA", "ctrl-trackingB", "rgb-left", "rgb-right"]:
            if name in ext_geom:
                b = ext_geom[name]
                baseline = b.get("baseline_m", 0) * 1000
                angle = b.get("angle_deg", 0)
                ppd = b.get("pixels_per_deg", 0)
                row = [name, f"{baseline:.1f}", f"{angle:.1f}deg", f"{ppd:.2f}"]
                builder.add_table_row(row, bl_widths, builder.font_tiny)

    # ========== 7. Camera Consistency ==========
    builder.add_section_title("7. Camera Consistency Analysis")

    cons_headers = ["Pair", "Focal Length Diff%", "Principal Point Shift", "Result"]
    cons_widths = [200, 120, 120, 100]
    builder.add_table_header(cons_headers, cons_widths, builder.font_small)

    for item in calib.get("results", {}).get("consistency", []):
        label = item.get("label", "N/A")
        if "trackingA" in label and "trackingB" in label:
            label = "Tracking Pair"
        elif "ctrl-trackingA" in label and "ctrl-trackingB" in label:
            label = "Ctrl-Tracking Pair"
        elif "rgb-left" in label and "rgb-right" in label:
            label = "RGB Pair"

        is_ok = item.get("result") == "PASS"
        icon = "[OK]" if is_ok else "[!!]"
        rcolor = builder.C_GREEN if is_ok else builder.C_RED

        row = [
            label,
            f"{item.get('fl_diff_pct', 0):.3f}%",
            item.get("pp_shift_str", "N/A"),
            f"{icon} {item.get('result', 'N/A')}",
        ]
        colors = ["#333333", "#333333", "#333333", rcolor]
        builder.add_table_row(row, cons_widths, builder.font_tiny, colors)

    # ========== 8. IMU Calibration Results ==========
    builder.add_section_title("8. IMU Calibration Results")

    imu = calib.get("imu", {})
    if imu:
        if "moving_accel_noise" in imu:
            builder.add_text(f"  Accelerometer Noise : {imu['moving_accel_noise']:.6f}", builder.font_body)
        if "moving_gyro_noise" in imu:
            builder.add_text(f"  Gyroscope Noise   : {imu['moving_gyro_noise']:.6f}", builder.font_body)
        if "delta" in imu:
            builder.add_text(f"  Time Alignment     : {imu['delta'] * 1000:.3f} ms", builder.font_body)
        if "aBias" in imu:
            ab = imu["aBias"]
            builder.add_text(f"  Accel bias   : ({ab[0]:.4f}, {ab[1]:.4f}, {ab[2]:.4f})", builder.font_body)
        if "wBias" in imu:
            wb = imu["wBias"]
            builder.add_text(f"  Gyro bias    : ({wb[0]:.6f}, {wb[1]:.6f}, {wb[2]:.6f})", builder.font_body)
    else:
        builder.add_text("  No IMU Data", builder.font_body)

    builder.add_spacer(8)
    imu_headers = ["Item", "Value", "Threshold", "Result"]
    imu_widths = [180, 120, 120, 100]
    builder.add_table_header(imu_headers, imu_widths, builder.font_small)

    for item in calib.get("results", {}).get("imu_bias", []):
        is_ok = item.get("result") == "PASS"
        icon = "[OK]" if is_ok else "[!!]"
        rcolor = builder.C_GREEN if is_ok else builder.C_RED
        row = [
            item.get("item", "N/A"),
            f"{item.get('value', 0):.6f}",
            f"{item.get('threshold', 0):.4f}",
            f"{icon} {item.get('result', 'N/A')}",
        ]
        colors = ["#333333", "#333333", "#333333", rcolor]
        builder.add_table_row(row, imu_widths, builder.font_tiny, colors)

    # ========== 9. Warnings & Exceptions ==========
    builder.add_section_title("9. Warnings & Exceptions")

    has_warn = False
    warnings = log_data.get("warnings", [])
    for warn in warnings[:10]:
        # Translate Chinese to English for PDF
        en_warn = _translate_to_english(str(warn))
        builder.add_text(f"  WARNING: {en_warn}", builder.font_body, builder.C_ORANGE)
        has_warn = True
    if len(warnings) > 10:
        builder.add_text(f"  ... Total {len(warnings)} warnings", builder.font_body, builder.C_GRAY)
        has_warn = True

    special = log_data.get("special_checks", [])
    for check in special:
        en_check = _translate_to_english(str(check))
        builder.add_text(f"  CHECK: {en_check}", builder.font_body, builder.C_ORANGE)
        has_warn = True

    xml_missing = calib.get("xml_missing_checks", [])
    for item in xml_missing:
        en_item = _translate_to_english(str(item))
        builder.add_text(f"  WARNING: {en_item}", builder.font_body, builder.C_RED)
        has_warn = True

    if not has_warn:
        builder.add_text("  No Warnings", builder.font_body, builder.C_GREEN)

    # ========== 10. Failure Reasons ==========
    builder.add_section_title("10. Failure Reasons")

    failures = result.get("failures", [])
    if not failures:
        builder.add_text("  (None)", builder.font_body, builder.C_GREEN)
    else:
        for i, f in enumerate(failures, 1):
            en_f = _translate_to_english(str(f))
            builder.add_text(f"  {i}. {en_f}", builder.font_body, builder.C_RED)

    # ========== 11. Summary ==========
    builder.add_section_title("11. Summary")

    overall_color = builder.C_GREEN if is_pass else builder.C_RED
    builder.add_text(f"  Overall: {overall}", builder.font_header, overall_color)

    ext_full = log_data.get("extrinsic", {}).get("CalibrateIMU-robust-Trajectory-Extrinsics-Intrinsics-Full", {})
    if ext_full:
        joint_rms = ext_full.get("rms", 0)
        builder.add_text(f"  Joint Calibration Residual: {joint_rms:.4f} px", builder.font_body)

    intrinsic_results = calib.get("results", {}).get("intrinsic", [])
    if intrinsic_results:
        worst = max(intrinsic_results, key=lambda x: x.get("rms", 0))
        builder.add_text(
            f"  Worst Intrinsic Camera: {worst.get('camera', 'N/A')} ({worst.get('rms', 0):.4f} px)",
            builder.font_body
        )

    det_data = log_data.get("detection", {})
    if det_data:
        worst_cam = "N/A"
        worst_rate = 100.0
        for cam_name, d in det_data.items():
            total_det = 0
            total_all = 0
            for target, vals in d.items():
                total_det += vals[0]
                total_all += vals[1]
            rate = (total_det / total_all * 100) if total_all > 0 else 0
            if rate < worst_rate:
                worst_rate = rate
                worst_cam = cam_name
        builder.add_text(f"  Lowest Detection Rate Camera: {worst_cam} ({worst_rate:.1f}%)", builder.font_body)

    builder.add_spacer(12)
    builder.add_line()


def main():
    if len(sys.argv) < 3:
        print("Usage: generate_calib_report.py <json_path> <output_dir>", file=sys.stderr)
        sys.exit(1)

    json_path = sys.argv[1]
    output_dir = sys.argv[2]

    with open(json_path, 'r', encoding='utf-8') as f:
        report = json.load(f)

    builder = ReportBuilder()
    build_report(report, builder)

    output_path = os.path.join(output_dir, "calib_report.pdf")
    builder.render(output_path)


if __name__ == "__main__":
    main()
