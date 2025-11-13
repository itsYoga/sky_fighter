"""
測試腳本：記錄和顯示 Dummy Device 的傾斜數據
用於分析手機傾斜時的實際數據範圍和模式
"""

import DAN
import time
import statistics
from collections import deque

# --- IoTtalk 設定 ---
ServerURL = 'https://class.iottalk.tw'
Reg_addr = None  # None = 使用 MAC address

# 註冊裝置
DAN.profile = {
    'd_name': 'Tilt_Test',
    'dm_name': 'Dummy_Device',
    'is_sim': False,  # 必須要有這個欄位，False 表示這是真實裝置
    'df_list': ['Dummy_Control'],
}

print("=" * 60)
print("📱 Gyroscope（陀螺儀）數據測試工具 - 極值檢測版")
print("=" * 60)
print("請在 IoTtalk 網頁上連接：")
print("   Smartphone (Gyroscope) -> Dummy_Device (Dummy_Control)")
print("")
print("⚠️  重要：確保連接的是 Gyroscope 的數值輸出（x1, x2, x3）")
print("   而不是方向描述輸出。如果收到方向字符串（如 '平躺'、'橫擺'），")
print("   請檢查 Canvas 連接並切換到數值輸出。")
print("=" * 60)
print("測試步驟：")
print("1. 保持手機水平 3 秒（基準值 - 用於計算中間點）")
print("2. 向右傾斜到極限 5 秒（盡可能向右傾斜）")
print("3. 回到水平 2 秒")
print("4. 向左傾斜到極限 5 秒（盡可能向左傾斜）")
print("5. 回到水平 2 秒")
print("")
print("💡 程式會自動檢測：")
print("   - 中間點（基準值）")
print("   - 極右值（最大值）")
print("   - 極左值（最小值）")
print("   - 並提供 Game.py 的建議設定")
print("=" * 60)
print("開始測試...\n")

# 註冊裝置
try:
    DAN.device_registration_with_retry(ServerURL, Reg_addr)
    print("✅ IoTtalk 連線成功！\n")
except Exception as e:
    print(f"❌ 連線失敗: {e}")
    exit(1)

# 數據記錄
all_data = []
current_session = []
session_start_time = None
session_name = ""

# 用於計算移動平均的窗口
data_window = deque(maxlen=10)

def print_statistics(data_list, label):
    """計算並顯示統計信息"""
    if not data_list:
        return
    
    values = [float(d['value']) for d in data_list]
    print(f"\n{label} 統計：")
    print(f"  數據點數: {len(values)}")
    print(f"  最小值: {min(values):.4f}")
    print(f"  最大值: {max(values):.4f}")
    print(f"  平均值: {statistics.mean(values):.4f}")
    print(f"  中位數: {statistics.median(values):.4f}")
    if len(values) > 1:
        print(f"  標準差: {statistics.stdev(values):.4f}")
    print(f"  範圍: {max(values) - min(values):.4f}")

# 測試階段 - 改為手動控制模式（延長測試時間）
phases = [
    ("保持水平（基準）", 5),      # 從 3 秒增加到 5 秒
    ("向右傾斜到極限", 8),        # 從 5 秒增加到 8 秒
    ("回到水平", 3),              # 從 2 秒增加到 3 秒
    ("向左傾斜到極限", 8),        # 從 5 秒增加到 8 秒
    ("回到水平", 3),              # 從 2 秒增加到 3 秒
]

phase_index = 0
phase_start_time = time.time()

print(f"階段 {phase_index + 1}/{len(phases)}: {phases[phase_index][0]}")
print("開始記錄數據...\n")

# 等待首次數據到達
print("⏳ 等待 IoTtalk 數據傳輸...")
wait_start = time.time()
first_data_received = False

