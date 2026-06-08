#!/bin/bash
#
# SkyCalib 工厂环境一键安装脚本
# 用途: 在全新的 Ubuntu 18.04+ 机器上安装完整的开发/运行环境
# 包含: 系统依赖、Node.js 20、Rust、Python 3.12、Python 依赖包
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# ==================== 1. 系统基础依赖 ====================
step1_system_deps() {
    log_info "步骤 1/6: 安装系统基础依赖..."
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
        adb \
        libwebkit2gtk-4.0-37 \
        libgtk-3-0 \
        libayatana-appindicator3-1 \
        libgdk-pixbuf2.0-0
    log_info "系统依赖安装完成"
}

# ==================== 2. Node.js 20+ ====================
step2_nodejs() {
    log_info "步骤 2/6: 安装 Node.js 20+..."
    if command -v node &> /dev/null && [[ $(node --version | cut -d'v' -f2 | cut -d'.' -f1) -ge 20 ]]; then
        log_warn "Node.js $(node --version) 已安装，跳过"
    else
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt install -y nodejs
        log_info "Node.js 安装完成: $(node --version)"
    fi
}

# ==================== 3. Rust 工具链 ====================
step3_rust() {
    log_info "步骤 3/6: 安装 Rust 工具链..."
    if command -v rustc &> /dev/null; then
        log_warn "Rust $(rustc --version) 已安装，跳过"
    else
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source "$HOME/.cargo/env"
        log_info "Rust 安装完成: $(rustc --version)"
    fi
}

# ==================== 4. Python 3.12 编译安装 ====================
step4_python312() {
    log_info "步骤 4/6: 编译安装 Python ${PYTHON_VERSION}..."
    if command -v python3.12 &> /dev/null && [[ $(python3.12 --version 2>&1) == *"${PYTHON_VERSION}"* ]]; then
        log_warn "Python ${PYTHON_VERSION} 已安装，跳过"
        return
    fi

    cd /tmp
    rm -rf "Python-${PYTHON_VERSION}"

    log_info "下载 Python ${PYTHON_VERSION}..."
    wget -q "${PYTHON_URL}" -O "${PYTHON_TARBALL}"
    tar xzf "${PYTHON_TARBALL}"
    cd "Python-${PYTHON_VERSION}"

    log_info "配置编译参数..."
    ./configure --enable-optimizations --prefix=/usr/local --with-ensurepip=install

    log_info "编译中（使用 $(nproc) 核并行编译，约 5-10 分钟）..."
    make -j"$(nproc)"

    log_info "安装到 /usr/local ..."
    sudo make install

    cd /tmp
    rm -rf "Python-${PYTHON_VERSION}" "${PYTHON_TARBALL}"

    log_info "Python 3.12 安装完成: $(python3.12 --version)"
}

# ==================== 5. Python 3.12 依赖包 ====================
step5_python_packages() {
    log_info "步骤 5/6: 安装 Python 3.12 依赖包..."
    python3.12 -m pip install --upgrade pip
    python3.12 -m pip install \
        numpy \
        pandas \
        scipy \
        matplotlib \
        opencv-python-headless
    log_info "Python 依赖包安装完成"
}

# ==================== 6. 项目 Node 依赖 ====================
step6_project_deps() {
    log_info "步骤 6/6: 安装项目 Node 依赖..."
    if [ -f "package.json" ]; then
        npm install
        log_info "项目依赖安装完成"
    else
        log_warn "当前目录无 package.json，跳过项目依赖安装"
        log_warn "如需安装，请进入项目目录后执行: npm install"
    fi
}

# ==================== 验证 ====================
verify_installation() {
    log_info "========== 安装验证 =========="
    echo ""

    local all_pass=true

    # Node.js
    if command -v node &> /dev/null; then
        echo -e "  Node.js:    ${GREEN}$(node --version)${NC}"
    else
        echo -e "  Node.js:    ${RED}未安装${NC}"
        all_pass=false
    fi

    # Rust
    if command -v rustc &> /dev/null; then
        echo -e "  Rust:       ${GREEN}$(rustc --version)${NC}"
    else
        echo -e "  Rust:       ${RED}未安装${NC}"
        all_pass=false
    fi

    # Python 3.12
    if command -v python3.12 &> /dev/null; then
        echo -e "  Python 3.12:${GREEN}$(python3.12 --version)${NC}"
    else
        echo -e "  Python 3.12:${RED}未安装${NC}"
        all_pass=false
    fi

    # 系统 Python
    if command -v python3 &> /dev/null; then
        echo -e "  系统 Python:${GREEN}$(python3 --version)${NC}"
    else
        echo -e "  系统 Python:${RED}未安装${NC}"
    fi

    # ADB
    if command -v adb &> /dev/null; then
        echo -e "  ADB:        ${GREEN}$(adb version | head -n1)${NC}"
    else
        echo -e "  ADB:        ${RED}未安装${NC}"
        all_pass=false
    fi

    # Python 关键依赖
    if python3.12 -c "import numpy; import cv2" 2>/dev/null; then
        echo -e "  Python 包:  ${GREEN}numpy, cv2 正常${NC}"
    else
        echo -e "  Python 包:  ${RED}numpy 或 cv2 导入失败${NC}"
        all_pass=false
    fi

    echo ""
    if [ "$all_pass" = true ]; then
        log_info "所有检查通过！环境就绪"
        echo ""
        log_info "可以运行: npm run tauri:dev    (开发模式)"
        log_info "可以运行: npm run tauri:build  (生产构建)"
    else
        log_error "部分检查未通过，请查看上方日志"
    fi
}

# ==================== 主流程 ====================
main() {
    echo "========================================"
    echo "  SkyCalib 工厂环境一键安装"
    echo "  目标系统: Ubuntu 18.04+"
    echo "========================================"
    echo ""

    # 检查是否在项目根目录
    if [ -f "package.json" ] && [ -d "src-tauri" ]; then
        log_info "检测到项目目录"
    else
        log_warn "当前目录似乎不是项目根目录（未找到 package.json 或 src-tauri）"
        log_warn "脚本将继续安装全局依赖，但步骤 6（项目依赖）将跳过"
    fi

    echo ""
    read -p "按 Enter 开始安装，或 Ctrl+C 取消..."
    echo ""

    step1_system_deps
    step2_nodejs
    step3_rust
    step4_python312
    step5_python_packages
    step6_project_deps

    echo ""
    verify_installation

    echo ""
    log_info "安装完成！"
}

main "$@"
