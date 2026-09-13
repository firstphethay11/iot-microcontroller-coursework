import sys
from machine import Pin, I2C, SoftI2C
from time import sleep, ticks_ms, ticks_diff
from i2c_lcd import I2cLcd
from lcd_api import LcdApi

# --- CONFIGURATION & INITIALIZATION ---
key_matrix = [
    ['1', '2', '3', 'A'], ['4', '5', '6', 'B'], 
    ['7', '8', '9', 'C'], ['*', '0', '#', 'D']
]
colPins = [14, 15, 32, 33]
rowPins = [4, 5, 12, 13]
DEBOUNCE_MS = 200

rows = [Pin(pin_name, mode=Pin.OUT) for pin_name in rowPins]
cols = [Pin(pin_name, mode=Pin.IN, pull=Pin.PULL_DOWN) for pin_name in colPins]
pin_sw1 = Pin(2, mode=Pin.IN, pull=Pin.PULL_UP)
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)

try:
    lcd = I2cLcd(i2c, i2c.scan()[0], 2, 16)
    lcd.clear()
    lcd.putstr("System OK")
    sleep(1)
except IndexError:
    print("LCD I2C Address Not Found! Exiting.")
    sys.exit()

# --- GLOBAL STATE VARIABLES ---
current_count = 0
max_limit = 0
last_interrupt_time = 0
LCD_UPDATE_FLAG = True
input_str = "" 
program_state = "INIT_SETUP" 

# --- HELPER FUNCTIONS ---

def show_lcd(max_limit, current_count):
    """แสดงค่าปัจจุบันและค่า Max Limit บน LCD."""
    lcd.move_to(0, 0)
    lcd.putstr("Input Max: {:<2d} ".format(max_limit)) 
    lcd.move_to(0, 1)
    lcd.putstr("Count: {:<2d} ".format(current_count))

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

def sw1_counter_isr(pin):
    """ฟังก์ชัน Interrupt: นับเมื่อปุ่ม SW1 ถูกกด"""
    global current_count, max_limit, last_interrupt_time, LCD_UPDATE_FLAG
    new_time = ticks_ms()
    
    # ป้องกันการกดซ้ำ (Debounce)
    if ticks_diff(new_time, last_interrupt_time) > DEBOUNCE_MS:
        # แก้ไขตรงนี้: ให้วนลูปกลับไป 0 เมื่อถึง Max
        if current_count < max_limit:
            current_count += 1
        else:
            current_count = 0 # วนกลับไป 0
            
        LCD_UPDATE_FLAG = True
        last_interrupt_time = new_time

pin_sw1.irq(trigger=Pin.IRQ_FALLING, handler=sw1_counter_isr)

# --- MAIN LOOP ---

def main_loop():
    global max_limit, current_count, LCD_UPDATE_FLAG, program_state, input_str
    
    # หน้าจอเริ่มต้น
    lcd.clear()
    lcd.putstr("Press * to set")
    lcd.move_to(0, 1)
    lcd.putstr("Max count (0-99)")
    
    while True: 
        key = scanKeypad()
        
        # 1. ตรวจสอบสถานะ INIT_SETUP (ตั้งค่าครั้งแรก)
        if program_state == "INIT_SETUP":
            if key == "*":
                program_state = "SET_MAX"
                input_str = ""
                lcd.clear()
                lcd.putstr("Input Max: ")
                lcd.move_to(11, 0)
                
        # 2. ตรวจสอบสถานะ SET_MAX (กำลังรับค่า)
        elif program_state == "SET_MAX":
            if key and key.isdigit() and len(input_str) < 2:
                input_str += key
                lcd.putstr(key)
                
            elif key == "#" and input_str != "":
                new_max = int(input_str)
                max_limit = max(0, min(new_max, 99))
                current_count = 0
                LCD_UPDATE_FLAG = True
                program_state = "COUNTING" 
                
            elif key == "*":
                input_str = ""
                lcd.move_to(11, 0)
                lcd.putstr("  ")
                lcd.move_to(11, 0)
                
        # 3. ตรวจสอบสถานะ COUNTING (นับปกติ)
        elif program_state == "COUNTING":
            if LCD_UPDATE_FLAG:
                show_lcd(max_limit, current_count)
                LCD_UPDATE_FLAG = False
                
            if key == "*":
                program_state = "SET_MAX"
                input_str = ""
                lcd.clear()
                lcd.putstr("Input Max: ")
                lcd.move_to(11, 0)
                
        sleep(0.1)

# --- PROGRAM START ---
if __name__ == "__main__":
    main_loop()
