# =================================================================
#                 DEVICE CONTROLLER - REFACTORED
# =================================================================
# Import libraries
from machine import Pin, SoftI2C
from lcd_api import LcdApi
from lcd_i2c import I2cLcd
from ds3231 import DS3231
from time import sleep, ticks_ms, ticks_diff
import os
import dht

# ================= Hardware Initialization =================
# ... (ส่วนนี้เหมือนเดิมทั้งหมด) ...
sensor = dht.DHT22(Pin(4))
I2C_ADDR = 0x27
totalRows = 2
totalColumns = 16
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
lcd = I2cLcd(i2c, I2C_ADDR, totalRows, totalColumns)
rtc = DS3231(i2c)
device = Pin(25, Pin.OUT)
device.value(0)
keyMatrix = [
    ['1', '2', '3', 'A'], ['4', '5', '6', 'B'],
    ['7', '8', '9', 'C'], ['*', '0', '#', 'D']
]
rowPins = [12, 13, 14, 15]
colPins = [26, 27, 32, 33]
rows = [Pin(r, Pin.OUT) for r in rowPins]
cols = [Pin(c, Pin.IN, Pin.PULL_DOWN) for c in colPins]

# ================= Global Variables =================
DATA_FILE = "data.txt"
startTime1, endTime1 = None, None
startTime2, endTime2 = None, None
startTemp, endTemp = None, None
timerEnable, manualOverride = False, False
temp = 0.0
command_buffer = ""
is_entering_command = False
last_key_press_time = 0

# ================= Data Persistence Functions =================
# ... (ฟังก์ชัน save_data และ load_data เหมือนเดิมทั้งหมด) ...
def save_data():
    with open(DATA_FILE, "w") as f:
        def format_time(t): return f"{t[0]}:{t[1]}:{t[2]}" if t is not None else "None"
        lines = [
            f"startTime1={format_time(startTime1)}", f"endTime1={format_time(endTime1)}",
            f"startTime2={format_time(startTime2)}", f"endTime2={format_time(endTime2)}",
            f"startTemp={startTemp if startTemp is not None else 'None'}",
            f"endTemp={endTemp if endTemp is not None else 'None'}",
            f"timerEnable={1 if timerEnable else 0}", f"device={device.value()}"
        ]
        f.write("\n".join(lines))

def load_data():
    global startTime1, endTime1, startTime2, endTime2, timerEnable, device, startTemp, endTemp, manualOverride
    if DATA_FILE not in os.listdir(): return
    with open(DATA_FILE, "r") as f:
        for line in f:
            key, val = line.strip().split("=", 1)
            def parse_time(v): return tuple(map(int, v.split(":"))) if v != "None" else None
            def parse_float(v): return float(v) if v != "None" else None
            if key == "startTime1": startTime1 = parse_time(val)
            elif key == "endTime1": endTime1 = parse_time(val)
            elif key == "startTime2": startTime2 = parse_time(val)
            elif key == "endTime2": endTime2 = parse_time(val)
            elif key == "startTemp": startTemp = parse_float(val)
            elif key == "endTemp": endTemp = parse_float(val)
            elif key == "timerEnable": timerEnable = val == "1"
            elif key == "device":
                device_val = int(val)
                device.value(device_val)
                manualOverride = (device_val == 1 and not timerEnable)

# ================= Keypad and Input Functions =================
# ... (ฟังก์ชัน scanKeypad และ readNumber เหมือนเดิม) ...
def scanKeypad():
    for i, row in enumerate(rows):
        row.value(1)
        for j, col in enumerate(cols):
            if col.value() == 1:
                row.value(0)
                return keyMatrix[i][j]
        row.value(0)
    return None

