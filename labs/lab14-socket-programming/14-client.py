##Tx
import network
import socket
import time
from machine import Pin

# -------- BUTTON SETUP --------
sw = Pin(2, Pin.IN, Pin.PULL_UP)

# -------- Wi-Fi STA Setup --------
wlan = network.WLAN(network.STA_IF)
wlan.active(False)
time.sleep(0.5)
wlan.active(True)

print("กำลังเชื่อมต่อกับ ESP32_RX_Timer", end="")
wlan.connect("ESP32_RX_Timer", "password123") 

timeout = 30 
while not wlan.isconnected() and timeout > 0:
    print(".", end="")
    time.sleep(0.5)
    timeout -= 1

if wlan.isconnected():
    print("\nเชื่อมต่อสำเร็จ! IP :", wlan.ifconfig()[0])
else:
    print("\nเชื่อมต่อล้มเหลว! ไม่พบ Wi-Fi")
    while True:
        pass 

# -------- Socket Setup --------
server_addr = ('192.168.4.1', 8080)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(0)

# -------- ฟังก์ชันส่งคำสั่ง --------
def send_cmd(cmd):
    if not cmd.endswith("#"):
        cmd += "#"
    try:
        sock.sendto(cmd.encode(), server_addr)
        print(f"ส่งคำสั่ง -> {cmd}")
    except Exception as err:
        print(f"ส่งคำสั่งไม่สำเร็จ: {err}")

# -------- ฟังก์ชันรอรับการตอบกลับ --------
def wait_response(timeout_ms=1500):
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
        try:
            msg, addr = sock.recvfrom(1024)
            if msg:
                print(f"คำตอบจาก Server <- {msg.decode()}")
                return
        except OSError:
            pass
        time.sleep(0.05)
    print("ไม่มีการตอบกลับ (Timeout)")

# -------- MAIN LOOP --------
print("กดปุ่ม SW1 เพื่อส่งคำสั่ง")

while True:
    try:
        if sw.value() == 0:
            time.sleep_ms(50)
            
            if sw.value() == 0:
                user_input = input("พิมพ์คำสั่ง: ")
                
                if user_input.strip() != "":
                    send_cmd(user_input)
                    wait_response(1500)
                
                while sw.value() == 0:
                    time.sleep_ms(10)
        
        time.sleep_ms(20)

    except KeyboardInterrupt:
        print("\nหยุดโปรแกรม")
        break
    except Exception as e_err:
        print("เกิดข้อผิดพลาด:", e_err)
