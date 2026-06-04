#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标定验证报告 PDF 生成器
使用 Pillow 生成图像并保存为 PDF
支持中文、颜色标记、表格布局（无图片）
"""

import json
import sys
import os

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("错误: Pillow 库未安装。请运行: pip install Pillow", file=sys.stderr)
    sys.exit(1)


def load_font(size):
    """加载支持中文的字体"""
    candidates = [
        ("C:/Windows/Fonts/msyh.ttc", 0),       # Windows 微软雅黑
        ("C:/Windows/Fonts/simhei.ttf", 0),     # Windows 黑体
        ("C:/Windows/Fonts/simsun.ttc", 0),     # Windows 宋体
        ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 0),   # Linux 文泉驿
        ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 0), # Linux 文泉驿微米黑
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0), # Linux DejaVu
    ]
    for path, index in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size, index=index)
            except Exception:
                continue
    return ImageFont.load_default()


def text_size(draw, text, font):
    """计算文本尺寸"""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def parse_color(color_str):
    """#RRGGBB -> (R, G, B)"""
    color_str = color_str.lstrip('#')
    return tuple(int(color_str[i:i+2], 16) for i in (0, 2, 4))


class ReportBuilder:
    """报告构建器，负责收集元素并分页渲染"""

    def __init__(self):
        # A4 尺寸 @ 180 DPI
        self.DPI = 180
        self.MM_TO_PX = self.DPI / 25.4
        self.PAGE_W = int(210 * self.MM_TO_PX)
        self.PAGE_H = int(297 * self.MM_TO_PX)
        self.MARGIN = int(18 * self.MM_TO_PX)
        self.CONTENT_W = self.PAGE_W - 2 * self.MARGIN

        # 字体
        self.font_title = load_font(36)
        self.font_header = load_font(24)
        self.font_body = load_font(18)
        self.font_small = load_font(15)
        self.font_tiny = load_font(13)

        # 颜色
        self.C_GREEN = "#008800"
        self.C_RED = "#cc0000"
        self.C_ORANGE = "#cc8800"
        self.C_BLUE = "#1a3a6a"
        self.C_GRAY = "#666666"
        self.C_LIGHT_GRAY = "#f0f0f0"

        # 收集所有页面
        self.pages = []
        self.current_page_elements = []
        self.y = self.MARGIN

    def new_page(self):
        """开始新页面"""
        if self.current_page_elements:
            self.pages.append(self.current_page_elements)
        self.current_page_elements = []
        self.y = self.MARGIN

    def check_page_break(self, needed_height):
        """检查是否需要分页"""
        if self.y + needed_height > self.PAGE_H - self.MARGIN:
            self.new_page()
            return True
        return False

    def add_text(self, text, font, color="#333333", x=None, gap=8):
        """添加文本"""
        if x is None:
            x = self.MARGIN
        # 临时计算高度
        temp_img = Image.new('RGB', (self.PAGE_W, 1), 'white')
        temp_draw = ImageDraw.Draw(temp_img)
        h = text_size(temp_draw, text, font)[1]

        self.check_page_break(h + gap)
        self.current_page_elements.append(("text", x, self.y, text, font, color))
        self.y += h + gap

    def add_line(self, color="#cccccc"):
        """添加水平分隔线"""
        self.check_page_break(4)
        self.current_page_elements.append(("hline", self.MARGIN, self.y, self.PAGE_W - self.MARGIN, self.y, color))
        self.y += 4

    def add_section_title(self, title, font=None):
        """添加章节标题（带下划线）"""
        if font is None:
            font = self.font_header
        temp_img = Image.new('RGB', (self.PAGE_W, 1), 'white')
        temp_draw = ImageDraw.Draw(temp_img)
        h = text_size(temp_draw, title, font)[1]

        self.check_page_break(h + 12)
        self.current_page_elements.append(("section", self.MARGIN, self.y, title, font, self.C_BLUE))
        self.y += h + 12

    def add_table_row(self, columns, widths, font=None, colors=None, bg_color=None):
        """添加表格行"""
        if font is None:
            font = self.font_small
        if colors is None:
            colors = ["#333333"] * len(columns)

        temp_img = Image.new('RGB', (self.PAGE_W, 1), 'white')
        temp_draw = ImageDraw.Draw(temp_img)
        max_h = max(text_size(temp_draw, str(c), font)[1] for c in columns)
        row_h = max_h + 6

        self.check_page_break(row_h + 2)

        x = self.MARGIN
        self.current_page_elements.append(("row", self.MARGIN, self.y, columns, widths, font, colors, bg_color, row_h))
        self.y += row_h + 2

    def add_table_header(self, columns, widths, font=None):
        """添加表格表头（带背景色）"""
        self.add_table_row(columns, widths, font, ["#333333"] * len(columns), "#e8e8e8")

    def add_spacer(self, height=10):
        """添加空白间距"""
        self.check_page_break(height)
        self.y += height

    def finalize(self):
        """结束最后一页"""
        if self.current_page_elements:
            self.pages.append(self.current_page_elements)

    def render(self, output_path):
        """渲染所有页面为 PDF"""
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
                    h = text_size(draw, title, font)[1]
                    draw.line([(x, y + h + 2), (self.PAGE_W - self.MARGIN, y + h + 2)],
                              fill=parse_color(color), width=2)
                elif etype == "row":
                    _, x, y, columns, widths, font, colors, bg_color, row_h = elem
                    if bg_color:
                        draw.rectangle([(x, y), (self.PAGE_W - self.MARGIN, y + row_h)],
                                       fill=parse_color(bg_color))
                    cx = x
                    for i, (col, width) in enumerate(zip(columns, widths)):
                        color = colors[i] if i < len(colors) else "#333333"
                        # 垂直居中
                        col_h = text_size(draw, str(col), font)[1]
                        vy = y + (row_h - col_h) // 2
                        draw.text((cx, vy), str(col), font=font, fill=parse_color(color))
                        cx += width

            rendered_pages.append(img)

        if not rendered_pages:
            return

        # 保存为 PDF（多页）
        first = rendered_pages[0].convert('RGB')
        rest = [p.convert('RGB') for p in rendered_pages[1:]]
        first.save(output_path, "PDF", resolution=self.DPI, save_all=True, append_images=rest)
        print(output_path)


