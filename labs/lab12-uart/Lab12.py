from machine import UART
import time

uart = UART(2, baudrate=9600, tx=17, rx=16)

while True:
    cmd = input("CMD: ")
    uart.write(cmd + "#")

    data = bytearray()
    while True:
        if uart.any():
            data.extend(uart.read())
            if data[-1] == 35:   # '#'
                break

    print("RX:", data.decode()[:-1])


