#MPY: soft reboot
#MAC Address (Raw): b'\x143\\8\x06\xdc'
#MAC Address (Hex): 14335c3806dc
#MAC Address (Format): 14:33:5c:38:06:dc
#com4
#peer = b'\x40\x22\xd8\x4f\x91\x18'
# ESP32 Sender Code (ต้องกดปุ่ม D2 ก่อนส่ง)
import network
import espnow
from machine import Pin
import time

sta = network.WLAN(network.STA_IF)  
sta.active(True)
sta.disconnect()      

e = espnow.ESPNow()
e.active(True)
# MAC Address ของบอร์ดรับ
peer = b'\x40\x22\xd8\x4f\x91\x18'
e.add_peer(peer)

pin_button2 = Pin(2, mode=Pin.IN, pull=Pin.PULL_UP)

print("--- Sender Ready! ---")
print("Press SW (Pin D2) to send command.")

while True: 
    # เช็คการกดปุ่ม (ทำงานเมื่อกดปุ่ม)
    if pin_button2.value() == 0:
        time.sleep(0.3) # หน่วงเวลากันปุ่มเบิ้ล
        
        print("-" * 30)
        command1 = input('Input command (ex. 1,12,30,00 หรือ 2): ')
        command1 = command1.strip() + '#' # เติม # ปิดท้ายให้สอดคล้องกับตาราง
        data_bytes = command1.encode('utf-8')
        
        # สั่งส่งข้อมูล
        e.send(peer, data_bytes, True)
        
        # รอรับคำตอบ (ระบบใส่เวลา Timeout กันบอร์ดค้าง)
        timeout = 50 
        reply_received = False
        
        while timeout > 0:
            if e.any():
                host, recv_data = e.recv()
                if recv_data[-1] == 35: # เช็คว่าลงท้ายด้วย '#'
                    # ปริ้นท์คำตอบโดยตัดเครื่องหมาย # ตัวท้ายออก
                    print("Result:", recv_data.decode('utf-8').strip()[:-1])
                    reply_received = True
                    break
            time.sleep(0.1)
            timeout -= 1
            
        if not reply_received:
            print("Result: Timeout!")
            
        print("Press SW (Pin D2) to send command.")

