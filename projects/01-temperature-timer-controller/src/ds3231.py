# MicroPython DS3231 Real-Time Clock Driver
from micropython import const

DS3231_I2C_ADDR = const(0x68)

def bcd2dec(bcd):
    return ((bcd >> 4) * 10) + (bcd & 0x0F)

def dec2bcd(dec):
    return ((dec // 10) << 4) | (dec % 10)

class DS3231:
    def __init__(self, i2c, addr=DS3231_I2C_ADDR):
        self.i2c = i2c
        self.addr = addr

    def datetime(self, dt=None):
        if dt is None:
            buf = self.i2c.readfrom_mem(self.addr, 0x00, 7)
            sec = bcd2dec(buf[0] & 0x7F)
            minute = bcd2dec(buf[1])
            hour = bcd2dec(buf[2] & 0x3F)
            weekday = bcd2dec(buf[3])
            day = bcd2dec(buf[4])
            month = bcd2dec(buf[5] & 0x1F)
            year = bcd2dec(buf[6]) + 2000
            return (year, month, day, weekday, hour, minute, sec, 0)
        else:
            year, month, day, hour, minute, sec = dt[0], dt[1], dt[2], dt[3], dt[4], dt[5]
            weekday = dt[6] if len(dt) > 6 else 1
            buf = bytearray([
                dec2bcd(sec),
                dec2bcd(minute),
                dec2bcd(hour),
                dec2bcd(weekday),
                dec2bcd(day),
                dec2bcd(month),
                dec2bcd(year - 2000 if year >= 2000 else year)
            ])
            self.i2c.writeto_mem(self.addr, 0x00, buf)