def readNumber(prompt, min_val, max_val):
    number_str = ''
    lcd.clear()
    lcd.putstr(prompt)
    lcd.move_to(0, 1)
    lcd.putstr(f"({min_val}-{max_val}): ")
    lcd.blink_cursor_on()
    last_key = None
    while True:
        key = scanKeypad()
        if key is not None and key != last_key:
            last_key = key
            if key.isdigit() and len(number_str) < 4:
                number_str += key; lcd.putstr(key)
            elif key == '*' and number_str:
                number_str = number_str[:-1]
                lcd.move_to(len(f"({min_val}-{max_val}): ") + len(number_str), 1)
                lcd.putstr(" ")
                lcd.move_to(len(f"({min_val}-{max_val}): ") + len(number_str), 1)
            elif key == '#':
                if number_str and min_val <= int(number_str) <= max_val:
                    lcd.blink_cursor_off()
                    return int(number_str)
                number_str = ''
                lcd.move_to(len(f"({min_val}-{max_val}): "), 1)
                lcd.putstr("    "); lcd.move_to(len(f"({min_val}-{max_val}): "), 1)
        elif key is None: last_key = None
        sleep(0.1)

# ================= Display Functions =================
# ... (ฟังก์ชัน display_main_screen, show_timed_message, show_time_range, show_temp_range เหมือนเดิม) ...
def display_main_screen():
    lcd.hide_cursor()
    t = rtc.datetime()
    time_str = f"{t[4]:02d}:{t[5]:02d}:{t[6]:02d}"
    status_str = "ON " if device.value() == 1 else "OFF"
    lcd.move_to(0, 0); lcd.putstr(f"{time_str} ST:{status_str}")
    temp_str = f"T:{temp:.1f}C"
    timer_str = "TMR:ON " if timerEnable else "TMR:OFF"
    lcd.move_to(0, 1); lcd.putstr(f"{temp_str}  {timer_str}")

def show_timed_message(line1, line2="", duration=2):
    lcd.clear()
    lcd.putstr(line1)
    if line2: lcd.move_to(0, 1); lcd.putstr(line2)
    sleep(duration)

def show_time_range(time_range_num):
    start_time = startTime1 if time_range_num == 1 else startTime2
    end_time = endTime1 if time_range_num == 1 else endTime2
    def format_t(t): return f"{t[0]:02d}:{t[1]:02d}:{t[2]:02d}" if t else "N/A"
    line1 = f"T{time_range_num} S: {format_t(start_time)}"
    line2 = f"   E: {format_t(end_time)}"
    show_timed_message(line1, line2, 4)

def show_temp_range():
    start_str = f"{startTemp:.1f}C" if startTemp is not None else "N/A"
    end_str = f"{endTemp:.1f}C" if endTemp is not None else "N/A"
    show_timed_message("Temp Range", f"S:{start_str} E:{end_str}", 3)

# ================= NEW: Command Handler Functions (แยกออกมาเพื่อง่ายต่อ Flowchart) =================
def handle_set_system_time():
    global rtc
    show_timed_message("Set System Time", "", 1.5)
    h = readNumber("Hour", 0, 23)
    m = readNumber("Minute", 0, 59)
    s = readNumber("Second", 0, 59)
    t = rtc.datetime()
    rtc.datetime((t[0], t[1], t[2], h, m, s, 0))
    show_timed_message("Time Updated!")

def handle_manual_off():
    global device, manualOverride
    device.value(0)
    manualOverride = True
    show_timed_message("Manual Mode: OFF")

def handle_manual_on():
    global device, manualOverride
    device.value(1)
    manualOverride = True
    show_timed_message("Manual Mode: ON")

def handle_timer_off():
    global timerEnable, manualOverride, device
    timerEnable = False
    manualOverride = False
    device.value(0)
    show_timed_message("Timer OFF")

def handle_timer_on():
    global timerEnable, manualOverride
    timerEnable = True
    manualOverride = False
    show_timed_message("Timer ON")
    
def handle_set_time(is_start, range_num):
    global startTime1, endTime1, startTime2, endTime2
    type_str = "Start" if is_start else "Stop"
    prompt = f"Set T{range_num} {type_str}"
    show_timed_message(prompt, "", 1.5)
    
    hour = readNumber("Hour", 0, 23)
    minute = readNumber("Minute", 0, 59)
    second = readNumber("Second", 0, 59)
    new_time = (hour, minute, second)
    
    if range_num == 1:
        if is_start: startTime1 = new_time
        else: endTime1 = new_time
    elif range_num == 2:
        if is_start: startTime2 = new_time
        else: endTime2 = new_time
    show_timed_message("Time Set!")

def handle_set_temp(is_start):
    global startTemp, endTemp
    if is_start:
        startTemp = readNumber("Start Temp", 0, 99)
        show_timed_message("Start Temp Set!")
    else:
        endTemp = readNumber("Stop Temp", 0, 99)
        show_timed_message("Stop Temp Set!")
        
