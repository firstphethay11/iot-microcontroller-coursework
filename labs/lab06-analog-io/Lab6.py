# ===============================================
#          โปรแกรมนับคนผ่านประตู (แก้ไขใหม่)
# ===============================================
from machine import Pin, SoftI2C
from lcd_api import LcdApi
from i2c_lcd import I2cLcd
from time import sleep

# --- การตั้งค่า Hardware ---
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

# เพิ่มเซ็นเซอร์ (SW1) ที่ขา D2 (GPIO 2)
sensor_pin = Pin(2, Pin.IN, Pin.PULL_UP)

# --- ฟังก์ชัน scanKeypad (เหมือนเดิม) ---
def scanKeypad():
    for rowKey in range(4):
        row[rowKey].value(1)
        for colKey in range(4):
            if column[colKey].value() == 1:
                key = keyMatrix[rowKey][colKey]
                row[rowKey].value(0)
                return key
        row[rowKey].value(0)
    return None

# --- ฟังก์ชัน get_number_from_keypad (เหมือนเดิม) ---
def get_number_from_keypad(is_first_run):
    lcd.clear()
    num_str = ""
    last_key = None
    
    if is_first_run:
        lcd.putstr("Press * to set")
        lcd.move_to(0, 1)
        lcd.putstr("Max count (0-99)")
        while True:
            key = scanKeypad()
            if key == '*':
                last_key = '*'
                break
            sleep(0.05)
            
    lcd.clear()
    lcd.putstr("Input Max: ") # แก้ไขข้อความให้สั้นลง
    lcd.move_to(0, 1)

    while True:
        key = scanKeypad()
        if key is not None and key != last_key:
            last_key = key
            if key.isdigit() and len(num_str) < 2:
                num_str += key
                lcd.putstr(key)
            elif key == '#' and num_str:
                val = int(num_str)
                if 0 <= val <= 99:
                    return val
                else:
                    lcd.clear()
                    lcd.putstr("Error: 0-99 Only")
                    sleep(2)
                    return get_number_from_keypad(is_first_run=False) 
            elif key == '*':
                return None
        elif key is None:
            last_key = None
        sleep(0.05)

# --- ลูปการทำงานหลัก (Main Loop) ---
is_first_run = True 
while True:
    # 1. รับค่าตัวเลขสูงสุด
    max_count = get_number_from_keypad(is_first_run=is_first_run)
    
    if max_count is not None:
        is_first_run = False 
        
        # 2. แสดงผลตามโจทย์ "Input Max: (ค่าที่รับมา)"
        lcd.clear()
        lcd.putstr(f"Input Max: {max_count}")
        sleep(2)
        
        # 3. เริ่ม 