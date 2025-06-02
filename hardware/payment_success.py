from database import ParkingDatabase
from datetime import datetime

# Initialize database
db = ParkingDatabase()


def mark_payment_success(plate_number, amount=None):
    """Mark a parking record as paid"""
    try:
        # Get the unpaid record
        record = db.get_unpaid_record(plate_number)

        if not record:
            print(f"[INFO] No unpaid record found for {plate_number}")
            return False

        # Calculate amount if not provided
        if amount is None:
            entry_time = record['entry_time']
            current_time = datetime.now()
            minutes_spent = int((current_time - entry_time).total_seconds() / 60) + 1
            amount = minutes_spent * 5  # 5 per minute

        # Update payment status
        if db.update_payment_status(plate_number, amount, 1):
            print(f"[SUCCESS] Payment of ${amount} marked for {plate_number}")
            return True
        else:
            print(f"[ERROR] Failed to update payment for {plate_number}")
            return False

    except Exception as e:
        print(f"[ERROR] {e}")
        return False


# ==== TESTING USAGE ====
if __name__ == "__main__":
    plate = input("Enter plate number to mark as paid: ").strip().upper()
    amount_input = input("Enter amount (or press Enter to auto-calculate): ").strip()

    amount = None
    if amount_input:
        try:
            amount = float(amount_input)
        except ValueError:
            print("[ERROR] Invalid amount entered, using auto-calculation")

    mark_payment_success(plate, amount)