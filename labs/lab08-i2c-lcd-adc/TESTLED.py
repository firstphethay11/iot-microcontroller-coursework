from machine import Pin
from time import sleep

# 1. ตั้งค่าขา Pin 25 และ 26 ให้เป็นโหมด Output (ส่งไฟออก)
led_25 = Pin(25, Pin.OUT)
led_26 = Pin(26, Pin.OUT)

print("LED Test Started: Blinking Alternate...")

while True:
    # 2. สั่งเปิด LED 25 และปิด LED 26
    led_25.value(1)  # เปิด (High)
    led_26.value(0)  # ปิด (Low)
    print("LED 25: ON  | LED 26: OFF")
    sleep(0.5)       # รอ 0.5 วินาที
    
    # 3. สลับกัน: ปิด LED 25 และเปิด LED 26
    led_25.value(0)  # ปิด (Low)
    led_26.value(1)  # เปิด (High)
    print("LED 25: OFF | LED 26: ON")
    sleep(0.5)       # รอ 0.5 วินาที