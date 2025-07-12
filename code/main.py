<<<<<<< HEAD
import cv2
import time
import sqlite3
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import RPi.GPIO as GPIO
from pyzbar.pyzbar import decode
from datetime import datetime
from ultralytics import YOLO

# GPIO Setup
GPIO.setmode(GPIO.BCM)

# IR Sensor
IR_PIN = 17
GPIO.setup(IR_PIN, GPIO.IN)

# Motor Driver (HW-095 / L298N)
MOTOR_IN1 = 23
MOTOR_IN2 = 24
MOTOR_ENA = 18
GPIO.setup(MOTOR_IN1, GPIO.OUT)
GPIO.setup(MOTOR_IN2, GPIO.OUT)
GPIO.setup(MOTOR_ENA, GPIO.OUT)
motor_pwm = GPIO.PWM(MOTOR_ENA, 1000)
motor_pwm.start(0)

def start_conveyor(speed=100):
    GPIO.output(MOTOR_IN1, GPIO.HIGH)
    GPIO.output(MOTOR_IN2, GPIO.HIGH)
    motor_pwm.ChangeDutyCycle(speed)
    print(f"Conveyor running at {speed}% speed")

def stop_conveyor():
    GPIO.output(MOTOR_IN1, GPIO.LOW)
    GPIO.output(MOTOR_IN2, GPIO.LOW)
    print("Conveyor stopped")
    
    

# Servo Motor Setup (GPIO 12 for example)
SERVO_PIN = 12
GPIO.setup(SERVO_PIN, GPIO.OUT)
servo_pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz
servo_pwm.start(0)

class RealServo:
    def __init__(self, pwm):
        self.pwm = pwm

    def move_to_angle(self, angle):
        duty = 2 + (angle / 18)
        self.pwm.ChangeDutyCycle(duty)
        print(f"Servo → {angle}°")
        time.sleep(0.5)
        self.pwm.ChangeDutyCycle(0)

    def mid(self):
        self.move_to_angle(180)

    def min(self):
        self.move_to_angle(0)

servo = RealServo(servo_pwm)

# Load YOLOv8 model
model = YOLO("best.pt")

