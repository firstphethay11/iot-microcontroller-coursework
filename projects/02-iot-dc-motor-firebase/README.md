# Project 2: ระบบควบคุมและมอนิเตอร์มอเตอร์ผ่าน IoT Web App & Firebase
### IoT DC Motor Web Controller with Firebase Realtime Database

## 1. คุณสมบัติของระบบ (Key Features)
- **การสื่อสารผ่านคลาวด์แบบเรียลไทม์:** เชื่อมต่อ Firebase Realtime Database รับ-ส่งข้อมูลแบบสองทาง
- **ควบคุมความเร็วและทิศทาง:** ปรับความเร็ว PWM 0-100% และสลับทิศทางหมุนตามเข็ม/ทวนเข็มนาฬิกา
- **หน้าเว็บแอปพลิเคชัน:** แดชบอร์ดแบบ Single Page Application (SPA) รองรับการเปิดใช้งานบนสมาร์ตโฟนและคอมพิวเตอร์
- **การตรวจสอบสถานะการเชื่อมต่อ:** มีสถานะ Online/Offline ของบอร์ด ESP32 แบบเรียลไทม์

## 2. โครงสร้างไฟล์
- irmware/miniproject.py: ซอร์สโค้ด ESP32 MicroPython เชื่อมต่อ Wi-Fi และ Firebase
- webapp/index.html: หน้าเว็บแดชบอร์ดสำหรับควบคุมมอเตอร์
- webapp/firebase.json: การตั้งค่า Firebase Hosting
- webapp/database.rules.json: กฎความปลอดภัยของฐานข้อมูล
