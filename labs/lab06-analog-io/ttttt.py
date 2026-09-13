from machine import Pin
from time import sleep, ticks_ms, ticks_diff

# --- ตัวแปรสำหรับจัดการ Interrupt ---
count = 0
last_interrupt_time = 0
DEBOUNCE_MS = 200
UPDATE_FLAG = False

# --- 1. ฟังก์ชัน Callback ที่จะถูกเรียกโดย Interrupt (ISR) ---
def handle_interrupt(pin):
    global count, last_interrupt_time, UPDATE_FLAG
    
    new_time = ticks_ms()
    
    if ticks_diff(new_time, last_interrupt_time) > DEBOUNCE_MS:
        count += 1
        UPDATE_FLAG = True
        last_interrupt_time = new_time

# --- 2. ตั้งค่า Pin ---
sensor_pin = Pin(2, Pin.IN, Pin.PULL_UP)

# --- 3. ผูก Interrupt เข้ากับ Pin ---
sensor_pin.irq(trigger=Pin.IRQ_FALLING, handler=handle_interrupt)

# --- 4. ลูปการทำงานหลัก (Main Loop) ---
print("ระบบทดสอบ Interrupt พร้อมทำงาน")
print("กรุณากดสวิตช์ที่ขา D2 (GPIO 2)...")

while True:
    # ✅ แก้ไข: ลบ 'global' ออกจากลูปนี้
    # เพราะเราอยู่ใน Main scope อยู่แล้ว ไม่จำเป็นต้องใช้
    
    # ตรวจสอบว่า "ธงถูกยก" หรือไม่
    if UPDATE_FLAG:
        print(f"Count: {count}")
        UPDATE_FLAG = False # เอาธงลง
    
    sleep(0.01)