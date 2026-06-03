# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目简介

**SkyCalib VR设备标定工具** — 一个基于 Tauri + Vue3 的桌面应用，用于通过 USB/ADB 连接 VR 头显设备，执行相机标定、验证标定结果，并将结果上传至 OSS。

- **前端**: Vue 3 + TypeScript + Vite
- **后端**: Rust + Tauri v1.x
- **目标平台**: Linux (Ubuntu 18.04+)，打包为 `.deb`
- **设备通信**: ADB (Android Debug Bridge)
- **标定脚本**: Python 3，位于 `src-tauri/resources/ProcessCal/`

## 常用命令

```bash
# 开发模式（前端 + Rust 后端）
npm run tauri:dev

# 仅前端开发（不启动 Rust 后端）
npm run dev

# 生产构建（输出 .deb 包）
npm run tauri:build

# 预览前端生产构建
npm run preview
```

**注意**: 本项目无单元测试框架，无 lint 配置。构建前请确保系统已安装 `adb`、`python3` 以及 Rust 工具链。

## 架构概述

### 前后端通信模式

前端通过 **Tauri Invoke** 调用 Rust 命令，通过 **Tauri Events** 接收后端推送的实时状态更新。

- **Invoke 命令** (`src/services/tauriCommands.ts` → `src-tauri/src/commands/`):
  - `start_device_test` — 启动指定槽位的标定流程
  - `get_slot_status` / `get_connected_devices` — 查询状态
  - `save_config` / `load_config` — 读写配置到 `config.json`

- **Events** (后端 `emit_all` → 前端 `listen`):
  - `device:{slot_id}:connected` — 设备接入
  - `device:{slot_id}:disconnected` — 设备断开
  - `device:{slot_id}:step` — 标定步骤进度更新
  - `device:{slot_id}:complete` — 标定完成
  - `device:{slot_id}:error` — 标定失败

### 后端核心模块 (Rust)

```
src-tauri/src/
├── lib.rs                    # Tauri 应用入口，注册命令和状态
├── commands/                 # Tauri 命令处理器（前后端接口层）
│   ├── calibration.rs        # start_device_test, get_slot_status
│   ├── device.rs             # get_connected_devices
│   └── config.rs             # save_config, load_config
├── services/                 # 业务逻辑
│   ├── device_manager.rs     # 每2秒轮询 ADB 设备，自动分配槽位，emit 连接事件
│   ├── calibration_pool.rs   # 管理槽位状态，启动/停止标定任务
│   └── calibration_engine.rs # 标定流程引擎（8步流程，见下方）
├── adapters/                 # 外部系统适配器
│   ├── adb.rs                # ADB 命令封装（shell/push/pull/reboot/wait-for-device）
│   ├── python_runner.rs      # 运行 Python 脚本，捕获 stdout/stderr
│   └── http_client.rs        # OSS 文件上传 + API 结果上报
├── models/                   # 数据模型
│   ├── device.rs             # DeviceSlot, SlotStatus, SlotResult
│   ├── config.rs             # AppConfig, DeviceConfig, ThresholdConfig
│   ├── calibration.rs        # CalibStep, CalibResult, VerifyData
│   └── events.rs             # 事件载荷结构
├── state/                    # 应用状态
│   ├── app_state.rs          # AppState: Arc<Mutex<Vec<DeviceSlot>>> + Arc<Mutex<AppConfig>>
│   └── slot_state.rs         # 槽位状态管理辅助
└── utils/                    # 工具
    ├── logger.rs             # DeviceTestLogger: 每个设备独立的日志文件
    ├── verify.rs             # 覆盖率验证、阈值检查
    └── paths.rs              # 资源目录和工作目录路径解析
```

### 标定流程 (8步)

`CalibrationEngine::run()` 在 `src-tauri/src/services/calibration_engine.rs` 中实现：

