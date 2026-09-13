from machine import Pin, SoftI2C
import machine
from time import sleep, sleep_ms, ticks_ms, ticks_diff
from ds3231 import DS3231
from i2c_lcd import I2cLcd
import os
import json

# ================= 1. SETUP =================
try:
    i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
    ds = DS3231(i2c)
    lcd = I2cLcd(i2c, 0x27, 2, 16)
except:
    print("I2C Error")

DEV = Pin(25, Pin.OUT)
DEV.value(1) 
device_on = False

# Global Vars
timer_enable = False
start_time = (18, 0, 0)
stop_time  = (6, 0, 0)
last_check_time = 0

key_matrix = [
    ['1','2','3','A'],
    ['4','5','6','B'],
    ['7','8','9','C'],
    ['*','0','#','D']
]
rows = [Pin(p, Pin.OUT) for p in [4, 5, 12, 13]]
cols = [Pin(p, Pin.IN, Pin.PULL_DOWN) for p in [14, 15, 32, 33]]

# ================= 2. LOGGING FUNCTION =================

def clear_log_file():
    """ ล้างไฟล์ log.txt ให้ว่างเปล่า (ใช้ตอนเริ่มระบบ) """
    try:
        with open('log.txt', 'w') as f:
            f.write("--- NEW SESSION STARTED ---\n")
        print("Log File Cleared!")
    except: pass

def write_log(message):
    """ บันทึกข้อความต่อท้ายไฟล์ (Append) """
    try:
        t = ds.datetime()
        timestamp = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            t[0], t[1], t[2], t[4], t[5], t[6]
        )
        log_line = f"{timestamp} -> {message}\n"
        print(f"Log: {log_line.strip()}") 
        
        with open('log.txt', 'a') as f:
            f.write(log_line)
    except Exception as e:
        print("Log Error:", e)

# ================= 3. CORE LOGIC =================

def scan_keypad():
    for r in range(4):
        rows[r].value(1)
        for c in range(4):
            if cols[c].value():
                sleep_ms(40)
                if cols[c].value():
                    key = key_matrix[r][c]
                    while cols[c].value(): pass
                    rows[r].value(0)
                    return key
        rows[r].value(0)
    return None

def save_settings():
    try:
        data = {"timer_enable": timer_enable, "start_time": start_time, "stop_time": stop_time}
        with open('config.json', 'w') as f: json.dump(data, f)
    except: pass

def load_settings():
    global timer_enable, start_time, stop_time
    try:
        with open('config.json', 'r') as f:
            data = json.load(f)
            timer_enable = data["timer_enable"]
            start_time = tuple(data["start_time"]) 
            stop_time = tuple(data["stop_time"])
    except: pass

def check_timer_logic():
    global last_check_time, device_on
    current_ms = ticks_ms()
    if ticks_diff(current_ms, last_check_time) < 1000: return
    last_check_time = current_ms
    
    if not timer_enable: return

    try:
        t = ds.datetime()
        h, m, s = t[4], t[5], t[6]
        now_sec = (h * 3600) + (m * 60) + s
        start_sec = (start_time[0] * 3600) + (start_time[1] * 60) + start_time[2]
        stop_sec = (stop_time[0] * 3600) + (stop_time[1] * 60) + stop_time[2]

        should_be_on = False
        
        # เงื่อนไข: ถ้าเวลาเริ่ม = เวลาจบ (00:00:00) ให้ถือว่าไม่ทำงาน
        if start_sec == stop_sec:
            should_be_on = False
        elif start_sec < stop_sec:
            if start_sec <= now_sec < stop_sec: should_be_on = True
        else:
            if now_sec >= start_sec or now_sec < stop_sec: should_be_on = True
        
        if should_be_on and not device_on:
            DEV.value(0); device_on = True
            print("AUTO-ON")
            write_log("DEVICE: AUTO ON") 
            
        elif not should_be_on and device_on:
            DEV.value(1); device_on = False
            print("AUTO-OFF")
            write_log("DEVICE: AUTO OFF") 
            
    except: pass

# ================= 4. UTILITY =================

# *** จุดที่แก้ไขหลัก: เอา check_timer_logic() ออกจาก loop รับค่า ***
def get_input(title, max_val):
    lcd.clear(); lcd.putstr(title)
    lcd.move_to(0,1); lcd.putstr("_")
    digits = ""
    while True:
        # check_timer_logic()  <-- เอาออกแล้ว! เพื่อไม่ให้แทรกตอนตั้งค่า
        key = scan_keypad()
        if not key: continue
        if key.isdigit():
            if len(digits) < 2:
                digits += key
                lcd.move_to(0,1); lcd.putstr(digits + " ")
        elif key == 'C' or key == '*':
            digits = ""; lcd.move_to(0,1); lcd.putstr("_  ")
        elif key == '#': 
            if digits == "": continue 
            val = int(digits)
            if val > max_val: val = max_val
            return val

def wait_any_key():
    while True:
        check_timer_logic()
        key = scan_keypad()
        if key: return key
        sleep_ms(100)

# ================= 5. MENUS =================