try:
    while True:
        try:
            # 從伺服器拉取數據
            data = DAN.pull('Dummy_Control')
            
            # 檢查是否首次收到數據
            if not first_data_received and data is not None:
                wait_time = time.time() - wait_start
                print(f"✅ 首次數據到達！等待時間: {wait_time:.1f} 秒\n")
                first_data_received = True
            
            # 調試：顯示接收到的數據（前5次非None數據）
            if data is not None and len(all_data) < 5:
                print(f"\n[調試 #{len(all_data)+1}] 收到數據: {data}, 類型: {type(data)}")
                if isinstance(data, (list, tuple)):
                    print(f"  [調試] 列表長度: {len(data)}")
                    for i, item in enumerate(data):
                        print(f"  [調試] 元素[{i}]: {item}, 類型: {type(item)}")
            
            # 如果一直收到 None，顯示等待提示（每5秒一次）
            if data is None and not first_data_received:
                elapsed = time.time() - wait_start
                if int(elapsed) % 5 == 0 and elapsed > 0:
                    print(f"\r⏳ 等待數據中... ({int(elapsed)}秒) - 請檢查 IoTtalk Canvas 連接", end='', flush=True)
                time.sleep(0.1)  # 避免過度消耗 CPU
                continue
            
            if data is not None:
                # 處理 Gyroscope（陀螺儀）數據：返回列表 [alpha, beta, gamma] 角速度值
                # alpha (繞 Z 軸旋轉), beta (繞 X 軸旋轉), gamma (繞 Y 軸旋轉)
                # 通常 beta (繞 X 軸) 用於左右傾斜控制
                raw_value = None
                alpha_value = None
                beta_value = None
                gamma_value = None
                
                # 調試：顯示原始數據格式（前幾次）
                if len(all_data) < 3:
                    print(f"\n[調試] 原始數據: {data}, 類型: {type(data)}")
                    if isinstance(data, (list, tuple)):
                        print(f"[調試] 列表長度: {len(data)}")
                        if len(data) > 0:
                            print(f"[調試] 第一個元素: {data[0]}, 類型: {type(data[0])}")
                
                # 先檢查數據是否為嵌套列表
                if isinstance(data, (list, tuple)):
                    # 檢查列表中的元素是否也是列表
                    if len(data) > 0 and isinstance(data[0], (list, tuple)):
                        # 嵌套列表，取第一個子列表
                        data = data[0]
                    
                    if len(data) >= 3:
                        # Gyroscope 有 3 個值：[alpha, beta, gamma] 角速度
                        # alpha = 繞 Z 軸（yaw）
                        # beta = 繞 X 軸（pitch）
                        # gamma = 繞 Y 軸（roll）- 通常用於左右傾斜
                        try:
                            # 確保每個元素都是數值
                            alpha_val = data[0]
                            if isinstance(alpha_val, (list, tuple)):
                                alpha_val = alpha_val[0] if len(alpha_val) > 0 else 0
                            alpha_value = float(alpha_val)
                            
                            beta_val = data[1]
                            if isinstance(beta_val, (list, tuple)):
                                beta_val = beta_val[0] if len(beta_val) > 0 else 0
                            beta_value = float(beta_val)
                            
                            gamma_val = data[2]
                            if isinstance(gamma_val, (list, tuple)):
                                gamma_val = gamma_val[0] if len(gamma_val) > 0 else 0
                            gamma_value = float(gamma_val)
                            
                            # 使用 gamma（繞 Y 軸，roll）作為主要控制值（左右傾斜）
                            raw_value = gamma_value
                        except (ValueError, TypeError) as e:
                            print(f"\n⚠️ 無法解析數據: {data}, 錯誤: {e}")
                            # 嘗試只讀取第一個值
                            try:
                                first_val = data[0]
                                if isinstance(first_val, (list, tuple)):
                                    first_val = first_val[0] if len(first_val) > 0 else 0
                                raw_value = float(first_val)
                            except (ValueError, TypeError):
                                continue
                    elif len(data) == 1:
                        val = data[0]
                        if isinstance(val, (list, tuple)):
                            val = val[0] if len(val) > 0 else 0
                        
                        # 檢查是否為字符串（Gyroscope 可能返回方向描述）
                        if isinstance(val, str):
                            # 將方向字符串映射為數值
                            # 根據實際測試調整這些映射
                            direction_map = {
                                '平躺': 0.0,      # 平躺 = 水平
                                '橫擺': 0.0,      # 橫擺 = 水平（橫向）
                                '左傾': -5.0,     # 左傾 = 向左
                                '右傾': 5.0,      # 右傾 = 向右
                                '直立': 0.0,      # 直立 = 垂直
                                '倒立': 0.0       # 倒立 = 倒置
                            }
                            raw_value = direction_map.get(val, 0.0)
                            if len(all_data) < 5:
                                print(f"  [調試] 方向字符串轉換: '{val}' -> {raw_value}")
                        else:
                            try:
                                raw_value = float(val)
                                if len(all_data) < 5:
                                    print(f"  [調試] 單一值轉換: {val} -> {raw_value}")
                            except (ValueError, TypeError) as e:
                                if len(all_data) < 5:
                                    print(f"  [調試] 轉換失敗: {val}, 錯誤: {e}")
                                raw_value = 0.0
                    else:
                        # 數據長度不是 1 或 3，可能是其他格式
                        if len(all_data) < 3:
                            print(f"\n[調試] 數據長度異常: {len(data)}, 數據內容: {data}")
                        continue
                else:
                    try:
                        if isinstance(data, (list, tuple)):
                            data = data[0] if len(data) > 0 else 0
                        raw_value = float(data)
                    except (ValueError, TypeError) as e:
                        if len(all_data) < 3:
                            print(f"\n⚠️ 無法轉換數據: {data}, 錯誤: {e}")
                        continue
                
                current_time = time.time()
                elapsed = current_time - phase_start_time
                
                # 記錄數據
                if raw_value is not None:
                    # 檢查是否為方向字符串
                    direction_str = None
                    if isinstance(data, (list, tuple)) and len(data) > 0:
                        if isinstance(data[0], str):
                            direction_str = data[0]
                    
                    data_point = {
                        'time': current_time,
                        'value': raw_value,
                        'phase': phases[phase_index][0],
                        'raw_data': data if isinstance(data, (list, tuple)) else [data],
                        'alpha': alpha_value,
                        'beta': beta_value,
                        'gamma': gamma_value,
                        'direction': direction_str
                    }
                    all_data.append(data_point)
                    current_session.append(data_point)
                    data_window.append(raw_value)
                    
                    # 計算移動平均（平滑顯示）
                    if len(data_window) > 0:
                        avg_value = statistics.mean(data_window)
                    else:
                        avg_value = raw_value
                    
                    # 顯示當前數據
                    phase_time_left = phases[phase_index][1] - elapsed
                    if alpha_value is not None and beta_value is not None and gamma_value is not None:
                        # 顯示 Gyroscope 的三個值：alpha, beta, gamma
                        print(f"\r[{phases[phase_index][0]:12s}] "
                              f"Alpha: {alpha_value:7.3f} | "
                              f"Beta: {beta_value:7.3f} | "
                              f"Gamma: {gamma_value:7.3f} | "
                              f"移動平均: {avg_value:7.3f} | "
                              f"剩餘: {phase_time_left:4.1f}s", end='', flush=True)
                    elif direction_str is not None:
                        # 顯示方向字符串和轉換後的值
                        print(f"\r[{phases[phase_index][0]:12s}] "
                              f"方向: {direction_str:8s} | "
                              f"轉換值: {raw_value:7.3f} | "
                              f"移動平均: {avg_value:7.3f} | "
                              f"剩餘: {phase_time_left:4.1f}s", end='', flush=True)
                    else:
                        print(f"\r[{phases[phase_index][0]:12s}] "
                              f"原始值: {raw_value:8.4f} | "
                              f"移動平均: {avg_value:8.4f} | "
                              f"剩餘時間: {phase_time_left:5.1f}s", end='', flush=True)
                
                # 檢查是否該進入下一階段
                if elapsed >= phases[phase_index][1]:
                    # 顯示階段統計
                    print_statistics(current_session, phases[phase_index][0])
                    current_session = []
                    
                    phase_index += 1
                    if phase_index >= len(phases):
                        print("\n\n✅ 測試完成！")
                        break
                    
                    phase_start_time = time.time()
                    print(f"\n\n階段 {phase_index + 1}/{len(phases)}: {phases[phase_index][0]}")
                    print("開始記錄數據...\n")
            
            time.sleep(0.05)  # 20Hz 採樣率
            
        except KeyboardInterrupt:
            print("\n\n⚠️ 測試中斷")
            break
        except Exception as e:
            import traceback
            print(f"\n⚠️ 錯誤: {e}")
            print(f"數據類型: {type(data)}, 數據內容: {data}")
            traceback.print_exc()
            time.sleep(1)

