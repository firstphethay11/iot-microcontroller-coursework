import network
import ufirebase as firebase
from machine import Pin, SoftI2C
import time, json, gc
from ds3231 import DS3231
from i2c_lcd import I2cLcd

gc.collect()

# ===== DEV & I2C SETUP =====
DEV = Pin(25, Pin.OUT)
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
ds = DS3231(i2c)
lcd = I2cLcd(i2c, 0x27, 2, 16)

# ===== DEFAULT STATE =====
device_on = False
timer_enable = False
start_time = [18, 0, 0] # ใช้ List เพื่อให้เซฟลง JSON ง่าย
stop_time  = [6, 0, 0]
current_screen = 2

# ===== SAVE / LOAD CONFIG =====
def save_config():
    data = {
        "device_on": device_on,
        "timer_enable": timer_enable,
        "start_time": start_time,
        "stop_time": stop_time,
        "screen": current_screen
    }
    try:
        with open("config.json", "w") as f:
            json.dump(data, f)
    except:
        pass

def load_config():
    global device_on, timer_enable, start_time, stop_time, current_screen
    try:
        with open("config.json", "r") as f:
            data = json.load(f)
            device_on = data["device_on"]
            timer_enable = data["timer_enable"]
            start_time = data["start_time"]
            stop_time = data["stop_time"]
            current_screen = data["screen"]
    except:
        pass

# โหลดค่าที่เคยเซฟไว้ และสั่งงานขา DEV (Active Low: 0=ON, 1=OFF)
load_config()
DEV.value(0 if device_on else 1)

# ===== WIFI SETUP =====
lcd.clear()
lcd.putstr("Connecting WiFi")
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect("First-Ji", "09806first1")

print("Connecting to Wi-Fi...")
while not wifi.isconnected():
    print(".", end="")
    time.sleep(1)
print("\nConnected:", wifi.ifconfig()[0])

lcd.clear()
lcd.putstr("WiFi Connected!")
time.sleep(2)

# ===== FIREBASE SETUP =====
firebase.setURL("https://labfirebase-ffe94-default-rtdb.asia-southeast1.firebasedatabase.app/")
firebase.put("command", "0", bg=0) # เคลียร์ค่าเริ่มต้น
firebase.put("esp32", '""', bg=0)

# ฟังก์ชันสำหรับส่งข้อความตอบกลับไปที่ Firebase
def send_fb(msg):
    firebase.put("esp32", msg, bg=0)

# ================= MAIN LOOP =================
while True:
    # 1. ดึงเวลาปัจจุบันจากโมดูล RTC DS3231
    t = ds.datetime() # format: (YYYY, MM, DD, WD, HH, MM, SS, SUB_SS)
    
    # 2. รับคำสั่งจาก Firebase
    firebase.get("command", "cmd_val", bg=0)
    cmd = str(firebase.cmd_val)
    
    # เช็คว่ามีคำสั่งเข้ามาหรือไม่
    if cmd != "0" and cmd != "None":
        print("Raw Data Received:", cmd)
        
        # --- เพิ่ม Try...Except เพื่อดักจับ Error ไม่ให้โปรแกรมค้าง ---
        try:
            # --- แก้บั๊ก ufirebase: ลบเครื่องหมาย " และ ' ที่อาจติดมา ---
            cmd_clean = cmd.replace('"', '').replace("'", "").strip("#")
            parts = cmd_clean.split(",")
            c = int(parts[0])

            # ---------- 1 SET CLOCK ----------
            if c == 1:
                h, m, s = int(parts[1]), int(parts[2]), int(parts[3])
                ds.datetime((2024, 1, 1, h, m, s, 0, 0))
                send_fb("OK!#")

            # ---------- 2 GET TIME ----------
            elif c == 2:
                current_screen = 2
                save_config()
                send_fb(f"Time:{t[4]:02d}:{t[5]:02d}:{t[6]:02d}#")

            # ---------- 3 DEV OFF / ON ----------
            elif c == 3:
                state = int(parts[1]) # 0=OFF, 1=ON
                device_on = True if state == 1 else False
                DEV.value(0 if device_on else 1)
                current_screen = 3
                save_config()
                send_fb("OK!#")

            # ---------- 4 DEV STATUS ----------
            elif c == 4:
                current_screen = 3
                save_config()
                send_fb("DEV is on.#" if device_on else "DEV is off.#")

            # ---------- 5 TIMER OFF / ON ----------
            elif c == 5:
                state = int(parts[1]) # 0=OFF, 1=ON
                timer_enable = True if state == 1 else False
                current_screen = 6
                save_config()
                send_fb("OK!#")

            # ---------- 6 TIMER STATUS ----------
            elif c == 6:
                current_screen = 6
                save_config()
                send_fb("TIMER is on.#" if timer_enable else "TIMER is off.#")

            # ---------- 7 SET START TIME ----------
            elif c == 7:
                start_time = [int(parts[1]), int(parts[2]), int(parts[3])]
                save_config()
                send_fb("OK!#")

            # ---------- 8 GET START TIME ----------
            elif c == 8:
                send_fb(f"Start Time:{start_time[0]:02d}:{start_time[1]:02d}:{start_time[2]:02d}#")

            # ---------- 9 SET STOP TIME ----------
            elif c == 9:
                stop_time = [int(parts[1]), int(parts[2]), int(parts[3])]
                save_config()
                send_fb("OK!#")

            # ---------- 10 GET STOP TIME ----------
            elif c == 10:
                send_fb(f"Stop Time:{stop_time[0]:02d}:{stop_time[1]:02d}:{stop_time[2]:02d}#")

        except Exception as e:
            # ถ้าแยกข้อความแล้วพัง มันจะแจ้งเตือนตรงนี้แทนที่จะหยุดทำงาน
            print("Error parsing command:", e)

        # ทำงานเสร็จแล้ว หรือ Error ก็ตาม ต้องเคลียร์คำสั่งใน Firebase กลับเป็น 0 เสมอ
        firebase.put("command", "0", bg=0)
        print("Command Reset to 0")

    # ===== AUTO TIMER (เช็คเวลาจาก DS3231) =====
    if timer_enable:
        now_sec = t[4]*3600 + t[5]*60 + t[6]
        st_sec  = start_time[0]*3600 + start_time[1]*60 + start_time[2]
        sp_sec  = stop_time[0]*3600  + stop_time[1]*60  + stop_time[2]

        should_on = (st_sec <= now_sec < sp_sec) if st_sec < sp_sec else (now_sec >= st_sec or now_sec < sp_sec)

        if should_on and not device_on:
            DEV.value(0); device_on = True; save_config()
        elif not should_on and device_on:
            DEV.value(1); device_on = False; save_config()

    # ===== LCD DISPLAY UPDATE =====
    lcd.move_to(0,0)

    if current_screen == 2:
        lcd.putstr("Time %02d:%02d:%02d   " % (t[4], t[5], t[6]))
        lcd.move_to(0,1)
        lcd.putstr("                ")

    elif current_screen == 3:
        lcd.putstr("Device Status   ")
        lcd.move_to(0,1)
        lcd.putstr("DEV: %s         " % ("ON" if device_on else "OFF"))

    elif current_screen == 6:
        lcd.putstr("Timer Status    ")
        lcd.move_to(0,1)
        lcd.putstr("TIMER: %s       " % ("ON" if timer_enable else "OFF"))

    time.sleep(0.5) # หน่วงเวลากัน Firebase/จอ รวน