from machine import Pin, SoftI2C
from time import sleep
from ds3231 import DS3231
from i2c_lcd import I2cLcd

# I2C
i2c = SoftI2C(sda=Pin(21), scl=Pin(22))

# RTC
rtc = DS3231(i2c)

# LCD
lcd = I2cLcd(i2c, 0x27, 2, 16)

while True:
    year, month, day, wd, hour, minute, second, _ = rtc.datetime()

    lcd.clear()
    lcd.putstr("Time {:02d}:{:02d}:{:02d}".format(hour, minute, second))
    lcd.move_to(0, 1)
    lcd.putstr("Date {:02d}/{:02d}/{:02d}".format(day, month, year % 100))

    sleep(1)
