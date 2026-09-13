import machine
import esp32
import network
from machine import Pin, SoftI2C, RTC
from time import sleep
from i2c_lcd import I2cLcd

# =========================================
# 1. Hardware Setup
# =========================================
try:
    wifi = network.WLAN(network.STA_IF); wifi.active(False)
    ap = network.WLAN(network.AP_IF); ap.active(False)
except: pass

try:
    i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
    lcd = I2cLcd(i2c, 0x27, 2, 16)
except:
    lcd = None

# SW1 (Pin 2)
sensor_pin = Pin(2, Pin.IN, Pin.PULL_UP)

# Keypad
key_matrix = [['1','2','3','A'],
              ['4','5','6','B'],
              ['7','8','9','C'],
              ['*','0','#','D']]
colPins = [14, 15, 32, 33]; rowPins = [4, 5, 12, 13]
rows = [Pin(p, Pin.OUT) for p in rowPins]
cols = [Pin(p, Pin.IN, Pin.PULL_DOWN) for p in colPins]

rtc = RTC()

# =========================================
# 2. ฟังก์ชันช่วย
# =========================================

def scanKeypad():
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

def go_sleep():
    """ฟังก์ชันสั่งหลับลึก"""
    if lcd: lcd.backlight_off()
    print("Going to Sleep...")
    esp32.wake_on_ext0(pin=sensor_pin, level=esp32.WAKEUP_ALL_LOW)
    sleep(0.1)
    machine.deepsleep()

def get_max_input():
    """รับค่าตัวเลข"""
    input_str = ""
    lcd.clear(); lcd.putstr("Input Max: "); lcd.move_to(0, 1)
    
    while True:
        key = scanKeypad()
        if key:
            if key.isdigit() and len(input_str) < 2:
                input_str += key
                lcd.putstr(key)
            elif key == '*': # ลบ
                input_str = ""
                lcd.move_to(0, 1); lcd.putstr("                "); lcd.move_to(0, 1)
            elif key == '#' and input_str != "": # ตกลง
                lcd.clear(); lcd.putstr("Saved!"); sleep(1)
                return int(input_str)
        sleep(0.1)

# =========================================
# 3. Main Logic
# =========================================

def main():
    if lcd: lcd.backlight_on()
    
    # อ่านค่าความจำ RTC
    try:
        data = rtc.memory().decode()
    except:
        data = ""

    # ----------------------------------------------------------------
    # CASE 1: โหมดรอใส่ค่า (ตื่นมาเพราะกด SW1 หลังกด *)
    # ----------------------------------------------------------------
    if data == "WAIT_FOR_INPUT":
        print("Mode: Input Max")
        
        # รับค่า Input
        max_val = get_max_input()
        
        # บันทึกค่าเริ่มต้นนับ (Max, 0)
        rtc.memory(f"{max_val},0")
        
        # หลับต่อ (รอ SW1 มากดเพื่อเริ่มนับ 1)
        lcd.clear(); lcd.putstr("Ready to Count"); lcd.move_to(0,1); lcd.putstr("Sleep.. Wait SW1")
        sleep(2)
        go_sleep()

    # ----------------------------------------------------------------
    # CASE 2: โหมดนับ (ตื่นมาเพราะกด SW1 เพื่อนับ)
    # ----------------------------------------------------------------
    elif "," in data: # เช็คว่ามีเครื่องหมายจุลภาคไหม (เช่น "10,0")
        print("Mode: Counting")
        try:
            max_val, current_val = map(int, data.split(","))
        except:
            rtc.memory(""); machine.reset(); return

        current_val += 1
        
        lcd.clear(); lcd.putstr(f"Count: {current_val} / {max_val}")
        print(f"Count: {current_val}/{max_val}")

        if current_val < max_val:
            # ยังไม่ครบ -> จำค่าใหม่ -> หลับ
            rtc.memory(f"{max_val},{current_val}")
            sleep(1.5)
            go_sleep()
        else:
            # ครบแล้ว -> โชว์ -> ล้างค่า -> หลับ
            lcd.move_to(0, 1); lcd.putstr("Complete!")
            rtc.memory("") # ล้างค่าทิ้งเพื่อให้กลับไปหน้าแรก
            sleep(3)
            go_sleep() # หลับยาว พอกด SW1 ใหม่จะไปเข้า CASE 3

    # ----------------------------------------------------------------
    # CASE 3: เริ่มต้นใหม่ (กด Reset หรือ เพิ่งเสียบปลั๊ก หรือ วนลูปครบแล้ว)
    # ----------------------------------------------------------------
    else: 
        print("Mode: Press *")
        lcd.clear(); lcd.putstr("Press * to Set")
        
        # รอจนกว่าจะกด *
        while True:
            if scanKeypad() == '*':
                break
            sleep(0.1)
            
        # พอกด * แล้ว -> จำสถานะว่า "รอบหน้าตื่นมาขอ Input นะ" -> แล้วหลับ
        lcd.clear(); lcd.putstr("Setup Mode...")
        rtc.memory("WAIT_FOR_INPUT") 
        sleep(1)
        go_sleep()

if __name__ == "__main__":
    main()
