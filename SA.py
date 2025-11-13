import random
import time

ServerURL = 'https://class.iottalk.tw'  # IoTtalk 伺服器網址
MQTT_broker = 'iot.iottalk.tw'  # MQTT Broker 位址，或 None = 不使用 MQTT
MQTT_port = 8883
MQTT_encryption = True
MQTT_User = 'iottalk'
MQTT_PW = 'iottalk2023'

device_model = 'Dummy_Device'
IDF_list = []  # 我們不需要 IDF，因為資料來自手機
ODF_list = ['Dummy_Control']  # 從這裡接收手機的加速度計數據
device_id = None  # if None, device_id = MAC address
device_name = None
exec_interval = 0.1  # ODF 拉取間隔（秒），越小越即時

def Dummy_Control(data:list):
    """
    接收手機 Smartphone (Acc-I) 傳來的加速度計數據
    data: 格式通常是 [x, y, z] 或單一數值
    """
    # 這裡的處理會在 Game.py 中透過 DAN.pull() 完成
    # 所以這個函數可以留空，或用來除錯
    if isinstance(data, (list, tuple)) and len(data) >= 1:
        print(f"收到手機數據: {data[0]:.2f}")
    else:
        print(f"收到手機數據: {data}")

def on_register(r):
    print(f'Device name: {r["d_name"]}')
    print('=' * 50)
    print('✅ Dummy_Device 註冊成功！')
    print(f'伺服器: {r["server"]}')
    print(f'裝置名稱: {r["d_name"]}')
    print('=' * 50)
