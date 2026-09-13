import _thread
import time
from machine import Pin

# Define a coroutine to blink an LED
def blink_led(led_pin, delay_ms):
    led = Pin(led_pin, Pin.OUT)
    while True:
        led.value(1)  # Turn LED on
        time.sleep_ms(delay_ms)
        led.value(0)  # Turn LED off
        time.sleep_ms(delay_ms)
# Define another coroutine to print a message periodically
def print_message(message, interval_ms):
    while True:
        print(message)
        time.sleep_ms(interval_ms)
# Start the threads
# Blink LED on pin 2 every 500ms
_thread.start_new_thread(blink_led, (2, 500,))
# Print message every 2 seconds
_thread.start_new_thread(print_message, ("Hello", 2000,))

# Main program can do other things or simply keep running
while True:
    # Do other main program tasks here if needed
    time.sleep(1)
