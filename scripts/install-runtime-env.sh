#!/bin/bash
#
# SkyCalib 运行时环境一键安装脚本
# 用途: 在工厂机器上安装 SkyCalib 应用运行所需的依赖
# 注意: 不安装 .deb 应用本身，只装运行环境
#
# 包含:
#   - ADB (设备通信)
#   - Python 3.12 + pip 依赖包 (SFR 标定脚本)
#   - Tauri 运行时库 (WebKitGTK, GTK3, AppIndicator 等)
#   - OpenGL / 图像处理库
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PYTHON_VERSION="3.12.3"
PYTHON_TARBALL="Python-${PYTHON_VERSION}.tgz"
PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/${PYTHON_TARBALL}"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[步骤 $1/4]${NC} $2"
}

# ==================== 1. 系统运行时库 ====================
step1_system_libs() {
    log_step 1 "安装系统运行时依赖..."
    sudo apt update

    # 编译工具链（Python 3.12 源码编译需要 gcc/make/ssl）
    log_info "安装编译工具链..."
    sudo apt install -y build-essential libssl-dev libffi-dev || {
        log_warn "build-essential / libssl-dev / libffi-dev 安装失败，Python 编译可能无法进行"
    }

    # 分两组安装，避免单个包缺失导致全部失败

    # ADB + 网络工具
    log_info "安装 ADB 和基础工具..."
    sudo apt install -y adb curl wget || {
        log_error "ADB 安装失败，请检查网络连接"
        exit 1
    }

    # Tauri v1.x 运行时库
    log_info "安装 Tauri 运行时库..."
    sudo apt install -y \
        libwebkit2gtk-4.0-37 \
        libgtk-3-0 \
        libayatana-appindicator3-1 \
        libgdk-pixbuf2.0-0 \
        libglib2.0-0 \
        libgl1-mesa-glx \
        libx11-6 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libxtst6 \
        libatk1.0-0 \
        libpango-1.0-0 \
        libcairo2 \
        libdbus-1-3 \
        libexpat1 \
        libuuid1 || {
        log_warn "部分 Tauri 库安装失败，应用可能无法启动"
    }

    log_info "系统运行时依赖安装完成"
}

# ==================== 2. Python 3.12 编译安装 ====================
step2_python312() {
    log_step 2 "安装 Python ${PYTHON_VERSION}..."

    if command -v python3.12 &> /dev/null; then
        local installed_ver
        installed_ver=$(python3.12 --version 2>&1)
        if [[ "$installed_ver" == *"${PYTHON_VERSION}"* ]]; then
            log_warn "Python ${PYTHON_VERSION} 已安装，跳过"
            return
        else
            log_warn "检测到其他版本: $installed_ver，将重新安装 ${PYTHON_VERSION}"
        fi
    fi

    cd /tmp
    rm -rf "Python-${PYTHON_VERSION}"

    log_info "下载 Python ${PYTHON_VERSION}..."
    if ! wget -q "${PYTHON_URL}" -O "${PYTHON_TARBALL}"; then
        log_error "Python 源码下载失败，请检查网络连接"
        exit 1
    fi

    tar xzf "${PYTHON_TARBALL}"
    cd "Python-${PYTHON_VERSION}"

    log_info "配置编译参数..."
    ./configure --enable-optimizations --prefix=/usr/local --with-ensurepip=install

    local ncpu
    ncpu=$(nproc)
    log_info "编译中（使用 ${ncpu} 核并行编译，约 5-10 分钟，请耐心等待）..."
    make -j"${ncpu}"

    log_info "安装到 /usr/local ..."
    sudo make altinstall

    # altinstall 不创建 python3 通用链接，避免覆盖系统 Python
    # 清理可能残留的旧通用链接
    sudo rm -f /usr/local/bin/python3 /usr/local/bin/python3-config \
        /usr/local/bin/idle3 /usr/local/bin/pydoc3 /usr/local/bin/2to3

    cd /tmp
    sudo rm -rf "Python-${PYTHON_VERSION}" "${PYTHON_TARBALL}"

    log_info "Python 3.12 安装完成: $(python3.12 --version)"
}

