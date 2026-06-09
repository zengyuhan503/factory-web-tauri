# SkyCalib 工厂环境安装脚本

## 脚本说明

| 脚本 | 用途 | 适用场景 |
|------|------|---------|
| `install-factory-env.sh` | 完整开发环境 | 开发/CI 机器，含 Node.js、Rust、Python 3.12 |
| `install-runtime-env.sh` | 仅运行时环境 | 工厂产线机器，只装运行依赖 |

## 使用方法

```bash
chmod +x scripts/*.sh

# 开发/编译机器
./install-factory-env.sh

# 工厂产线机器（只运行，不编译）
./install-runtime-env.sh
```

## install-runtime-env.sh 安装内容

运行时环境，**不安装 SkyCalib 应用本身**，只装依赖：

| 组件 | 说明 |
|------|------|
| ADB | Android Debug Bridge，连接 VR 设备 |
| Python 3.12 | SFR 清晰度标定脚本专用 |
| pip 包 | numpy, pandas, scipy, matplotlib, opencv-python-headless |
| Tauri 运行时库 | libwebkit2gtk, libgtk-3, libayatana-appindicator3 等 |
| 图像/渲染库 | libgl1-mesa-glx, libgdk-pixbuf, cairo, pango 等 |

## 工厂产线部署流程

```bash
# 1. 复制脚本到工厂机器
scp scripts/install-runtime-env.sh user@factory-machine:/tmp/

# 2. SSH 登录并运行
ssh user@factory-machine
cd /tmp
chmod +x install-runtime-env.sh
./install-runtime-env.sh

# 3. 安装 SkyCalib .deb 包
sudo dpkg -i skycalib-tauri_2.0.0_amd64.deb

# 4. 从应用菜单启动
```

## 验证清单

脚本运行结束后自动验证，也可手动检查：

```bash
# ADB
adb version

# Python 3.12
python3.12 --version   # Python 3.12.3

# Python 包
python3.12 -c "import numpy, pandas, scipy, matplotlib, cv2; print('OK')"

# Tauri 运行时库
ldconfig -p | grep libwebkit2gtk
ldconfig -p | grep libgtk-3
ldconfig -p | grep libayatana-appindicator3
```

## 常见问题

**Q: 为什么 Python 3.12 需要编译安装？**
> Ubuntu 18.04 官方源没有 Python 3.12，必须从源码编译。

**Q: 编译需要多久？**
> 约 5-10 分钟，取决于 CPU 核心数。脚本会自动使用全部核心并行编译。

**Q: 可以重复运行吗？**
> 可以。已安装的组件会自动跳过。

**Q: 安装失败怎么办？**
> - 检查网络（需下载 Python 源码和 pip 包）
> - 检查 sudo 权限
> - 检查磁盘空间（需要至少 3GB）

**Q: 如何只重装 Python 包？**
> ```bash
> python3.12 -m pip install --upgrade numpy pandas scipy matplotlib opencv-python-headless
> ```
