import network
import urequests
from machine import Pin, I2C
from time import sleep
import ds3231
import dht
import ujson
from i2c_lcd import I2cLcd

# WIFI
SSID = "First-Ji"
PASSWORD = "09806first1"

wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASSWORD)

print("Connecting WiFi...")
while not wifi.isconnected():
    sleep(1)

print("Connected:", wifi.ifconfig()[0])

# FIREBASE
BASE = "https://labfirebase-ffe94-default-rtdb.asia-southeast1.firebasedatabase.app/"
cmd_url = BASE + "command.json"
esp_url = BASE + "esp32.json"

# DEVICE & SENSOR
device = Pin(25, Pin.OUT)
sensor = dht.DHT22(Pin(2))

# RTC & LCD
i2c = I2C(0, sda=Pin(21), scl=Pin(22))
rtc = ds3231.DS3231(i2c)
lcd = I2cLcd(i2c, 0x27, 2, 16)

# DATA
DATA_FILE = "config.json"
data = {
    "timer_enabled": 0,
    "start_time": [0, 0, 0],
    "stop_time": [0, 0, 0],
    "start_temp": 25,
    "stop_temp": 35
}

def save():
    with open(DATA_FILE, "w") as f:
        ujson.dump(data, f)

def load():
    global data
    try:
        with open(DATA_FILE) as f:
            loaded_data = ujson.load(f)
            data.update(loaded_data)
    except:
        save()

load()

# FIREBASE
def send(msg):
    try:
        urequests.put(esp_url, data='"' + msg + '"').close()
    except:
        pass

def read_cmd():
    try:
        r = urequests.get(cmd_url)
        c = r.text.replace('"', '')
        r.close()
        return c
    except:
        return "0"

# --- ฟังก์ชันแสดง Pop-up บนจอ LCD ---
def popup_lcd(line1, line2):
    lcd.clear()
    lcd.move_to(0, 0)
    lcd.putstr(line1)
    lcd.move_to(0, 1)
    lcd.putstr(line2)
    sleep(1.5) # แสดงค้างไว้ 1.5 วินาที เพื่อให้มองทัน
    lcd.clear()

# COMMAND
def handle(cmd):
    p = cmd.split(",")
    c = p[0]

    if c == "1":
        rtc.datetime((2025, 1, 1, int(p[1]), int(p[2]), int(p[3]), 0))
        send("OK!#")
        popup_lcd("System Time Set", "%02d:%02d:%02d" % (int(p[1]), int(p[2]), int(p[3])))

    elif c == "2":
        dt = rtc.datetime()
        send("Time:%02d:%02d:%02d#" % (dt[4], dt[5], dt[6]))
        popup_lcd("Read Time", "Sent to Web")

    elif c == "3":
        val = int(p[1])
        device.value(val)
        send("OK!#")
        popup_lcd("Device Control", "DEV -> ON" if val else "DEV -> OFF")

    elif c == "4":
        status = "ON" if device.value() else "OFF"
        send(f"DEV is {status}.")
        popup_lcd("Read Dev Status", f"Current: {status}")
        
    elif c == "5":
        data["timer_enabled"] = int(p[1])
        save()
        send("OK!#")
        popup_lcd("Timer Mode", "TIMER -> ON" if data["timer_enabled"] else "TIMER -> OFF")

    elif c == "6":
        status = "ON" if data["timer_enabled"] else "OFF"
        send(f"TIMER is {status}.")
        popup_lcd("Read TMR Status", f"Current: {status}")

    elif c == "7":
        data["start_time"] = [int(p[1]), int(p[2]), int(p[3])]
        save()
        send("OK!#")
        popup_lcd("Set Start Time", "%02d:%02d:%02d" % (int(p[1]), int(p[2]), int(p[3])))

    elif c == "8":
        t = data["start_time"]
        send("Start Time:%02d:%02d:%02d#" % (t[0], t[1], t[2]))
        popup_lcd("Read Start Time", "Sent to Web")

    elif c == "9":
        data["stop_time"] = [int(p[1]), int(p[2]), int(p[3])]
        save()
        send("OK!#")
        popup_lcd("Set Stop Time", "%02d:%02d:%02d" % (int(p[1]), int(p[2]), int(p[3])))

    elif c == "10":
        t = data["stop_time"]
        send("Stop Time:%02d:%02d:%02d#" % (t[0], t[1], t[2]))
        popup_lcd("Read Stop Time", "Sent to Web")

    elif c == "11":
        sensor.measure()
        send("Temp:%.1f#" % sensor.temperature())
        popup_lcd("Read Temp", "Sent to Web")

    elif c == "12":
        data["start_temp"] = float(p[1])
        save()
        send("OK!#")
        popup_lcd("Set Start Temp", "Temp: %.1f C" % float(p[1]))

    elif c == "13":
        send("Start Temp:%.1f#" % data["start_temp"])
        popup_lcd("Read Start Temp", "Sent to Web")

    elif c == "14":
        data["stop_temp"] = float(p[1])
        save()
        send("OK!#")
        popup_lcd("Set Stop Temp", "Temp: %.1f C" % float(p[1]))

    elif c == "15":
        send("Stop Temp:%.1f#" % data["stop_temp"])
        popup_lcd("Read Stop Temp", "Sent to Web")


# timer_enabled CONTROL
def control_device():
    if not data["timer_enabled"]:
        return
    try:
        dt = rtc.datetime()
        now = dt[4] * 3600 + dt[5] * 60 + dt[6]

        st = data["start_time"]
        sp = data["stop_time"]
        start = st[0] * 3600 + st[1] * 60 + st[2]
        stop  = sp[0] * 3600 + sp[1] * 60 + sp[2]
        time_ok = start <= now < stop

        sensor.measure()
        temp = sensor.temperature()
        temp_ok = data["start_temp"] <= temp <= data["stop_temp"]

        if time_ok and temp_ok:
            device.value(1)
        else:
            device.value(0)
    except:
        pass

# LCD MAIN SHOW
def lcd_show():
    try:
        sensor.measure()
        temp = sensor.temperature()
        dt = rtc.datetime()

        lcd.move_to(0, 0)
        lcd.putstr("DEV:%s TMR:%s  " % (
            "ON" if device.value() else "OFF",
            "ON" if data["timer_enabled"] else "OFF"
        ))
        lcd.move_to(0, 1)
        lcd.putstr("T:%4.1fC" % temp)
        lcd.move_to(8, 1)
        lcd.putstr("%02d:%02d:%02d" % (dt[4], dt[5], dt[6]))
    except:
        pass

# MAIN
print("System Ready")
while True:
    cmd = read_cmd()

    if cmd != "0":
        if cmd.endswith("#"):
            cmd = cmd[:-1]

        handle(cmd)

        urequests.put(cmd_url, data='"0"').close()

    control_device()
    lcd_show()
    sleep(0.5)
