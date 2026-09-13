import network
import ufirebase as firebase
from machine import Pin, SoftI2C
from i2c_lcd import I2cLcd
from ds3231 import DS3231
from time import sleep
import gc
import ujson

gc.collect()

# ======================
# I2C
# ======================

i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
rtc = DS3231(i2c)
lcd = I2cLcd(i2c,0x27,2,16)

# ======================
# DEVICE
# ======================

dev = Pin(25,Pin.OUT)
dev.value(0)   # Active HIGH (0=OFF)

# ======================
# CONFIG FILE
# ======================

CONFIG_FILE = "config.json"

def save_config():

    data = {
        "timer": timer_mode,
        "start": start_time,
        "stop": stop_time
    }

    try:
        with open(CONFIG_FILE,"w") as f:
            ujson.dump(data,f)
    except:
        pass


def load_config():

    global timer_mode,start_time,stop_time

    try:

        with open(CONFIG_FILE) as f:
            data = ujson.load(f)

        timer_mode = data["timer"]
        start_time = data["start"]
        stop_time  = data["stop"]

    except:
        pass


# ======================
# WIFI
# ======================

lcd.clear()
lcd.putstr("Connecting WiFi")

wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect("First-Ji","09806first1")

while not wifi.isconnected():
    sleep(1)

print("WiFi:",wifi.ifconfig()[0])

lcd.clear()
lcd.putstr("WiFi Connected")
sleep(2)

# ======================
# FIREBASE
# ======================

firebase.setURL("https://labfirebase-ffe94-default-rtdb.asia-southeast1.firebasedatabase.app/")
firebase.put("command","0",bg=0)

# ======================
# VARIABLES
# ======================

timer_mode = 0
start_time = [0,0,0]
stop_time  = [0,0,0]

last_cmd = ""

lcd.clear()

# ===== โหลดค่าที่เคยบันทึก =====
load_config()

# ======================
# MAIN LOOP
# ======================

while True:

    gc.collect()

    if not wifi.isconnected():
        wifi.connect("First-Ji","09806first1")

    # ======================
    # RTC TIME
    # ======================

    t = rtc.datetime()

    hh = int(t[4])
    mm = int(t[5])
    ss = int(t[6])

    # ======================
    # FIREBASE COMMAND
    # ======================

    try:
        firebase.get("command","cmd",bg=0)
        cmd = str(firebase.cmd)
    except:
        cmd = "0"

    if cmd == last_cmd:
        cmd = "0"

    if cmd != "0" and cmd != "None":

        last_cmd = cmd
        print("CMD:",cmd)

        try:

            cmd = cmd.replace('"','').replace("'","").replace("#","")
            parts = cmd.split(",")

            op = int(parts[0])

            # ======================
            # SET CLOCK
            # ======================

            if op == 1:

                h = int(parts[1])
                m = int(parts[2])
                s = int(parts[3])

                rtc.datetime((2024,1,1,h,m,s,0,0))

                firebase.put("esp32","OK!#",bg=0)

            # ======================
            # READ CLOCK
            # ======================

            elif op == 2:

                firebase.put(
                "esp32",
                "Time:%02d:%02d:%02d#"%(hh,mm,ss),
                bg=0)

            # ======================
            # DEVICE CONTROL
            # ======================

            elif op == 3:

                state = int(parts[1])

                dev.value(state)

                firebase.put("esp32","OK!#",bg=0)

            # ======================
            # READ DEVICE
            # ======================

            elif op == 4:

                status = "DEV is on.#" if dev.value()==1 else "DEV is off.#"

                firebase.put("esp32",status,bg=0)

            # ======================
            # TIMER MODE
            # ======================

            elif op == 5:

                timer_mode = int(parts[1])

                save_config()

                firebase.put("esp32","OK!#",bg=0)

            # ======================
            # READ TIMER
            # ======================

            elif op == 6:

                firebase.put(
                "esp32",
                "TIMER is on.#" if timer_mode else "TIMER is off.#",
                bg=0)

            # ======================
            # SET START TIME
            # ======================

            elif op == 7:

                start_time = [
                int(parts[1]),
                int(parts[2]),
                int(parts[3])]

                save_config()

                firebase.put("esp32","OK!#",bg=0)

                lcd.clear()
                lcd.move_to(0,0)
                lcd.putstr("Start Time Set")

                lcd.move_to(0,1)
                lcd.putstr("%02d:%02d:%02d"%(start_time[0],start_time[1],start_time[2]))

                sleep(2)

            # ======================
            # READ START TIME
            # ======================

            elif op == 8:

                firebase.put(
                "esp32",
                "Start Time:%02d:%02d:%02d#"%(
                start_time[0],
                start_time[1],
                start_time[2]),
                bg=0)

            # ======================
            # SET STOP TIME
            # ======================

            elif op == 9:

                stop_time = [
                int(parts[1]),
                int(parts[2]),
                int(parts[3])]

                save_config()

                firebase.put("esp32","OK!#",bg=0)

                lcd.clear()
                lcd.move_to(0,0)
                lcd.putstr("Stop Time Set")

                lcd.move_to(0,1)
                lcd.putstr("%02d:%02d:%02d"%(stop_time[0],stop_time[1],stop_time[2]))

                sleep(2)

            # ======================
            # READ STOP TIME
            # ======================

            elif op == 10:

                firebase.put(
                "esp32",
                "Stop Time:%02d:%02d:%02d#"%(
                stop_time[0],
                stop_time[1],
                stop_time[2]),
                bg=0)

        except Exception as e:

            print("Parse Error:",e)

        firebase.put("command","0",bg=0)

    # ======================
    # TIMER AUTO CONTROL
    # ======================

    if timer_mode == 1 and start_time != [0,0,0] and stop_time != [0,0,0]:

        now = hh*3600 + mm*60 + ss

        st = start_time[0]*3600 + start_time[1]*60 + start_time[2]
        sp = stop_time[0]*3600 + stop_time[1]*60 + stop_time[2]

        should_on = (st <= now < sp) if st < sp else (now >= st or now < sp)

        if should_on:
            dev.value(1)
        else:
            dev.value(0)

    # ======================
    # LCD DISPLAY
    # ======================

    lcd.move_to(0,0)
    lcd.putstr("Time %02d:%02d:%02d"%(hh,mm,ss))

    dev_stat = "ON " if dev.value()==1 else "OFF"
    tim_stat = "ON " if timer_mode else "OFF"

    lcd.move_to(0,1)
    lcd.putstr("D:%s T:%s   "%(dev_stat,tim_stat))

    sleep(1)