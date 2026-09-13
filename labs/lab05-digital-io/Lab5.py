# ===============================================
#          โปรแกรมนับเลขตามโจทย์ (ปรับปรุง)
# ===============================================
from machine import Pin, SoftI2C
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

# ===============================================
#       ส่วนที่เพิ่มเข้ามาใหม่ตามโจทย์
# ==============================================

#เพิ่ม parameter `is_first_run` เข้าไปในฟังก์ชัน
def get_number_from_keypad(is_first_run):
    """
    ฟังก์ชันสำหรับรับค่าตัวเลข 0-99 ตามรูปแบบ * (ตัวเลข) #
    """
    lcd.clear()
    num_str = ""
    last_key = None
    
    #ตรวจสอบว่าเป็น "ครั้งแรก" หรือไม่
    if is_first_run:
        lcd.putstr("Press * to set")
        lcd.move_to(0, 1)
        lcd.putstr("Max count (0-99)")
        
        # 1. รอรับปุ่ม '*' เพื่อเริ่ม
        while True:
            key = scanKeypad()
            if key == '*':
                last_key = '*'
                break # ไปขั้นตอนต่อไป
            sleep(0.05)
            
    # ---------------------------------------------
    # (ถ้า is_first_run = False จะข้ามมาทำงานตรงนี้เลย)
    # ---------------------------------------------
    lcd.clear()
    lcd.putstr("Input (0-99):")
    lcd.move_to(0, 1)

    # 2. รับค่าตัวเลข (สูงสุด 2 หลัก) จนกว่าจะเจอปุ่ม '#'
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
                    return val # คืนค่ตัวเลขที่ถูกต้อง
                else:
                    lcd.clear()
                    lcd.putstr("Error: 0-99 Only")
                    sleep(2)
                    #ส่ง False กลับไป เพราะไม่ใช่ครั้งแรกแล้ว
                    return get_number_from_keypad(is_first_run=False) 
            
            elif key == '*':
                return None # คืนค่า None เพื่อบอกว่ายกเลิก

        elif key is None:
            last_key = None
            
        sleep(0.05)

# --- ลูปการทำงานหลัก (Main Loop) ---
is_first_run = True #สร้างตัวแปรสถานะ "ครั้งแรก"
while True:
    # 1. รับค่าตัวเลขสูงสุด
    #ส่งสถานะ `is_first_run` เข้าไป
    max_count = get_number_from_keypad(is_first_run=is_first_run)
    
    if max_count is not None:
        # ถ้าการรับค่าสำเร็จ (ไม่กดยกเลิก)
        # ให้ตั้งค่าว่า "ไม่ใช่ครั้งแรกแล้ว"
        is_first_run = False 
        
        # 2. แสดงผลตามโจทย์ "Input: (ค่าที่รับมา)"
        lcd.clear()
        lcd.putstr(f"Input: {max_count}")
        sleep(2)
        
        # 3. เริ่มโปรแกรมนับเลขวนซ้ำ
        key_check = None 
        while True:
            for i in range(max_count + 1):
                lcd.clear()
                lcd.putstr(f"Input: {max_count}")
                lcd.move_to(0, 1)
                lcd.putstr(f"Count: {i}  ")
                sleep(1)
                
                key_check = scanKeypad()
                if key_check == '*':
                    break # ออกจาก for loop
            
            if key_check == '*':
                break # ออกจาก while loop (กลับไปรอรับค่าใหม่)
    
    else:
        # กรณีที่ผู้ใช้กด '*' ตอนอยู่หน้า "Input" (เพื่อยกเลิก)
        # ให้วนกลับไปรอรับค่าใหม่ โดย `is_first_run` จะยังเป็นค่าเดิม
        # (ถ้าเป็นครั้งแรก ก็จะกลับไปหน้า "Press *", ถ้าไม่ใช่ ก็จะกลับไปหน้า "Input")
        pass