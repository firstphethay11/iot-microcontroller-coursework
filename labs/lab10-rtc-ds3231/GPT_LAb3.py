# ==========================================
# SERVER (Rx) - ใช้ DS3231 (ปรับแก้ KeyError)
# ==========================================
from machine import Pin, SoftI2C
from i2c_lcd import I2cLcd
from ds3231 import DS3231
import network
import socket
import ujson
import time
import os # นำเข้า os เพื่อใช้ลบไฟล์เก่าที่มีปัญหา

SSID = "First_AP"
PASSWORD = "password123"
PORT = 10000

# -------- 1. ฮาร์ดแวร์ --------
dev = Pin(25, Pin.OUT)
dev.value(0) 

i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
lcd = I2cLcd(i2c, 0x27, 2, 16)
rtc = DS3231(i2c)

# -------- 2. ตัวแปรระบบ --------
DATA_FILE = "timer.json"

# 🔴 ใช้ชื่อ timer_on ให้เหมือนกันทั้งหมด
data = {
    "start": 0,
    "stop": 0,
    "timer_on": False 
}

lcd_temp_until = 0

# -------- 3. ระบบไฟล์ (SAVE/LOAD) --------
def save_data():
    try:
        with open(DATA_FILE,"w") as f:
            ujson.dump(data,f)
    except Exception as e:
        print("Save error:", e)

def load_data():
    global data
    try:
        # ถ้าไฟล์มีปัญหา ให้เคลียร์ทิ้งแล้วสร้างใหม่
        with open(DATA_FILE,"r") as f:
            temp_data = ujson.load(f)
            # เช็คว่ามี key ที่เราต้องการไหม ถ้าไม่มีให้ error เพื่อไปสร้างใหม่
            if "timer_on" not in temp_data:
                raise Exception("Old file format")
            data = temp_data
    except:
        save_data()

# -------- 4. ฟังก์ชันจัดการเวลา --------
def now_sec():
    t = rtc.datetime()
    return t[4]*3600 + t[5]*60 + t[6]

def hms(sec):
    h = sec//3600
    m = (sec%3600)//60
    s = sec%60
    return "%02d:%02d:%02d" % (h,m,s)

# -------- 5. ระบบหน้าจอ LCD --------
def show_temp_msg(line1, line2="", duration_ms=2000):
    global lcd_temp_until
    lcd.clear()
    time.sleep_ms(20)
    lcd.move_to(0,0)
    lcd.putstr(line1[:16])
    lcd.move_to(0,1)
    lcd.putstr(line2[:16])
    lcd_temp_until = time.ticks_ms() + duration_ms

def update_lcd_default():
    if time.ticks_diff(lcd_temp_until, time.ticks_ms()) > 0:
        return

    now = now_sec()

    d_stat = "ON" if dev.value() else "OFF"
    t_stat = "ON" if data["timer_on"] else "OFF" # 🔴 แก้ชื่อ

    line1 = f"D:{d_stat} T:{t_stat}"
    line2 = hms(now)

    lcd.move_to(0,0)
    lcd.putstr((line1+"                ")[:16])
    lcd.move_to(0,1)
    lcd.putstr((line2+"                ")[:16])

# -------- 6. ฟังก์ชันรับคำสั่ง --------
def process_command(cmd_str):
    global data

    try:
        parts = cmd_str.split(",")
        cmd_id = int(parts[0])
        reply = "Error!"

        if cmd_id == 1:
            h = int(parts[1])
            m = int(parts[2])
            s = int(parts[3])
            rtc.datetime((2026, 1, 1, 0, h, m, s, 0))
            reply = "OK!"
            show_temp_msg("SET CLOCK", hms(now_sec()))

        elif cmd_id == 2:
            reply = "Time:" + hms(now_sec())
            show_temp_msg("READ TIME", hms(now_sec()))

        elif cmd_id == 3:
            dev.value(0)
            reply = "OK!"
            show_temp_msg("DEVICE", "OFF")

        elif cmd_id == 4:
            dev.value(1)
            reply = "OK!"
            show_temp_msg("DEVICE", "ON")

        elif cmd_id == 5:
            reply = "DEV is " + ("on." if dev.value() else "off.")
            show_temp_msg("STATUS", reply[:16])

        elif cmd_id == 6:
            data["timer_on"] = False # 🔴 แก้ชื่อ
            save_data()
            reply = "OK!"
            show_temp_msg("TIMER", "OFF")

        elif cmd_id == 7:
            data["timer_on"] = True # 🔴 แก้ชื่อ
            save_data()
            reply = "OK!"
            show_temp_msg("TIMER", "ON")

        elif cmd_id == 8:
            reply = "TIMER is " + ("on." if data["timer_on"] else "off.") # 🔴 แก้ชื่อ
            show_temp_msg("TIMER STATUS", reply[:16])

        elif cmd_id == 9:
            h = int(parts[1])
            m = int(parts[2])
            s = int(parts[3])
            data["start"] = h*3600 + m*60 + s
            save_data()
            reply = "OK!"
            show_temp_msg("SET START", hms(data["start"]))

        elif cmd_id == 10:
            h = int(parts[1])
            m = int(parts[2])
            s = int(parts[3])
            data["stop"] = h*3600 + m*60 + s
            save_data()
            reply = "OK!"
            show_temp_msg("SET STOP", hms(data["stop"]))

        elif cmd_id == 11:
            start_time = hms(data["start"])
            stop_time = hms(data["stop"])
            reply = "Time control:{}-{}".format(start_time, stop_time)
            show_temp_msg("START " + start_time, "STOP  " + stop_time, 3000)

        elif cmd_id == 12:
            dev.value(0 if dev.value() else 1)
            show_temp_msg("DEVICE", "ON" if dev.value() else "OFF")
            reply = "OK!"

        return reply

    except Exception as e:
        print("Command error:", e)
        return "Error!"

# -------- 7. ระบบเช็คเวลาอัตโนมัติ --------
def auto_timer_check():
    if data["timer_on"]: # 🔴 แก้ชื่อ
        now = now_sec()
        start = data["start"]
        stop = data["stop"]
        is_on = False

        if start < stop:
            if start <= now < stop:
                is_on = True
        else:
            if now >= start or now < stop:
                is_on = True

        dev.value(1 if is_on else 0)

# ==========================================
# MAIN PROGRAM
# ==========================================
# ลบไฟล์เก่าทิ้งเพื่อเริ่มใหม่ให้ชัวร์
try:
    os.remove(DATA_FILE)
except:
    pass

load_data()

ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid=SSID, password=PASSWORD, authmode=3)

print("AP Ready! IP:", ap.ifconfig()[0])

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', PORT))
sock.settimeout(0)

lcd.clear()
print("Server is listening on UDP port", PORT)

while True:
    try:
        msg, addr = sock.recvfrom(1024)
        payload = msg.decode().strip()
        print("[RX Received] <-", payload)

        commands = [c for c in payload.split("#") if c]
        for cmd in commands:
            reply = process_command(cmd)
            sock.sendto((reply + "#").encode(), addr)

    except OSError:
        pass

    auto_timer_check()
    update_lcd_default()
    time.sleep(0.1)