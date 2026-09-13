# ===== ESP-NOW RECEIVER + I2C LCD STATUS =====
#MPY: soft reboot
#MAC Address (Raw): b'@"\xd8O\x91\x18'
#MAC Address (Hex): 4022d84f9118
#MAC Address (Format): 40:22:d8:4f:91:18
#com6
#peer = b'\x14\x33\x5c\x38\x06\xdc'
# ===== ESP-NOW RECEIVER FINAL =====
import network, espnow, time, json
from machine import Pin, RTC, SoftI2C
from i2c_lcd import I2cLcd

# ---------- Wi-Fi ESP-NOW ----------
sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.disconnect()

e = espnow.ESPNow()
e.active(True)

peer = b'\x14\x33\x5c\x38\x06\xdc'   # MAC sender
e.add_peer(peer)

# ---------- DEVICE (Active-LOW) ----------
led2 = Pin(25, Pin.OUT)

# ---------- RTC ----------
rtc = RTC()

# ---------- I2C LCD ----------
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
lcd = I2cLcd(i2c, 0x27, 2, 16)
lcd.clear()

# ---------- DEFAULT STATE ----------
timer_enable = False
start_h, start_m, start_s = 0, 0, 0
stop_h, stop_m, stop_s = 0, 0, 0


# =====================================================
# SAVE / LOAD STATE  (ไม่บันทึกเวลา RTC)
# =====================================================
def save_state():
    data = {
        "dev": led2.value(),
        "timer": timer_enable,
        "start": [start_h, start_m, start_s],
        "stop": [stop_h, stop_m, stop_s]
    }
    try:
        with open("state.json", "w") as f:
            json.dump(data, f)
    except:
        pass


def load_state():
    global timer_enable, start_h, start_m, start_s, stop_h, stop_m, stop_s
    try:
        with open("state.json", "r") as f:
            d = json.load(f)

        led2.value(d["dev"])
        timer_enable = d["timer"]

        start_h, start_m, start_s = d["start"]
        stop_h, stop_m, stop_s = d["stop"]

    except:
        led2.value(1)  # ปิดถ้าไม่มีไฟล์


load_state()

print("--- Receiver Ready! ---")


# =====================================================
# MAIN LOOP
# =====================================================
while True:

    # ===== RECEIVE ESP-NOW =====
    if e.any():
        host, data_bytes = e.recv()

        if data_bytes and data_bytes[-1] == 35:  # '#'
            cmd = data_bytes.decode().strip()[:-1].split(",")
            c = cmd[0]
            reply = "Error!#"

            try:
                # 1 ตั้งเวลา RTC
                if c == '1' and len(cmd) == 4:
                    rtc.datetime((2026,1,1,0,int(cmd[1]),int(cmd[2]),int(cmd[3]),0))
                    reply = "OK!#"

                # 2 ขอเวลา
                elif c == '2':
                    t = rtc.datetime()
                    reply = f"Time:{t[4]:02d}:{t[5]:02d}:{t[6]:02d}#"

                # 3 DEV OFF
                elif c == '3':
                    led2.value(1)
                    save_state()
                    reply = "OK!#"

                # 4 DEV ON
                elif c == '4':
                    led2.value(0)
                    save_state()
                    reply = "OK!#"

                # 5 DEV STATUS
                elif c == '5':
                    status = "on" if led2.value()==0 else "off"
                    reply = f"DEV is {status}.#"

                # 6 TIMER OFF
                elif c == '6':
                    timer_enable = False
                    save_state()
                    reply = "OK!#"

                # 7 TIMER ON
                elif c == '7':
                    timer_enable = True
                    save_state()
                    reply = "OK!#"

                # 8 TIMER STATUS
                elif c == '8':
                    status = "on" if timer_enable else "off"
                    reply = f"TIMER is {status}.#"

                # 9 SET START
                elif c == '9' and len(cmd)==4:
                    start_h,start_m,start_s = int(cmd[1]),int(cmd[2]),int(cmd[3])
                    save_state()
                    reply = "OK!#"

                # 10 SET STOP
                elif c == '10' and len(cmd)==4:
                    stop_h,stop_m,stop_s = int(cmd[1]),int(cmd[2]),int(cmd[3])
                    save_state()
                    reply = "OK!#"

                # 11 SHOW RANGE
                elif c == '11':
                    reply = (
                        f"Time control:"
                        f"{start_h:02d}:{start_m:02d}:{start_s:02d}-"
                        f"{stop_h:02d}:{stop_m:02d}:{stop_s:02d}#"
                    )

            except:
                reply = "Error: Format Incorrect#"

            e.send(peer, reply.encode(), True)


    # ===== AUTO TIMER =====
    if timer_enable:
        t = rtc.datetime()
        curr = t[4]*3600 + t[5]*60 + t[6]
        st = start_h*3600 + start_m*60 + start_s
        sp = stop_h*3600 + stop_m*60 + stop_s

        if st <= sp:
            should_on = st <= curr < sp
        else:
            should_on = (curr >= st or curr < sp)

        led2.value(0 if should_on else 1)


    # ===== LCD STATUS =====
    t = rtc.datetime()
    dev = "ON " if led2.value()==0 else "OFF"
    tim = "ON " if timer_enable else "OFF"

    lcd.move_to(0,0)
    lcd.putstr(f"Time {t[4]:02d}:{t[5]:02d}:{t[6]:02d} ")

    lcd.move_to(0,1)
    lcd.putstr(f"D:{dev} T:{tim}   ")

    time.sleep(0.2)


