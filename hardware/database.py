import psycopg2
from datetime import datetime

class ParkingDatabase:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname="parking_system",
            user="postgres",
            password="password",  # Replace with your actual password
            host="localhost",
            port="5432"
        )
        self.cursor = self.conn.cursor()

    def add_entry(self, plate_number):
        try:
            query = """
                INSERT INTO parking_records (car_plate, entry_time, created_at)
                VALUES (%s, %s, %s) RETURNING id
            """
            self.cursor.execute(query, (plate_number, datetime.now(), datetime.now()))
            self.conn.commit()
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"[ERROR] Failed to add entry: {e}")
            self.conn.rollback()
            return None

    def has_unpaid_record(self, plate_number):
        query = """
            SELECT id FROM parking_records
            WHERE car_plate = %s AND payment_status = 0 AND exit_time IS NULL
        """
        self.cursor.execute(query, (plate_number,))
        return bool(self.cursor.fetchone())

    def get_paid_record(self, plate_number):
        query = """
            SELECT * FROM parking_records
            WHERE car_plate = %s AND payment_status = 1 AND exit_time IS NULL
            ORDER BY entry_time DESC LIMIT 1
        """
        self.cursor.execute(query, (plate_number,))
        record = self.cursor.fetchone()
        if record:
            return {
                'id': record[0],
                'entry_time': record[1],
                'exit_time': record[2],
                'car_plate': record[3],
                'due_payment': record[4],
                'payment_status': record[5],
                'created_at': record[6]
            }
        return None

    def record_exit(self, plate_number):
        query = """
            UPDATE parking_records
            SET exit_time = %s
            WHERE car_plate = %s AND payment_status = 1 AND exit_time IS NULL
            RETURNING id
        """
        self.cursor.execute(query, (datetime.now(), plate_number))
        self.conn.commit()
        return bool(self.cursor.fetchone())

    def get_unpaid_record(self, plate_number):
        query = """
            SELECT * FROM parking_records
            WHERE car_plate = %s AND payment_status = 0 AND exit_time IS NULL
            ORDER BY entry_time DESC LIMIT 1
        """
        self.cursor.execute(query, (plate_number,))
        record = self.cursor.fetchone()
        if record:
            return {
                'id': record[0],
                'entry_time': record[1],
                'exit_time': record[2],
                'car_plate': record[3],
                'due_payment': record[4],
                'payment_status': record[5],
                'created_at': record[6]
            }
        return None

    def update_payment_status(self, plate_number, amount, status):
        query = """
            UPDATE parking_records
            SET due_payment = %s, payment_status = %s
            WHERE car_plate = %s AND payment_status = 0 AND exit_time IS NULL
            RETURNING id
        """
        self.cursor.execute(query, (amount, status, plate_number))
        self.conn.commit()
        return bool(self.cursor.fetchone())

    def get_all_entries(self):
        query = """
            SELECT id, car_plate, entry_time
            FROM parking_records
            WHERE entry_time IS NOT NULL
            ORDER BY entry_time DESC
        """
        self.cursor.execute(query)
        return [
            {
                'id': row[0],
                'car_plate': row[1],
                'entry_time': row[2].strftime('%Y-%m-%d %H:%M:%S')
            }
            for row in self.cursor.fetchall()
        ]

    def get_all_exits(self):
        query = """
            SELECT id, car_plate, exit_time
            FROM parking_records
            WHERE exit_time IS NOT NULL
            ORDER BY exit_time DESC
        """
        self.cursor.execute(query)
        return [
            {
                'id': row[0],
                'car_plate': row[1],
                'exit_time': row[2].strftime('%Y-%m-%d %H:%M:%S')
            }
            for row in self.cursor.fetchall()
        ]

    def get_all_payments(self):
        query = """
            SELECT car_plate, due_payment, created_at
            FROM parking_records
            WHERE payment_status = 1
            ORDER BY created_at DESC
        """
        self.cursor.execute(query)
        return [
            {
                'car_plate': row[0],
                'due_payment': float(row[1]),
                'created_at': row[2].strftime('%Y-%m-%d %H:%M:%S')
            }
            for row in self.cursor.fetchall()
        ]

    def get_all_alerts(self):
        query = """
            SELECT car_plate, created_at, 'Unauthorized Exit' as reason
            FROM parking_records
            WHERE payment_status = 0 AND exit_time IS NOT NULL
            ORDER BY created_at DESC
        """
        self.cursor.execute(query)
        return [
            {
                'car_plate': row[0],
                'timestamp': row[1].strftime('%Y-%m-%d %H:%M:%S'),
                'reason': row[2]
            }
            for row in self.cursor.fetchall()
        ]

    def __del__(self):
        self.cursor.close()
        self.conn.close()