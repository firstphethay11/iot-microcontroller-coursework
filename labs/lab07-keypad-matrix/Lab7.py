import sys
from machine import Pin, I2C, SoftI2C, reset
from time import sleep, ticks_ms, ticks_diff
from i2c_lcd import I2cLcd
from lcd_api import LcdApi

# --- CONFIGURATION ---
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
except:
    sys.exit()

# --- GLOBAL VARIABLES ---
current_count = 0
max_limit = 0
last_interrupt_time = 0
LCD_UPDATE_FLAG = True

# --- HARDWARE FUNCTIONS ---
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
    global current_count, max_limit, last_interrupt_time, LCD_UPDATE_FLAG
    new_time = ticks_ms()
    if ticks_diff(new_time, last_interrupt_time) > DEBOUNCE_MS:
        if current_count < max_limit:
            current_count += 1
        else:
            current_count = 0 
        LCD_UPDATE_FLAG = True
        last_interrupt_time = new_time

pin_sw1.irq(trigger=Pin.IRQ_FALLING, handler=sw1_counter_isr)

# --- 1. ฟังก์ชันรับค่า (โซนอันตราย: มีระเบิดเวลา 5 วินาที) ---
def get_input_with_timeout():
    lcd.clear()
    lcd.putstr("Input Max: ")
    lcd.move_to(11, 0)
    
    input_str = ""
    
    # ✅ เริ่มจับเวลา 5 วินาทีทันทีที่เข้าฟังก์ชันนี้
    last_action_time = ticks_ms()
    
    print("Enter Input Mode -> 5s Timer Started")

    while True:
        current_time = ticks_ms()
        
        # 🔥 เช็คเวลา: ถ้าผ่านไป 5000ms (5 วินาที) โดยไม่ได้จบด้วย #
        if ticks_diff(current_time, last_action_time) > 5000:
            lcd.clear()
            lcd.putstr("Timeout 5s!")
            lcd.move_to(0, 1)
            lcd.putstr("Rebooting...")
            sleep(1)
            reset() # ⚠️ บังคับรีบูตบอร์ดทันที
            
        key = scanKeypad()
        
        if key:
            # ✅ มีการกดปุ่ม -> ต่อเวลาให้ 5 วินาที
            last_action_time = ticks_ms() 
            
            if key.isdigit() and len(input_str) < 2:
                input_str += key
                lcd.putstr(key)
                
            elif key == "*" : # ลบค่า
                input_str = ""
                lcd.move_to(11, 0)
                lcd.putstr("  ")
                lcd.move_to(11, 0)
                
            elif key == "#" and input_str != "":
                # ✅ กด # สำเร็จ -> ส่งค่ากลับไป (รอดตาย!)
                return int(input_str)
                
        sleep(0.05)

# --- 2. ฟังก์ชันนับเลข (โซนปลอดภัย: ทำงานยาว จนกว่าจะกด *) ---
def run_counter_loop(limit_val):
    global current_count, max_limit, LCD_UPDATE_FLAG
    
    # ตั้งค่าเริ่มต้น
    max_limit = limit_val
    current_count = 0
    LCD_UPDATE_FLAG = True
    
    print("Enter Counter Mode (Safe)")
    
    while True:
        # อัปเดตหน้าจอ
        if LCD_UPDATE_FLAG:
            lcd.move_to(0, 0)
            lcd.putstr("Input Max: {:<2d} ".format(max_limit))
            lcd.move_to(0, 1)
            lcd.putstr("Count: {:<2d} ".format(current_count))
            LCD_UPDATE_FLAG = False
            
        # เช็คปุ่ม * เพื่อออก
        key = scanKeypad()
        if key == "*":
            print("Exit Counter Mode -> Go to Input")
            return # จบฟังก์ชันนี้ กลับไปที่ main เพื่อเรียก get_input ใหม่
            
        sleep(0.1)

# --- MAIN PROGRAM FLOW ---
def main():
    # 1. หน้าแรก: รอจนกว่าจะกด * (ไม่มีจับเวลา)
    lcd.clear()
    lcd.putstr("Press * to set")
    lcd.move_to(0, 1)
    lcd.putstr("Max count (0-99)")
    
    while True:
        key = scanKeypad()
        if key == "*":
            break # ออกไปสู่ลูปหลัก
        sleep(0.1)
        
    # 2. ลูปหลัก: รับค่า -> นับ -> รับค่า -> นับ ...
    while True:
        # เรียกฟังก์ชันรับค่า (มีระเบิดเวลา 5 วิ ในตัว)
        new_max = get_input_with_timeout()
        
        # ถ้าผ่านด่านมาได้ (กด # ทัน) ก็จะมานับเลข
        run_counter_loop(new_max)
        
        # ถ้า run_counter_loop จบ (เพราะกด *) 
        # มันจะวนลูปกลับไปบรรทัดบนเพื่อเรียก get_input ใหม่ (เริ่มจับเวลาใหม่)

if __name__ == "__main__":
    main()