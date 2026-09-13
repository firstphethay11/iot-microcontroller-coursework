import bluetooth
import network
from machine import Pin, I2C, PWM
from time import ticks_ms, ticks_diff, sleep
from ds3231 import DS3231
from bh1750 import BH1750
import json
import ufirebase as firebase
import gc
from i2c_lcd import I2cLcd
from micropython import const, schedule
import struct

gc.collect()

key_matrix = [
    ['1', '2', '3', 'A'],
    ['4', '5', '6', 'B'],
    ['7', '8', '9', 'C'],
    ['*', '0', '#', 'D']
]

colPins = [14,15,32,33]
rowPins = [4,5,12,13]
rows = [Pin(pin_name, mode=Pin.OUT) for pin_name in rowPins] 
columns = [Pin(pin_name, mode=Pin.IN, pull=Pin.PULL_DOWN) for pin_name in colPins]

i2c = I2C(0, sda=Pin(21), scl=Pin(22), freq=400000)
rtc = DS3231(i2c)
light_sensor = BH1750(i2c)
lcd = I2cLcd(i2c, 0x27, 2, 16)

led = PWM(Pin(18), freq=1000)
led.duty(0)

ble_name = "First"
buffer_size = 100

data = {
    "s1": 0, "e1": 0,
    "s2": 0, "e2": 0,
    "min_lux": 100,
    "max_lux": 1000,
    "timer": "off",
    "target_brightness": 0,
    "current_brightness": 0
}

screen_time = 0
last_lcd_update = 0
last_time = 0
last_check_command = 0

SSID = "First-Ji"
PASSWORD = "09806first1"

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.disconnect()

try:
    wlan.connect(SSID, PASSWORD)
    print(f"Connecting to {SSID}...")
    while not wlan.isconnected():
        sleep(0.02)
    print(f"Connected! with IP: {wlan.ifconfig()[0]}")
except Exception as e:
    print(e)

firebase.setURL("https://labfirebase-ffe94-default-rtdb.asia-southeast1.firebasedatabase.app/")

_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID128 = const(0x07)
_ADV_TYPE_APPEARANCE = const(0x19)

def advertising_payload(limited_disc=False, br_edr=False, name=None, services=None, appearance=0):
    payload = bytearray()
    
    def _append(adv_type, value):
        nonlocal payload
        payload += struct.pack("BB", len(value) + 1, adv_type) + value
    
    _append(
        _ADV_TYPE_FLAGS,
        struct.pack("B", (0x01 if limited_disc else 0x02) + (0x18 if br_edr else 0x04)),
    )
    
    if name:
        _append(_ADV_TYPE_NAME, name)
        
    if services:
        for uuid in services:
            b = bytes(uuid)
            if len(b) == 16:
                _append(_ADV_TYPE_UUID128, b)
                
    if appearance:
        _append(_ADV_TYPE_APPEARANCE, struct.pack("<h", appearance))
    
    return payload 

class BLEUART:
    _UART_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
    _UART_TX = (bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E"), bluetooth.FLAG_NOTIFY)
    _UART_RX = (bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E"), bluetooth.FLAG_WRITE)
    _UART_SERVICE = (_UART_UUID, (_UART_TX, _UART_RX))
    
    def __init__(self, name="ESP32-BLE"):
        self._ble = bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._tx_handle, self._rx_handle), ) = self._ble.gatts_register_services((self._UART_SERVICE, ))
        self._ble.gatts_set_buffer(self._rx_handle, buffer_size, True)
        self._connections = set()
        self._rx_buffer = bytearray()
        self._handler = None
        
        self._payload = advertising_payload(name=name, services=[self._UART_UUID])
        self._advertise()
        
    def irq(self, handler):
        self._handler = handler
        
    def _irq(self, event, data):
        if event == 1:
            connection_handle, _, _ = data
            self._connections.add(connection_handle)
            print(f"Connected: {connection_handle}")
        elif event == 2:
            connection_handle, _, _ = data
            self._connections.remove(connection_handle)
            sleep(1)
            self._advertise()
            print(f"Disconnection: {connection_handle}")
        elif event == 3:
            connection_handle, value_handle = data
            if value_handle == self._rx_handle:
                self._rx_buffer += self._ble.gatts_read(self._rx_handle)
                if self._handler:
                    self._handler()
    
    def any(self):
        return len(self._rx_buffer)

    def read(self):
        data = self._rx_buffer[:]
        self._rx_buffer = bytearray()
        return data
    
    def write(self, data):
        for conn_handle in self._connections:
            self._ble.gatts_notify(conn_handle, self._tx_handle, data)
            
    def close(self):
          for conn_handle in self._connections:
              self._ble.gap_disconnect(conn_handle)
          self._connections.clear()
          self._ble.active(False)
                
    def _advertise(self, interval_us=500000):
        self._ble.gap_advertise(interval_us, adv_data=self._payload)
        
