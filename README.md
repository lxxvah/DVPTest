# 泄气充气压力性能测试系统

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/PySide6-6.0+-green.svg)](https://doc.qt.io/qtforpython/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)]()

> 基于 PySide6 的无创血压（NIBP）模拟器 / 测试板压力性能测试软件  
> —— 实时采集、动态绘图、拐点检测、结果自动计算

---

## 📖 简介

本项目是一款专为 **无创血压（NIBP）模拟器** 和 **测试板** 设计的压力性能测试工具。它通过串口采集压力数据，实时绘制曲线，自动识别充气/泄气阶段，精准检测泄气拐点，并生成直观的结果报告。

系统同时支持 **文本协议**（如 `cuff=123.4 mmHg`）和 **二进制协议**（帧头 `0xAA`，定长 8 字节），能够自动识别设备类型并切换协议，适配多种硬件。

---

## ✨ 核心功能

| 功能模块 | 说明 |
|----------|------|
| 📡 **实时数据采集** | 支持多种波特率（最高 921600），兼容文本与二进制协议 |
| 📈 **动态波形显示** | 压力曲线 + 速率曲线同步刷新，可随时暂停/恢复绘图 |
| 🎯 **充气/泄气测试** | 用户可设置起始、中间、目标三个压力节点，自动记录到达时间并计算各段平均速率 |
| 🔍 **智能拐点检测** | 内置多策略检测器（速率+加速度、持续下降、漏气背景等），精确定位泄气起始点 |
| ⚡ **运动学分析** | 实时计算带符号速度和加速度，自动限幅防噪 |
| 📊 **结果自动格式化** | 以 `起始→中间`、`起始→目标` 等清晰格式展示充气和泄气结果 |
| 💾 **数据持久化** | 自动保存 CSV 原始数据；支持加载历史 CSV 进行离线分析（重放生成结果） |
| 🖱️ **双光标测量** | 两组独立光标（C1/C2 和 B1/B2），可标注点并计算 Δt、ΔP 和速率 |
| 🪵 **分级日志系统** | DEBUG / INFO / SUCCESS / WARNING / ERROR / CMD，同时输出至文件、控制台和 UI 面板，支持级别筛选 |
| 🔗 **多设备适配** | 自动识别模拟器（VID=0x1A86, PID=0x7523）和测试板，支持 PC 模式切换与压力表测试命令 |

---

## 🖥️ 系统要求

- **操作系统**：Windows 10/11、Linux（Ubuntu 20.04+）、macOS 10.15+
- **Python 版本**：3.8 及以上
- **依赖库**：
  - `PySide6 >= 6.0`
  - `pyqtgraph >= 0.12.0`
  - `numpy >= 1.21`
  - `pyserial >= 3.5`

---

## 📦 安装与运行

### 1️⃣ 克隆仓库

```bash
git clone https://github.com/yourusername/pressure-test-system.git
cd pressure-test-system
```

### 2️⃣ 安装依赖

推荐使用虚拟环境：

```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows

pip install -r requirements.txt
```

若没有 `requirements.txt`，可手动安装：

```bash
pip install PySide6 pyqtgraph numpy pyserial
```

### 3️⃣ 启动程序

```bash
python main.py
```

首次运行会自动在项目根目录创建 `logs/debug/` 和 `logs/csv/` 文件夹，日志文件以时间戳命名。

---

## 🚀 使用指南

### 🔌 连接设备

1. 点击工具栏 **“刷新”** 获取可用串口列表。
2. 选择正确的 **串口号** 和 **波特率**（默认 115200）。
3. 点击 **“连接”**，程序自动识别设备类型并切换协议。
   - 若成功，状态栏显示 **“● 监听中”**（绿色）。
   - 若失败，状态栏变红并提示错误信息。

### ⚙️ 设置测试参数

左侧面板：
- **充气测试**：起始、中间、目标值（必须满足 `起始 < 中间 < 目标`，单位 mmHg）。
- **泄气测试**：起始、中间、目标值（必须满足 `起始 > 中间 > 目标`）。

修改参数后自动生效，**测试进行中禁止修改**。

### ▶️ 开始 / 停止测试

- 点击 **“开始”** 发送 `AT#AG` 命令（测试板）或进入相应模式（模拟器）。
- 测试过程中，压力曲线和速率曲线实时更新。
- 点击 **“结束”** 发送 `AT#AH` 命令，测试终止，状态变为 `DONE`，结果自动显示在底部信息栏。

### 📋 查看结果

充气和泄气结果显示在右侧下方信息栏。示例：
- **充气**：`起始值5→中间值200 时间2.50s 速率78.00mmHg/s  起始值5→目标值300 时间4.20s 速率70.24mmHg/s`
- **泄气**：`峰值300→目标值5 时间4.50s 速率65.56mmHg/s  中间值200→目标值5 时间2.80s 速率69.64mmHg/s`

### 💾 数据记录与导出

- 连接后自动开始 CSV 记录（保存在 `logs/csv/`），断开或停止测试时停止记录。
- 点击 **“保存CSV”** 可将当前波形导出为 CSV 文件。
- 点击 **“加载波形”** 可导入历史 CSV 文件，系统自动重放并生成分析结果。

### 🖱️ 绘图交互

- **Ctrl + 滚轮**：横向缩放
- **Shift + 滚轮**：纵向缩放
- **清屏**：重置时间轴并清空数据（保留连接状态）
- **暂停绘图**：停止曲线更新（适合观察静态波形）

### 📏 光标测量

- 点击 **“光标测量”** 启用/禁用光标。
- 在绘图区**单击**依次添加光标点（最多 4 个）。
- 前两个点（C1, C2）为一组，后两个点（B1, B2）为第二组。
- 拖动光标线（垂直/水平）可调整位置，测量结果实时更新（Δt、ΔP、速率）。

### 🔧 高级功能

- **PC 模式切换**：模拟器专用，点击“进入PC界面”发送二进制命令，可进行压力表测试。
- **压力表测试**：在 PC 模式下发送固定命令，用于设备自检。

---

## ⚙️ 配置说明

所有可调参数集中在 `config.py` 中，主要分组如下：

| 分组 | 说明 |
|------|------|
| `SERIAL_*` | 串口连接参数（波特率、超时、默认端口等） |
| `PLOT_*` / `UI_*` | 绘图和界面尺寸（数据点数、刷新间隔、面板宽度等） |
| `INFLATE_*` / `DEFLATE_*` | 充气和泄气测试默认阈值 |
| `INFLECTION_*` | 拐点检测算法各项阈值（速率、加速度、漏气判定等） |
| `RATE_*` / `MAX_*` | 速率计算滤波、限幅、时间差保护 |
| `BINARY_*` / `HEARTBEAT_*` | 二进制协议帧格式、心跳、命令字等 |

您可以根据实际设备特性调整这些参数。

---

## 📁 项目结构

```
.
├── config.py                # 全局配置
├── data_controller.py       # 数据中枢（串口数据处理、状态机驱动）
├── inflection_detector.py   # 拐点检测算法
├── logger.py                # 日志系统 + CSV 数据记录器
├── main.py                  # 程序入口
├── result_calculator.py     # 速率与运动学计算
├── result_formatter.py      # 结果格式化
├── serial_worker.py         # 串口线程（文本/二进制协议解析）
├── test_managers.py         # 测试状态机（充气/泄气阶段管理）
├── ui_components.py         # UI 组件（主题、日志控件、状态类）
├── ui_main.py               # 主窗口（布局 + 交互逻辑）
├── utils.py                 # 通用工具（时间、CSV解析等）
├── logs/                    # 运行时生成（debug/ 和 csv/ 子目录）
│   ├── debug/               # 调试日志 .log
│   └── csv/                 # 压力数据 .csv
└── README.md                # 本文件
```

---

## 🧪 依赖库版本

| 库名 | 最低版本 | 用途 |
|------|----------|------|
| PySide6 | 6.0 | GUI 框架（Qt for Python） |
| pyqtgraph | 0.12.0 | 高性能科学绘图 |
| numpy | 1.21 | 数值计算 |
| pyserial | 3.5 | 串口通信 |

建议使用虚拟环境安装，避免依赖冲突。

---

## ❓ 常见问题

<details>
<summary><b>无法连接串口</b></summary>

- 检查设备是否被其他程序占用（关闭串口调试工具）。
- 确认驱动安装正确（Windows 需安装 CH340/CP210x 驱动）。
- 尝试更换 USB 端口或重启计算机。
</details>

<details>
<summary><b>压力数据不更新</b></summary>

- 检查协议类型是否正确（自动检测失败时可尝试手动切换）。
- 查看日志面板（UI 底部）是否有错误信息。
- 确认设备已正确发送数据（可用串口监听工具验证）。
</details>

<details>
<summary><b>拐点检测不灵敏或误报</b></summary>

- 调整 `config.py` 中 `INFLECTION_*` 相关阈值（如 `INFLECTION_ACTIVE_RATE`、`INFLECTION_ACTIVE_ACCELERATION`）。
- 若数据噪声较大，可增大 `RATE_FILTER_WINDOW` 或 `RATE_FILTER_SIGMA` 使速率更平滑。
</details>

<details>
<summary><b>波形显示卡顿</b></summary>

- 减小 `MAX_DATA_POINTS`（默认 5000）。
- 增大 `PLOT_INTERVAL_MS`（默认 50 ms）以降低刷新频率。
</details>

---

## 👨‍💻 作者与版权

- **作者**：得鹿梦鱼
- **反馈**：如有问题，请在 [GitHub Issues](https://github.com/yourusername/pressure-test-system/issues) 中提出
- **版权声明**：本项目仅供学习和研究使用，未经授权不得用于商业目的。引用请注明出处。

---

## 📅 更新日志

### v1.0 (2026-09)
- 初始版本，实现完整功能。
  - 串口通信（文本/二进制）
  - 实时绘图（压力+速率）
  - 充气/泄气状态机
  - 拐点检测（多策略）
  - 结果自动格式化
  - CSV 数据记录与加载
  - 双光标测量
  - 分级日志系统

---

**Enjoy your testing!**  
*“莫道桑榆晚，为霞尚满天”*