# ================= REFACTORED: Core Logic & Command Execution =================
def execute_command(cmd):
    """Executes a command by calling its dedicated handler function."""
    command_map = {
        1: handle_set_system_time,
        2: handle_manual_off,
        3: handle_manual_on,
        4: handle_timer_off,
        5: handle_timer_on,
        6: lambda: handle_set_time(True, 1),
        7: lambda: handle_set_time(False, 1),
        8: lambda: show_time_range(1),
        9: lambda: handle_set_time(True, 2),
        10: lambda: handle_set_time(False, 2),
        11: lambda: show_time_range(2),
        12: lambda: handle_set_temp(True),
        13: lambda: handle_set_temp(False),
        14: show_temp_range
    }
    
    action = command_map.get(cmd)
    if action:
        action()
    else:
        show_timed_message("Invalid Command!")
    
    save_data()

def check_timer():
    """Checks time and temperature to control the device automatically."""
    global temp, device
    if manualOverride:
        return # ถ้าอยู่ในโหมด Manual ให้ข้ามการตรวจสอบทั้งหมด

    try:
        sensor.measure()
        temp = sensor.temperature()
    except Exception as e:
        print(f"Sensor read error: {e}")
        device.value(0)
        return
        
    # ตรวจสอบเงื่อนไขเวลา
    is_in_time_range = False
    if timerEnable:
        t = rtc.datetime()
        current_sec = t[4] * 3600 + t[5] * 60 + t[6]
        def to_seconds(time_tuple):
            if time_tuple is None: return -1
            return time_tuple[0] * 3600 + time_tuple[1] * 60 + time_tuple[2]

        start1_sec, end1_sec = to_seconds(startTime1), to_seconds(endTime1)
        start2_sec, end2_sec = to_seconds(startTime2), to_seconds(endTime2)

        range1_active = (start1_sec != -1 and end1_sec != -1 and start1_sec <= current_sec <= end1_sec)
        range2_active = (start2_sec != -1 and end2_sec != -1 and start2_sec <= current_sec <= end2_sec)
        is_in_time_range = range1_active or range2_active

    # ตรวจสอบเงื่อนไขอุณหภูมิ
    is_in_temp_range = False
    if startTemp is not None and endTemp is not None:
        if startTemp <= temp < endTemp:
            is_in_temp_range = True
    
    # ตัดสินใจเปิด/ปิดอุปกรณ์
    if timerEnable and is_in_time_range and is_in_temp_range:
        device.value(1)
    else:
        device.value(0)

# ================= REFACTORED: Main System Loop =================
def handle_command_input(key):
    """Manages the state of entering a command."""
    global is_entering_command, command_buffer
    
    if key == '*' and not is_entering_command:
        # เริ่มโหมดรับคำสั่ง
        is_entering_command = True
        command_buffer = ""
        lcd.clear()
        lcd.putstr("CMD: ")
        lcd.blink_cursor_on()
    elif is_entering_command:
        # ขณะอยู่ในโหมดรับคำสั่ง
        if key.isdigit():
            command_buffer += key
            lcd.putstr(key)
        elif key == '#': # ยืนยันคำสั่ง
            lcd.blink_cursor_off()
            if command_buffer:
                execute_command(int(command_buffer))
            is_entering_command = False
            command_buffer = ""
        elif key == '*': # ยกเลิก
            is_entering_command = False
            command_buffer = ""

# --- Program Start ---
lcd.clear()
lcd.putstr("Device Control")
lcd.move_to(0,1)
lcd.putstr("System Init...")
load_data()
sleep(2)

while True:
    # 1. ตรวจสอบและจัดการสถานะของระบบ (โหมด Auto หรือ Manual)
    if not is_entering_command:
        check_timer()
        display_main_screen()

    # 2. ตรวจสอบการกดปุ่มจาก Keypad
    key = scanKeypad()
    
    # 3. จัดการกับการกดปุ่ม (Debounce และเรียก Handler)
    if key and ticks_diff(ticks_ms(), last_key_press_time) > 250:
        last_key_press_time = ticks_ms()
        handle_command_input(key)
        
    sleep(0.05)