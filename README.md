markdown
# DVPTest - 泄气阀压力测试上位机

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/PySide6-6.5+-green.svg)](https://doc.qt.io/qtforpython-6/)

> 泄气阀压力测试上位机软件 —— 作者：得鹿梦鱼

---

## 📖 项目简介

DVPTest 是一款基于 **PySide6** 开发的泄气阀压力测试上位机软件，用于实时采集压力传感器数据、计算充气/泄气速率、自动检测拐点，并支持离线 CSV 数据回放分析。

### 应用场景
- 泄气阀性能测试
- 压力传感器数据采集
- 充气/泄气速率分析
- 离线波形回放与结果复现

---

## ✨ 功能特点

| 功能模块 | 说明 |
|----------|------|
| 🔌 **串口通信** | 自动检测文本协议（`cuff=xxx mmHg`）和二进制协议（帧头 `0xAA`） |
| 📈 **实时波形** | 压力曲线 + 速率曲线双轴显示，支持暂停/恢复绘图 |
| ⚡ **运动学分析** | 瞬时速率（一阶导）+ 加速度（二阶导）实时计算 |
| 🎯 **结果计算** | 充气/泄气起始值、中间值、目标值自动记录与显示 |
| 🔍 **拐点检测** | 多策略自适应拐点检测（速率+加速度、持续下降、连续下降等） |
| 📊 **离线回放** | 加载 CSV 文件自动重放分析，生成充气/泄气结果 |
| 📝 **统一日志** | 日志输出到文件、控制台和 UI（支持 info/success/warning/error/cmd 级别过滤） |
| 🖥️ **光标测量** | 两组独立光标（C1/C2、B1/B2），自动计算 Δt、ΔP、速率 |
| 🔒 **视图锁定** | 锁定/解锁波形自动缩放，方便细节查看 |
| 📦 **一键安装** | Inno Setup 生成安装包，方便部署 |

---

## 🛠️ 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.12 | 编程语言 |
| PySide6 | 6.5+ | GUI 框架（Qt for Python） |
| PyQtGraph | 0.13+ | 高性能波形绘图 |
| PySerial | 3.5+ | 串口通信 |
| NumPy | 1.24+ | 数值计算 |
| PyInstaller | 6.0+ | 打包 exe |
| Inno Setup | 6.0+ | 制作安装包 |

---

## 🚀 快速开始

### 1️⃣ 克隆仓库

```bash
git clone https://github.com/lxxvah/DVPTest.git
cd DVPTest
2️⃣ 安装依赖
bash
pip install -r requirements.txt
3️⃣ 运行程序
bash
python main.py
4️⃣ 打包成 exe
bash
pyinstaller --onedir --windowed --name DVPTest --icon app.ico --add-data "app.ico;." --hidden-import PySide6.QtXml --hidden-import PySide6.QtMultimedia main.py
5️⃣ 制作安装包
使用 Inno Setup 编译 setup.iss 脚本。

📖 使用说明
基本操作流程
text
┌─────────────────────────────────────────────────────────┐
│  1. 连接设备                                          │
│     ├── 选择串口号 + 波特率（默认 115200）            │
│     └── 点击 "连接" → 状态栏显示 "监听中"             │
│                                                         │
│  2. 设置参数                                            │
│     ├── 充气：起始值 → 中间值 → 目标值                │
│     │    （默认 5 → 200 → 300 mmHg）                   │
│     └── 泄气：起始值 → 中间值 → 目标值                │
│          （默认 300 → 200 → 5 mmHg）                   │
│                                                         │
│  3. 开始测试                                            │
│     ├── 点击 "开始 AT#AG"                              │
│     ├── 波形实时绘制，速率曲线同步显示                  │
│     └── 充气/泄气结果自动计算并显示                    │
│                                                         │
│  4. 结束测试                                            │
│     └── 点击 "结束 AT#AH"                              │
│                                                         │
│  5. 数据保存与回放                                      │
│     ├── "保存CSV" → 导出时间-压力数据                  │
│     └── "加载波形" → 离线回放分析，自动生成结果        │
└─────────────────────────────────────────────────────────┘
快捷操作
操作	效果
Ctrl + 滚轮	横向缩放波形
Shift + 滚轮	纵向缩放波形
光标测量 按钮	启用/禁用光标（C1/C2 一组，B1/B2 一组）
锁定视图 按钮	锁定/解锁自动缩放
清屏 按钮	清空波形并重置时间轴
📁 项目结构
text
DVPTest/
├── main.py                  # 程序入口
├── config.py                # 全局配置（颜色、波特率、阈值等）
├── logger.py                # 日志系统（自定义级别 + Qt 桥接）
├── data_controller.py       # 数据中枢（串口→状态机→绘图）
├── test_managers.py         # 状态机（充气/泄气流程控制）
├── result_calculator.py     # 运动学计算（速度/加速度）
├── inflection_detector.py   # 拐点检测（多策略自适应）
├── serial_worker.py         # 串口通信（文本/二进制协议）
├── ui_main.py               # 主界面（约 1200 行）
├── result_formatter.py      # 结果格式化（充气/泄气显示）
├── utils.py                 # 工具函数（时间戳、CSV解析等）
├── app.ico                  # 程序图标
├── setup.iss                # Inno Setup 安装脚本
├── requirements.txt         # Python 依赖列表
└── README.md                # 项目说明（本文件）
📝 日志系统
日志同时输出到三个地方：

文件：./logs/debug/debug_YYYYMMDD_HHMMSS.log

控制台：实时输出（带颜色）

UI：主界面下方日志区域（支持级别过滤）

日志级别
级别	说明	颜色
info	常规信息	白色
success	操作成功	绿色
warning	警告信息	黄色
error	错误信息	红色
cmd	命令发送	蓝色
debug	调试信息	灰色
使用示例
python
import logging
logger = logging.getLogger("DVPTest")

logger.info("常规信息")
logger.success("操作成功")
logger.warning("警告信息")
logger.error("错误信息")
logger.cmd("发送命令: AT#AG")
⚠️ 注意事项
大文件：dist/DVPTest.exe 和 installer/DVPTest_Setup.exe 超过 GitHub 50MB 限制，请在 Release 页面下载，不要提交到仓库。

日志目录：程序首次运行时会自动创建 ./logs/ 目录。如果安装到 Program Files，请确保有写入权限。

串口权限：Windows 下可能需要管理员权限才能访问某些串口。

Python 版本：建议使用 Python 3.12，低版本可能不兼容。

📄 许可证
本项目采用 MIT License 开源协议。

text
MIT License

Copyright (c) 2026 得鹿梦鱼

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
👤 作者
得鹿梦鱼

GitHub: @lxxvah

邮箱: 792789598@qq.com

🙏 致谢
Qt for Python (PySide6) — 强大的 GUI 框架

PyQtGraph — 高性能波形绘制

PySerial — 跨平台串口通信
