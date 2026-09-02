# test_result_formatter.py
from result_formatter import ResultFormatter

def test_all_scenarios():
    print("="*70)
    print("充气结果场景测试")
    print("="*70)

    # ---- 充气情况1：起始→峰值 ----
    packet = {
        'state': 'DONE',
        'start': {'value': 5.0, 'time': 1.23, 'reached': True},
        'mid': {'value': 200.0, 'time': None, 'reached': False},
        'target': {'value': 300.0, 'time': None, 'reached': False},
        'peak': {'value': 105.0, 'time': 5.10}
    }
    result = ResultFormatter.format_result("inflate", packet)
    print(f"情况1: {result['text']}")
    print(f"预期: 5→105 3.87s 25.84mmHg/s\n")

    # ---- 充气情况2：起始→中间 + 起始→峰值 ----
    packet = {
        'state': 'DONE',
        'start': {'value': 5.0, 'time': 1.23, 'reached': True},
        'mid': {'value': 200.0, 'time': 3.73, 'reached': True},
        'target': {'value': 300.0, 'time': None, 'reached': False},
        'peak': {'value': 230.0, 'time': 5.10}
    }
    result = ResultFormatter.format_result("inflate", packet)
    print(f"情况2: {result['text']}")
    print(f"预期: 5→200 2.50s 78.00mmHg/s  5→230 3.87s 58.14mmHg/s\n")

    # ---- 充气情况3：起始→中间 + 起始→目标 ----
    packet = {
        'state': 'DONE',
        'start': {'value': 5.0, 'time': 1.23, 'reached': True},
        'mid': {'value': 200.0, 'time': 3.73, 'reached': True},
        'target': {'value': 300.0, 'time': 5.03, 'reached': True},
        'peak': {'value': 305.0, 'time': 5.10}
    }
    result = ResultFormatter.format_result("inflate", packet)
    print(f"情况3: {result['text']}")
    print(f"预期: 5→200 2.50s 78.00mmHg/s  5→300 3.80s 77.63mmHg/s\n")

    print("="*70)
    print("泄气结果场景测试")
    print("="*70)

    # ---- 泄气情况1：峰值→目标 ----
    packet = {
        'state': 'DONE',
        'start': {'value': 300.0, 'time': None, 'reached': False},
        'mid': {'value': 200.0, 'time': None, 'reached': False},
        'target': {'value': 5.0, 'time': 9.80, 'reached': True},
        'peak': {'value': 105.0, 'time': 5.10}
    }
    result = ResultFormatter.format_result("deflate", packet)
    print(f"情况1: {result['text']}")
    print(f"预期: 105→5 4.70s 21.28mmHg/s\n")

    # ---- 泄气情况2：峰值→目标 + 中间→目标 ----
    packet = {
        'state': 'DONE',
        'start': {'value': 300.0, 'time': None, 'reached': False},
        'mid': {'value': 200.0, 'time': 7.35, 'reached': True},
        'target': {'value': 5.0, 'time': 9.80, 'reached': True},
        'peak': {'value': 220.0, 'time': 5.10}
    }
    result = ResultFormatter.format_result("deflate", packet)
    print(f"情况2: {result['text']}")
    print(f"预期: 220→5 4.70s 45.74mmHg/s  200→5 2.45s 79.59mmHg/s\n")

    # ---- 泄气情况3：起始→目标 + 中间→目标 ----
    packet = {
        'state': 'DONE',
        'start': {'value': 300.0, 'time': 5.10, 'reached': True},
        'mid': {'value': 200.0, 'time': 7.35, 'reached': True},
        'target': {'value': 5.0, 'time': 9.80, 'reached': True},
        'peak': {'value': 307.0, 'time': 5.10}
    }
    result = ResultFormatter.format_result("deflate", packet)
    print(f"情况3: {result['text']}")
    print(f"预期: 300→5 4.70s 62.77mmHg/s  200→5 2.45s 79.59mmHg/s\n")

if __name__ == "__main__":
    test_all_scenarios()