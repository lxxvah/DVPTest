# config.py
"""全局配置"""

class Config:
    COLORS = {
        'bg_main': '#0d1117',
        'bg_panel': '#151b22',
        'bg_chart': '#0d1117',
        'border': '#21262d',
        'fg_text': '#c9d1d9',
        'fg_secondary': '#8b949e',
        'fg_highlight': '#58a6ff',
        'pressure_curve': '#58a6ff',
        'rate_curve': '#d4a373',         # 改为柔和金色
        'inflate_result': '#3fb950',
        'deflate_result': '#f85149',
        'instant_rate': '#d29922',
        'avg_rate': '#58a6ff',
        'log_green': '#3fb950',
        'log_white': '#c9d1d9',
        'log_yellow': '#d29922',
        'log_blue': '#58a6ff',
        'log_red': '#f85149',
    }
    BAUDRATES = ["1200", "2400", "4800", "9600", "19200", "38400", "57600",
                 "115200", "230400", "460800", "921600"]
    DEFAULT_BAUD = "115200"
    DEFAULT_PORT = "COM7"
    MAX_DATA_POINTS = 5000
    PLOT_INTERVAL_MS = 50
    INFLATE_DEFAULT = (5, 200, 300)
    DEFLATE_DEFAULT = (300, 200, 5)

    DATA_PATTERN = r'^cuff=(\d+\.?\d*)\s*mmHg$'
    MAX_PRESSURE_STEP = 0

    SIMULATOR_VID = 0x1A86
    SIMULATOR_PID = 0x7523

    RATE_FILTER_ENABLE = True
    RATE_FILTER_WINDOW = 5
    RATE_FILTER_SIGMA = 2.0

    DIRECTION_THRESHOLD = 0.05
    RATE_CURVE_MAX = 1000.0
    MAX_RATE_LIMIT = 2000.0

    FONT_SIZE = 13
    FONT_SIZE_TITLE = 15
    FONT_SIZE_DATA = 13
    FONT_SIZE_LOG = 11

    PLOT_STOP_THRESHOLD = 0.2
    MAX_LOG_ENTRIES = 10000

    LEAK_RATE_THRESHOLD = 3.0
    ACTIVE_RELEASE_THRESHOLD = 12.0

    HEARTBEAT_CMD = 0x09
    PRESSURE_SCALE = 0.01
    PRESSURE_OFFSET = -10.0
    NIBP_VID = 0x0000
    NIBP_PID = 0x0000
    DETECT_TIMEOUT = 0.3

    BUTTON_TEXTS = {
        "refresh": ("刷新", "btn_action", False, False),
        "clear": ("清屏", "btn_action", False, False),
        "toggle_plot": ("暂停绘图", "btn_toggle_plot", False, False),
        "toggle_rate": ("速率曲线：开", "btn_action", True, True),
        "connect": ("连接", "btn_connect", False, False),
        "disconnect": ("断开", "btn_disconnect", False, False),
        "start": ("开始 AT#AG", "btn_start", False, False),
        "stop": ("结束 AT#AH", "btn_stop", False, False),
        "save_img": ("保存图片", "btn_action", False, False),
        "save_csv": ("保存CSV", "btn_action", False, False),
        "load_wave": ("加载波形", "btn_action", False, False),
        "cursor": ("光标测量", "btn_action", False, False),
    }

    BINARY_COMMANDS = {
        "enter_pc": [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
        "exit_pc":  [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
        "pressure_test": [0x03, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    }

    # ============================================================
    # ★ 按钮样式字典（集中定义，保证所有按钮样式统一且 100% 生效）
    #   使用方法：btn.setStyleSheet(Config.BUTTON_STYLES["样式名"])
    # ============================================================
    BUTTON_STYLES = {
        # 连接：柔光绿
        "connect": """
            QPushButton {
                background: #66bb6a;
                color: #ffffff;
                border: 1px solid #4caf50;
                border-radius: 4px;
                padding: 5px 12px;
                font-weight: bold;
            }
            QPushButton:hover { background: #81c784; }
            QPushButton:pressed { background: #4caf50; padding-top: 6px; padding-bottom: 4px; }
            QPushButton:disabled { background: #2e7d32; color: #a5d6a7; border: 1px solid #388e3c; }
        """,
        # 断开：柔光红
        "disconnect": """
            QPushButton {
                background: #ef9a9a;
                color: #ffffff;
                border: 1px solid #e57373;
                border-radius: 4px;
                padding: 5px 12px;
                font-weight: bold;
            }
            QPushButton:hover { background: #ffcdd2; }
            QPushButton:pressed { background: #e57373; padding-top: 6px; padding-bottom: 4px; }
            QPushButton:disabled { background: #c62828; color: #ef9a9a; border: 1px solid #b71c1c; }
        """,
        # 开始：柔光蓝渐变
        "start": """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #64b5f6, stop:1 #1e88e5);
                color: #ffffff;
                border: 1px solid #1e88e5;
                border-radius: 4px;
                padding: 5px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #90caf9, stop:1 #42a5f5);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #1565c0, stop:1 #0d47a1);
                border: 1px solid #0d47a1;
                padding-top: 6px;
                padding-bottom: 4px;
            }
            QPushButton:disabled { background: #0d47a1; color: #90caf9; border: 1px solid #1565c0; }
        """,
        # 停止：柔光橙渐变
        "stop": """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #ffb74d, stop:1 #f57c00);
                color: #ffffff;
                border: 1px solid #f57c00;
                border-radius: 4px;
                padding: 5px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #ffcc80, stop:1 #fb8c00);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #e65100, stop:1 #bf360c);
                border: 1px solid #bf360c;
                padding-top: 6px;
                padding-bottom: 4px;
            }
            QPushButton:disabled { background: #bf360c; color: #ffcc80; border: 1px solid #e65100; }
        """,
        # 通用操作：柔光灰蓝
        "action": """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #78909c, stop:1 #546e7a);
                color: #ffffff;
                border: 1px solid #546e7a;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #90a4ae, stop:1 #78909c);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #455a64, stop:1 #37474f);
                border: 1px solid #37474f;
                padding-top: 5px;
                padding-bottom: 3px;
            }
            QPushButton:disabled { background: #37474f; color: #90a4ae; border: 1px solid #455a64; }
        """,
        # 暂停绘图：柔光绿边框
        "toggle_plot": """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #388e3c, stop:1 #1b5e20);
                color: #ffffff;
                border: 1px solid #4caf50;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #43a047, stop:1 #2e7d32);
                color: #ffffff;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #1b5e20, stop:1 #0a2a0a);
                border: 1px solid #1b5e20;
                padding-top: 5px;
                padding-bottom: 3px;
            }
            QPushButton:disabled { background: #1b5e20; color: #81c784; border: 1px solid #2e7d32; }
        """,
        # 速率曲线开：金色（呼应曲线颜色）
        "rate_on": """
            QPushButton {
                background: #d4a373;
                color: #ffffff;
                border: 1px solid #b8956a;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background: #c9a07a; }
            QPushButton:pressed { background: #b8956a; padding-top: 5px; padding-bottom: 3px; }
            QPushButton:disabled { background: #8d6e63; color: #d7ccc8; border: 1px solid #795548; }
        """,
        # 速率曲线关：柔和灰
        "rate_off": """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #78909c, stop:1 #546e7a);
                color: #ffffff;
                border: 1px solid #546e7a;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #90a4ae, stop:1 #78909c);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #455a64, stop:1 #37474f);
                border: 1px solid #37474f;
                padding-top: 5px;
                padding-bottom: 3px;
            }
            QPushButton:disabled { background: #37474f; color: #90a4ae; border: 1px solid #455a64; }
        """,
        # 锁定视图激活：深绿
        "lock_active": """
            QPushButton {
                background: #1f6f3b;
                color: #ffffff;
                border: 1px solid #1f6f3b;
                border-radius: 4px;
                padding: 4px 10px;
                font-weight: bold;
            }
            QPushButton:hover { background: #2a8f4b; }
            QPushButton:pressed { background: #145a2a; }
        """,
    }

    STYLESHEET = f"""
    * {{ margin: 0; padding: 0; }}
    QMainWindow, QWidget {{ background-color: #0d1117; color: #c9d1d9; }}

    /* ----- 通用按钮（无 id）—— 使用 background-color 纯色，避免覆盖 ID 选择器 ----- */
    QPushButton {{
        background-color: #4a6a8a;
        color: #ffffff;
        border: 1px solid #3a5a7a;
        border-radius: 4px;
        padding: 5px 10px;
        font-size: {FONT_SIZE}px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: #5a7a9a;
    }}
    QPushButton:pressed {{
        background-color: #2a4a6a;
        border: 1px solid #2a4a6a;
        padding-top: 6px;
        padding-bottom: 4px;
    }}
    QPushButton:disabled {{
        background-color: #2a3a4a;
        color: #6a7a8a;
        border: 1px solid #3a4a5a;
    }}

    /* ----- 连接按钮（柔光绿） ----- */
    QPushButton#btn_connect {{
        background: #66bb6a;
        color: #ffffff;
        border: 1px solid #4caf50;
        border-radius: 4px;
        padding: 5px 12px;
        font-weight: bold;
    }}
    QPushButton#btn_connect:hover {{
        background: #81c784;
    }}
    QPushButton#btn_connect:pressed {{
        background: #4caf50;
        padding-top: 6px;
        padding-bottom: 4px;
    }}
    QPushButton#btn_connect:disabled {{
        background: #2e7d32;
        color: #a5d6a7;
        border: 1px solid #388e3c;
    }}

    /* ----- 断开按钮（柔光红） ----- */
    QPushButton#btn_disconnect {{
        background: #ef9a9a;
        color: #ffffff;
        border: 1px solid #e57373;
        border-radius: 4px;
        padding: 5px 12px;
        font-weight: bold;
    }}
    QPushButton#btn_disconnect:hover {{
        background: #ffcdd2;
    }}
    QPushButton#btn_disconnect:pressed {{
        background: #e57373;
        padding-top: 6px;
        padding-bottom: 4px;
    }}
    QPushButton#btn_disconnect:disabled {{
        background: #c62828;
        color: #ef9a9a;
        border: 1px solid #b71c1c;
    }}

    /* ----- 开始按钮（柔光蓝渐变） ----- */
    QPushButton#btn_start {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #64b5f6, stop:1 #1e88e5);
        color: #ffffff;
        border: 1px solid #1e88e5;
        border-radius: 4px;
        padding: 5px 12px;
        font-weight: bold;
    }}
    QPushButton#btn_start:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #90caf9, stop:1 #42a5f5);
    }}
    QPushButton#btn_start:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #1565c0, stop:1 #0d47a1);
        border: 1px solid #0d47a1;
        padding-top: 6px;
        padding-bottom: 4px;
    }}
    QPushButton#btn_start:disabled {{
        background: #0d47a1;
        color: #90caf9;
        border: 1px solid #1565c0;
    }}

    /* ----- 停止按钮（柔光橙渐变） ----- */
    QPushButton#btn_stop {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #ffb74d, stop:1 #f57c00);
        color: #ffffff;
        border: 1px solid #f57c00;
        border-radius: 4px;
        padding: 5px 12px;
        font-weight: bold;
    }}
    QPushButton#btn_stop:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #ffcc80, stop:1 #fb8c00);
    }}
    QPushButton#btn_stop:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #e65100, stop:1 #bf360c);
        border: 1px solid #bf360c;
        padding-top: 6px;
        padding-bottom: 4px;
    }}
    QPushButton#btn_stop:disabled {{
        background: #bf360c;
        color: #ffcc80;
        border: 1px solid #e65100;
    }}

    /* ----- 通用操作按钮（柔光灰蓝） ----- */
    QPushButton#btn_action {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #78909c, stop:1 #546e7a);
        color: #ffffff;
        border: 1px solid #546e7a;
        border-radius: 4px;
        padding: 4px 10px;
        font-size: {FONT_SIZE}px;
        font-weight: bold;
    }}
    QPushButton#btn_action:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #90a4ae, stop:1 #78909c);
        color: #ffffff;
    }}
    QPushButton#btn_action:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #455a64, stop:1 #37474f);
        border: 1px solid #37474f;
        padding-top: 5px;
        padding-bottom: 3px;
    }}
    QPushButton#btn_action:disabled {{
        background: #37474f;
        color: #90a4ae;
        border: 1px solid #455a64;
    }}

    /* ----- 暂停绘图按钮（柔光绿边框） ----- */
    QPushButton#btn_toggle_plot {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #388e3c, stop:1 #1b5e20);
        color: #ffffff;
        border: 1px solid #4caf50;
        border-radius: 4px;
        padding: 4px 10px;
        font-size: {FONT_SIZE}px;
        font-weight: bold;
    }}
    QPushButton#btn_toggle_plot:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #43a047, stop:1 #2e7d32);
        color: #ffffff;
    }}
    QPushButton#btn_toggle_plot:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #1b5e20, stop:1 #0a2a0a);
        border: 1px solid #1b5e20;
        padding-top: 5px;
        padding-bottom: 3px;
    }}
    QPushButton#btn_toggle_plot:disabled {{
        background: #1b5e20;
        color: #81c784;
        border: 1px solid #2e7d32;
    }}

    /* ----- 其他控件（字体增大、高亮白、加粗） ----- */
    QLineEdit, QComboBox {{
        background-color: #0d1117;
        color: #c9d1d9;
        border: 1px solid #21262d;
        padding: 3px 4px;
        border-radius: 0px;
        font-size: {FONT_SIZE}px;
    }}
    QComboBox::drop-down {{ border: none; }}
    QComboBox::down-arrow {{ image: none; }}
    QTextEdit {{
        background-color: #0d1117;
        color: #c9d1d9;
        border: 1px solid #21262d;
        font-family: Consolas;
        font-size: {FONT_SIZE_LOG}pt;
        border-radius: 0px;
    }}
    QGroupBox {{
        border: 1px solid #21262d;
        margin-top: 8px;
        border-radius: 0px;
        font-size: {FONT_SIZE}px;
        padding-top: 8px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
        color: #ffffff;          /* 高亮白 */
        font-size: 14px;         /* 单独调大 */
        font-weight: bold;       /* 加粗 */
    }}
    QLabel {{
        font-size: 14px;         /* 或 {FONT_SIZE}px */
        color: #ffffff;          /* 高亮白 */
        font-weight: bold;       /* 加粗 */
    }}

    /* ========== 新增：通用动态按钮状态属性选择器 ========== */
    QPushButton[state="normal"]{{}}
    QPushButton[state="active"]{{
        background-color:#1f6f3b;
        color:#ffffff;
    }}
    QPushButton[state="warn"]{{
        background-color:#6b2a2a;
        color:#ffffff;
    }}
    QPushButton[state="highlight"]{{
        background-color:#254b9c;
        color:#ffffff;
    }}
    """
    DISCONNECT_DELAY = 0.2