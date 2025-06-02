import platform
import cv2
from ultralytics import YOLO
import pytesseract
import os
import time
import serial
import serial.tools.list_ports
from collections import Counter
from database import ParkingDatabase

# Load YOLOv8 model
model = YOLO('../model_dev/runs/detect/train/weights/best.pt')

# Configurations
SAVE_DIR = 'plates'
ENTRY_COOLDOWN = 300  # seconds
MAX_DISTANCE = 50     # cm
MIN_DISTANCE = 0      # cm
CAPTURE_THRESHOLD = 3 # number of consistent reads before logging
GATE_OPEN_TIME = 15   # seconds

# Initialize database
db = ParkingDatabase()

# Ensure directories exist
os.makedirs(SAVE_DIR, exist_ok=True)

# Auto-detect Arduino Serial Port
def detect_arduino_port():
    for port in serial.tools.list_ports.comports():
        dev = port.device
        if platform.system() == 'Linux' and 'ttyACM' in dev:
            return dev
        if platform.system() == 'Darwin' and ('usbmodem' in dev or 'usbserial' in dev):
            return dev
        if platform.system() == 'Windows' and 'COM' in dev:
            return dev
    return None

# Read distance from Arduino (returns float or None)
def read_distance(arduino):
    if not arduino or arduino.in_waiting == 0:
        return None
    try:
        val = arduino.readline().decode('utf-8').strip()
        return float(val)
    except (UnicodeDecodeError, ValueError):
        return None

# Initialize Arduino
arduino_port = detect_arduino_port()
arduino = None
if arduino_port:
    print(f"[CONNECTED] Arduino on {arduino_port}")
    arduino = serial.Serial(arduino_port, 9600, timeout=1)
    time.sleep(2)
else:
    print("[ERROR] Arduino not detected.")

# Initialize Webcam and Windows
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("[ERROR] Cannot open camera.")
    exit(1)
cv2.namedWindow('Webcam Feed', cv2.WINDOW_NORMAL)
cv2.namedWindow('Plate', cv2.WINDOW_NORMAL)
cv2.namedWindow('Processed', cv2.WINDOW_NORMAL)
cv2.resizeWindow('Webcam Feed', 800, 600)

# State variables
plate_buffer = []
last_saved_plate = None
last_entry_time = 0

print("[SYSTEM] Ready. Press 'q' to exit.")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Frame capture failed.")
            break

        # Get distance reading, default to safe value
        distance = read_distance(arduino) or (MAX_DISTANCE - 1)
        annotated = frame.copy()

        if MIN_DISTANCE <= distance <= MAX_DISTANCE:
            results = model(frame)[0]
            annotated = results.plot()

            for box in results.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                plate_img = frame[y1:y2, x1:x2]

                # OCR preprocess
                gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
                blur = cv2.GaussianBlur(gray, (5,5), 0)
                thresh = cv2.threshold(blur, 0, 255,
                                       cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

                text = pytesseract.image_to_string(
                    thresh,
                    config='--psm 8 --oem 3 '
                           '-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                ).strip().replace(' ', '')

                # Validate Rwandan format RAxxxA
                if text.startswith('RA') and len(text) >= 7:
                    plate = text[:7]
                    pr, dg, su = plate[:3], plate[3:6], plate[6]
                    if pr.isalpha() and dg.isdigit() and su.isalpha():
                        plate_buffer.append(plate)

                # Once buffer is full, decide
                if len(plate_buffer) >= CAPTURE_THRESHOLD:
                    common = Counter(plate_buffer).most_common(1)[0][0]
                    now = time.time()

                    # Only save if not duplicate unpaid
                    if not db.has_unpaid_record(common):
                        # Optional cooldown logic still applies
                        if common != last_saved_plate or (now - last_entry_time) > ENTRY_COOLDOWN:
                            entry_id = db.add_entry(common)
                            if entry_id:
                                print(f"[NEW] Logged plate {common} with ID {entry_id}")

                                # Gate actuation
                                if arduino:
                                    arduino.write(b'1')
                                    time.sleep(GATE_OPEN_TIME)
                                    arduino.write(b'0')

                                last_saved_plate = common
                                last_entry_time = now
                            else:
                                print(f"[ERROR] Failed to log plate {common}")
                        else:
                            print(f"[SKIPPED] Cooldown: {common}")
                    else:
                        print(f"[SKIPPED] Unpaid record exists for {common}")

                    plate_buffer.clear()

                # Show previews
                cv2.imshow('Plate', plate_img)
                cv2.imshow('Processed', thresh)
                time.sleep(0.5)

        # Display feed
        cv2.imshow('Webcam Feed', annotated)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    cap.release()
    if arduino:
        arduino.close()
    cv2.destroyAllWindows()