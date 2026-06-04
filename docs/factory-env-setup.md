# SkyCalib 工厂环境安装文档

## 概述

本文档描述在工厂 Linux 电脑（Ubuntu 18.04+）上部署 SkyCalib VR 设备标定工具的完整步骤。

**环境特点：**
- 前端：Vue 3 + TypeScript + Vite
- 后端：Rust + Tauri v1.x
- 标定脚本：Python 3（系统默认 3.6 + 独立安装的 3.12）
- 目标平台：Linux (Ubuntu 18.04+)

**版本说明：**
- Tauri v1.x（兼容 Ubuntu 18.04）
- Node.js 20+
- Python 3.12（SFR 清晰度标定专用，不覆盖系统 Python 3.6）

---

## 系统要求

| 组件 | 最低版本 | 说明 |
|------|---------|------|
| OS | Ubuntu 18.04 LTS | 工厂标准系统 |
| 内存 | 8 GB | 编译 Rust 需要 |
| 磁盘 | 20 GB 可用空间 | 含编译缓存 |
| 网络 | 可访问外网 | 下载依赖包 |

---

## 安装步骤

### 1. 安装系统基础依赖

```bash
sudo apt update
sudo apt install -y \
    git \
    curl \
    wget \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libreadline-dev \
    libsqlite3-dev \
    libgdbm-dev \
    libdb5.3-dev \
    libbz2-dev \
    libexpat1-dev \
    liblzma-dev \
    tk-dev \
    libffi-dev \
    pkg-config \
    adb
```

**说明：**
- `build-essential`：gcc/g++ 编译器，编译 Python 3.12 必需
- `lib*-dev`：Python 3.12 编译所需的开发库
- `adb`：Android Debug Bridge，连接 VR 设备必需

---

### 2. 安装 Node.js 20+

```bash
# 使用 NodeSource 官方源
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 验证
node --version   # v20.x.x
npm --version    # 10.x.x
```

---

### 3. 安装 Rust 工具链

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# 验证
rustc --version    # 1.70+
cargo --version
```

**注意：** 项目要求 Rust >= 1.70。

---

### 4. 编译安装 Python 3.12（SFR 专用）

**重要：** 不可替换系统 Python 3.6，使用 `make install` 安装到 `/usr/local`，系统 Python 保持不动。

```bash
cd ~
wget https://www.python.org/ftp/python/3.12.3/Python-3.12.3.tgz
tar xzf Python-3.12.3.tgz
cd Python-3.12.3

# 配置编译参数
./configure --enable-optimizations --prefix=/usr/local

# 编译（根据 CPU 核心数并行）
make -j$(nproc)

# 安装（使用 install，不是 altinstall）
sudo make install

# 验证
python3.12 --version    # Python 3.12.3
python3 --version       # Python 3.6.9（系统默认，不变）
```

**安装后检查：**
```bash
ls /usr/local/lib/python3.12/encodings/   # 应输出大量 .py 文件
ls /usr/local/bin/python3.12              # 应存在
```

---

### 5. 安装 Python 3.12 依赖包（SFR 脚本所需）

```bash
python3.12 -m pip install \
    numpy \
    pandas \
    scipy \
    matplotlib \
    opencv-python-headless

# 验证关键依赖
python3.12 -c "import numpy; import cv2; print('All OK')"
```

**说明：**
- `opencv-python-headless`：无 GUI 版本的 OpenCV，适合工厂服务器环境
- 如果 `opencv-python-headless` 安装失败，尝试 `opencv-python`

---

### 6. 克隆项目并安装 Node 依赖

```bash
cd ~/work
git clone <仓库地址> factory-web-tauri
cd factory-web-tauri

# 安装前端依赖
npm install
```

---

### 7. 运行开发模式（验证环境）

```bash
npm run tauri:dev
```

首次运行会自动编译 Rust 后端，耗时约 2-5 分钟。

---

## 生产构建

### 构建 .deb 安装包

```bash
npm run tauri:build
```

构建产物位于：
```
src-tauri/target/release/bundle/deb/skycalib-tauri_2.0.0_amd64.deb
```

### 安装 deb 包

```bash
sudo dpkg -i skycalib-tauri_2.0.0_amd64.deb
```

---

## 验证清单

| 检查项 | 命令 | 预期结果 |
|--------|------|---------|
| Node.js | `node --version` | v20.x.x |
| Rust | `rustc --version` | 1.70+ |
| Python 3.12 | `python3.12 --version` | Python 3.12.3 |
| 系统 Python | `python3 --version` | Python 3.6.9（不变） |
| ADB | `adb version` | 显示版本号 |
| numpy | `python3.12 -c "import numpy"` | 无报错 |
| cv2 | `python3.12 -c "import cv2"` | 无报错 |

---

## 常见问题

### Q1: `make install` 会覆盖系统 Python 吗？

不会。系统 Python 3.6 位于 `/usr/bin/python3`，新装的 Python 3.12 位于 `/usr/local/bin/python3.12`，两者独立共存。

### Q2: 为什么需要 Python 3.12？

SFR（清晰度标定）脚本使用了 Python 3.9+ 的泛型语法（如 `list[dict]`），Python 3.6 不支持。其他标定模块（高通标定等）继续使用系统 Python 3.6，不受影响。

### Q3: `npm run tauri:dev` 报错 `ENOSPC`

系统文件监视器数量限制：
```bash
sudo sysctl fs.inotify.max_user_watches=524288
```

### Q4: Rust 编译缓存导致代码修改不生效

```bash
cd src-tauri && cargo clean && cd ..
npm run tauri:dev
```

### Q5: Tauri 资源文件（Python 脚本）更新后未生效

```bash
rm -rf src-tauri/target/debug/resources/
npm run tauri:dev
```

---

## 附录：模块与 Python 版本对应关系

| 功能模块 | Python 版本 | 说明 |
|---------|------------|------|
| SFR 清晰度标定 | Python 3.12 | 使用泛型语法，需独立安装 |
| 高通标定 (ProcessCal) | 系统 Python 3.6 | 使用标准语法，兼容性好 |
| 设备检测 (ADB) | 不涉及 | Rust 直接调用 adb 命令 |
| 结果上传 (OSS) | 不涉及 | Rust 直接调用 HTTP API |
