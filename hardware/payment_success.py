import csv
import os

csv_file = 'db.csv'

def mark_payment_success(plate_number):
    if not os.path.exists(csv_file):
        print("[ERROR] Log file does not exist.")
        return

    updated = False
    rows = []

    # Read existing data
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        print(f"[DEBUG] Header: {header}")  # Print header to verify columns
        for row in reader:
            print(f"[DEBUG] Row: {row}")  # Print each row to inspect data
            # Match the plate with unpaid status
            if row[3] == plate_number and row[5] == '0':  # Use correct indices
                row[5] = '1'  # Mark as paid
                updated = True
            rows.append(row)

    if updated:
        # Write back updated data
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        print(f"[UPDATED] Payment status set to 1 for {plate_number}")
    else:
        print(f"[INFO] No unpaid record found for {plate_number}")

# ==== TESTING USAGE ====
if __name__ == "__main__":
    plate = input("Enter plate number to mark as paid: ").strip().upper()
    print(f"[DEBUG] Input plate: {plate}")  # Print input for verification
    mark_payment_success(plate)