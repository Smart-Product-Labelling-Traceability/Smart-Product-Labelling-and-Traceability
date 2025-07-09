# 🏷️ Smart Product Labelling and Traceability System

An Intel Unnati Industry Training Project using Raspberry Pi 4, Computer Vision (YOLO), and real-time database logging to ensure RoHS compliance and detect PCB defects on a conveyor belt system.

---
## 🔗 Table of Contents

- [📦 Features](#-features)
- [🧰 Hardware Used](#-hardware-used)
- [💻 Software Stack](#-software-stack)
- [📁 Folder Structure](#-folder-structure)
- [🧪 How It Works](#-how-it-works)
- [🗃️ Databases](#️-databases)
- [📸 Model Info](#-model-info)
- [👥 Team Members](#-team-members)
- [📄 License](#-license)

---

## 📦 Features

- 🎞️ IR sensor detects product entry on conveyor  
- 🎥 Camera captures PCB image upon detection  
- 📄 QR is read → Device ID & Batch ID extracted  
- ✅ RoHS compliance verified from local database (`rohs_compliance.csv`)  
- 🔍 YOLOv8 model checks for cracks, holes, and burns on PCB  
- ❌ Non-compliant or defective PCBs are removed using servo motor  
- ⚙️ Conveyor belt is controlled via Raspberry Pi and motor driver  
- 🖨️ Final label (Device ID, Batch ID, RoHS Status, Result) is displayed on screen  
- 🗃️ All inspection records logged into `inspection_log.db`  

---

## 🧰 Hardware Used

- Raspberry Pi 4  
- IR Sensor  
- USB Webcam  
- Motor Driver (L298N)  
- 2 DC Motors (Conveyor)  
- Servo Motor (for removal system)

---

## 💻 Software Stack

- Python  
- OpenCV  
- YOLOv8 (Ultralytics)  
- pyzbar (for QR code reading)  
- SQLite3 / CSV for databases  

## 📁 Folder Structure

📁 code/ → main.py - single Python script

📁 models/ → YOLOv8 model for PCB defect detection

📁 db/

├── rohs_compliance.csv → device/batch RoHS status

└── inspection_log.db → log of all inspections

📁 docs/ → Project Report

📁 images/ → system diagram / photos

## 🧪 How It Works

1. IR sensor detects incoming product  
2. Camera captures image → QR is read  
3. Device ID & Batch ID checked in RoHS DB (`rohs_compliance.csv`)  
4. If not compliant → PCB is rejected using servo  
5. YOLO model checks for defects (cracks, holes, burn)  
6. If defective → PCB is also rejected  
7. Label with result is displayed on screen  
8. Inspection is logged into `inspection_log.db`  

---

## 🗃️ Databases
rohs_compliance.csv – stores known device ID, batch ID, and compliance info

inspection_log.db – stores all results (pass/fail, timestamps, image ref, etc.)

## 📸 Model Info
YOLOv8 trained on 300+ PCB defect images (crack, hole, burn)

models/pcb_defect_yolo.pt

## 👥 Team Members
ABIJITH SS
JEFFIN I PATRICK
GEORGE K JOHN


## 📄 License
This project is licensed under the MIT License.
