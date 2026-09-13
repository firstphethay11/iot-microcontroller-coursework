import network
import usocket as socket
import utime as time
import ujson
from machine import Pin, I2C
from i2c_lcd import I2cLcd
from ds3231 import DS3231
import gc

gc.collect()

# -------- 1. Setup Hardware --------
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)

lcd = I2cLcd(i2c, 0x27, 2, 16)

rtc = DS3231(i2c)

DEV = Pin(25, Pin.OUT)

DEV.off()   # เริ่มต้นไฟดับ


# -------- 2. Data --------
DATA_FILE = "timer.json"

data = {
"start":0,
"stop":0,
"timer":False
}

lcd_temp_until = 0


def save():
    with open(DATA_FILE,"w") as f:
        ujson.dump(data,f)


def load():
    global data
    try:
        with open(DATA_FILE) as f:
            data=ujson.load(f)
    except:
        save()


# -------- Time --------
def now_sec():

    t = rtc.datetime()

    return t[4]*3600 + t[5]*60 + t[6]


def hms(sec):

    return "%02d:%02d:%02d"%(sec//3600,(sec%3600)//60,sec%60)


# -------- LCD Alert --------
def lcd_alert(msg1,msg2="",t=1500):

    global lcd_temp_until

    lcd.clear()

    lcd.move_to(0,0)
    lcd.putstr(msg1[:16])

    lcd.move_to(0,1)
    lcd.putstr(msg2[:16])

    lcd_temp_until = time.ticks_ms() + t


# -------- LCD Default --------
def lcd_default():

    global lcd_temp_until

    if time.ticks_diff(lcd_temp_until,time.ticks_ms())>0:
        return

    now = now_sec()

    lcd.move_to(0,0)

    status_line = "D:" + ("ON " if DEV.value()==1 else "OFF")
    status_line += " T:" + ("ON " if data["timer"] else "OFF")

    lcd.putstr(status_line + "      ")

    lcd.move_to(0,1)

    lcd.putstr("T: " + hms(now) + "      ")


# -------- Timer --------
def timer_task():

    if not data["timer"]:
        return

    now = now_sec()

    start = data["start"]
    stop = data["stop"]

    is_on = (start <= now < stop) if start < stop else (now >= start or now < stop)

    if is_on:

        if DEV.value()!=1:
            DEV.on()

    else:

        if DEV.value()!=0:
            DEV.off()


# -------- HTML --------
def get_html():

    return """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Electric Device Control</title>
</head>

<body>

<h2>Electric Device Control</h2>

Time:
hh:<input id="th">
mm:<input id="tm">
ss:<input id="ts">

<button onclick="readTime()">Read</button>
<button onclick="setTime()">Set</button>

<br><br>

Device Status:
<input id="devStatus" value="OFF">

<button onclick="sendCmd('/3/','devStatus')">OFF</button>
<button onclick="sendCmd('/4/','devStatus')">ON</button>

<br><br>

Timer Status:
<input id="tmrStatus" value="OFF">

<button onclick="sendCmd('/6/','tmrStatus')">OFF</button>
<button onclick="sendCmd('/7/','tmrStatus')">ON</button>

<br><br>

Start Time:
hh:<input id="sh">
mm:<input id="sm">
ss:<input id="ss_start">

<button onclick="setTimer('9','sh','sm','ss_start')">Set</button>

<br><br>

Stop Time:
hh:<input id="ph">
mm:<input id="pm">
ss:<input id="ps">

<button onclick="setTimer('10','ph','pm','ps')">Set</button>

<script>

function sendCmd(url,target){

fetch(url).then(r=>r.text()).then(d=>{

if(target && d!=""){
document.getElementById(target).value=d
}

})

}

function readTime(){

fetch('/2/').then(r=>r.text()).then(data=>{

let p=data.split(',')

th.value=p[0]
tm.value=p[1]
ts.value=p[2]

})

}

function setTime(){

let h=th.value.padStart(2,'0')
let m=tm.value.padStart(2,'0')
let s=ts.value.padStart(2,'0')

sendCmd('/'+h+'/'+m+'/'+s+'/')

}

function setTimer(cmd,h,m,s){

let hh=document.getElementById(h).value.padStart(2,'0')
let mm=document.getElementById(m).value.padStart(2,'0')
let ss=document.getElementById(s).value.padStart(2,'0')

sendCmd('/'+cmd+'/'+hh+'/'+mm+'/'+ss+'/')

}

</script>

</body>
</html>
"""


# -------- WiFi --------
ap = network.WLAN(network.AP_IF)

ap.active(True)

ap.config(
essid="ESP32_First",
password="12345678",
authmode=3
)


# -------- Server --------
sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)

sock.setblocking(False)

sock.bind(('',80))

sock.listen(5)


load()

lcd.clear()

print("Server Ready")
print("Connect WiFi: ESP32_First")
print("URL: http://192.168.4.1")


while True:

    timer_task()

    lcd_default()

    try:

        conn,addr = sock.accept()

        request = conn.recv(1024).decode()

        if not request:
            continue

        path = request.split(' ')[1]

        parts = [p for p in path.split('/') if p]

        res_body=""

        # ----- API -----

        if len(parts)==3:

            h,m,s = int(parts[0]),int(parts[1]),int(parts[2])

            rtc.datetime((2026,1,1,h,m,s,0,0))

            res_body="%02d,%02d,%02d"%(h,m,s)

            lcd_alert("RTC SETTING","%02d:%02d:%02d"%(h,m,s))


        elif len(parts)==1:

            c=parts[0]

            if c=='2':

                t=rtc.datetime()

                res_body="%02d,%02d,%02d"%(t[4],t[5],t[6])


            elif c=='3':

                data["timer"]=False
                save()

                DEV.off()

                res_body="OFF"

                lcd_alert("DEVICE STATUS","OFF")


            elif c=='4':

                data["timer"]=False
                save()

                DEV.on()

                res_body="ON"

                lcd_alert("DEVICE STATUS","ON")


            elif c=='6':

                data["timer"]=False
                save()

                res_body="OFF"

                lcd_alert("TIMER SYSTEM","OFF")


            elif c=='7':

                data["timer"]=True
                save()

                res_body="ON"

                lcd_alert("TIMER SYSTEM","ON")


        elif len(parts)==4:

            cmd,h,m,s = parts[0],int(parts[1]),int(parts[2]),int(parts[3])

            res_body="%02d,%02d,%02d"%(h,m,s)

            if cmd=='9':

                data["start"]=h*3600+m*60+s
                save()

                lcd_alert("START TIME SET","%02d:%02d:%02d"%(h,m,s))


            elif cmd=='10':

                data["stop"]=h*3600+m*60+s
                save()

                lcd_alert("STOP TIME SET","%02d:%02d:%02d"%(h,m,s))


        # ----- RESPONSE -----

        if path=="/":

            conn.send('HTTP/1.1 200 OK\nContent-Type: text/html\nConnection: close\n\n')

            conn.sendall(get_html())

        else:

            conn.send('HTTP/1.1 200 OK\nContent-Type: text/plain\nConnection: close\n\n')

            conn.sendall(res_body)

        conn.close()

    except:
        pass

    time.sleep_ms(20)
