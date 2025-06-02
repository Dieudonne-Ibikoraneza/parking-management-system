import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os
from contextlib import contextmanager

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'parking_system'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password'),
    'port': os.getenv('DB_PORT', '5432')
}


class ParkingDatabase:
    def __init__(self):
        self.config = DB_CONFIG
        self.init_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = psycopg2.connect(**self.config)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def init_database(self):
        """Initialize database and create tables if they don't exist"""
        create_table_query = """
                             CREATE TABLE IF NOT EXISTS parking_records \
                             ( \
                                 id \
                                 SERIAL \
                                 PRIMARY \
                                 KEY, \
                                 entry_time \
                                 TIMESTAMP \
                                 NOT \
                                 NULL, \
                                 exit_time \
                                 TIMESTAMP, \
                                 car_plate \
                                 VARCHAR \
                             ( \
                                 10 \
                             ) NOT NULL,
                                 due_payment DECIMAL \
                             ( \
                                 10, \
                                 2 \
                             ) DEFAULT 0,
                                 payment_status INTEGER DEFAULT 0,
                                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                 );

                             CREATE INDEX IF NOT EXISTS idx_car_plate ON parking_records(car_plate);
                             CREATE INDEX IF NOT EXISTS idx_payment_status ON parking_records(payment_status); \
                             """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(create_table_query)
                    conn.commit()
                    print("[DATABASE] Tables initialized successfully")
        except Exception as e:
            print(f"[DATABASE ERROR] Failed to initialize: {e}")

    def add_entry(self, plate_number):
        """Add new parking entry"""
        query = """
                INSERT INTO parking_records (entry_time, car_plate, payment_status)
                VALUES (%s, %s, 0) RETURNING id \
                """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (datetime.now(), plate_number))
                    entry_id = cur.fetchone()[0]
                    conn.commit()
                    return entry_id
        except Exception as e:
            print(f"[DATABASE ERROR] Failed to add entry: {e}")
            return None

    def has_unpaid_record(self, plate_number):
        """Check if plate has unpaid parking record"""
        query = """
                SELECT COUNT(*) \
                FROM parking_records
                WHERE car_plate = %s \
                  AND payment_status = 0 \
                  AND exit_time IS NULL \
                """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (plate_number,))
                    count = cur.fetchone()[0]
                    return count > 0
        except Exception as e:
            print(f"[DATABASE ERROR] Failed to check unpaid records: {e}")
            return False

    def get_unpaid_record(self, plate_number):
        """Get unpaid record for a plate"""
        query = """
                SELECT * \
                FROM parking_records
                WHERE car_plate = %s \
                  AND payment_status = 0 \
                  AND exit_time IS NULL
                ORDER BY entry_time DESC LIMIT 1 \
                """

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, (plate_number,))
                    return cur.fetchone()
        except Exception as e:
            print(f"[DATABASE ERROR] Failed to get unpaid record: {e}")
            return None

    def update_payment_status(self, plate_number, amount_due, new_status=1):
        """Update payment status and due amount"""
        query = """
                UPDATE parking_records
                SET payment_status = %s, \
                    due_payment    = %s
                WHERE car_plate = %s \
                  AND payment_status = 0 \
                  AND exit_time IS NULL RETURNING id \
                """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (new_status, amount_due, plate_number))
                    result = cur.fetchone()
                    conn.commit()
                    return result is not None
        except Exception as e:
            print(f"[DATABASE ERROR] Failed to update payment: {e}")
            return False

    def record_exit(self, plate_number):
        """Record exit time for paid vehicle"""
        query = """
                UPDATE parking_records
                SET exit_time = %s
                WHERE car_plate = %s \
                  AND payment_status = 1 \
                  AND exit_time IS NULL RETURNING id, entry_time, due_payment \
                """

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, (datetime.now(), plate_number))
                    result = cur.fetchone()
                    conn.commit()
                    return result
        except Exception as e:
            print(f"[DATABASE ERROR] Failed to record exit: {e}")
            return None

    def get_paid_record(self, plate_number):
        """Check if plate has paid record without exit"""
        query = """
                SELECT * \
                FROM parking_records
                WHERE car_plate = %s \
                  AND payment_status = 1 \
                  AND exit_time IS NULL
                ORDER BY entry_time DESC LIMIT 1 \
                """

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, (plate_number,))
                    return cur.fetchone()
        except Exception as e:
            print(f"[DATABASE ERROR] Failed to get paid record: {e}")
            return None