# ==================== 3. Python pip 依赖包 ====================
step3_python_packages() {
    log_step 3 "安装 Python 3.12 依赖包..."

    python3.12 -m pip install --upgrade pip setuptools wheel

    log_info "安装 numpy pandas scipy..."
    python3.12 -m pip install numpy pandas scipy

    log_info "安装 matplotlib..."
    python3.12 -m pip install matplotlib

    log_info "安装 opencv-python-headless..."
    python3.12 -m pip install opencv-python-headless || {
        log_warn "opencv-python-headless 安装失败，尝试 opencv-python..."
        python3.12 -m pip install opencv-python
    }

    log_info "Python 依赖包安装完成"
}

# ==================== 4. 验证 ====================
step4_verify() {
    log_step 4 "验证安装结果..."
    echo ""

    local all_pass=true

    # ADB
    if command -v adb &> /dev/null; then
        echo -e "  ADB              ${GREEN}$(adb version | head -n1)${NC}"
    else
        echo -e "  ADB              ${RED}未安装${NC}"
        all_pass=false
    fi

    # Python 3.12
    if command -v python3.12 &> /dev/null; then
        echo -e "  Python 3.12      ${GREEN}$(python3.12 --version)${NC}"
    else
        echo -e "  Python 3.12      ${RED}未安装${NC}"
        all_pass=false
    fi

    # Python 包
    local py_check
    py_check=$(python3.12 -c "
import sys
missing = []
for pkg in ['numpy', 'pandas', 'scipy', 'matplotlib', 'cv2']:
    try:
        __import__(pkg)
    except ImportError:
        missing.append(pkg)
if missing:
    print('MISSING:' + ','.join(missing))
else:
    print('OK')
" 2>&1)

    if [[ "$py_check" == "OK" ]]; then
        echo -e "  Python 包        ${GREEN}全部正常${NC}"
    else
        echo -e "  Python 包        ${RED}缺失: ${py_check#MISSING:}${NC}"
        all_pass=false
    fi

    # Tauri 运行时库检查
    local tauri_libs=(
        "libwebkit2gtk-4.0.so.37"
        "libgtk-3.so.0"
        "libayatana-appindicator3.so.1"
        "libgdk_pixbuf-2.0.so.0"
        "libGL.so.1"
    )
    local missing_libs=()
    for lib in "${tauri_libs[@]}"; do
        if ! ldconfig -p | grep -q "$lib"; then
            missing_libs+=("$lib")
        fi
    done

    if [ ${#missing_libs[@]} -eq 0 ]; then
        echo -e "  Tauri 运行时库   ${GREEN}全部就位${NC}"
    else
        echo -e "  Tauri 运行时库   ${YELLOW}缺失: ${missing_libs[*]}${NC}"
    fi

    echo ""
    if [ "$all_pass" = true ]; then
        log_info "核心依赖检查通过！SkyCalib 运行环境就绪"
    else
        log_error "部分核心依赖未安装成功，请查看上方日志"
        return 1
    fi
}

# ==================== 主流程 ====================
main() {
    echo "========================================"
    echo "  SkyCalib 运行时环境一键安装"
    echo "  目标系统: Ubuntu 18.04+"
    echo "========================================"
    echo ""
    echo "此脚本仅安装 SkyCalib 运行所需的依赖，"
    echo "不安装 SkyCalib 应用本身。"
    echo ""
    echo "安装内容:"
    echo "  - ADB (设备通信)"
    echo "  - Python 3.12 + numpy/pandas/scipy/matplotlib/opencv"
    echo "  - Tauri 运行时库 (WebKitGTK, GTK3, AppIndicator, OpenGL)"
    echo ""

    read -r -p "按 Enter 开始安装，或 Ctrl+C 取消..."
    echo ""

    step1_system_libs
    step2_python312
    step3_python_packages
    step4_verify

    echo ""
    log_info "运行时环境安装完成！"
    echo ""
    echo "接下来可以:"
    echo "  1. 安装 SkyCalib .deb 包: sudo dpkg -i skycalib-tauri_*.deb"
    echo "  2. 从应用菜单启动 SkyCalib"
}

main "$@"
