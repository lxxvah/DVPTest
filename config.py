"""业务、设备和运行参数配置。"""


class Config:
    # ==================== 串口连接 ====================
    # 下拉框中允许选择的串口通信波特率。
    BAUDRATES = [
        "1200", "2400", "4800", "9600", "19200", "38400", "57600",
        "115200", "230400", "460800", "921600",
    ]
    # 程序首次启动时使用的默认波特率；也会作为串口设置的初始值。
    DEFAULT_BAUD = "115200"
    # 程序首次启动时优先选择的默认串口号；不存在时会自动选择可用串口。
    DEFAULT_PORT = "COM7"
    # 串口读写超时时间，单位为秒；过小可能丢数据，过大会降低停止响应速度。
    SERIAL_READ_TIMEOUT = 0.5
    SERIAL_WRITE_TIMEOUT = 0.5

    # ==================== 数据采集和显示 ====================
    # 实时波形保留的数据点数量；0 表示不截断，避免长测试时丢失前段波形。
    # PlotDataItem 已启用自动降采样，绘图性能不依赖于手动丢弃历史数据。
    MAX_DATA_POINTS = 0
    # 两次绘图信号更新的最小间隔，单位为毫秒；数值越小刷新越快，但 UI 负担越大。
    PLOT_INTERVAL_MS = 50
    # 泄气达到目标后，当压力低于该值时暂停绘图更新，单位为 mmHg。
    PLOT_STOP_THRESHOLD = 0.2
    # 日志窗口最多保留的日志条数；超过后自动删除最早的记录。
    MAX_LOG_ENTRIES = 10000
    # 自动检测串口设备的执行周期，单位为毫秒。
    AUTO_CONNECT_INTERVAL_MS = 2000
    # 等待设备切换 PC 模式完成的时间，单位为秒。
    PC_MODE_SWITCH_DELAY = 0.2

    # ==================== 测试默认参数 ====================
    # 充气测试的默认阈值：(起始压力, 中间压力, 目标压力)，单位为 mmHg。
    INFLATE_DEFAULT = (5, 200, 300)
    # 泄气测试的默认阈值：(起始压力, 中间压力, 目标压力)，单位为 mmHg。
    DEFLATE_DEFAULT = (300, 200, 5)
    # 慢速泄气判定阈值，单位为 mmHg/s；低于该速率时可被识别为慢漏气。
    LEAK_RATE_THRESHOLD = 3.0
    # 主动泄气判定阈值，单位为 mmHg/s；达到该速率时可被识别为主动释放。
    ACTIVE_RELEASE_THRESHOLD = 12.0
    # 判断压力变化方向的最小速率，单位为 mmHg/s；绝对值小于该值时视为基本不变。
    DIRECTION_THRESHOLD = 0.05

    # ==================== 拐点检测参数 ====================
    # 拐点检测保留的历史数据点数；增大可观察更长趋势，但响应会变慢。
    INFLECTION_HISTORY_SIZE = 10
    # 开始趋势判断所需的最少数据点数。
    INFLECTION_MIN_POINTS = 4
    # 计算趋势斜率时的最小时间差，单位为秒；用于避免除以接近零的时间差。
    INFLECTION_MIN_TIME_DELTA = 0.001
    # 峰值附近的压力距离，单位为 mmHg；用于识别慢漏气起始区域。
    INFLECTION_LEAK_PEAK_DISTANCE = 2.0
    # 慢漏气速率下限和上限，单位为 mmHg/s。
    INFLECTION_SLOW_LEAK_RATE_MIN = -1.0
    INFLECTION_SLOW_LEAK_RATE_MAX = -0.05
    # 从慢漏气切换到主动泄气的速率阈值，单位为 mmHg/s。
    INFLECTION_ACTIVE_FROM_LEAK_RATE = -1.0
    # 速率+加速度策略的速率阈值，单位为 mmHg/s。
    INFLECTION_ACTIVE_RATE = -0.5
    # 速率+加速度策略的加速度阈值，单位为 mmHg/s^2。
    INFLECTION_ACTIVE_ACCELERATION = -5.0
    # 主动泄气检测要求距离峰值的最小压力差，单位为 mmHg。
    INFLECTION_ACTIVE_PEAK_DISTANCE = 0.2
    # 仅速率持续下降策略的速率阈值，单位为 mmHg/s。
    INFLECTION_CONTINUOUS_RATE = -0.3
    # 持续下降策略的最小压力下降量，单位为 mmHg。
    INFLECTION_CONTINUOUS_DROP = 0.3
    # 候选拐点连续满足条件的次数。
    INFLECTION_CANDIDATE_COUNT = 2
    # 连续下降策略确认所需的连续点数。
    INFLECTION_ACTIVE_COUNT = 3
    # 连续下降策略的最小累计压力下降量，单位为 mmHg。
    INFLECTION_TOTAL_DROP = 0.15
    # 判断压力重新上升的速率阈值，单位为 mmHg/s。
    INFLECTION_RISING_RATE = 0.05
    # 判断峰值附近恢复稳定的压力距离，单位为 mmHg。
    INFLECTION_RESET_PEAK_DISTANCE = 0.5
    # 检测到拐点后，部分状态不再重复触发。
    INFLECTION_RATE_EPSILON = -0.05
    # 漏气平均速率的历史值权重；越大越平滑但响应越慢。
    INFLECTION_LEAK_AVERAGE_WEIGHT = 0.8
    # 当前速率在漏气平均值中的权重。
    INFLECTION_LEAK_CURRENT_WEIGHT = 0.2
    # 连续下降策略要求压力低于峰值的最小差值，单位为 mmHg。
    INFLECTION_CONTINUOUS_PEAK_DISTANCE = 0.0

    # ==================== 数据解析和速率计算 ====================
    # 文本协议压力数据格式；用于匹配类似“cuff=123.4 mmHg”的设备输出。
    DATA_PATTERN = r"^cuff=(\d+\.?\d*)\s*mmHg$"
    # 单次采样允许的最大压力变化量；0 表示当前不限制该项。
    MAX_PRESSURE_STEP = 0
    # 是否启用速率滤波；关闭后使用未滤波的速率数据。
    RATE_FILTER_ENABLE = True
    # 速率滤波使用的历史采样窗口大小；增大可使曲线更平滑，但响应更慢。
    RATE_FILTER_WINDOW = 5
    # 速率滤波的离群值判断参数；数值越大，越不容易剔除突变点。
    RATE_FILTER_SIGMA = 2.0
    # 速率曲线显示允许的最大值，单位为 mmHg/s；用于限制绘图曲线范围。
    RATE_CURVE_MAX = 1000.0
    # 速率计算和结果显示的总上限，单位为 mmHg/s；超过后会被截断或显示为上限提示。
    MAX_RATE_LIMIT = 2000.0
    # 时间差保护下限，单位为秒；小于该值时不进行差分计算。
    TIME_DELTA_EPSILON = 1e-9
    # NumPy 速率曲线替换零时间差时使用的时间值，单位为秒。
    ZERO_TIME_DELTA = 1e-6
    # 加速度计算上限，单位为 mmHg/s^2；用于抑制传感器尖峰。
    MAX_ACCELERATION_LIMIT = 10000.0
    # 界面显示压力的最低有效值，单位为 mmHg；低于该值显示占位符。
    MIN_DISPLAY_PRESSURE = 0.0

    # ==================== 设备识别 ====================
    # 无创模拟器/测试板的 USB 厂商 ID 和产品 ID，用于自动识别设备。
    SIMULATOR_VID = 0x1A86
    SIMULATOR_PID = 0x7523
    # NIBP 设备的 USB 厂商 ID 和产品 ID；0x0000 表示当前未配置专用识别号。
    NIBP_VID = 0x0000
    NIBP_PID = 0x0000
    # 自动探测串口协议的最长等待时间，单位为秒；超时后使用默认协议处理。
    DETECT_TIMEOUT = 0.3
    # 断开串口前的等待时间，单位为秒；用于等待设备完成命令处理。
    DISCONNECT_DELAY = 0.2
    # 协议探测开始前的等待时间，单位为秒。
    PROTOCOL_DETECT_DELAY = 0.1
    # 协议探测循环的轮询间隔，单位为秒。
    PROTOCOL_SNIFF_INTERVAL = 0.01
    # 串口无数据时的读取线程休眠时间，单位为秒。
    SERIAL_IDLE_INTERVAL = 0.001
    # 未知协议嗅探时，达到该字节数后提前结束读取。
    PROTOCOL_SNIFF_MAX_BYTES = 64
    # 二进制帧头和完整帧长度，长度单位为字节。
    BINARY_FRAME_HEADER = 0xAA
    BINARY_FRAME_LENGTH = 8
    # 心跳回复帧长度，长度单位为字节。
    HEARTBEAT_REPLY_LENGTH = 8
    # 二进制压力表测试命令的实际发送帧。
    PRESSURE_TABLE_COMMAND = [0x03, 0x02, 0x00]

    # ==================== 二进制协议换算 ====================
    # 二进制协议中的心跳命令字节；用于维持设备通信状态。
    HEARTBEAT_CMD = 0x09
    # 二进制压力原始值的缩放系数：压力值 = 原始值 * PRESSURE_SCALE + PRESSURE_OFFSET。
    PRESSURE_SCALE = 0.01
    # 二进制压力换算时的固定偏移量，单位为 mmHg。
    PRESSURE_OFFSET = -10.0

    # ==================== 二进制控制命令 ====================
    # 发送给设备的固定长度二进制命令；修改字节可能改变设备工作模式或测试动作。
    BINARY_COMMANDS = {
        # 进入设备 PC 控制界面。
        "enter_pc": [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
        # 退出设备 PC 控制界面。
        "exit_pc": [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
        # 执行压力表测试。
        "pressure_test": [0x03, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    }

    # ==================== 绘图和界面尺寸 ====================
    # 主窗口自动连接定时器和初始绘图范围等 UI 参数。
    PLOT_INITIAL_X_RANGE = (0, 60)
    PLOT_INITIAL_Y_RANGE = (0, 350)
    PLOT_INITIAL_RATE_RANGE = (0, 50)
    PLOT_AUTO_MIN_TIME = 10
    PLOT_AUTO_TIME_PADDING = 2
    PLOT_AUTO_PRESSURE_PADDING = 10
    PLOT_RATE_CURRENT_THRESHOLD = 20
    PLOT_RATE_LOW_MAX = 25.0
    PLOT_RATE_MEDIUM_MAX = 50
    PLOT_RATE_LOW_STEP = 0.5
    PLOT_RATE_MEDIUM_STEP = 2
    PLOT_RATE_HIGH_STEP = 5
    PLOT_RATE_HIGH_PADDING = 5
    PLOT_MAX_TICK_COUNT = 15
    PLOT_ZOOM_FACTOR = 1.1

    UI_TOOLBAR_HEIGHT = 36
    UI_LEFT_PANEL_WIDTH = 260
    UI_LOG_HEIGHT = 140
    UI_STATUS_BAR_HEIGHT = 24
    UI_INFO_HEIGHT = 75
    UI_PORT_WIDTH = 80
    UI_BAUD_WIDTH = 80
    UI_THRESHOLD_WIDTH = 40
    UI_PARAM_WIDTH = 44