1. **DevicePull** — 通过 ADB 从设备拉取标定原始数据（调用 `DevicePull.py`）
2. **CamCali** — 运行相机标定算法（调用 `ProcessCam.py`）
3. **ConvertYaml** — 转换 SLAM YAML 配置文件（调用 `ConvertSlamYaml.py`）
4. **VerifyCoverage** — 验证相机覆盖率，检查阈值（DOF/RGB/TOF）
5. **CheckResult** — 高通标定结果判定（调用 `CheckResult/parse_calib.py`）
6. **PushAndUpload** — 推送标定文件到设备、重启设备、上传结果到 OSS、API 上报

每个步骤通过 `emit_step()` 向前端发送进度，`DeviceTestLogger` 记录详细日志到 `logs/{cpu_id}_{timestamp}.log`。

### 前端核心模块 (Vue 3)

```
src/
├── main.ts                   # Vue 应用入口
├── App.vue                   # 根组件：标题栏 + 设置按钮 + DeviceGrid
├── components/
│   ├── DeviceGrid.vue        # 响应式网格布局（1-9设备自动调整行列）
│   ├── DeviceCard.vue        # 单设备卡片：状态、进度环、启动按钮、结果
│   └── SettingsModal.vue     # 配置弹窗：RGB/TOF开关、QVR类型、阈值
├── composables/
│   └── useCalibration.ts     # 核心状态管理：9槽位、事件监听、startTest()
├── services/
│   └── tauriCommands.ts      # Rust 命令的 TypeScript 封装 + 类型定义
├── constants/
│   ├── deviceTypes.ts        # QVR类型映射（VQ910/VQ920/VQ930 + RGB/TOF组合）
│   └── thresholds.ts         # 阈值验证工具函数
└── styles/
    └── main.css              # 全局样式
```

### 关键设计决策

- **9槽位固定架构**: `AppState::new(9)` 初始化9个槽位，前端 `MAX_SLOTS = 9`，`DeviceGrid` 根据实际连接数动态调整网格布局（1→1x1, 2→2x1, 3-4→2x2, 5-9→3x3）。
- **槽位状态机**: `Empty → Connected → Running → Success|Error`，状态转换由 `DeviceManager`（连接检测）和 `CalibrationPool`（测试启动）驱动。
- **设备标识**: 使用 CPU ID (`/sys/devices/soc0/serial_number`) 作为设备唯一标识，用于日志命名；获取失败时 fallback 到 ADB serial。
- **配置持久化**: 配置保存在运行目录的 `config.json` 中，不是 Tauri 的 app-data 目录。
- **标定结果目录**: 硬编码为 `/home/ssnwt/work/skycalib/CalibratResult/{serial}/`（见 `src-tauri/src/utils/paths.rs`）。
- **资源打包**: `src-tauri/resources/` 下的 `ProcessCal`、`CheckResult`、`tools` 目录会随应用一起打包；`tools` 目录内容被 `.gitignore` 但保留空目录结构。
- **Tauri v1.x**: 项目使用 Tauri 1.x（非 2.x），因为需要兼容 Ubuntu 18.04。`reqwest` 使用 `native-tls-vendored` 特性实现 OpenSSL 静态链接。

### 添加新设备类型

如需支持新的 QVR 设备型号：
1. 在 `src/constants/deviceTypes.ts` 的 `QVR_TYPE_TEXT` 中添加映射
2. 在 `RGB_DEVICE_TYPES` / `TOF_DEVICE_TYPES` 中标记是否支持 RGB/TOF
3. 在 `getAndroidVersion()` 中映射 Android 版本
4. 后端 `DeviceConfig.qvr_type` 为字符串，无需修改 Rust 代码

### 修改标定流程

标定步骤定义在 `src-tauri/src/models/calibration.rs` 的 `CalibStep` 枚举中。修改流程时：
1. 在 `CalibrationEngine::run()` 中增删步骤
2. 如需新增 Python 脚本调用，在 `PythonRunner` 中添加方法
3. 步骤进度通过 `step.progress()` 和 `step.hint()` 定义，需同步更新
4. 新错误类型需添加到 `src-tauri/src/error.rs` 的 `CalibError` 枚举