# Traceability DB
conn = sqlite3.connect('pcb_traceability.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS pcbs (
    device_id TEXT,
    batch_id TEXT,
    timestamp TEXT,
    defect TEXT,
    rohs_status TEXT,
    status TEXT
)''')

# RoHS DB
rohs_conn = sqlite3.connect('rohs_data.db')
rohs_cursor = rohs_conn.cursor()

def wait_for_pcb():
    print("Waiting for PCB...")
    while GPIO.input(IR_PIN) == 1:
        time.sleep(1.5)
    print("📦 PCB Detected!")

def capture_image(filename="pcb.jpg"):
    cap = cv2.VideoCapture(0)
    time.sleep(2)
    for _ in range(10):
        cap.read()
        time.sleep(0.1)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(filename, frame)
    cap.release()
    return ret

def decode_qr(image_path="pcb.jpg"):
    image = cv2.imread(image_path)
    decoded_objs = decode(image)
    for obj in decoded_objs:
        data = obj.data.decode('utf-8')
        print("QR Code Data:", data)
        return data
    return ""

def parse_qr_data(data):
    device_id, batch_id = "UNKNOWN", "UNKNOWN"
    parts = data.split(';')
    for part in parts:
        if 'DeviceID' in part:
            device_id = part.split(':')[1].strip()
        if 'BatchID' in part:
            batch_id = part.split(':')[1].strip()
    return device_id, batch_id

def check_rohs(device_id, batch_id):
    rohs_cursor.execute("SELECT rohs_status FROM rohs_compliance WHERE device_id = ? AND batch_id = ?", (device_id, batch_id))
    result = rohs_cursor.fetchone()
    return result[0] if result else "Unknown"

def detect_defect(image_path="pcb.jpg"):
    try:
        results = model.predict(image_path, conf=0.25, imgsz=640)
        labels = [model.model.names[int(cls)] for cls in results[0].boxes.cls]
        print("Detected labels:", labels)
        reject_labels = {'mouse_bite', 'spur', 'missing_hole', 'short', 'open_circuit', 'spurious_copper'}
        return any(label.lower() in reject_labels for label in labels)
    except Exception as e:
        print("Defect detection error:", e)
        return False

def generate_label(device_id, batch_id, rohs_status, status):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    label_text = f"Device ID: {device_id}\nBatch ID: {batch_id}\nTimestamp: {timestamp}\nRoHS: {rohs_status}\nStatus: {status}"
    label_img = Image.new('RGB', (300, 150), color='white')
    draw = ImageDraw.Draw(label_img)
    font = ImageFont.load_default()
    draw.text((10, 10), label_text, fill='black', font=font)
    label_img_cv = cv2.cvtColor(np.array(label_img), cv2.COLOR_RGB2BGR)
    filename = f"label_{device_id}_{timestamp.replace(':', '-')}.jpg"
    cv2.imwrite(filename, label_img_cv)
    print(f"Label saved: {filename}")
    cv2.imshow("Label", label_img_cv)
    cv2.waitKey(3000)
    cv2.destroyAllWindows()

def log_data(device_id, batch_id, rohs_status, defect, status):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT INTO pcbs VALUES (?, ?, ?, ?, ?, ?)",
                   (device_id, batch_id, timestamp, "Yes" if defect else "No", rohs_status, status))
    conn.commit()

def reject_pcb():
    servo.mid()
    time.sleep(0.5)
    servo.min()
    time.sleep(0.5)
    servo.mid()
    time.sleep(0.5)

def main():
    start_conveyor()
    while True:
        wait_for_pcb()
        time.sleep(1)
        stop_conveyor()
        

        if not capture_image():
            time.sleep(2)
            start_conveyor()
            continue
        
        qr_data = decode_qr()
        
        if not qr_data:
            print("No QR code found. Skipping...")
            start_conveyor()
            continue

        device_id, batch_id = parse_qr_data(qr_data)
        rohs_status = check_rohs(device_id, batch_id)

        if rohs_status != "Compliant":
            defect = False
            status = "Rejected: RoHS"
            reject_pcb()
        else:
            defect = detect_defect()
            if defect:
                status = "Rejected: Defect"
                reject_pcb()
            else:
                status = "Passed"

        log_data(device_id, batch_id, rohs_status, defect, status)
        generate_label(device_id, batch_id, rohs_status, status)
        start_conveyor()

if __name__ == "__main__":
    try:
        main()
    finally:
        print("Cleaning up...")
        motor_pwm.stop()
        servo_pwm.stop()
        conn.close()
        rohs_conn.close()
        GPIO.cleanup()

=======
import cv2
import time
import sqlite3
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import RPi.GPIO as GPIO
from pyzbar.pyzbar import decode
from datetime import datetime
from ultralytics import YOLO

# GPIO Setup
GPIO.setmode(GPIO.BCM)

# IR Sensor
IR_PIN = 17
GPIO.setup(IR_PIN, GPIO.IN)

# Motor Driver (HW-095 / L298N)
MOTOR_IN1 = 23
MOTOR_IN2 = 24
MOTOR_ENA = 18
GPIO.setup(MOTOR_IN1, GPIO.OUT)
GPIO.setup(MOTOR_IN2, GPIO.OUT)
GPIO.setup(MOTOR_ENA, GPIO.OUT)
motor_pwm = GPIO.PWM(MOTOR_ENA, 1000)
motor_pwm.start(0)

def start_conveyor(speed=100):
    GPIO.output(MOTOR_IN1, GPIO.HIGH)
    GPIO.output(MOTOR_IN2, GPIO.HIGH)
    motor_pwm.ChangeDutyCycle(speed)
    print(f"Conveyor running at {speed}% speed")

def stop_conveyor():
    GPIO.output(MOTOR_IN1, GPIO.LOW)
    GPIO.output(MOTOR_IN2, GPIO.LOW)
    print("Conveyor stopped")
    
    

# Servo Motor Setup (GPIO 12 for example)
SERVO_PIN = 12
GPIO.setup(SERVO_PIN, GPIO.OUT)
servo_pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz
servo_pwm.start(0)

class RealServo:
    def __init__(self, pwm):
        self.pwm = pwm

    def move_to_angle(self, angle):
        duty = 2 + (angle / 18)
        self.pwm.ChangeDutyCycle(duty)
        print(f"Servo → {angle}°")
        time.sleep(0.5)
        self.pwm.ChangeDutyCycle(0)

    def mid(self):
        self.move_to_angle(180)

    def min(self):
        self.move_to_angle(0)

servo = RealServo(servo_pwm)

# Load YOLOv8 model
model = YOLO("best.pt")

# Traceability DB
conn = sqlite3.connect('pcb_traceability.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS pcbs (
    device_id TEXT,
    batch_id TEXT,
    timestamp TEXT,
    defect TEXT,
    rohs_status TEXT,
    status TEXT
)''')

