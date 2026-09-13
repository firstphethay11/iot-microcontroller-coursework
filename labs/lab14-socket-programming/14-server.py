##Rx
from machine import Pin, I2C
from i2c_lcd import I2cLcd
from ds3231 import DS3231
import time, ujson
import network
import socket

# -------- Wi-Fi AP Setup --------
ap = network.WLAN(network.AP_IF)
ap.active(False)
time.sleep(0.5)
ap.active(True)

ap.config(essid="ESP32_RX_Timer", password="password123", authmode=3)

while not ap.active():
    pass

print("สร้าง Wi-Fi สำเร็จ! ชื่อ: ESP32_RX_Timer | IP:", ap.ifconfig()[0])

# -------- Socket Setup --------
port = 8080
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', port))
sock.settimeout(0)

client_addr = None

# -------- I2C & Hardware --------
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)

lcd = I2cLcd(i2c, 0x27, 2, 16)

rtc = DS3231(i2c)

DEV = Pin(25, Pin.OUT)
DEV.off()   # เริ่มต้นให้ไฟดับ

# -------- FILE --------
DATA_FILE = "timer.json"

data = {"start":0, "stop":0, "timer":False}

lcd_temp_until = 0

# -------- LCD TEMP --------
def lcd_temp(l1,l2="",t=2000):

    global lcd_temp_until

    lcd.clear()

    lcd.move_to(0,0)
    lcd.putstr(l1[:16])

    lcd.move_to(0,1)
    lcd.putstr(l2[:16])

    lcd_temp_until = time.ticks_ms() + t


# -------- SAVE / LOAD --------
def save():
    with open(DATA_FILE,"w") as f:
        ujson.dump(data,f)

def load():

    global data

    try:
        with open(DATA_FILE) as f:
            data = ujson.load(f)
    except:
        save()


# -------- TIME --------
def now_sec():

    t = rtc.datetime()

    return t[4]*3600 + t[5]*60 + t[6]


def hms(sec):

    return "%02d:%02d:%02d"%(sec//3600,(sec%3600)//60,sec%60)


# -------- SEND SOCKET --------
def send(msg):

    global client_addr

    if client_addr:

        try:
            sock.sendto((msg+"#").encode(),client_addr)

        except:
            pass


# -------- COMMAND EXECUTOR --------
def execute(cmd):

    p = cmd.split(",")

    fn = int(p[0])


    if fn == 1:

        rtc.datetime((2025,1,1,int(p[1]),int(p[2]),int(p[3]),0,0))

        send("OK!")

        lcd_temp("SET TIME",p[1]+":"+p[2]+":"+p[3])


    elif fn == 2:

        t = hms(now_sec())

        send("Time:"+t)

        lcd_temp("TIME",t)


    elif fn == 3:

        DEV.off()  # OFF

        send("OK!")

        lcd_temp("DEVICE","OFF")


    elif fn == 4:

        DEV.on()   # ON

        send("OK!")

        lcd_temp("DEVICE","ON")


    elif fn == 5:

        msg = "DEV is " + ("on." if DEV.value()==1 else "off.")

        send(msg)

        lcd_temp("STATUS",msg)


    elif fn == 6:

        data["timer"] = False

        save()

        send("OK!")

        lcd_temp("TIMER","OFF")


    elif fn == 7:

        data["timer"] = True

        save()

        send("OK!")

        lcd_temp("TIMER","ON")


    elif fn == 8:

        msg = "TIMER is " + ("on." if data["timer"] else "off.")

        send(msg)

        lcd_temp("TIMER STATUS",msg)


    elif fn == 9:

        data["start"] = int(p[1])*3600 + int(p[2])*60 + int(p[3])

        save()

        send("OK!")

        lcd_temp("START TIME",p[1]+":"+p[2]+":"+p[3])


    elif fn == 10:

        data["stop"] = int(p[1])*3600 + int(p[2])*60 + int(p[3])

        save()

        send("OK!")

        lcd_temp("STOP TIME",p[1]+":"+p[2]+":"+p[3])


    elif fn == 11:

        msg = "Time control:"+hms(data["start"])+"-"+hms(data["stop"])

        send(msg)

        lcd_temp("CONTROL",hms(data["start"])+"-"+hms(data["stop"]))


    elif fn == 12:

        if DEV.value() == 1:

            DEV.off()

            send("OK!")

            lcd_temp("DEVICE","OFF")

        else:

            DEV.on()

            send("OK!")

            lcd_temp("DEVICE","ON")


# -------- TIMER --------
def timer_task():

    if data["timer"]:

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


        if is_on:

            DEV.on()

        else:

            DEV.off()


# -------- LCD DEFAULT --------
def lcd_default():

    global lcd_temp_until

    if time.ticks_diff(lcd_temp_until,time.ticks_ms()) > 0:

        return


    now = now_sec()

    lcd.move_to(0,0)

    line = "DEV:"+("ON " if DEV.value()==1 else "OFF")

    line += " TMR:"+("ON " if data["timer"] else "OFF")

    lcd.putstr(line[:16])


    lcd.move_to(0,1)

    lcd.putstr(hms(now))


# -------- RECEIVE SOCKET --------
def read_socket():

    global client_addr

    try:

        msg,addr = sock.recvfrom(1024)

        client_addr = addr

        if msg:

            payload = msg.decode().strip()

            commands = payload.split("#")

            for cmd in commands:

                if cmd:

                    execute(cmd)

    except OSError:

        pass


# -------- MAIN --------
load()

lcd.clear()

while True:

    read_socket()

    timer_task()

    lcd_default()

    time.sleep(0.1)
