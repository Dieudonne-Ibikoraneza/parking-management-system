from flask import Flask, jsonify
from database import ParkingDatabase
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests for the dashboard

db = ParkingDatabase()

@app.route('/api/logs', methods=['GET'])
def get_logs():
    try:
        checkins = db.get_all_entries()
        checkouts = db.get_all_exits()
        payments = db.get_all_payments()
        alerts = db.get_all_alerts()
        return jsonify({
            'checkins': checkins,
            'checkouts': checkouts,
            'payments': payments,
            'alerts': alerts
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)