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
├── main.rs                   # 初始化日志并启动 Tauri 应用
├── error.rs                  # 标定错误体系（CalibError / AdbError）及 Python 日志错误解析
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
│   ├── sfr_runner.rs         # SFR 清晰度验证：拉 snapshot、跑 run_sfr50_qc.py、解析 CSV
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
    ├── paths.rs              # 资源目录和工作目录路径解析
    ├── sfr_report.rs         # 生成 SFR 清晰度验证的 JSON / TXT / PDF 报告
    └── calib_report.rs       # 生成高通标定验证的 JSON / TXT / PDF 报告
```

### 标定流程 (8步)

`CalibrationEngine::run()` 在 `src-tauri/src/services/calibration_engine.rs` 中实现：

1. **SfrVerify** — SFR 清晰度验证（可选，调用 `run_sfr50_qc.py`）
2. **DevicePull** — 通过 ADB 从设备拉取标定原始数据（调用 `DevicePull.py`）
3. **CamCali** — 运行相机标定算法（调用 `ProcessCam.py`）
4. **ConvertYaml** — 转换 SLAM YAML 配置文件（调用 `ConvertSlamYaml.py`）
5. **VerifyCoverage** — 验证相机覆盖率，检查阈值（DOF/RGB/TOF）
6. **CheckResult** — 高通标定结果判定（调用 `CheckResult/parse_calib.py`）
7. **PushCalAndReboot** — 推送标定文件到设备并重启
8. **UploadResult** — 压缩标定详情、上传 OSS、向云端 API 上报结果

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

---

## File Function Index / 文件功能索引

Use this index to quickly locate the file responsible for a feature or bug. / 使用该索引快速定位某个功能或 bug 对应的文件。

### Rust Backend — Entry, Commands, Errors

| File | Function |
|------|----------|
| `src-tauri/src/lib.rs` | Tauri app entry: registers invoke handlers, starts device polling, initializes global state. / Tauri 应用入口：注册命令处理器、启动设备轮询、初始化全局状态。 |
| `src-tauri/src/main.rs` | Initializes logging and delegates to `skycalib_lib::run()`. / 初始化日志并调用 `skycalib_lib::run()`。 |
| `src-tauri/src/error.rs` | Defines `CalibError` and `AdbError`; parses Python failure logs into typed errors. / 定义 `CalibError` / `AdbError`；将 Python 失败日志解析为类型化错误。 |
| `src-tauri/src/commands/calibration.rs` | Handles `start_device_test` and `get_slot_status`. / 处理 `start_device_test` 和 `get_slot_status`。 |
| `src-tauri/src/commands/device.rs` | Handles `get_connected_devices`. / 处理 `get_connected_devices`。 |
| `src-tauri/src/commands/config.rs` | Handles `save_config` / `load_config`, including backward-compatible field migrations. / 处理配置的保存/加载，包括旧字段兼容。 |

### Rust Backend — Services & Engine

| File | Function |
|------|----------|
| `src-tauri/src/services/device_manager.rs` | Polls ADB every 2 s, auto-assigns slots, fetches CPU ID, emits connection events. / 每 2 秒轮询 ADB，自动分配槽位，获取 CPU ID，发送连接事件。 |
| `src-tauri/src/services/calibration_pool.rs` | Schedules calibration tasks per slot; validates state and auto-resets failed slots after 20 s. / 管理每个槽位的标定任务调度；校验状态，失败后 20 秒自动重置。 |
| `src-tauri/src/services/calibration_engine.rs` | Runs the full calibration pipeline: SFR → pull data → calibrate → convert YAML → verify coverage → check result → push/reboot → upload/report. / 执行完整标定流水线。 |

### Rust Backend — Adapters

| File | Function |
|------|----------|
| `src-tauri/src/adapters/adb.rs` | Wraps ADB: shell, push, pull, reboot, wait-for-boot, device list, CPU ID read. / 封装 ADB 命令：shell、push、pull、重启、设备列表、读取 CPU ID。 |
| `src-tauri/src/adapters/python_runner.rs` | Invokes Python scripts (`DevicePull.py`, `ProcessCam.py`, `ConvertSlamYaml.py`, `parse_calib.py`) and parses stdout/stderr. / 调用 Python 脚本并解析输出。 |
| `src-tauri/src/adapters/sfr_runner.rs` | Pulls device snapshot images, runs `run_sfr50_qc.py`, parses SFR CSV results. / 拉取设备 snapshot，运行 SFR50 QC 脚本，解析 CSV 结果。 |
| `src-tauri/src/adapters/http_client.rs` | Uploads zip to OSS and reports calibration result to the DVC/cloud API. / 上传 zip 到 OSS 并向云端 API 上报标定结果。 |

### Rust Backend — Models

| File | Function |
|------|----------|
| `src-tauri/src/models/device.rs` | Core data types: `DeviceSlot`, `SlotStatus`, `SlotResult`. / 核心数据类型：设备槽位、状态、结果。 |
| `src-tauri/src/models/config.rs` | `AppConfig`, `DeviceConfig`, `ThresholdConfig` structures. / 应用配置、设备配置、阈值配置结构。 |
| `src-tauri/src/models/calibration.rs` | `CalibStep` enum, calibration status, `VerifyData`, Qualcomm parse result. / 标定步骤枚举、状态、验证数据、高通解析结果。 |
| `src-tauri/src/models/events.rs` | Payload structures for step/log/complete/error/connected/disconnected events. / 前后端事件载荷结构。 |

### Rust Backend — State & Utils

| File | Function |
|------|----------|
| `src-tauri/src/state/app_state.rs` | Global Tauri state: thread-safe slots list + app config. / 全局 Tauri 状态：槽位列表 + 应用配置的线程安全封装。 |
| `src-tauri/src/state/slot_state.rs` | Per-slot runtime state machine helpers: step switching, progress updates, cancel checks. / 单槽位运行时状态机辅助。 |
| `src-tauri/src/utils/logger.rs` | `DeviceTestLogger`: per-device log file plus standard log output. / 设备测试日志记录器，按 CPU ID 生成独立日志。 |
| `src-tauri/src/utils/verify.rs` | Parses `Calib.log` to compute camera coverage and checks DOF/RGB/TOF thresholds. / 解析 Calib.log 计算覆盖率并按阈值检查。 |
| `src-tauri/src/utils/paths.rs` | Resolves calibration result directory, working directory, and resource paths. / 解析标定结果目录、工作目录、资源目录路径。 |
| `src-tauri/src/utils/sfr_report.rs` | Generates JSON / TXT / PDF sharpness reports from SFR results. / 根据 SFR 结果生成 JSON/TXT/PDF 清晰度报告。 |
| `src-tauri/src/utils/calib_report.rs` | Generates JSON / TXT / PDF calibration reports from `parse_calib.py` output. / 根据高通解析结果生成 JSON/TXT/PDF 标定报告。 |

### Frontend — Entry & Components

| File | Function |
|------|----------|
| `src/main.ts` | Vue 3 bootstrap entry. / Vue 3 应用启动入口。 |
| `src/App.vue` | Root shell: header, settings button, `DeviceGrid`, `SettingsModal`; persists config. / 根组件：标题栏、设置按钮、设备网格、配置弹窗；持久化配置。 |
| `src/components/DeviceCard.vue` | Single-device card: status, progress ring, start button, error details, pass/fail badge. / 单设备卡片：状态、进度环、启动按钮、错误详情、结果标识。 |
| `src/components/DeviceGrid.vue` | Responsive grid layout (1×1 to 3×3) and card sizing based on connected count. / 响应式设备网格布局，根据连接数自动调整行列。 |
| `src/components/SettingsModal.vue` | Password-protected modal (`ssnwt`) for QVR type, RGB/TOF toggles, thresholds. / 密码保护配置弹窗：QVR 型号、RGB/TOF 开关、阈值。 |
| `src/styles/main.css` | Global reset and base styles. / 全局重置与基础样式。 |

### Frontend — State, Services, Constants

| File | Function |
|------|----------|
| `src/composables/useCalibration.ts` | Reactive 9-slot state machine; subscribes to Tauri events; exposes `startTest()`. / 响应式 9 槽位状态机；监听 Tauri 事件；暴露 `startTest()`。 |
| `src/services/tauriCommands.ts` | TypeScript wrappers for Rust invoke commands and event types. / Rust 命令的 TypeScript 封装与类型定义。 |
| `src/constants/deviceTypes.ts` | QVR type catalog (`VQ910`–`VQ930`), RGB/TOF flags, Android version mapping. / QVR 型号目录、RGB/TOF 标记、Android 版本映射。 |
| `src/constants/thresholds.ts` | `checkArrayThreshold` and combined DOF/RGB/TOF coverage verification. / 数组阈值检查与综合覆盖率验证工具。 |

### Python Resources — Calibration Pipeline

| File | Function |
|------|----------|
| `src-tauri/resources/ProcessCal/adb.py` | ADB wrapper used by Python scripts: shell, push, pull, root, serial detection. / Python 脚本使用的 ADB 封装。 |
| `src-tauri/resources/ProcessCal/captureData.py` | Orchestrates `qvrdatalogger` capture, robot motion, and sensor log pulling. / 协调 qvrdatalogger 采集、机械臂运动、拉取传感器日志。 |
| `src-tauri/resources/ProcessCal/runCalibration.py` | Full calibration automation: capture → `XRCalib` → parse failures → push to device. / 完整标定自动化脚本。 |
| `src-tauri/resources/ProcessCal/ProcessCam.py` | Main camera calibration dispatcher per QVR config. / 按 QVR 配置分发的主相机标定脚本。 |
| `src-tauri/resources/ProcessCal/DevicePull.py` | Waits for ADB and pulls `qvrdataset` to `CalibratResult/{cpu_id}/`. / 等待 ADB 并将标定数据集拉取到结果目录。 |
| `src-tauri/resources/ProcessCal/ConvertSlamYaml.py` | Copies `Calib.log` and zips `calibDetails/` for downstream use. / 复制 Calib.log 并压缩 calibDetails 目录。 |
| `src-tauri/resources/ProcessCal/addVirtualRgbConfig.py` | Injects hardcoded virtual RGB camera blocks into `device_calibration.xml`. / 向标定文件注入虚拟 RGB 相机配置。 |
| `src-tauri/resources/ProcessCal/utils.py` | Shared helpers: `CaptureCommand`, logger version comparison, elapsed timer. / 共享辅助：采集命令构建、日志版本比较、计时器。 |

### Python Resources — Validation, Reports & Tools

| File | Function |
|------|----------|
| `src-tauri/resources/CheckResult/parse_calib.py` | Parses `device_calibration.xml` + `Calib.log`, evaluates thresholds, outputs JSON/text report. / 解析标定文件与日志，评估阈值，输出报告。 |
| `src-tauri/resources/CheckResult/generate_calib_report.py` | Renders calibration report JSON into a multi-page PDF. / 将标定报告 JSON 渲染为多页 PDF。 |
| `src-tauri/resources/sfr/checkerboard_sfr.py` | Computes SFR metrics per camera from checkerboard images. / 从棋盘格图像计算每相机的 SFR 指标。 |
| `src-tauri/resources/sfr/analyze_sfr50.py` | Aggregates SFR50 across cameras and grades pass/fail with outlier detection. / 汇总 6 相机 SFR50 并判定通过/异常。 |
| `src-tauri/resources/sfr/run_sfr50_qc.py` | End-to-end SFR50 QC wrapper. / SFR50 QC 端到端封装脚本。 |
| `src-tauri/resources/sfr/generate_sfr_report.py` | Generates PDF sharpness report from SFR JSON and annotated images. / 根据 SFR JSON 和标注图生成 PDF 清晰度报告。 |
