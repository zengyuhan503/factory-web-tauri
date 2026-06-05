# SkyCalib 运行环境依赖与部署指南

本文档说明 **打包后的 SkyCalib 应用** 在目标机器上运行所需的系统环境、依赖库和第三方工具。

> **适用范围**：`.deb` 安装包安装后的运行环境，非开发编译环境。

---

## 1. 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Linux (Ubuntu 18.04+) |
| 架构 | x86_64 (amd64) |
| 显示环境 | X11 / Wayland 桌面环境（GUI 应用必需） |
| 内存 | 建议 8GB+ |
| 磁盘空间 | 建议 20GB+（标定结果数据占用较大） |

---

## 2. 系统级依赖

### 2.1 ADB (Android Debug Bridge)

**必需**。用于与 VR 设备通信（shell、push、pull、reboot）。

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install android-tools-adb

# 验证
adb version
```

> **注意**：运行应用的用户需要 ADB 权限。udev 规则未配置时可能需要 `sudo`。

### 2.2 Python 3

**必需**。标定流水线大量依赖 Python 脚本。

```bash
# Ubuntu 18.04/20.04/22.04 默认已安装，验证版本
python3 --version   # 建议 3.8+，SFR 脚本优先检测 python3.12

# 如未安装
sudo apt install python3 python3-pip
```

### 2.3 Bash

**必需**。部分脚本通过 `bash` 调用外部工具。

```bash
# 通常已预装，验证
bash --version
```

---

## 3. Python 第三方库

标定脚本依赖以下 Python 包，**需要在目标机器上安装**：

### 3.1 核心依赖（标定主流程）

| 包名 | 用途 | 安装命令 |
|------|------|----------|
| `numpy` | 数组运算、标定数据处理 | `pip3 install numpy` |
| `scipy` | SFR 图像处理、空间变换 | `pip3 install scipy` |
| `opencv-python` | 图像读取、SFR 棋盘格分析 | `pip3 install opencv-python` |

### 3.2 报告生成依赖

| 包名 | 用途 | 安装命令 |
|------|------|----------|
| `pandas` | 数据表格处理（ferraris 工具、GT Calib Checker） | `pip3 install pandas` |
| `matplotlib` | 图表绘制（标定结果可视化） | `pip3 install matplotlib` |

### 3.3 其他依赖

| 包名 | 用途 | 安装命令 |
|------|------|----------|
| `packaging` | 版本解析（imucal 内部依赖） | `pip3 install packaging` |
| `typing_extensions` | 类型扩展（imucal 内部依赖） | `pip3 install typing_extensions` |

### 3.4 一键安装

```bash
pip3 install numpy scipy opencv-python pandas matplotlib packaging typing_extensions
```

> **注意**：`imucal` 库已内置在应用 `resources/tools/ferraris/dependence_library/` 目录下，**无需 pip 安装**。

---

## 4. 外部可执行工具（需随应用部署）

以下工具**不属于 pip 包**，需要确保存在于应用运行目录的对应位置，并具有可执行权限。

### 4.1 XRCalib（核心标定引擎）

| 项目 | 说明 |
|------|------|
| 路径 | `<app_dir>/tools/qvr_calib/XRCalib` |
| 用途 | 运行相机标定算法的主程序 |
| 权限 | 必须具有可执行权限 (`chmod +x`) |
| 配置 | 同目录下 `config/` 需包含各型号标定配置文件 |

**配置清单**（`tools/qvr_calib/config/` 目录）：
- `Target-config.xml`
- `Vq910_XRCalib-config.xml`
- `Vq910_XRCalib_Rgb-config.xml`
- `Vq920_XRCalib-config.xml`
- `Vq920_XRCalib_Rgb-config.xml`
- `Vq920_XRCalib_Hand-config.xml`
- `Vq920_XRCalib_Rgb_Hand-config.xml`
- `Vq930_XRCalib-config.xml`
- `Vq930_XRCalib_Rgb-config.xml`
- `Vq930_XRCalib_Tof-config.xml`
- `Vq930_XRCalib_Rgb_Tof-config.xml`

### 4.2 GT_Calib_Checker（RGB 光轴夹角检测）

| 项目 | 说明 |
|------|------|
| 路径 | `<app_dir>/tools/GT_Calib_Checker_Api/` |
| 入口 | `GT_Calib_Checker_Api.py` |
| 用途 | 检测两个 RGB 相机光轴夹角是否符合要求 |
| 依赖 | 该目录下包含大量内部模块和 C++ 动态库，需完整保留目录结构 |

### 4.3 QVR 标定结果验证工具

| 项目 | 说明 |
|------|------|
| 路径 | `<app_dir>/tools/verify_qvr_calibrate_result/verify_qvr_calibrate.sh` |
| 用途 | 验证 QVR 标定结果的正确性 |
| 权限 | shell 脚本需可执行权限 |

### 4.4 其他 tools 子目录

以下目录如存在，也需完整保留：

```
tools/
├── qvr_calib/              # XRCalib 核心标定程序 + 配置
├── GT_Calib_Checker_Api/   # RGB 光轴夹角检测
├── verify_qvr_calibrate_result/  # QVR 结果验证
├── ferraris/               # IMU 标定（含内置 imucal 库）
├── transform_result_to_ssc/
├── transform_result_to_slam/
├── transform_ivslam_to_skyworth_slam/
└── verify_calibrate_result/
```

---

## 5. 应用运行时目录

### 5.1 标定结果输出目录

生产环境下**硬编码**为：

```
/home/ssnwt/work/skycalib/CalibratResult/{cpu_id}/
```

**要求**：
- 运行应用的用户对该路径有 **读写权限**
- 磁盘空间充足（单次标定约数百 MB）
- 该目录会被自动创建，但父目录 `/home/ssnwt/work/skycalib/` 需存在或应用有权限创建

### 5.2 配置文件

- 路径：`config.json`（应用运行目录下）
- 首次启动时如不存在会自动创建
- 保存阈值、QVR 型号等设备配置

### 5.3 日志目录

- 路径：`logs/`（应用运行目录下）
- 按设备 `cpu_id_{timestamp}.log` 生成独立日志

---

## 6. 网络要求

标定完成后需要上传结果，目标机器需能访问：

| 用途 | 说明 |
|------|------|
| OSS 上传 | 压缩后的标定详情 zip 文件上传 |
| 云端 API | 标定结果上报（JSON 格式） |

> 如处于内网或离线环境，上传步骤会失败，但本地标定流程不受影响。

---

## 7. 快速部署检查清单

在目标机器上运行应用前，请逐项确认：

- [ ] 操作系统为 Ubuntu 18.04+ x86_64
- [ ] 具有图形桌面环境
- [ ] `adb` 已安装且可用（`adb version`）
- [ ] `python3` 已安装（建议 3.8+）
- [ ] Python 第三方库已安装（`numpy`, `scipy`, `opencv-python`, `pandas`, `matplotlib`）
- [ ] `tools/qvr_calib/XRCalib` 存在且具有可执行权限
- [ ] `tools/qvr_calib/config/` 下配置文件齐全
- [ ] `tools/GT_Calib_Checker_Api/` 目录结构完整
- [ ] `tools/verify_qvr_calibrate_result/verify_qvr_calibrate.sh` 存在且可执行
- [ ] `/home/ssnwt/work/skycalib/` 目录存在且应用用户有读写权限
- [ ] 网络可访问 OSS 和云端 API（如需上传结果）

---

## 8. 常见问题

### Q: 提示 "XRCalib工具不存在"
**A**: 确认 `tools/qvr_calib/XRCalib` 存在且已添加可执行权限：
```bash
chmod +x /path/to/app/tools/qvr_calib/XRCalib
```

### Q: 提示 "RGB夹角检测工具不存在"
**A**: 确认 `tools/GT_Calib_Checker_Api/GT_Calib_Checker_Api.py` 存在且目录结构完整。

### Q: Python 脚本报错 `ModuleNotFoundError`
**A**: 按第 3 节安装缺失的 pip 包。

### Q: ADB 无权限
**A**: 配置 udev 规则或临时使用 `sudo adb kill-server && sudo adb start-server`。

### Q: 标定结果无法写入
**A**: 确认 `/home/ssnwt/work/skycalib/` 目录存在且当前用户有写权限，或根据实际环境修改 `src-tauri/src/utils/paths.rs` 后重新打包。