def menu_1_set_clock():
    h = get_input("Set Hour", 23)
    m = get_input("Set Min", 59)
    s = get_input("Set Sec", 59)
    ds.datetime((2024, 1, 1, h, m, s, 0, 0)) 
    write_log(f"Time Updated: {h:02d}:{m:02d}:{s:02d}")
    lcd.clear(); lcd.putstr("Time Saved!"); sleep(1)
    return '2'

def menu_2_home():
    lcd.clear()
    while True:
        try:
            t = ds.datetime()
            lcd.move_to(0,0); lcd.putstr("Time %02d:%02d:%02d" % (t[4], t[5], t[6]))
            lcd.move_to(0,1)
            ts = "ON " if timer_enable else "OFF"
            ds_stat = "ON " if device_on else "OFF"
            lcd.putstr(f"T:{ts} D:{ds_stat}")
        except: pass
        
        check_timer_logic()
        key = scan_keypad()
        if key: return key
        sleep_ms(100)

def menu_3_man_off():
    global device_on, timer_enable 
    
    # สั่งปิดมือ ต้องปิดออโต้ก่อน
    if timer_enable:
        timer_enable = False
        save_settings()
        write_log("TIMER: AUTO DISABLED")

    if device_on:
        write_log("Device: OFF") 
    DEV.value(1); device_on = False
    lcd.clear(); lcd.putstr("Device: OFF")
    return wait_any_key()

def menu_4_man_on():
    global device_on, timer_enable 
    
    # สั่งเปิดมือ ต้องปิดออโต้ก่อน
    if timer_enable:
        timer_enable = False
        save_settings()
        write_log("TIMER: AUTO DISABLED")

    if not device_on:
        write_log("Device: ON") 
    DEV.value(0); device_on = True
    lcd.clear(); lcd.putstr("Divice: ON")
    return wait_any_key()

def menu_5_dev_status():
    lcd.clear(); lcd.putstr("Device Status:"); lcd.move_to(0,1)
    lcd.putstr("ON" if device_on else "OFF")
    return wait_any_key()

def menu_6_tmr_off():
    global timer_enable
    timer_enable = False; save_settings()
    write_log("TIMER: off")
    lcd.clear(); lcd.putstr("Timer: off"); sleep(1)
    return wait_any_key()

def menu_7_tmr_on():
    global timer_enable
    timer_enable = True; save_settings()
    write_log("TIMER: on")
    lcd.clear(); lcd.putstr("Timer: on"); sleep(1)
    return wait_any_key()

def menu_8_tmr_status():
    lcd.clear(); lcd.putstr("Timer Config:"); lcd.move_to(0,1)
    lcd.putstr("on" if timer_enable else "off")
    return wait_any_key()

def menu_9_set_start():
    global start_time
    h = get_input("Start Hour", 23)
    m = get_input("Start Min", 59)
    s = get_input("Start Sec", 59)
    start_time = (h, m, s); save_settings()
    write_log(f"Set Start: {h}:{m}:{s}")
    lcd.clear(); lcd.putstr("Start Saved!"); sleep(1)
    return '2'

def menu_A_set_stop():
    global stop_time
    h = get_input("Stop Hour", 23)
    m = get_input("Stop Min", 59)
    s = get_input("Stop Sec", 59)
    stop_time = (h, m, s); save_settings()
    write_log(f"Set Stop: {h}:{m}:{s}")
    lcd.clear(); lcd.putstr("Stop Saved!"); sleep(1)
    return '2'

def menu_B_show_conf():
    lcd.clear()
    lcd.putstr("ON  %02d:%02d:%02d" % start_time)
    lcd.move_to(0,1)
    lcd.putstr("OFF %02d:%02d:%02d" % stop_time)
    return wait_any_key()

# ================= 6. MAIN PROGRAM =================

load_settings()

lcd.clear()
lcd.putstr("System Booting...")
sleep(0.5)

# ล้าง Log ทิ้งตอนเปิดเครื่อง
clear_log_file() 

# บันทึกบรรทัดแรกว่าระบบเริ่มทำงาน
reset_cause = machine.reset_cause()
msg = "System Started"
if reset_cause == machine.PWRON_RESET: msg += " (Power On)"
elif reset_cause == machine.SOFT_RESET: msg += " (Soft Reboot)"
write_log(msg) 

print("Recovering State...")
check_timer_logic() 

next_key = '2'

while True:
    if next_key:
        key = next_key
        next_key = None
    else:
        key = scan_keypad()

    if key:
        print(f"Go to Menu: {key}")
        if   key == '1': next_key = menu_1_set_clock()
        elif key == '2': next_key = menu_2_home()
        elif key == '3': next_key = menu_3_man_off()
        elif key == '4': next_key = menu_4_man_on()
        elif key == '5': next_key = menu_5_dev_status()
        elif key == '6': next_key = menu_6_tmr_off()
        elif key == '7': next_key = menu_7_tmr_on()
        elif key == '8': next_key = menu_8_tmr_status()
        elif key == '9': next_key = menu_9_set_start()
        elif key == 'A': next_key = menu_A_set_stop()
        elif key == 'B': next_key = menu_B_show_conf()
            
    check_timer_logic()
    sleep_ms(50)
