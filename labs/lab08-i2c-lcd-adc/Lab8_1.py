import machine
from machine import Pin, ADC, PWM, SoftI2C
from time import sleep
from i2c_lcd import I2cLcd

# =========================================
# 1. ตั้งค่า Hardware
# =========================================

# --- LCD Setup (I2C) ---
I2C_ADDR = 0x27
try:
    i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
    lcd = I2cLcd(i2c, I2C_ADDR, 2, 16)
except:
    print("LCD Error")
    lcd = None

# --- VR Setup (Pin 36) ---
vr_pin = ADC(Pin(36))
vr_pin.atten(ADC.ATTN_11DB)
vr_pin.width(ADC.WIDTH_12BIT) # 0-4095

# --- LED Setup (Pin 25) ---
led = PWM(Pin(25), freq=5000)

# =========================================
# 2. ฟังก์ชันหลัก (Main)
# =========================================

def main():
    # --- ตรวจสอบสถานะการตื่น ---
    if machine.reset_cause() == machine.DEEPSLEEP_RESET:
        print("Woke up from Deep Sleep (Timer)")
    else:
        print("Power On / Hard Reset")
        if lcd:
            lcd.clear()
            lcd.putstr("System Start...")
            sleep(1)

    # --- A. อ่านค่า (Input) ---
    vr_value = vr_pin.read()   # อ่านค่า VR (0-4095)
    
    # --- B. คำนวณความสว่าง (Processing) ---
    
    # 1. แปลงเป็นเปอร์เซ็นต์ (0.0 ถึง 1.0)
    percent = vr_value / 4095
    
    # 2. Gamma Correction (ให้แสงนุ่มนวล)
    corrected_percent = percent ** 2.5 
    
    # 3. แปลงเป็น PWM (0-1023)
    pwm_val = int(corrected_percent * 1023)
    
    # ✅ เลือกโหมด (Active High/Low)
    # ถ้าหมุนขวาแล้วสว่างน้อย ให้ใช้บรรทัดที่มี 1023 - ...
    # ถ้าหมุนขวาแล้วสว่างมาก ให้ใช้บรรทัด pwm_val เฉยๆ
    
    # led_brightness = 1023 - pwm_val  # (แบบกลับค่า)
    led_brightness = pwm_val         # (แบบปกติ)
    
    # --- C. สั่งงาน LED (Output) ---
    led.duty(led_brightness)
    
    # --- D. แสดงผลบน LCD ---
    if lcd:
        lcd.clear()
        lcd.putstr(f"VR Raw: {vr_value}")
        lcd.move_to(0, 1)
        lcd.putstr(f"LED PWM: {led_brightness}")
        
    print(f"VR: {vr_value} | LED PWM: {led_brightness}")
    
    # เปิดไฟค้างไว้ 2 วินาที ให้เห็นผล
    sleep(2)
    
    # (ถ้าอยากปิดไฟตอนหลับ ให้เอาคอมเมนต์ออก)
    # led.duty(0) 
    
    # --- E. เข้าโหมด Deep Sleep ---
    print("Going to Sleep for 5 seconds...")
    machine.deepsleep(5000) # หลับ 5 วินาที

if __name__ == "__main__":
    sleep(2) 
    main()