def on_ble_rx():
    global ble_command
    if Ble.any():
        try:
            received = Ble.read().decode().strip()
            print(f"Received Command from BLE: {received}")
            ble_command = received
        except Exception as e:
            print(f"ERROR: {e}")
            Ble.write("ERROR: Processing Failed\n".encode())
            ble_command = ''

def map_value(value, in_min, in_max, out_min, out_max):
    result = (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    return result

def scanKeypad():
    key = ''
    for row in range(len(rows)):
        rows[row].value(1)
        for col in range(len(columns)):
            if columns[col].value() == 1:
                key = key_matrix[row][col]
                rows[row].value(0)
                return key
        rows[row].value(0)
    return key

def back_space(x, y, amount, key=' '):
    lcd.move_to(x, y)
    for i in range(amount):
        lcd.putstr(key)
    lcd.move_to(x, y)

def wait_release():
    while scanKeypad():
        sleep(0.01)

def read_number():
    global last_time
    wait_release()
    num = ""
    while True:
        if ticks_diff(ticks_ms(), last_time) > 10000: break
        key = scanKeypad()
        if key:
            last_time = ticks_ms()
            if key.isdigit():
                num += key
                lcd.putstr(key)
            elif (key == '#') and num:
                return int(num)
            wait_release()
        sleep(0.02)

def read_time_number():
    wait_release()
    num = ""
    lcd.show_cursor()
    lcd.blink_cursor_on()
    while True:
        key = scanKeypad()
        if key.isdigit() and len(num) < 2:
            num += key
            lcd.putstr(key)
            if len(num) == 2:
                lcd.hide_cursor()
        elif (key == '#') and num:
            return int(num)
        wait_release()
        sleep(0.02)

def recovery_data():
    global data
    try: 
        with open('backup.json', 'r') as file:
            data.update(json.load(file))
    except: 
        backup_data()

def backup_data():
    with open('backup.json', 'w') as file:
        json.dump(data, file)
        
def time_convert(sec):
    hour = sec // 3600
    minute = (sec % 3600) // 60
    second = sec % 60
    return hour, minute, second

def get_time():
    wait_release()
    lcd.move_to(4, 1)
    
    hour = read_time_number()
    while hour > 23:
        back_space(4, 1, 2, '0')
        hour = read_time_number()
    lcd.move_to(7, 1)
    
    minute = read_time_number()
    while minute > 59:
        back_space(7, 1, 2, '0')
        minute = read_time_number()
    lcd.move_to(10, 1)
    
    second = read_time_number()
    while second > 59:
        back_space(10, 1, 2, '0')
        second = read_time_number()
        
    lcd.hide_cursor()
    lcd.clear()
        
    return hour, minute, second

def set_time(mode=1, option=1, web=0, ble=0, string_data=''):
    if web or ble:
        hour = int(string_data[1])
        minute = int(string_data[2])
        second = int(string_data[3])
    else:
        lcd.clear()
        if mode == 1:
            lcd.putstr("    Set time")
        elif mode == 2:
            if option == 1:
                lcd.putstr("  Start time 1")
            elif option == 2:
                lcd.putstr("  Start time 2")
        elif mode == 3:
            if option == 1:
                lcd.putstr("   Stop time 1")
            elif option == 2:
                lcd.putstr("   Stop time 2")
            
        lcd.move_to(1, 1)
        lcd.putstr(f">> {00:02}:{00:02}:{00:02} <<")
        
        hour, minute, second = get_time()
    
    new_time = (hour * 3600) + (minute * 60) + second
    if mode == 1:
        current = rtc.datetime()
        new_date = [current[0], current[1], current[2], hour, minute, second, current[3]]
        rtc.datetime(new_date)
    elif mode == 2:
        if option == 1:
            data["s1"] = new_time
        elif option == 2:
            data["s2"] = new_time
    elif mode == 3:
        if option == 1:
            data["e1"] = new_time
        elif option == 2:
            data["e2"] = new_time

def set_brightness_range(web=0, ble=0, luxs=''):
    if web or ble:
        new_min_lux = luxs[1]
        new_max_lux = luxs[2]
    else:
        lcd.clear()
        lcd.putstr("Min lux: ")
        new_min_lux = read_number()
        lcd.move_to(0, 1)
        lcd.putstr("Max lux: ")
        new_max_lux = read_number()
        
    data['min_lux'] = new_min_lux
    data['max_lux'] = new_max_lux
    lcd.clear()

def show_brightness_range():
    global screen_time
    lcd.clear()
    lcd.putstr(f"Min lux: {data['min_lux']}")
    lcd.move_to(0, 1)
    lcd.putstr(f"Max lux: {data['max_lux']}")
    screen_time = ticks_ms()
    return f"Light range: {data['min_lux']} - {data['max_lux']}"

def show_lux():
    global screen_time
    lux_value = light_sensor.luminance(BH1750.ONCE_HIRES_1)
    
    lcd.clear()
    lcd.putstr(f"Bright: {lux_value:.1f} lux")
    screen_time = ticks_ms()
    return f"Bright: {lux_value:.1f}"

def show_time_range(period=1):
    global screen_time
    
    if period == 1:
        sh, sm, ss = time_convert(data['s1'])
        eh, em, es = time_convert(data['e1'])
    else:
        sh, sm, ss = time_convert(data['s2'])
        eh, em, es = time_convert(data['e2'])
        
    lcd.clear()
    lcd.putstr(f"Start{period}: {sh:02}:{sm:02}:{ss:02}")
    lcd.move_to(0, 1)
    lcd.putstr(f"Stop {period}: {eh:02}:{em:02}:{es:02}")
    screen_time = ticks_ms()
    return f"Period{period}: {sh:02}:{sm:02}:{ss:02} - {eh:02}:{em:02}:{es:02}"

def set_brightness_target(web=0, ble=0, percen=0):
    if not web and not ble:
        lcd.clear()
        lcd.putstr(f"Brightness(%):")
        lcd.move_to(0, 1)
        lcd.putstr(">>")
        percen = read_number()
 
    if percen > 100: percen = 100
    if percen < 0: percen = 0
    data['target_brightness'] = percen * 10.23
    
    if data['timer'] == "off":
        data['current_brightness'] = data['target_brightness']
        led.duty(int(data['current_brightness']))
    
def adjust_brightness(bright):
    data['current_brightness'] = bright
    led.duty(int(bright))

def show_current_time(web=0, ble=0, keypad=0):
    global screen_time
    current = rtc.datetime()
    hour = current[4]
    minute = current[5]
    second = current[6]
    if web or ble:
        lcd.clear()
        lcd.putstr(f"Time: {hour:02}:{minute:02}:{second:02}")
        screen_time = ticks_ms()
        return f"Time: {hour:02}:{minute:02}:{second:02}"
    elif keypad:
        lcd.clear()
        lcd.putstr(f"Time: {hour:02}:{minute:02}:{second:02}")
        screen_time = ticks_ms()
    else:
        lcd.putstr(f"{hour:02}:{minute:02}:{second:02}")

def show_detail():
    global screen_time
    if screen_time:
        if ticks_diff(ticks_ms(), screen_time) >= 3000:
            lcd.clear()
            screen_time = 0
    else:
        lcd.move_to(0, 0)
        show_current_time()
        lcd.putstr(f" L:{light_sensor.luminance(BH1750.ONCE_HIRES_1):.0f}  ")
        lcd.move_to(0, 1)
        lcd.putstr(f"LED: {int(data['current_brightness']/10.23)}% T:{data['timer']}  ")

def led_timer():
    current = rtc.datetime()
    current_time = (current[4] * 3600) + (current[5] * 60) + current[6]
    lux = light_sensor.luminance(BH1750.ONCE_HIRES_1)
    
    active_time1 = current_time >= data['s1'] and current_time < data['e1']
    active_time2 = current_time >= data['s2'] and current_time < data['e2']
    in_brightness_range = lux >= data['min_lux'] and lux < data['max_lux']
    
    if active_time1 or active_time2:
        if in_brightness_range:
            adjust_brightness(data['target_brightness'])
        else:
            adjust_brightness(0)
    else:
        if data['current_brightness'] > 0:
            adjust_brightness(0)
            
def execute(command, web=0, ble=0):
    try:
        cmd_part = [int(c) for c in str(command).split(',')]
        function = int(cmd_part[0])
    except: return
    
    res = ''
    if function == 1:
        set_time(mode=1, web=web, ble=ble, string_data=cmd_part)
        res = 'OK!'
    elif function == 2:
        if web or ble:
            set_brightness_target(web=web, ble=ble, percen=int(cmd_part[1]))
        else: set_brightness_target()
        res = 'OK!'
    elif function == 3:
        res = show_lux()
    elif function == 4:
        data['timer'] = "off"
        res = f"Timer is {data['timer']}"
    elif function == 5:
        data['timer'] = "on"
        res = f"Timer is {data['timer']}"
    elif function == 6:
        set_brightness_range(web=web, ble=ble, luxs=cmd_part)
        res = 'OK!'
    elif function == 7:
        res = show_brightness_range()
    elif function == 8:
        set_time(mode=2, option=1, web=web, ble=ble, string_data=cmd_part)
        res = 'OK!'
    elif function == 9:
        set_time(mode=3, option=1, web=web, ble=ble, string_data=cmd_part)
        res = 'OK!'
    elif function == 10:
        res = show_time_range(period=1)
    elif function == 11:
        set_time(mode=2, option=2, web=web, ble=ble, string_data=cmd_part)
        res = 'OK!'
    elif function == 12:
        set_time(mode=3, option=2, web=web, ble=ble, string_data=cmd_part)
        res = 'OK!'
    elif function == 13:
        res = show_time_range(period=2)
    elif function == 14:
        if web or ble:
            res = show_current_time(web=web, ble=ble)
        else:
            show_current_time(keypad=1)
    else:
        return
    
    if res:
        if web:
            respond(res)
        elif ble:
            Ble.write(res)
    
    backup_data()

def respond(msg):
    try: firebase.put("esp32", msg, bg=False)
    except: pass

def check_command():
    try:
        firebase.get("command", "current_cmd", bg=False)
        return firebase.current_cmd
    except: return 0

def reset_command(): 
    try:
        firebase.put("command", 0, bg=False)
    except Exception as e:
        print(f"Request Error: {e}")
    
def get_function():
    lcd.clear()
    lcd.putstr(f"Function: ")
    func_num = read_number()
    return func_num

keypad_command = ''
web_command = ''
ble_command = ''

if __name__ == "__main__":
    Ble = BLEUART(name=ble_name)
    Ble.irq(handler=on_ble_rx)
    recovery_data()
    led.duty(int(data['current_brightness']))
    show_detail()
    print(f"System Ready: {ble_name}.")
    while True:
        if ble_command:
            execute(ble_command, ble=1)
            ble_command = ''
        
        if scanKeypad() == '*':
            last_time = ticks_ms()
            keypad_command = get_function()
        
        if ticks_diff(ticks_ms(), last_check_command) > 2000:
            web_command = check_command()
            last_check_command = ticks_ms()
           
        if keypad_command:
            execute(keypad_command)
            keypad_command = ''
        elif web_command:
            execute(web_command, web=1)
            web_command = ''
            reset_command()
            
        if data['timer'] == 'on':
            led_timer()
        
        if ticks_diff(ticks_ms(), last_lcd_update) > 200:
            show_detail()
            last_lcd_update = ticks_ms()
    
        sleep(0.1)



