from machine import Pin, SoftI2C
from ds3231 import DS3231
from i2c_lcd import I2cLcd
from time import sleep

# I2C
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))

# RTC + LCD
rtc = DS3231(i2c)
lcd = I2cLcd(i2c, 0x27, 2, 16)

days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

while True:
    t = rtc.datetime()

    day_name = days[t[3]]
    date_str = "{} {:02}/{:02}/{}".format(day_name, t[2], t[1], t[0])
    time_str = "Time {:02}:{:02}:{:02}".format(t[4], t[5], t[6])

    lcd.clear()
    lcd.putstr(date_str)
    lcd.move_to(0, 1)
    lcd.putstr(time_str)

    sleep(1)
