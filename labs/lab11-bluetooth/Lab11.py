from machine import Pin, SoftI2C
import machine
from time import sleep, sleep_ms, ticks_ms, ticks_diff
from ds3231 import DS3231
from i2c_lcd import I2cLcd
import json
import ble_uart

# ================= SETUP =================

i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)

ds = DS3231(i2c)
lcd = I2cLcd(i2c, 0x27, 2, 16)

uart = ble_uart.BLEUART("ESP32-Light")

LED = Pin(25, Pin.OUT)

# ================= GLOBAL =================

device_on = False
timer_enable = False

start_time = (18,0,0)
stop_time = (6,0,0)

last_check = 0

# ================= KEYPAD =================

key_matrix = [
['1','2','3','A'],
['4','5','6','B'],
['7','8','9','C'],
['*','0','#','D']
]

rows = [Pin(p, Pin.OUT) for p in [4,5,12,13]]
cols = [Pin(p, Pin.IN, Pin.PULL_DOWN) for p in [14,15,32,33]]

# ================= SAVE CONFIG =================

def save_settings():
    data={
    "timer_enable":timer_enable,
    "start_time":start_time,
    "stop_time":stop_time
    }
    
    with open("config.json","w") as f:
        json.dump(data,f)

def load_settings():
    global timer_enable,start_time,stop_time
    
    try:
        with open("config.json","r") as f:
            data=json.load(f)
            
            timer_enable=data["timer_enable"]
            start_time=tuple(data["start_time"])
            stop_time=tuple(data["stop_time"])
    except:
        pass

# ================= KEYPAD SCAN =================

def scan_keypad():
    
    for r in range(4):
        
        rows[r].value(1)
        
        for c in range(4):
            
            if cols[c].value():
                
                sleep_ms(50)
                
                if cols[c].value():
                    
                    key=key_matrix[r][c]
                    
                    while cols[c].value():
                        pass
                    
                    rows[r].value(0)
                    
                    return key
        
        rows[r].value(0)
    
    return None

# ================= TIMER =================

def check_timer():
    
    global device_on,last_check
    
    now=ticks_ms()
    
    if ticks_diff(now,last_check)<1000:
        return
    
    last_check=now
    
    if not timer_enable:
        return
    
    t=ds.datetime()
    
    h,m,s=t[4],t[5],t[6]
    
    now_sec=h*3600+m*60+s
    
    start_sec=start_time[0]*3600+start_time[1]*60+start_time[2]
    
    stop_sec=stop_time[0]*3600+stop_time[1]*60+stop_time[2]
    
    should_on=False
    
    if start_sec<stop_sec:
        
        if start_sec<=now_sec<stop_sec:
            should_on=True
    
    else:
        
        if now_sec>=start_sec or now_sec<stop_sec:
            should_on=True
    
    if should_on:
        
        LED.value(0)
        device_on=True
        
    else:
        
        LED.value(1)
        device_on=False

# ================= BLUETOOTH =================

def bluetooth_control():
    
    global device_on,timer_enable,start_time,stop_time
    
    if uart.any():
        
        msg=uart.read().decode().strip()
        
        print("BT:",msg)
        
        parts=msg.split(",")
        
        cmd=int(parts[0])
        
        if cmd==1:
            
            h=int(parts[1])
            m=int(parts[2])
            s=int(parts[3])
            
            ds.datetime((2024,1,1,h,m,s,0,0))
            
            uart.write("TIME SET\n")
        
        elif cmd==2:
            
            t=ds.datetime()
            
            uart.write("%02d:%02d:%02d\n"%(t[4],t[5],t[6]))
        
        elif cmd==3:
            
            LED.value(1)
            device_on=False
            
            uart.write("LED OFF\n")
        
        elif cmd==4:
            
            LED.value(0)
            device_on=True
            
            uart.write("LED ON\n")
        
        elif cmd==6:
            
            timer_enable=False
            
            save_settings()
            
            uart.write("TIMER OFF\n")
        
        elif cmd==7:
            
            timer_enable=True
            
            save_settings()
            
            uart.write("TIMER ON\n")
        
        elif cmd==9:
            
            h=int(parts[1])
            m=int(parts[2])
            s=int(parts[3])
            
            start_time=(h,m,s)
            
            save_settings()
            
            uart.write("START SAVED\n")
        
        elif cmd==10:
            
            h=int(parts[1])
            m=int(parts[2])
            s=int(parts[3])
            
            stop_time=(h,m,s)
            
            save_settings()
            
            uart.write("STOP SAVED\n")

# ================= DISPLAY =================

def show_home():
    
    lcd.clear()
    
    while True:
        
        bluetooth_control()
        check_timer()
        
        t=ds.datetime()
        
        lcd.move_to(0,0)
        lcd.putstr("Time %02d:%02d:%02d"%(t[4],t[5],t[6]))
        
        lcd.move_to(0,1)
        
        timer="ON" if timer_enable else "OFF"
        dev="ON" if device_on else "OFF"
        
        lcd.putstr("T:%s D:%s"%(timer,dev))
        
        key=scan_keypad()
        
        if key:
            return key
        
        sleep_ms(200)

# ================= MENU =================

def manual_on():
    
    global device_on
    
    LED.value(0)
    device_on=True
    
    lcd.clear()
    lcd.putstr("MANUAL ON")
    
    sleep(1)

def manual_off():
    
    global device_on
    
    LED.value(1)
    device_on=False
    
    lcd.clear()
    lcd.putstr("MANUAL OFF")
    
    sleep(1)

def timer_on():
    
    global timer_enable
    
    timer_enable=True
    
    save_settings()
    
    lcd.clear()
    lcd.putstr("TIMER ON")
    
    sleep(1)

def timer_off():
    
    global timer_enable
    
    timer_enable=False
    
    save_settings()
    
    lcd.clear()
    lcd.putstr("TIMER OFF")
    
    sleep(1)

# ================= MAIN =================

load_settings()

lcd.clear()
lcd.putstr("System Start")

sleep(1)

next_key='2'

while True:
    
    key=show_home()
    
    if key=='3':
        manual_off()
    
    elif key=='4':
        manual_on()
    
    elif key=='6':
        timer_off()
    
    elif key=='7':
        timer_on()
    
    sleep_ms(100)