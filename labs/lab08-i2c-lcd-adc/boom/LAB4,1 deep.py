from machine import ADC, Pin, PWM
from time import sleep

# -----------------------------
# ตั้งค่า POT
# -----------------------------
pot = ADC(Pin(34))
pot.atten(ADC.ATTN_11DB)
pot.width(ADC.WIDTH_12BIT)

# -----------------------------
# ตั้งค่า LED PWM
# -----------------------------
led = PWM(Pin(5), freq=1000)
led.duty(0)  # เริ่มต้น LED ดับ

# -----------------------------
# วนทำงานเรื่อยๆ
# -----------------------------
while True:
    # 1️⃣ อ่านค่า Pot
    value = pot.read()                   # 0–4095
    duty = int((value / 4095) * 1023)    # แปลงเป็น PWM 0–1023
    
    # 2️⃣ LED ติดตามค่า 2 วินาที
    led.duty(duty)
    print("LED ติด 2 วิ | ADC =", value, "Duty =", duty)
    sleep(2)
    
    # 3️⃣ LED ดับ 3 วินาที
    led.duty(0)
    print("LED ดับ 5 วิ")
    sleep(5)