except KeyboardInterrupt:
    print("\n\n⚠️ 測試中斷")

# 顯示整體統計
print("\n" + "=" * 60)
print("📊 整體統計報告")
print("=" * 60)

if all_data:
    # 按階段分組
    phases_data = {}
    for point in all_data:
        phase = point['phase']
        if phase not in phases_data:
            phases_data[phase] = []
        phases_data[phase].append(point)
    
    # 顯示每個階段的統計
    for phase_name in phases_data.keys():
        print_statistics(phases_data[phase_name], phase_name)
    
    # 整體統計
    all_values = [float(d['value']) for d in all_data]
    print(f"\n整體統計（所有數據）：")
    print(f"  總數據點數: {len(all_values)}")
    print(f"  最小值: {min(all_values):.4f}")
    print(f"  最大值: {max(all_values):.4f}")
    print(f"  平均值: {statistics.mean(all_values):.4f}")
    print(f"  中位數: {statistics.median(all_values):.4f}")
    if len(all_values) > 1:
        print(f"  標準差: {statistics.stdev(all_values):.4f}")
    print(f"  範圍: {max(all_values) - min(all_values):.4f}")
    
    # 判斷數據類型
    print(f"\n📋 數據類型判斷：")
    # 檢查第一個數據點的原始格式
    if all_data and 'raw_data' in all_data[0]:
        raw_format = all_data[0]['raw_data']
        # 檢查是否為方向字符串
        if all_data[0].get('direction') is not None:
            print("  ⚠️ 這是 Gyroscope（陀螺儀）方向字符串數據")
            print("  💡 問題：IoTtalk 返回的是方向描述，而不是數值")
            print("  🔧 解決方案：")
            print("     1. 檢查 IoTtalk Canvas 上的連接")
            print("     2. 確保連接的是 Smartphone (Gyroscope) 的數值輸出（x1, x2, x3）")
            print("     3. 而不是方向描述輸出")
            # 統計各方向出現的頻率
            directions = [d.get('direction') for d in all_data if d.get('direction') is not None]
            if directions:
                from collections import Counter
                direction_counts = Counter(directions)
                print("  📊 方向統計（所有階段）：")
                for direction, count in direction_counts.items():
                    print(f"    {direction}: {count} 次")
        elif isinstance(raw_format, (list, tuple)) and len(raw_format) >= 3:
            print("  ✅ 這是 Gyroscope（陀螺儀）數據（[alpha, beta, gamma] 角速度）")
            print("  💡 建議：使用 Gyroscope 模式，使用 Gamma（繞 Y 軸，roll）控制左右")
            print(f"  📊 Gamma 範圍: {min(all_values):.3f} 到 {max(all_values):.3f}")
            if all_data[0].get('alpha') is not None:
                alpha_values = [d.get('alpha', 0) for d in all_data if d.get('alpha') is not None]
                beta_values = [d.get('beta', 0) for d in all_data if d.get('beta') is not None]
                gamma_values = [d.get('gamma', 0) for d in all_data if d.get('gamma') is not None]
                if alpha_values:
                    print(f"  📊 Alpha 範圍: {min(alpha_values):.3f} 到 {max(alpha_values):.3f}")
                if beta_values:
                    print(f"  📊 Beta 範圍: {min(beta_values):.3f} 到 {max(beta_values):.3f}")
                if gamma_values:
                    print(f"  📊 Gamma 範圍: {min(gamma_values):.3f} 到 {max(gamma_values):.3f}")
        elif isinstance(raw_format, (list, tuple)):
            print("  ✅ 這是列表格式數據")
            print(f"  📊 數據長度: {len(raw_format)}")
            if len(raw_format) > 0:
                print(f"  📊 第一個元素: {raw_format[0]}, 類型: {type(raw_format[0])}")
        else:
            print("  ✅ 這是單一數值數據")
    elif 0 <= min(all_values) <= 360 and 0 <= max(all_values) <= 360:
        print("  ✅ 這是指南針數據（角度 0-360）")
        print("  💡 建議：使用指南針模式")
    else:
        print("  ✅ 這是加速度計或其他單一數值數據")
        print("  💡 建議：使用加速度計模式")
    
    # 分析左右傾斜的數據範圍（特別針對 Gamma 值）
    right_phase_name = "向右傾斜到極限"
    left_phase_name = "向左傾斜到極限"
    center_phase_name = "保持水平（基準）"
    
    if right_phase_name in phases_data and left_phase_name in phases_data:
        right_values = [float(d['value']) for d in phases_data[right_phase_name]]
        left_values = [float(d['value']) for d in phases_data[left_phase_name]]
        center_values = []
        if center_phase_name in phases_data:
            center_values = [float(d['value']) for d in phases_data[center_phase_name]]
        
        print(f"\n" + "=" * 60)
        print(f"🎯 關鍵數值分析（用於 Game.py 設定）")
        print(f"=" * 60)
        
        # 計算極值
        right_max = max(right_values) if right_values else 0
        right_min = min(right_values) if right_values else 0
        right_avg = statistics.mean(right_values) if right_values else 0
        
        left_max = max(left_values) if left_values else 0
        left_min = min(left_values) if left_values else 0
        left_avg = statistics.mean(left_values) if left_values else 0
        
        center_avg = statistics.mean(center_values) if center_values else 0
        center_min = min(center_values) if center_values else 0
        center_max = max(center_values) if center_values else 0
        
        print(f"\n📊 Gamma 值統計：")
        print(f"  🎯 中間點（基準值）: {center_avg:.4f}")
        print(f"     範圍: {center_min:.4f} 到 {center_max:.4f}")
        print(f"\n  ➡️  極右（向右傾斜到極限）:")
        print(f"     最大值: {right_max:.4f}")
        print(f"     最小值: {right_min:.4f}")
        print(f"     平均值: {right_avg:.4f}")
        print(f"\n  ⬅️  極左（向左傾斜到極限）:")
        print(f"     最大值: {left_max:.4f}")
        print(f"     最小值: {left_min:.4f}")
        print(f"     平均值: {left_avg:.4f}")
        
        # 計算建議的參數
        print(f"\n💡 Game.py 建議設定：")
        print(f"  baseline = {center_avg:.4f}  # 中間點（基準值）")
        
        # 計算偏移範圍
        right_offset_max = right_max - center_avg
        right_offset_min = right_min - center_avg
        left_offset_max = left_max - center_avg
        left_offset_min = left_min - center_avg
        
        max_offset = max(abs(right_offset_max), abs(right_offset_min), 
                        abs(left_offset_max), abs(left_offset_min))
        
        if max_offset > 0:
            # 計算縮放因子，讓最大偏移映射到 10
            suggested_scale = 10.0 / max_offset
            print(f"  scale_factor = {suggested_scale:.4f}  # 縮放因子（約 {suggested_scale:.2f}）")
            print(f"  dead_zone = {max_offset * 0.1:.2f}  # 死區（建議為最大偏移的 10%）")
        
        print(f"\n  📝 控制邏輯：")
        print(f"     offset = gamma_value - {center_avg:.4f}")
        if right_avg > center_avg:
            print(f"     offset > 0 → 向右移動")
            print(f"     offset < 0 → 向左移動")
        else:
            print(f"     offset > 0 → 向左移動")
            print(f"     offset < 0 → 向右移動（可能需要反轉）")
        
        # 如果使用方向字符串，顯示各階段的方向統計
        if all_data and all_data[0].get('direction') is not None:
            right_directions = [d.get('direction') for d in phases_data[right_phase_name] if d.get('direction')]
            left_directions = [d.get('direction') for d in phases_data[left_phase_name] if d.get('direction')]
            if right_directions:
                from collections import Counter
                right_counts = Counter(right_directions)
                print(f"\n  📊 向右傾斜時的方向分布：")
                for direction, count in right_counts.items():
                    print(f"    {direction}: {count} 次")
            if left_directions:
                from collections import Counter
                left_counts = Counter(left_directions)
                print(f"\n  📊 向左傾斜時的方向分布：")
                for direction, count in left_counts.items():
                    print(f"    {direction}: {count} 次")
    elif "向右傾斜" in phases_data and "向左傾斜" in phases_data:
        # 舊版本兼容
        right_values = [float(d['value']) for d in phases_data["向右傾斜"]]
        left_values = [float(d['value']) for d in phases_data["向左傾斜"]]
        
        print(f"\n📐 傾斜方向分析：")
        print(f"  向右傾斜平均值: {statistics.mean(right_values):.4f}")
        print(f"  向左傾斜平均值: {statistics.mean(left_values):.4f}")
        
        if statistics.mean(right_values) > statistics.mean(left_values):
            print(f"  ✅ 向右傾斜的值 > 向左傾斜的值")
            print(f"  💡 如果方向相反，需要反轉邏輯")
        else:
            print(f"  ✅ 向右傾斜的值 < 向左傾斜的值")
            print(f"  💡 如果方向相反，需要反轉邏輯")

print("\n" + "=" * 60)
print("測試完成！請將上述統計信息提供給開發者以調整設定。")
print("=" * 60)

