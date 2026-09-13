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
# I2C / LCD / RTC
# ======================

i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
rtc = DS3231(i2c)
lcd = I2cLcd(i2c,0x27,2,16)

# ======================
# DEVICE (Active HIGH)
# ======================

dev = Pin(25,Pin.OUT)
dev.value(0)   # 0 = OFF

# ======================
# SAVE CONFIG (กัน EN Reset)
# ======================

CONFIG_FILE="config.json"

def save_config():

    data={
    "timer":timer_mode,
    "start":start_time,
    "stop":stop_time
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
            data=ujson.load(f)

        timer_mode=data["timer"]
        start_time=data["start"]
        stop_time=data["stop"]

    except:
        pass


# ======================
# WIFI
# ======================

wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect("First-Ji","09806first1")

lcd.clear()
lcd.putstr("Connecting WiFi")

while not wifi.isconnected():
    sleep(1)

print("WiFi:",wifi.ifconfig()[0])

lcd.clear()
lcd.putstr("WiFi OK!")
sleep(2)

# ======================
# FIREBASE
# ======================

firebase.setURL("https://labfirebase-ffe94-default-rtdb.asia-southeast1.firebasedatabase.app/")
firebase.put("command","0",bg=0)

# ======================
# VARIABLES
# ======================

timer_mode=0
start_time=[0,0,0]
stop_time=[0,0,0]

current_screen=2

load_config()

lcd.clear()

# ======================
# LOOP
# ======================

while True:

    gc.collect()

    t = rtc.datetime()

    hh=int(t[4])
    mm=int(t[5])
    ss=int(t[6])

    try:
        firebase.get("command","cmd",bg=0)
        cmd=str(firebase.cmd)
    except:
        cmd="0"

    if cmd!="0" and cmd!="None":

        try:

            cmd=cmd.replace('"','').replace("'","").replace("#","")
            parts=cmd.split(",")

            op=int(parts[0])

            # ======================
            # SET CLOCK
            # ======================

            if op==1:

                h=int(parts[1])
                m=int(parts[2])
                s=int(parts[3])

                rtc.datetime((2024,1,1,h,m,s,1))

                lcd.clear()
                lcd.putstr("Clock Set")
                lcd.move_to(0,1)
                lcd.putstr("%02d:%02d:%02d"%(h,m,s))

                firebase.put("esp32","OK!#",bg=0)

                sleep(2)
                current_screen=2


            # ======================
            # DEVICE CONTROL
            # ======================

            elif op==3:

                state=int(parts[1])

                dev.value(state)

                firebase.put("esp32","OK!#",bg=0)

                lcd.clear()
                lcd.putstr("Device")
                lcd.move_to(0,1)

                if state==1:
                    lcd.putstr("ON")
                else:
                    lcd.putstr("OFF")

                sleep(2)
                current_screen=2


            # ======================
            # TIMER MODE
            # ======================

            elif op==5:

                timer_mode=int(parts[1])

                save_config()

                lcd.clear()
                lcd.putstr("Timer Mode")

                lcd.move_to(0,1)

                if timer_mode==1:
                    lcd.putstr("ON")
                else:
                    lcd.putstr("OFF")

                firebase.put("esp32","OK!#",bg=0)

                sleep(2)
                current_screen=2


            # ======================
            # SET START
            # ======================

            elif op==7:

                start_time=[int(parts[1]),int(parts[2]),int(parts[3])]

                save_config()

                lcd.clear()
                lcd.putstr("Start Time")
                lcd.move_to(0,1)

                lcd.putstr("%02d:%02d:%02d"%(start_time[0],start_time[1],start_time[2]))

                firebase.put("esp32","OK!#",bg=0)

                sleep(2)
                current_screen=2


            # ======================
            # SET STOP
            # ======================

            elif op==9:

                stop_time=[int(parts[1]),int(parts[2]),int(parts[3])]

                save_config()

                lcd.clear()
                lcd.putstr("Stop Time")
                lcd.move_to(0,1)

                lcd.putstr("%02d:%02d:%02d"%(stop_time[0],stop_time[1],stop_time[2]))

                firebase.put("esp32","OK!#",bg=0)

                sleep(2)
                current_screen=2


        except Exception as e:

            print("Parse Error:",e)

        firebase.put("command","0",bg=0)

    # ======================
    # TIMER AUTO
    # ======================

    if timer_mode==1:

        now_sec=(hh*3600)+(mm*60)+ss

        start_sec=(start_time[0]*3600)+(start_time[1]*60)+start_time[2]
        stop_sec=(stop_time[0]*3600)+(stop_time[1]*60)+stop_time[2]

        should_on=False

        if start_sec<stop_sec:
            should_on=(start_sec<=now_sec<stop_sec)

        elif start_sec>stop_sec:
            should_on=(now_sec>=start_sec or now_sec<stop_sec)

        if should_on and dev.value()==0:
            dev.value(1)

        elif not should_on and dev.value()==1:
            dev.value(0)

    # ======================
    # LCD CLOCK SCREEN
    # ======================

    if current_screen==2:

        lcd.move_to(0,0)
        lcd.putstr("Time %02d:%02d:%02d"%(hh,mm,ss))

        dev_stat="ON " if dev.value()==1 else "OFF"
        tim_stat="ON " if timer_mode else "OFF"

        lcd.move_to(0,1)
        lcd.putstr("D:%s T:%s"%(dev_stat,tim_stat))

    sleep(0.5)