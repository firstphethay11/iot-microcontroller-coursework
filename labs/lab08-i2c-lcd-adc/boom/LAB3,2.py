from machine import Pin, I2C
from time import sleep, ticks_ms

# -----------------------------
# Keypad Setup
# -----------------------------
colPins = [14, 15, 32, 33]   # คอลัมน์
rowPins = [4, 5, 12, 13]     # แถว

rows = [Pin(pin, Pin.OUT) for pin in rowPins]
cols = [Pin(pin, Pin.IN, Pin.PULL_UP) for pin in colPins]  # ใช้ Pull-up

keys = [
    ['1','2','3','A'],
    ['4','5','6','B'],
    ['7','8','9','C'],
    ['*','0','#','D']
]

# -----------------------------
# LCD I2C Setup
# -----------------------------
from lcd_api import LcdApi
from i2c_lcd import I2cLcd

i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
lcd = I2cLcd(i2c, 0x27, 2, 16)

# -----------------------------
# Read Key Function
# -----------------------------
def get_key():
    for r in range(4):
        rows[r].value(0)
        for c in range(4):
            if cols[c].value() == 0:  # กดปุ่ม → 0
                rows[r].value(1)
                sleep(0.2)  # debounce
                return keys[r][c]
        rows[r].value(1)
    return None

# -----------------------------
# Input number with timeout
# -----------------------------
def input_number(timeout=5000):
    lcd.clear()
    lcd.putstr("Enter number ")

    data = ""
    start = ticks_ms()

    while ticks_ms() - start < timeout:
        k = get_key()
        if k:
            if k == '#':      # complete input
                return data
            if k.isdigit():
                data += k
                lcd.clear()
                lcd.putstr("Input: " + data)
            sleep(0.2)

    # timeout (no number or no #)
    return None

# -----------------------------
# Count Loop (0–user_value)
# -----------------------------
def count_loop(max_value):
    if not max_value.isdigit():
        return
    max_val = int(max_value)
    i = 0
    while True:
        lcd.clear()
        lcd.putstr("Count: {:02d}".format(i))
        sleep(0.5)

        # check if user presses *
        key = get_key()
        if key == '*':
            return   # กลับไปหน้าแรก

        i += 1
        if i > max_val:
            i = 0    # loop 0–max_value

# -----------------------------
# Main Program
# -----------------------------
while True:
    # 1) First screen: wait for *
    lcd.clear()
    lcd.putstr("Press * to start")

    while True:
        k = get_key()
        if k == '*':
            sleep(0.2)
            break

    # 2) Ask user to enter number within 5 seconds
    num = input_number(timeout=5000)

    # 3) If no input or no # → back to first screen
    if num is None or num == "":
        continue

    # 4) Show entered number
    lcd.clear()
    lcd.putstr("Number: " + num)
    sleep(1)  # แสดงเลข 1 วินาที

    # 5) Start counting loop up to entered number
    count_loop(num)
