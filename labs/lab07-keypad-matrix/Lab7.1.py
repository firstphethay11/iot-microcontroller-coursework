import sys
from machine import Pin, SoftI2C, Timer
from time import sleep
from i2c_lcd import I2cLcd

# --- CONFIGURATION & INITIALIZATION ---
key_matrix = [
    ['1', '2', '3', 'A'],
    ['4', '5', '6', 'B'], 
    ['7', '8', '9', 'C'],
    ['*', '0', '#', 'D']
]
colPins = [14, 15, 32, 33]
rowPins = [4, 5, 12, 13]

rows = [Pin(pin_name, mode=Pin.OUT) for pin_name in rowPins]
cols = [Pin(pin_name, mode=Pin.IN, pull=Pin.PULL_DOWN) for pin_name in colPins]
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)

try:
    lcd = I2cLcd(i2c, i2c.scan()[0], 2, 16)
    lcd.clear()
    lcd.putstr("System Init...")
    sleep(1)
except IndexError:
    print("LCD I2C Address Not Found! Exiting.")
    sys.exit()

# --- GLOBAL STATE VARIABLES ---
global_seconds = 0
timer_running = False 

# --- TIMER SETUP ---
def timer_callback(timer):
    global global_seconds, timer_running
    if timer_running:
        global_seconds += 1

tim0 = Timer(0)
tim0.init(period=1000, callback=timer_callback)

# --- HELPER FUNCTIONS ---

def scanKeypad():
    for r in range(4):
        rows[r].value(1)
        for c in range(4):
            if cols[c].value() == 1:
                key = key_matrix[r][c]
                while cols[c].value() == 1:
                    sleep(0.01)
                rows[r].value(0)
                return key
        rows[r].value(0)
    return None

def format_time(total_seconds):
    total_seconds = total_seconds % 86400
    H = total_seconds // 3600
    M = (total_seconds % 3600) // 60
    S = total_seconds % 60
    return "{:02d}:{:02d}:{:02d}".format(H, M, S)

def show_main_lcd(status_text, time_str):
    """หน้าจอหลักสำหรับแสดงเวลาและสถานะ"""
    # ใช้ move_to เขียนทับ เพื่อลดการกระพริบ
    lcd.move_to(0, 0)
    lcd.putstr("Status: {:<7s}".format(status_text))
    lcd.move_to(0, 1)
    lcd.putstr("Time: {}".format(time_str))

def get_input_number(prompt_text, max_value):
    """ฟังก์ชันรับค่าตัวเลขตอนตั้งเวลาเริ่มต้น"""
    input_str = ""
    lcd.clear()
    lcd.putstr(prompt_text)
    lcd.move_to(0, 1)
    lcd.putstr("Value: ")
    
    while True:
        key = scanKeypad()
        if key:
            if key.isdigit():
                if len(input_str) < 2:
                    input_str += key
                    lcd.putstr(key)
            
            elif key == '*': 
                input_str = ""
                lcd.move_to(7, 1)
                lcd.putstr("  ")
                lcd.move_to(7, 1)
                
            elif key == '#':
                if input_str == "": val = 0
                else: val = int(input_str)
                
                if val <= max_value:
                    return val
                else:
                    lcd.move_to(0, 1)
                    lcd.putstr("Err: Max {:2d}   ".format(max_value))
                    sleep(1)
                    input_str = ""
                    lcd.move_to(0, 1)
                    lcd.putstr("Value:       ")
                    lcd.move_to(7, 1)
        sleep(0.05)

# --- MAIN LOOP ---

def main_loop():
    global timer_running, global_seconds
    
    # -------------------------------------------------
    # PHASE 1: ตั้งค่าเวลา (Set Time)
    # -------------------------------------------------
    lcd.clear()
    lcd.putstr("Set Clock Mode")
    sleep(1)
    
    set_hour = get_input_number("Set Hour (0-23)", 23)
    set_min  = get_input_number("Set Minute(0-59)", 59)
    set_sec  = get_input_number("Set Second(0-59)", 59)
    
    global_seconds = (set_hour * 3600) + (set_min * 60) + set_sec
    
    lcd.clear()
    lcd.putstr("Time Set OK!")
    sleep(1)

    # -------------------------------------------------
    # PHASE 2: ทำงานปกติ (Start/Stop Mode)
    # -------------------------------------------------
    input_cmd_str = ""
    program_state = "IDLE"
    last_display_time = -1
    force_update = True # ตัวแปรช่วยบังคับอัพเดทหน้าจอ
    
    while True:
        key = scanKeypad()
        
        # --- ส่วนจัดการการรับปุ่ม ---
        if key:
            # 1. ถ้าอยู่หน้าปกติ แล้วกด * -> เข้าหน้าป้อนคำสั่ง
            if program_state == "IDLE" and key == "*":
                program_state = "INPUT_CMD"
                input_cmd_str = "*"
                
                # ✅ เปลี่ยนหน้าจอไปเป็นหน้า Input
                lcd.clear()
                lcd.putstr("Input Command:")
                lcd.move_to(0, 1)
                lcd.putstr("*") 
            
            # 2. ถ้ากำลังป้อนคำสั่ง รับตัวเลข 0 หรือ 1
            elif program_state == "INPUT_CMD" and key in ['0', '1']:
                if len(input_cmd_str) < 2: # รับได้แค่ *X
                    input_cmd_str += key
                    lcd.putstr(key) # แสดงตัวเลขที่กด
            
            # 3. ถ้ากำลังป้อนคำสั่ง กด # -> ยืนยัน
            elif program_state == "INPUT_CMD" and key == "#":
                if len(input_cmd_str) == 2: # ต้องมี * และตัวเลขแล้ว (*X)
                    command = input_cmd_str[1]
                    if command == '1':
                        timer_running = True
                    elif command == '0':
                        timer_running = False
                
                # กลับสู่สถานะปกติ
                program_state = "IDLE"
                force_update = True # บังคับให้วาดหน้าจอหลักใหม่ทันที
                lcd.clear() # เคลียร์หน้า Input ทิ้ง
            
            # 4. กดปุ่มอื่นผิดๆ ระหว่างป้อน -> ยกเลิก
            elif program_state == "INPUT_CMD":
                program_state = "IDLE"
                force_update = True
                lcd.clear()

        # --- ส่วนอัพเดทหน้าจอ ---
        # ทำงานเฉพาะเมื่ออยู่ในหน้าหลัก (IDLE)
        if program_state == "IDLE":
            current_time_display = format_time(global_seconds)
            
            # อัพเดทถ้าเวลาเปลี่ยน หรือ มีการบังคับ (เช่น เพิ่งออกจากหน้า Input)
            if current_time_display != last_display_time or force_update:
                status_text = "Start" if timer_running else "Stop"
                show_main_lcd(status_text, current_time_display)
                
                last_display_time = current_time_display
                force_update = False # รีเซ็ตตัวบังคับ
        
        sleep(0.1)

# --- PROGRAM START ---
if __name__ == "__main__":
    main_loop()