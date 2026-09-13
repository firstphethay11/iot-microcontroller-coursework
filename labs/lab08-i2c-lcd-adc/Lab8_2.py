import machine
import esp32
import network # ต้องเพิ่ม import network เพื่อปิด WiFi สำหรับ Touch Sensor
from machine import Pin, SoftI2C, TouchPad
from time import sleep
from i2c_lcd import I2cLcd

# =========================================
# 0. ปิด WiFi (เพื่อแก้ปัญหา TouchPad resource conflict)
# =========================================
try:
    wifi = network.WLAN(network.STA_IF)
    wifi.active(False)
    ap = network.WLAN(network.AP_IF)
    ap.active(False)
except:
    pass

# =========================================
# 1. ตั้งค่า Hardware (Keypad, LCD, Touch)
# =========================================

# --- LCD Setup ---
I2C_ADDR = 0x27
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
try:
    lcd = I2cLcd(i2c, I2C_ADDR, 2, 16)
except:
    print("LCD Error")

# --- Keypad Setup ---
key_matrix = [
    ['1', '2', '3', 'A'],
    ['4', '5', '6', 'B'],
    ['7', '8', '9', 'C'],
    ['*', '0', '#', 'D']
]
colPins = [14,15,32,33]
rowPins = [4,5,12,13] 
# Pin 27 ถูกใช้เป็น Touch Pad และไม่ได้ชนกับ Keypad ใน Setup นี้
TOUCH_PIN_NUM = 27 

rows = [Pin(p, Pin.OUT) for p in rowPins]
cols = [Pin(p, Pin.IN, Pin.PULL_DOWN) for p in colPins]

# --- Touch Pad Setup (สำหรับปลุก) ---
# **ข้อสังเกต:** การสร้าง Object tp = TouchPad(Pin(TOUCH_PIN_NUM)) และ esp32.wake_on_touch(True) 
# ใน Global scope อาจทำให้เกิดปัญหาได้หลังการตื่นจาก Deep Sleep
# แต่ผมจะคงไว้ตามโค้ดต้นฉบับของคุณก่อน และจะไปสร้างใหม่ก่อน Deep Sleep ในส่วนล่างเพื่อให้มั่นใจ
tp = TouchPad(Pin(TOUCH_PIN_NUM)) 
tp.config(300) 
esp32.wake_on_touch(True) 

# =========================================
# 2. ฟังก์ชันต่างๆ
# =========================================

def scanKeypad():
    # (ฟังก์ชัน Keypad เหมือนเดิม)
    for r in range(4):
        rows[r].value(1)
        for c in range(4):
            if cols[c].value() == 1:
                key = key_matrix[r][c]
                while cols[c].value() == 1: sleep(0.01)
                rows[r].value(0)
                return key
        rows[r].value(0)
    return None

def get_input_number():
    """รับค่าตัวเลขจาก Keypad (0-99)"""
    # (ฟังก์ชัน Input Number เหมือนเดิม)
    lcd.clear()
    lcd.putstr("Input Max (0-99):")
    lcd.move_to(0, 1)
    
    input_str = ""
    while True:
        key = scanKeypad()
        if key:
            if key.isdigit() and len(input_str) < 2:
                input_str += key
                lcd.putstr(key)
            elif key == '*' : # ลบ
                input_str = ""
                lcd.move_to(0, 1)
                lcd.putstr("                ")
                lcd.move_to(0, 1)
            elif key == '#' and input_str != "": # ตกลง
                return int(input_str)
        sleep(0.1)

# =========================================
# 3. Main Program Loop
# =========================================

# ตรวจสอบว่าตื่นมาจาก Deep Sleep หรือเปล่า
if machine.reset_cause() == machine.DEEPSLEEP_RESET:
    print("Woke up from Deep Sleep!")
    lcd.clear()
    lcd.putstr("Woke up!")
    sleep(1)
else:
    print("Power On / Hard Reset")
    lcd.clear()
    lcd.putstr("System Start")
    sleep(1)

# --- ส่วนที่เพิ่ม: รอผู้ใช้กด * เพื่อเริ่ม ---
lcd.clear()
lcd.putstr("Press * to START")
lcd.move_to(0, 1)
lcd.putstr("or Wait for Sleep")

while True:
    key = scanKeypad()
    if key == '*':
        print("Starting program...")
        break
    sleep(0.1)

# 1. รับค่า Max Count
max_count = get_input_number()

# 2. เริ่มนับเลข (แสดงผล)
lcd.clear()
lcd.putstr("Input: {}".format(max_count))

for i in range(max_count + 1):
    lcd.move_to(0, 1)
    lcd.putstr("Count: {:<2}".format(i))
    print(f"Count: {i}")
    sleep(1) # นับทีละ 1 วินาที

# 3. นับเสร็จ -> เตรียมหลับ
lcd.clear()
lcd.putstr("Count Finished!")
lcd.move_to(0, 1)
lcd.putstr("Sleep in 3s...")
sleep(3)

# เคลียร์หน้าจอก่อนหลับ
lcd.clear()
lcd.putstr("Deep Sleep Zzz...")
sleep(1) 
lcd.backlight_off() # ปิดไฟจอ (ถ้าทำได้)

# 4. เข้าสู่โหมด Deep Sleep
print("Entering Deep Sleep. Touch P{} to wake up.".format(TOUCH_PIN_NUM))
# --- ต้องตั้งค่า Touch ใหม่ก่อนนอนอีกครั้งเพื่อให้แน่ใจว่าทำงานได้ ---
try:
    tp_final = TouchPad(Pin(TOUCH_PIN_NUM))
    tp_final.config(300) 
    esp32.wake_on_touch(True)
    print("Touch Wakeup Configured.")
except Exception as e:
    print(f"Error setting Touch Wakeup: {e}")

machine.deepsleep()