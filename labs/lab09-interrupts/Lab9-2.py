import _thread
import machine
from machine import Pin, SoftI2C
import time
import sys
import uselect
from i2c_lcd import I2cLcd

# =========================================
# 1. Hardware Setup
# =========================================
# LCD
try:
    i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
    lcd = I2cLcd(i2c, 0x27, 2, 16)
except:
    lcd = None

# Keypad
key_matrix = [['1','2','3','A'],
              ['4','5','6','B'],
              ['7','8','9','C'],
              ['*','0','#','D']]
colPins = [14, 15, 32, 33]; rowPins = [4, 5, 12, 13]
rows = [Pin(p, Pin.OUT) for p in rowPins]
cols = [Pin(p, Pin.IN, Pin.PULL_DOWN) for p in colPins]

# =========================================
# 2. Helper Functions
# =========================================
def scan_keypad():
    for r in range(4):
        rows[r].value(1)
        for c in range(4):
            if cols[c].value() == 1:
                key = key_matrix[r][c]
                while cols[c].value() == 1: pass 
                rows[r].value(0)
                return key
        rows[r].value(0)
    return None

# =========================================
# 3. Thread Function (งานแยก - LCD System)
# =========================================

def task_lcd_system():
    """Loop ของงาน LCD: เช็คปุ่มตลอดเวลา + นับเลขตามเวลา"""
    current_max = 0
    current_count = 1
    input_str = ""
    last_time = time.ticks_ms() # ตัวจับเวลา

    if lcd: lcd.clear(); lcd.putstr("LCD Ready...")

    while True:
        # --- 1. เช็ค Keypad (ทำงานเร็ว) ---
        key = scan_keypad()
        if key:
            if key == '#': # ตกลง
                if input_str:
                    try:
                        current_max = int(input_str)
                        current_count = 1 # รีเซ็ตเริ่ม 1 ใหม่
                        if lcd: 
                            lcd.move_to(0, 1); lcd.putstr("Saved!          ")
                            time.sleep(0.5)
                            lcd.move_to(0, 1); lcd.putstr("                ")
                    except: pass
                    input_str = ""
            elif key == '*': # ลบ
                input_str = ""
                if lcd: lcd.move_to(0, 1); lcd.putstr("Cleared         ")
            elif key.isdigit():
                input_str += key
                if lcd: lcd.move_to(0, 1); lcd.putstr(f"Set: {input_str}")

        # --- 2. เช็คเวลาเพื่อนับเลข (ทำงานทุก 0.8 วิ) ---
        if current_max > 0 and time.ticks_diff(time.ticks_ms(), last_time) > 800:
            if lcd:
                lcd.move_to(0, 0)
                lcd.putstr(f"Count: {current_count} / {current_max}   ")
            
            current_count += 1
            if current_count > current_max:
                current_count = 1 # วนลูปกลับมา 1
            
            last_time = time.ticks_ms() # รีเซ็ตเวลา

        # พักสั้นๆ เพื่อให้ CPU ไม่ทำงานหนักเกินไป
        time.sleep(0.05)

# =========================================
# 4. Main Program (งานหลัก - Monitor System)
# =========================================

def main():
    print("--- System Started (Thread Loop Mode) ---")
    print("[PC] Type Max & Enter to update.")
    
    # 1. ปล่อย Thread LCD ให้ทำงานขนาน
    _thread.start_new_thread(task_lcd_system, ())
    
    # 2. ตัวแปรสำหรับ Main Loop
    current_max = 0
    current_count = 1
    input_buf = ""
    last_time = time.ticks_ms()

    # เตรียมตัวรับค่าแบบ Non-blocking (ไม่ใช้ input() ธรรมดา)
    spoll = uselect.poll()
    spoll.register(sys.stdin, uselect.POLLIN)

    # 3. Main Loop (เช็คคีย์บอร์ด + นับเลข)
    while True:
        # --- A. เช็ค Keyboard PC (Non-blocking) ---
        if spoll.poll(0):
            char = sys.stdin.read(1)
            if char:
                if char == '\n' or char == '\r': # กด Enter
                    try:
                        val = int(input_buf)
                        current_max = val
                        current_count = 1 # รีเซ็ตเริ่ม 1 ใหม่
                        print(f"\n[PC] Updated Max: {current_max}")
                    except:
                        print("\n[PC] Error")
                    input_buf = ""
                    print("[PC] New Max: ", end="")
                else:
                    sys.stdout.write(char) # แสดงตัวที่พิมพ์
                    input_buf += char

        # --- B. เช็คเวลาเพื่อนับเลข (ทุก 1 วินาที) ---
        if current_max > 0 and time.ticks_diff(time.ticks_ms(), last_time) > 1000:
            print(f"[PC Running]: {current_count} / {current_max}")
            
            current_count += 1
            if current_count > current_max:
                current_count = 1 # วนลูป
            
            last_time = time.ticks_ms()

        # พักสั้นๆ
        time.sleep(0.05)

# รันโปรแกรม
try:
    main()
except KeyboardInterrupt:
    print("Stopped")