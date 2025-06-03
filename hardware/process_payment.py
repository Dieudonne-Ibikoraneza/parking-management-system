import serial
import time
import serial.tools.list_ports
import platform
from datetime import datetime
from math import ceil
from database import ParkingDatabase

# Initialize database
db = ParkingDatabase()

RATE_PER_HOUR = 500  # ₦500 per hour


def detect_arduino_port():
    ports = list(serial.tools.list_ports.comports())
    system = platform.system()
    for port in ports:
        if system == "Linux":
            if "ttyUSB" in port.device or "ttyACM" in port.device:
                return port.device
        elif system == "Darwin":
            if "usbmodem" in port.device or "usbserial" in port.device:
                return port.device
        elif system == "Windows":
            if "COM" in port.device:
                return port.device
    return None


def parse_arduino_data(line):
    try:
        parts = line.strip().split(',')
        print(f"[ARDUINO] Parsed parts: {parts}")
        if len(parts) != 2:
            return None, None
        plate = parts[0].strip()

        # Remove any non-digit characters
        balance_str = ''.join(c for c in parts[1] if c.isdigit())
        print(f"[ARDUINO] Cleaned balance: {balance_str}")

        if balance_str:
            return plate, int(balance_str)
        else:
            return None, None
    except ValueError as e:
        print(f"[ERROR] Parsing error: {e}")
        return None, None


def process_payment(plate, balance, ser):
    try:
        record = db.get_unpaid_record(plate)
        if not record:
            print("[PAYMENT] Plate not found or already paid.")
            return

        entry_time = record['entry_time']
        now = datetime.now()
        hours_spent = ceil((now - entry_time).total_seconds() / 3600)
        amount_due = hours_spent * RATE_PER_HOUR

        print(f"[PAYMENT] Plate: {plate}, Hours: {hours_spent}, Due: ₦{amount_due}")

        if balance < amount_due:
            print("[PAYMENT] Insufficient balance")
            ser.write(b'I\n')
            return

        new_balance = balance - amount_due

        # Wait for Arduino to send READY
        print("[WAIT] Waiting for Arduino to be READY...")
        start = time.time()
        while True:
            if ser.in_waiting:
                arduino_response = ser.readline().decode().strip()
                print(f"[ARDUINO] {arduino_response}")
                if arduino_response == "READY":
                    break
            if time.time() - start > 5:
                print("[ERROR] Arduino not ready in time")
                return

        ser.write(f"{new_balance}\r\n".encode())
        print(f"[PAYMENT] Sent new balance ₦{new_balance}")

        # Wait for DONE
        print("[WAIT] Waiting for confirmation...")
        start = time.time()
        while True:
            if ser.in_waiting:
                confirm = ser.readline().decode().strip()
                print(f"[ARDUINO] {confirm}")
                if "DONE" in confirm:
                    print("[ARDUINO] Payment confirmed")
                    if db.update_payment_status(plate, amount_due, 1):
                        print(f"[SUCCESS] Payment processed for {plate}")
                    else:
                        print(f"[ERROR] Could not update database for {plate}")
                    break
            if time.time() - start > 10:
                print("[ERROR] Arduino did not confirm in time")
                break
            time.sleep(0.1)

    except Exception as e:
        print(f"[ERROR] Payment error: {e}")


def main():
    port = detect_arduino_port()
    if not port:
        print("[ERROR] Arduino not found")
        return

    try:
        ser = serial.Serial(port, 9600, timeout=1)
        print(f"[CONNECTED] Listening on {port}")
        time.sleep(2)
        ser.reset_input_buffer()

        while True:
            if ser.in_waiting:
                line = ser.readline().decode().strip()
                print(f"[SERIAL] Received: {line}")
                plate, balance = parse_arduino_data(line)
                if plate and balance is not None:
                    process_payment(plate, balance, ser)

    except KeyboardInterrupt:
        print("[EXIT] Stopping gracefully.")
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        if 'ser' in locals():
            ser.close()


if __name__ == "__main__":
    main()
