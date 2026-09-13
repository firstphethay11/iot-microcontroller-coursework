from machine import Pin, ADC
from time import sleep

# 1. ตั้งค่าขา Pin 36 ให้เป็นขาอ่านค่า Analog (ADC)
vr_pin = ADC(Pin(36))

# 2. ตั้งค่า Attenuation เพื่อให้อ่านค่าไฟได้เต็มช่วง 0 - 3.3V
# (ถ้าไม่ตั้งค่านี้ จะอ่านได้สูงสุดแค่ประมาณ 1.1V)
vr_pin.atten(ADC.ATTN_11DB)

# 3. (ทางเลือก) ตั้งค่าความละเอียดเป็น 12-bit (ค่า 0 - 4095)
# โดยปกติ ESP32 เป็น 12-bit อยู่แล้ว แต่อาจตั้งไว้เพื่อความชัวร์
vr_pin.width(ADC.WIDTH_12BIT)

print("Start reading VR on Pin 36...")

while True:
    # อ่านค่าดิบ (Raw Value) ช่วง 0 - 4095
    raw_value = vr_pin.read()
    
    # แปลงเป็นค่าแรงดันไฟฟ้า (Voltage) 0.0 - 3.3V (โดยประมาณ)
    voltage = (raw_value / 4095) * 3.3
    
    # แสดงผล
    print("Raw Value: {}, Voltage: {:.2f} V".format(raw_value, voltage))
    
    # หน่วงเวลา 0.1 วินาที เพื่อให้ดูทัน
    sleep(0.1)