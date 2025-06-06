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

# Initialize database
db = ParkingDatabase()

MAX_DISTANCE = 50  # cm
MIN_DISTANCE = 0  # cm


# ===== Auto-detect Arduino Serial Port =====
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


arduino_port = detect_arduino_port()
if arduino_port:
    print(f"[CONNECTED] Arduino on {arduino_port}")
    arduino = serial.Serial(arduino_port, 9600, timeout=1)
    time.sleep(2)
else:
    print("[ERROR] Arduino not detected.")
    arduino = None


# ===== Handle exit logic =====
def handle_exit(plate_number):
    """Handle vehicle exit - check if paid and record exit time"""
    paid_record = db.get_paid_record(plate_number)

    if paid_record:
        exit_record = db.record_exit(plate_number)
        if exit_record:
            print(f"[ACCESS GRANTED] Exit recorded for {plate_number}")
            return True
        else:
            print(f"[ERROR] Failed to record exit for {plate_number}")
            return False
    else:
        print(f"[ACCESS DENIED] No paid record found for {plate_number}")
        return False


# ===== Webcam and Main Loop =====
cap = cv2.VideoCapture(0)
plate_buffer = []

print("[EXIT SYSTEM] Ready. Press 'q' to quit.")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Get distance reading, default to safe value
        distance = read_distance(arduino) or (MAX_DISTANCE - 1)
        print(f"[SENSOR] Distance: {distance} cm")

        if MIN_DISTANCE <= distance <= MAX_DISTANCE:
            results = model(frame)

            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    plate_img = frame[y1:y2, x1:x2]

                    # Preprocess
                    gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
                    blur = cv2.GaussianBlur(gray, (5, 5), 0)
                    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

                    # OCR
                    plate_text = pytesseract.image_to_string(
                        thresh, config='--psm 8 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                    ).strip().replace(" ", "")

                    if "RA" in plate_text:
                        start_idx = plate_text.find("RA")
                        plate_candidate = plate_text[start_idx:]
                        if len(plate_candidate) >= 7:
                            plate_candidate = plate_candidate[:7]
                            prefix, digits, suffix = plate_candidate[:3], plate_candidate[3:6], plate_candidate[6]
                            if (prefix.isalpha() and prefix.isupper() and
                                    digits.isdigit() and suffix.isalpha() and suffix.isupper()):
                                print(f"[VALID] Plate Detected: {plate_candidate}")
                                plate_buffer.append(plate_candidate)

                                if len(plate_buffer) >= 3:
                                    most_common = Counter(plate_buffer).most_common(1)[0][0]
                                    plate_buffer.clear()

                                    if handle_exit(most_common):
                                        print(f"[ACCESS GRANTED] Exit recorded for {most_common}")
                                        if arduino:
                                            arduino.write(b'1')  # Open gate
                                            print("[GATE] Opening gate (sent '1')")
                                            time.sleep(15)
                                            arduino.write(b'0')  # Close gate
                                            print("[GATE] Closing gate (sent '0')")
                                    else:
                                        print(f"[ACCESS DENIED] Exit not allowed for {most_common}")
                                        if arduino:
                                            arduino.write(b'2')  # Buzzer or alert
                                            print("[ALERT] Buzzer triggered (sent '2')")

                    cv2.imshow("Plate", plate_img)
                    cv2.imshow("Processed", thresh)
                    time.sleep(0.5)

        annotated_frame = results[0].plot() if distance <= 50 else frame
        cv2.imshow("Exit Webcam Feed", annotated_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    cap.release()
    if arduino:
        arduino.close()
    cv2.destroyAllWindows()