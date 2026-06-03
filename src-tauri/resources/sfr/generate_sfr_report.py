#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SFR 清晰度验证报告 PDF 生成器
使用 Pillow 生成图像并保存为 PDF
支持中文、图片嵌入、颜色标记
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


def main():
    if len(sys.argv) < 4:
        print("Usage: generate_sfr_report.py <json_path> <output_dir> <img_dir>", file=sys.stderr)
        sys.exit(1)

    json_path = sys.argv[1]
    output_dir = sys.argv[2]
    img_dir = sys.argv[3]

    with open(json_path, 'r', encoding='utf-8') as f:
        report = json.load(f)

    # A4 尺寸 @ 180 DPI (足够清晰且文件不会太大)
    DPI = 180
    MM_TO_PX = DPI / 25.4
    PAGE_W = int(210 * MM_TO_PX)   # A4 宽
    MARGIN = int(18 * MM_TO_PX)
    CONTENT_W = PAGE_W - 2 * MARGIN

    # 字体
    font_title = load_font(42)
    font_header = load_font(28)
    font_body = load_font(22)
    font_small = load_font(18)
    font_tiny = load_font(15)

    # 先创建临时图像来计算总高度
    temp_img = Image.new('RGB', (PAGE_W, 1), 'white')
    temp_draw = ImageDraw.Draw(temp_img)

    def get_h(text, font):
        return text_size(temp_draw, text, font)[1]

    # 收集所有绘制元素
    elements = []
    y = MARGIN

    def add_text(text, font, color="#000000", x=None, gap=10):
        nonlocal y
        if x is None:
            x = MARGIN
        elements.append(("text", x, y, text, font, color))
        y += get_h(text, font) + gap

    def add_hline(color="#cccccc"):
        nonlocal y
        elements.append(("line", MARGIN, y, PAGE_W - MARGIN, y, color))
        y += 4

    def add_space(h):
        nonlocal y
        y += h

    # ========== 标题 ==========
    add_text("SFR 清晰度验证报告", font_title, "#1a1a1a", gap=12)
    add_hline("#999999")
    add_space(15)

    # ========== 设备信息 ==========
    add_text("设备信息", font_header, "#1a1a1a", gap=8)
    add_text(f"  设备序列号 (SN): {report['sn']}", font_body, "#333333", gap=7)
    add_text(f"  CPU ID: {report['cpu_id']}", font_body, "#333333", gap=7)
    add_text(f"  生成时间: {report['generated_at']}", font_body, "#333333", gap=7)
    add_space(15)

    # ========== 整体结果 ==========
    is_pass = report['result']['overall'] == 'PASS'
    result_color = "#008800" if is_pass else "#cc0000"
    result_text = "整体结果: [ PASS ]" if is_pass else "整体结果: [ FAIL ]"
    add_text(result_text, font_header, result_color, gap=10)
    add_text(f"设备判级: {report['sfr']['device_grade']}", font_body, "#333333", gap=7)
    add_space(15)

    # ========== 验证配置 ==========
    add_text("验证配置", font_header, "#1a1a1a", gap=8)
    add_text(f"  清晰度均值阈值 (mean_avg50_min): {report['sfr']['mean_avg50_min_pass']:.4f}", font_body, "#555555", gap=6)
    add_text(f"  摄像头间标准差阈值 (cam_std_max): {report['sfr']['cam_std_max_pass']:.4f}", font_body, "#555555", gap=6)
    add_space(12)

    # ========== 验证结果统计 ==========
    add_text("验证结果统计", font_header, "#1a1a1a", gap=8)

    mean_ok = report['sfr']['device_mean_avg50'] >= report['sfr']['mean_avg50_min_pass']
    mean_color = "#008800" if mean_ok else "#cc0000"
    mean_label = f"  设备 mean_avg50: {report['sfr']['device_mean_avg50']:.4f}"
    mean_tag = "  [PASS]" if mean_ok else "  [FAIL]"
    add_text(mean_label + mean_tag, font_body, mean_color, gap=6)

    std_ok = report['sfr']['device_std_avg50'] <= report['sfr']['cam_std_max_pass']
    std_color = "#008800" if std_ok else "#cc0000"
    std_label = f"  设备 std_avg50: {report['sfr']['device_std_avg50']:.6f}"
    std_tag = "  [PASS]" if std_ok else "  [FAIL]"
    add_text(std_label + std_tag, font_body, std_color, gap=6)

    add_text(f"  摄像头数量: {len(report['sfr']['cameras'])}", font_body, "#555555", gap=6)
    add_space(12)

    # ========== 失败原因 ==========
    if report['result']['failures']:
        add_text("失败原因", font_header, "#cc0000", gap=8)
        for f in report['result']['failures']:
            add_text(f"  ● {f}", font_small, "#cc0000", gap=5)
        add_space(12)

    # ========== 摄像头详情表格 ==========
    if report['sfr']['cameras']:
        add_text("各摄像头清晰度详情", font_header, "#1a1a1a", gap=10)

        # 表头
        header_text = f"{'摄像头':<14} {'V-SFR50':>10} {'H-SFR50':>10} {'AVG50':>10} {'结果':>8}"
        add_text(header_text, font_small, "#666666", gap=5)
        add_hline("#bbbbbb")

        for cam in report['sfr']['cameras']:
            cam_pass = cam['pass']
            color = "#008800" if cam_pass else "#cc0000"
            result = "PASS" if cam_pass else "FAIL"
            line = f"{cam['cam']:<14} {cam['v50']:>10.4f} {cam['h50']:>10.4f} {cam['avg50']:>10.4f} {result:>8}"
            add_text(line, font_small, color, gap=5)
        add_space(20)

    # ========== 图片区域 ==========
    if report['sfr']['cameras']:
        add_text("SFR 图片", font_header, "#1a1a1a", gap=15)

        img_cols = 2
        img_gap = 25
        img_w = (CONTENT_W - img_gap) // img_cols
        img_h = int(img_w * 0.75)

        for i, cam in enumerate(report['sfr']['cameras']):
            col = i % img_cols
            row = i // img_cols
            img_x = MARGIN + col * (img_w + img_gap)
            img_y = y

            # 尝试多个可能的图片文件名（CSV 中可能是 sfr_0.png，实际文件可能是 0.png）
            img_path = None
            candidates = [
                os.path.join(img_dir, cam['image']),
                os.path.join(img_dir, cam['image'].replace('sfr_', '')),
                os.path.join(img_dir, cam['image'].replace('.png', '.jpg').replace('sfr_', '')),
                os.path.join(img_dir, cam['cam'] + '.png'),
                os.path.join(img_dir, cam['cam'] + '.jpg'),
            ]
            for cand in candidates:
                if os.path.exists(cand):
                    img_path = cand
                    break

            if img_path:
                elements.append(("image", img_x, img_y, img_w, img_h, img_path))

            # 图片标签
            label_color = "#008800" if cam['pass'] else "#cc0000"
            label = f"{cam['cam']}: AVG50={cam['avg50']:.4f} [{'PASS' if cam['pass'] else 'FAIL'}]"
            elements.append(("text", img_x, img_y + img_h + 6, label, font_tiny, label_color))

            if col == img_cols - 1:
                y += img_h + 40

        # 最后一行未满时也需要换行
        if len(report['sfr']['cameras']) % img_cols != 0:
            y += img_h + 40

    # 底部留白
    y += MARGIN

    # ========== 创建最终图像并绘制 ==========
    total_height = y
    img = Image.new('RGB', (PAGE_W, total_height), 'white')
    draw = ImageDraw.Draw(img)

    for elem in elements:
        kind = elem[0]
        if kind == "text":
            _, x, y_pos, text, font, color = elem
            draw.text((x, y_pos), text, font=font, fill=parse_color(color))
        elif kind == "line":
            _, x1, y1, x2, y2, color = elem
            draw.line([(x1, y1), (x2, y2)], fill=parse_color(color), width=2)
        elif kind == "image":
            _, x, y_pos, w, h, path = elem
            try:
                cam_img = Image.open(path)
                # 保持宽高比缩放
                cam_img.thumbnail((w, h), Image.LANCZOS)
                # 居中放置
                actual_w, actual_h = cam_img.size
                offset_x = x + (w - actual_w) // 2
                offset_y = y_pos + (h - actual_h) // 2
                img.paste(cam_img, (offset_x, offset_y))
            except Exception as e:
                print(f"Warning: 加载图片失败 {path}: {e}", file=sys.stderr)

    # 保存为 PDF
    output_path = os.path.join(output_dir, "sfr_report.pdf")
    img.save(output_path, "PDF", resolution=DPI)
    print(output_path)


if __name__ == "__main__":
    main()