def result_color(result):
    """根据结果返回颜色"""
    if result == "PASS":
        return "#008800"
    elif result == "FAIL":
        return "#cc0000"
    return "#333333"


def rating_color(rate_pct, thresholds):
    """根据检测率返回颜色"""
    if rate_pct >= thresholds["excellent"]:
        return "#008800"
    elif rate_pct >= thresholds["good"]:
        return "#008800"
    elif rate_pct >= thresholds["acceptable"]:
        return "#cc8800"
    return "#cc0000"


def build_report(report_data, builder):
    """根据 JSON 数据构建报告元素"""
    calib = report_data.get("calib", {})
    result = report_data.get("result", {})

    overall = result.get("overall", "UNKNOWN")
    is_pass = overall == "PASS"

    # ========== 标题 ==========
    builder.add_text("VR 设备标定验证报告", builder.font_title, builder.C_BLUE)
    builder.add_text("", builder.font_body, gap=4)
    builder.add_line()
    builder.add_text("", builder.font_body, gap=4)

    # ========== 头部信息 ==========
    builder.add_text(f"设备序列号: {report_data.get('sn', 'N/A')}", builder.font_body)
    builder.add_text(f"CPU ID: {report_data.get('cpu_id', 'N/A')}", builder.font_body)
    builder.add_text(f"生成时间: {report_data.get('generated_at', 'N/A')}", builder.font_body)

    overall_text = f"整体结果: [PASS]" if is_pass else f"整体结果: [FAIL]"
    overall_color = builder.C_GREEN if is_pass else builder.C_RED
    builder.add_text(overall_text, builder.font_header, overall_color, gap=12)
    builder.add_line()

    # ========== 一、设备基本信息 ==========
    builder.add_section_title("一、设备基本信息")
    builder.add_text(f"  设备 UID  : {calib.get('device_uid', 'N/A')}", builder.font_body)

    log_data = calib.get("log_data", {})
    ct = log_data.get("calibration_time", {})
    if ct:
        det_s = ct.get("detection_s", 0)
        cal_s = ct.get("calibration_s", 0)
        total = ct.get("total_s", det_s + cal_s)
        builder.add_text(
            f"  标定耗时  : 检测 {det_s:.1f}s + 优化 {cal_s:.1f}s = {total:.1f}s",
            builder.font_body
        )

    cameras = calib.get("cameras", {})
    builder.add_text(f"  摄像头数量 : {len(cameras)}", builder.font_body)

    # ========== 二、摄像头内参 ==========
    builder.add_section_title("二、摄像头内参")

    cam_headers = ["摄像头", "分辨率", "焦距(px)", "主点(px)", "模型", "快门"]
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

    # ========== 三、标定板检测率 ==========
    builder.add_section_title("三、标定板检测率")

    det_headers = ["摄像头", "A板", "B板", "综合检测率", "评级"]
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

    # ========== 四、内参标定精度 ==========
    builder.add_section_title("四、内参标定精度 (RMS 残差)")

    intrin_headers = ["摄像头", "残差(px)", "阈值", "结果"]
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

    # ========== 五、联合标定精度 ==========
    builder.add_section_title("五、联合标定精度 (外参 + IMU)")

    ext_headers = ["阶段", "RMS(px)", "结果"]
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
            result_text = f"{icon} {item.get('result', 'N/A')} (阈值 < {item.get('threshold', 0)})"
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

    # ========== 六、外参几何关系 ==========
    builder.add_section_title("六、外参几何关系 (相对 trackingA)")

    ext_geom = log_data.get("extrinsic", {}).get("baselines", {})
    if ext_geom:
        bl_headers = ["摄像头", "基线(mm)", "主轴夹角", "角分辨率(px/°)"]
        bl_widths = [160, 120, 120, 140]
        builder.add_table_header(bl_headers, bl_widths, builder.font_small)

        for name in ["trackingB", "ctrl-trackingA", "ctrl-trackingB", "rgb-left", "rgb-right"]:
            if name in ext_geom:
                b = ext_geom[name]
                baseline = b.get("baseline_m", 0) * 1000
                angle = b.get("angle_deg", 0)
                ppd = b.get("pixels_per_deg", 0)
                row = [name, f"{baseline:.1f}", f"{angle:.1f}°", f"{ppd:.2f}"]
                builder.add_table_row(row, bl_widths, builder.font_tiny)

    # ========== 七、摄像头一致性 ==========
    builder.add_section_title("七、摄像头一致性分析")

    cons_headers = ["对比组", "焦距差%", "主点偏移", "结果"]
    cons_widths = [200, 120, 120, 100]
    builder.add_table_header(cons_headers, cons_widths, builder.font_small)

    for item in calib.get("results", {}).get("consistency", []):
        label = item.get("label", "N/A")
        # 简化标签
        if "trackingA" in label and "trackingB" in label:
            label = "Tracking 组"
        elif "ctrl-trackingA" in label and "ctrl-trackingB" in label:
            label = "Ctrl-Tracking 组"
        elif "rgb-left" in label and "rgb-right" in label:
            label = "RGB 组"

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

    # ========== 八、IMU 标定结果 ==========
    builder.add_section_title("八、IMU 标定结果")

    imu = calib.get("imu", {})
    if imu:
        if "moving_accel_noise" in imu:
            builder.add_text(f"  加速度计噪声 : {imu['moving_accel_noise']:.6f}", builder.font_body)
        if "moving_gyro_noise" in imu:
            builder.add_text(f"  陀螺仪噪声   : {imu['moving_gyro_noise']:.6f}", builder.font_body)
        if "delta" in imu:
            builder.add_text(f"  时间对齐     : {imu['delta'] * 1000:.3f} ms", builder.font_body)
        if "aBias" in imu:
            ab = imu["aBias"]
            builder.add_text(f"  Accel bias   : ({ab[0]:.4f}, {ab[1]:.4f}, {ab[2]:.4f})", builder.font_body)
        if "wBias" in imu:
            wb = imu["wBias"]
            builder.add_text(f"  Gyro bias    : ({wb[0]:.6f}, {wb[1]:.6f}, {wb[2]:.6f})", builder.font_body)
    else:
        builder.add_text("  无 IMU 数据", builder.font_body)

    # IMU bias 判定表格
    builder.add_text("", builder.font_body, gap=4)
    imu_headers = ["检查项", "值", "阈值", "结果"]
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

    # ========== 九、警告 & 异常 ==========
    builder.add_section_title("九、警告 & 异常")

    has_warn = False
    warnings = log_data.get("warnings", [])
    for warn in warnings[:10]:
        builder.add_text(f"  WARNING: {warn}", builder.font_body, builder.C_ORANGE)
        has_warn = True
    if len(warnings) > 10:
        builder.add_text(f"  ... 共 {len(warnings)} 条警告", builder.font_body, builder.C_GRAY)
        has_warn = True

    special = log_data.get("special_checks", [])
    for check in special:
        builder.add_text(f"  CHECK: {check}", builder.font_body, builder.C_ORANGE)
        has_warn = True

    xml_missing = calib.get("xml_missing_checks", [])
    for item in xml_missing:
        builder.add_text(f"  WARNING: {item}", builder.font_body, builder.C_RED)
        has_warn = True

    if not has_warn:
        builder.add_text("  无警告", builder.font_body, builder.C_GREEN)

    # ========== 十、失败原因 ==========
    builder.add_section_title("十、失败原因")

    failures = result.get("failures", [])
    if not failures:
        builder.add_text("  （无）", builder.font_body, builder.C_GREEN)
    else:
        for i, f in enumerate(failures, 1):
            builder.add_text(f"  {i}. {f}", builder.font_body, builder.C_RED)

    # ========== 十一、总结 ==========
    builder.add_section_title("十一、总结")

    # 总评（大号醒目显示）
    overall_color = builder.C_GREEN if is_pass else builder.C_RED
    builder.add_text(f"  总评: {overall}", builder.font_header, overall_color)

    # 联合标定残差
    ext_full = log_data.get("extrinsic", {}).get("CalibrateIMU-robust-Trajectory-Extrinsics-Intrinsics-Full", {})
    if ext_full:
        joint_rms = ext_full.get("rms", 0)
        builder.add_text(f"  联合标定残差: {joint_rms:.4f} px", builder.font_body)

    # 最弱摄像头
    intrinsic_results = calib.get("results", {}).get("intrinsic", [])
    if intrinsic_results:
        worst = max(intrinsic_results, key=lambda x: x.get("rms", 0))
        builder.add_text(
            f"  内参最弱摄像头: {worst.get('camera', 'N/A')} ({worst.get('rms', 0):.4f} px)",
            builder.font_body
        )

    # 检测率最低
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
        builder.add_text(f"  检测率最低摄像头: {worst_cam} ({worst_rate:.1f}%)", builder.font_body)

    builder.add_text("", builder.font_body, gap=8)
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
