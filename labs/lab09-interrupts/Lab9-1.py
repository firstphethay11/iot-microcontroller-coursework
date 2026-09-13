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
# LCD Setup
try:
    i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
    lcd = I2cLcd(i2c, 0x27, 2, 16)
except:
    lcd = None

# Keypad Setup
key_matrix = [['1','2','3','A'],
              ['4','5','6','B'],
              ['7','8','9','C'],
              ['*','0','#','D']]
colPins = [14, 15, 32, 33]; rowPins = [4, 5, 12, 13]
rows = [Pin(p, Pin.OUT) for p in rowPins]
cols = [Pin(p, Pin.IN, Pin.PULL_DOWN) for p in colPins]

# ตัวแปรควบคุมระบบ (Global Variable)
# ถ้าค่านี้เป็น False โปรแกรมทุกส่วนจะหยุดทำงาน
system_running = True 

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
# 3. Thread Function (งานจอ LCD + Keypad)
# =========================================

def task_lcd_system():
    global system_running
    
    # ตัวแปรภายใน Loop
    current_max = 0
    current_count = 1
    input_str = ""
    last_time = time.ticks_ms()

    if lcd: lcd.clear(); lcd.putstr("LCD Ready...")

    # วนลูปตราบใดที่ระบบยังทำงานอยู่
    while system_running:
        # --- A. เช็ค Keypad ---
        key = scan_keypad()
        if key:
            # 1. กด D เพื่อออกจากโปรแกรม
            if key == 'D':
                if lcd: lcd.clear(); lcd.putstr("Exiting...")
                system_running = False # สั่งปิดสวิตช์หลัก
                break 

            # 2. กด # เพื่อยืนยันค่า Max
            elif key == '#': 
                if input_str:
                    try:
                        current_max = int(input_str)
                        current_count = 1 # รีเซ็ตเลขเริ่มนับใหม่
                        if lcd: 
                            lcd.move_to(0, 1); lcd.putstr("Saved!          ")
                            time.sleep(0.5)
                            lcd.move_to(0, 1); lcd.putstr("                ")
                    except: pass
                    input_str = ""
            
            # 3. กด * เพื่อลบ
            elif key == '*': 
                input_str = ""
                if lcd: lcd.move_to(0, 1); lcd.putstr("Cleared         ")
            
            # 4. กดตัวเลข
            elif key.isdigit():
                input_str += key
                if lcd: lcd.move_to(0, 1); lcd.putstr(f"Set: {input_str}")

        # --- B. ส่วนนับเลข (ทำงานทุก 0.8 วินาที) ---
        if current_max > 0 and time.ticks_diff(time.ticks_ms(), last_time) > 800:
            if lcd:
                lcd.move_to(0, 0)
                lcd.putstr(f"Count: {current_count} / {current_max}   ")
            
            current_count += 1
            if current_count > current_max:
                current_count = 1 # วนกลับมา 1
            
            last_time = time.ticks_ms() # รีเซ็ตเวลา

        time.sleep(0.05) # พัก CPU

# =========================================
# 4. Main Program (งาน Monitor + Keyboard PC)
# =========================================

def main():
    global system_running
    print("--- System Started ---")
    print("1. Type Max number & Enter to set monitor counter.")
    print("2. Type 'exit' to stop program.")
    print("3. Press 'D' on Keypad to stop program.")
    
    # เริ่ม Thread LCD ให้ทำงานขนานไปเลย
    _thread.start_new_thread(task_lcd_system, ())
    
    # ตัวแปรภายใน Main Loop
    current_max = 0
    current_count = 1
    input_buf = ""
    last_time = time.ticks_ms()

    # ตั้งค่ารับคีย์บอร์ดแบบไม่บล็อก (Non-blocking)
    spoll = uselect.poll()
    spoll.register(sys.stdin, uselect.POLLIN)
    
    print("\n[PC] Enter Max: ", end="")

    # Main Loop
    while system_running:
        # --- A. เช็ค Keyboard PC ---
        if spoll.poll(0):
            char = sys.stdin.read(1)
            if char:
                # ถ้ากด Enter
                if char == '\n' or char == '\r':
                    # เช็คคำสั่ง exit
                    if input_buf.strip().lower() == 'exit':
                        print("\n[PC] Stopping System...")
                        system_running = False # สั่งปิดสวิตช์หลัก
                        break
                    
                    # แปลงค่าตัวเลข
                    try:
                        val = int(input_buf)
                        current_max = val
                        current_count = 1 # รีเซ็ตนับใหม่
                        print(f"\n[PC] Updated Max: {current_max}")
                    except:
                        if input_buf: print("\n[PC] Error: Number only")
                    
                    input_buf = ""
                    print("[PC] Enter Max: ", end="")
                else:
                    sys.stdout.write(char) # แสดงตัวที่พิมพ์
                    input_buf += char

        # --- B. ส่วนนับเลข (ทำงานทุก 1 วินาที) ---
        if current_max > 0 and time.ticks_diff(time.ticks_ms(), last_time) > 1000:
            print(f"[PC Running]: {current_count} / {current_max}")
            
            current_count += 1
            if current_count > current_max:
                current_count = 1 # วนกลับ
            
            last_time = time.ticks_ms()

        time.sleep(0.05) # พัก CPU

    print("--- Program Ended ---")

# รันโปรแกรม
try:
    main()
except KeyboardInterrupt:
    print("Stopped by Ctrl+C")
    system_running = False