from machine import Pin, DAC, SoftI2C
from lcd_api import LcdApi
from i2c_lcd import I2cLcd
from time import sleep

# --- การตั้งค่า Hardware (เหมือนเดิม) ---
I2C_ADDR = 0x27
totalRows = 2
totalColumns = 16
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=10000)
lcd = I2cLcd(i2c, I2C_ADDR, totalRows, totalColumns)

keyMatrix = [[ "1", "2", "3", "A"],
            [ "4", "5", "6", "B"],
            [ "7", "8", "9", "C"],
            ["*",  "0", "#", "D"]]

colPins = [14,15,32,33]
rowPins = [4,5,12,13]
row = [Pin(pin_name, mode=Pin.OUT) for pin_name in rowPins] 
column = [Pin(pin_name, mode=Pin.IN, pull=Pin.PULL_DOWN) for pin_name in colPins]

# --- แก้ไขฟังก์ชัน scanKeypad ---
# (เอา global key ออก และเพิ่ม return None)
def scanKeypad():
    for rowKey in range(4):
        row[rowKey].value(1)
        for colKey in range(4):
            if column[colKey].value() == 1:
                key = keyMatrix[rowKey][colKey]
                row[rowKey].value(0)
                return key  # คืนค่าปุ่มที่กด
        row[rowKey].value(0)
    return None # คืนค่า None ถ้าไม่มีการกด

# --- นี่คือส่วนหลักที่แก้ไข ---
lcd.clear()
lcd.putstr("Press a key:")
last_key_pressed = None  # ตัวแปรเก็บค่าปุ่มล่าสุด

while True:
    key = scanKeypad() # สแกนปุ่ม
    
    # 1. เมื่อมีการกดปุ่มใหม่ (และไม่ใช่ปุ่มเดิมที่กดค้าง)
    if key is not None and key != last_key_pressed:
        print(f"Key pressed: {key}") # (สำหรับดูใน Shell)
        
        # ส่งค่า Key ที่กด ออกทาง I2C ไปยังจอ LCD
        lcd.move_to(0, 1) # ไปยังแถวที่สอง
        lcd.putstr(f"You pressed: {key} ") # แสดงผล และเว้นวรรคเพื่อลบตัวเก่า
        
        last_key_pressed = key # อัปเดตปุ่มล่าสุด
    
    # 2. เมื่อมีการปล่อยปุ่ม
    elif key is None and last_key_pressed is not None:
        last_key_pressed = None # รีเซ็ตค่าปุ่มล่าสุด
    
    sleep(0.05) # หน่วงเวลาเล็กน้อยเพื่อลดภาระ CPU