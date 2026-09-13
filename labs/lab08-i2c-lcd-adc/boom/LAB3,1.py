from machine import Pin, I2C, RTC
from time import sleep, ticks_ms, ticks_diff
from i2c_lcd import I2cLcd

# --------------------------
# LCD I2C
# --------------------------
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
lcd = I2cLcd(i2c, 0x27, 2, 16)

# --------------------------
# RTC
# --------------------------
rtc = RTC()
rtc.datetime((2025, 11, 26, 2, 9, 30, 0, 0))

# --------------------------
# Keypad 4x4
# --------------------------
colPins = [14, 15, 32, 33]
rowPins = [4, 5, 12, 13]

rows = [Pin(pin, Pin.OUT) for pin in rowPins]
cols = [Pin(pin, Pin.IN, Pin.PULL_DOWN) for pin in colPins]

keys = [
    ['1','2','3','A'],
    ['4','5','6','B'],
    ['7','8','9','C'],
    ['*','0','#','D']
]

def get_key():
    for r in range(4):
        rows[r].value(1)
        for c in range(4):
            if cols[c].value() == 1:
                rows[r].value(0)
                return keys[r][c]
        rows[r].value(0)
    return None

# --------------------------
# เวลา
# --------------------------
def time_to_counter():
    y, m, d, wd, hh, mm, ss, sub = rtc.datetime()
    return hh*3600 + mm*60 + ss

def counter_to_time(counter):
    hh = (counter // 3600) % 24
    mm = (counter % 3600) // 60
    ss = counter % 60
    return f"{hh:02}:{mm:02}:{ss:02}"

time_counter = time_to_counter()

# --------------------------
# โหมดแสดงผล
# --------------------------
MODE_TIME = 0
MODE_CMD = 1
mode = MODE_TIME

buffer = ""
status = "Waiting"
start_flag = False  # ควบคุมการเริ่มนับเวลา

# --------------------------
# แสดงหน้าจอเวลา (เต็มครั้งแรก)
# --------------------------
def show_time_screen():
    lcd.clear()
    lcd.putstr("Time: " + counter_to_time(time_counter))
    lcd.move_to(0,1)
    lcd.putstr("Status: " + status)

# --------------------------
# แสดงเวลาบน LCD แบบ non-blocking
# --------------------------
def update_time_status():
    lcd.move_to(6,0)
    lcd.putstr(counter_to_time(time_counter))
    lcd.move_to(8,1)
    lcd.putstr(status + "  ")

# --------------------------
# แสดงหน้าคำสั่ง
# --------------------------
def show_command_screen():
    lcd.clear()
    lcd.putstr("Command:\n")
    lcd.putstr(buffer)

# --------------------------
# ตั้งเวลา HH:MM:SS
# --------------------------
def set_time_mode():
    global time_counter, rtc, status
    lcd.clear()
    lcd.putstr("Set Time:\nHH:MM:SS")
    lcd.move_to(0,1)
    lcd.putstr("Input: ")

    num = ""
    while True:
        key = get_key()
        if key:
            sleep(0.2)  # debounce
            if key.isdigit():
                if len(num) < 6:
                    num += key
                    # แสดงเวลาแบบ HH:MM:SS ขณะป้อน
                    display = ""
                    for i, n in enumerate(num):
                        display += n
                        if i == 1 or i == 3:
                            display += ":"
                    lcd.move_to(7,1)
                    lcd.putstr(display + "   ")  # เติมวรรคเพื่อลบตัวเก่า
            elif key == "#":  # ยืนยัน
                if len(num) < 6:
                    num = num.ljust(6, '0')  # เติม 0 หน้าให้ครบ
                hh = int(num[0:2])
                mm = int(num[2:4])
                ss = int(num[4:6])
                rtc.datetime((2025, 11, 26, 2, hh, mm, ss, 0))  # length = 8
                time_counter = hh*3600 + mm*60 + ss
                status = "Time Set"
                break
            elif key == "*":  # ยกเลิก
                break
        sleep(0.05)

    show_time_screen()

# --------------------------
# Main Loop
# --------------------------
show_time_screen()
last_tick = ticks_ms()

while True:
    key = get_key()

    # --------------------------
    # Keypad
    # --------------------------
    if key is not None:
        if mode == MODE_TIME:
            if key == "*":
                mode = MODE_CMD
                buffer = "*"
                show_command_screen()
                sleep(0.3)
                continue
            elif key == "A":  # ตั้งเวลา
                set_time_mode()
                continue

        if mode == MODE_CMD:
            buffer += key
            show_command_screen()
            sleep(0.3)

            # START
            if buffer == "*1#":
                status = "Start"
                start_flag = True
                buffer = ""
                mode = MODE_TIME
                update_time_status()

            # STOP
            elif buffer == "*0#":
                status = "Stop"
                start_flag = False
                buffer = ""
                mode = MODE_TIME
                update_time_status()

            # ป้อนผิด
            elif len(buffer) >= 3:
                buffer = ""
                show_command_screen()

    # --------------------------
    # นับเวลาแบบ non-blocking
    # --------------------------
    if start_flag:
        now = ticks_ms()
        if ticks_diff(now, last_tick) >= 1000:
            time_counter += 1
            last_tick = now
            update_time_status()

    sleep(0.05)
