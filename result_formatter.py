# result_formatter.py
"""
结果格式化模块
职责：根据数据包生成显示文本
输入：数据包 (dict)
输出：显示结果 (dict: {'key': key, 'text': text})
"""
from typing import Dict


class ResultFormatter:
    @staticmethod
    def format_result(key: str, packet: Dict) -> Dict:
        """统一格式化入口"""
        if key == "inflate":
            text = ResultFormatter._format_inflate(packet)
        elif key == "deflate":
            text = ResultFormatter._format_deflate(packet)
        else:
            text = "--"
        return {'key': key, 'text': text}

    # ==================== 辅助函数 ====================
    @staticmethod
    def _format_segment(
        start_val: float,
        start_time: float,
        end_val: float,
        end_time: float,
        start_label: str = "",
        end_label: str = ""
    ) -> str:
        """
        格式化单个段
        :param start_val: 起点数值
        :param start_time: 起点时间
        :param end_val: 终点数值
        :param end_time: 终点时间
        :param start_label: 起点标签（如"起始值"、"峰值"）
        :param end_label: 终点标签（如"目标值"）
        """
        dt = end_time - start_time
        rate = abs((end_val - start_val) / dt) if dt > 0 else 0

        # 数值格式化：整数不显示小数点
        start_str = f"{start_val:.0f}" if start_val == int(start_val) else f"{start_val:.1f}"
        end_str = f"{end_val:.0f}" if end_val == int(end_val) else f"{end_val:.1f}"

        # 构建带标签的显示字符串
        if start_label:
            start_display = f"{start_label}{start_str}"
        else:
            start_display = start_str

        if end_label:
            end_display = f"{end_label}{end_str}"
        else:
            end_display = end_str

        return f"{start_display}→{end_display} 时间{dt:.2f}s 速率{rate:.2f}mmHg/s"

    # ==================== 充气格式化 ====================
    @staticmethod
    def _format_inflate(packet: Dict) -> str:
        state = packet.get('state', 'IDLE')

        if state == 'IDLE':
            return "--"
        if state == 'INFLATING':
            return "充气中..."

        # state == DONE
        start = packet.get('start', {})
        mid = packet.get('mid', {})
        target = packet.get('target', {})
        peak = packet.get('peak', {})

        start_time = start.get('time')
        start_val = start.get('value', 0)
        mid_time = mid.get('time')
        mid_val = mid.get('value', 0)
        target_time = target.get('time')
        target_val = target.get('value', 0)
        peak_time = peak.get('time')
        peak_val = peak.get('value', 0)

        # 如果起始未到达，无法产生结果
        if start_time is None:
            return "--"

        segments = []

        # ---- 情况3：起始→中间 + 起始→目标（完整充气） ----
        if mid_time is not None and target_time is not None:
            segments.append(ResultFormatter._format_segment(
                start_val, start_time, mid_val, mid_time,
                start_label="起始值", end_label="中间值"
            ))
            segments.append(ResultFormatter._format_segment(
                start_val, start_time, target_val, target_time,
                start_label="起始值", end_label="目标值"
            ))
            return "  ".join(segments)

        # ---- 情况2：起始→中间 + 起始→峰值 ----
        if mid_time is not None and peak_time is not None:
            segments.append(ResultFormatter._format_segment(
                start_val, start_time, mid_val, mid_time,
                start_label="起始值", end_label="中间值"
            ))
            segments.append(ResultFormatter._format_segment(
                start_val, start_time, peak_val, peak_time,
                start_label="起始值", end_label="峰值"
            ))
            return "  ".join(segments)

        # ---- 情况1：起始→峰值 ----
        if peak_time is not None:
            segments.append(ResultFormatter._format_segment(
                start_val, start_time, peak_val, peak_time,
                start_label="起始值", end_label="峰值"
            ))
            return "  ".join(segments)

        return "--"

    # ==================== 泄气格式化 ====================
    @staticmethod
    def _format_deflate(packet: Dict) -> str:
        state = packet.get('state', 'IDLE')

        if state == 'IDLE':
            return "--"
        if state == 'DEFLATING':
            return "泄气中..."

        # state == DONE
        start = packet.get('start', {})
        mid = packet.get('mid', {})
        target = packet.get('target', {})
        peak = packet.get('peak', {})

        start_time = start.get('time')
        start_val = start.get('value', 0)
        mid_time = mid.get('time')
        mid_val = mid.get('value', 0)
        target_time = target.get('time')
        target_val = target.get('value', 0)
        peak_time = peak.get('time')
        peak_val = peak.get('value', 0)

        # 如果目标未到达，无法产生结果
        if target_time is None:
            return "--"

        # 峰值必须存在
        if peak_time is None:
            return "--"

        segments = []

        has_start = start_time is not None
        has_mid = mid_time is not None

        # ---- 情况3：有起始值 + 有中间值 + 有目标值 ----
        # 输出：起始值→目标 + 中间值→目标
        if has_start and has_mid:
            segments.append(ResultFormatter._format_segment(
                start_val, start_time, target_val, target_time,
                start_label="起始值", end_label="目标值"
            ))
            segments.append(ResultFormatter._format_segment(
                mid_val, mid_time, target_val, target_time,
                start_label="中间值", end_label="目标值"
            ))
            return "  ".join(segments)

        # ---- 情况2：无起始值 + 有中间值 + 有目标值 ----
        # 输出：峰值→目标 + 中间值→目标
        if has_mid:  # has_start == False
            segments.append(ResultFormatter._format_segment(
                peak_val, peak_time, target_val, target_time,
                start_label="峰值", end_label="目标值"
            ))
            segments.append(ResultFormatter._format_segment(
                mid_val, mid_time, target_val, target_time,
                start_label="中间值", end_label="目标值"
            ))
            return "  ".join(segments)

        # ---- 情况1：无起始值 + 无中间值 + 有目标值 ----
        # 输出：峰值→目标
        segments.append(ResultFormatter._format_segment(
            peak_val, peak_time, target_val, target_time,
            start_label="峰值", end_label="目标值"
        ))
        return "  ".join(segments)