# RoHS DB
rohs_conn = sqlite3.connect('rohs_data.db')
rohs_cursor = rohs_conn.cursor()

def wait_for_pcb():
    print("Waiting for PCB...")
    while GPIO.input(IR_PIN) == 1:
        time.sleep(1.5)
    print("📦 PCB Detected!")

def capture_image(filename="pcb.jpg"):
    cap = cv2.VideoCapture(0)
    time.sleep(2)
    for _ in range(10):
        cap.read()
        time.sleep(0.1)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(filename, frame)
    cap.release()
    return ret

def decode_qr(image_path="pcb.jpg"):
    image = cv2.imread(image_path)
    decoded_objs = decode(image)
    for obj in decoded_objs:
        data = obj.data.decode('utf-8')
        print("QR Code Data:", data)
        return data
    return ""

def parse_qr_data(data):
    device_id, batch_id = "UNKNOWN", "UNKNOWN"
    parts = data.split(';')
    for part in parts:
        if 'DeviceID' in part:
            device_id = part.split(':')[1].strip()
        if 'BatchID' in part:
            batch_id = part.split(':')[1].strip()
    return device_id, batch_id

def check_rohs(device_id, batch_id):
    rohs_cursor.execute("SELECT rohs_status FROM rohs_compliance WHERE device_id = ? AND batch_id = ?", (device_id, batch_id))
    result = rohs_cursor.fetchone()
    return result[0] if result else "Unknown"

def detect_defect(image_path="pcb.jpg"):
    try:
        results = model.predict(image_path, conf=0.25, imgsz=640)
        labels = [model.model.names[int(cls)] for cls in results[0].boxes.cls]
        print("Detected labels:", labels)
        reject_labels = {'mouse_bite', 'spur', 'missing_hole', 'short', 'open_circuit', 'spurious_copper'}
        return any(label.lower() in reject_labels for label in labels)
    except Exception as e:
        print("Defect detection error:", e)
        return False

def generate_label(device_id, batch_id, rohs_status, status):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    label_text = f"Device ID: {device_id}\nBatch ID: {batch_id}\nTimestamp: {timestamp}\nRoHS: {rohs_status}\nStatus: {status}"
    label_img = Image.new('RGB', (300, 150), color='white')
    draw = ImageDraw.Draw(label_img)
    font = ImageFont.load_default()
    draw.text((10, 10), label_text, fill='black', font=font)
    label_img_cv = cv2.cvtColor(np.array(label_img), cv2.COLOR_RGB2BGR)
    filename = f"label_{device_id}_{timestamp.replace(':', '-')}.jpg"
    cv2.imwrite(filename, label_img_cv)
    print(f"Label saved: {filename}")
    cv2.imshow("Label", label_img_cv)
    cv2.waitKey(3000)
    cv2.destroyAllWindows()

def log_data(device_id, batch_id, rohs_status, defect, status):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT INTO pcbs VALUES (?, ?, ?, ?, ?, ?)",
                   (device_id, batch_id, timestamp, "Yes" if defect else "No", rohs_status, status))
    conn.commit()

def reject_pcb():
    servo.mid()
    time.sleep(0.5)
    servo.min()
    time.sleep(0.5)
    servo.mid()
    time.sleep(0.5)

def main():
    start_conveyor()
    while True:
        wait_for_pcb()
        time.sleep(1)
        stop_conveyor()
        

        if not capture_image():
            time.sleep(2)
            start_conveyor()
            continue
        
        qr_data = decode_qr()
        
        if not qr_data:
            print("No QR code found. Skipping...")
            start_conveyor()
            continue

        device_id, batch_id = parse_qr_data(qr_data)
        rohs_status = check_rohs(device_id, batch_id)

        if rohs_status != "Compliant":
            defect = False
            status = "Rejected: RoHS"
            reject_pcb()
        else:
            defect = detect_defect()
            if defect:
                status = "Rejected: Defect"
                reject_pcb()
            else:
                status = "Passed"

        log_data(device_id, batch_id, rohs_status, defect, status)
        generate_label(device_id, batch_id, rohs_status, status)
        start_conveyor()

if __name__ == "__main__":
    try:
        main()
    finally:
        print("Cleaning up...")
        motor_pwm.stop()
        servo_pwm.stop()
        conn.close()
        rohs_conn.close()
        GPIO.cleanup()

>>>>>>> 72fa9377200c0038b426c821bc40fed0da9f34c1
