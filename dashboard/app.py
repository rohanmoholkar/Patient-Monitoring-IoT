from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'patient-monitor-iot'
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data', methods=['POST'])
def receive_data():
    """Receive data from the camera node and broadcast to all dashboard clients."""
    data = request.get_json()
    if data:
        socketio.emit('patient_data', data)
        return jsonify({"status": "ok"}), 200
    return jsonify({"status": "error"}), 400

if __name__ == '__main__':
    print("=" * 50)
    print("  PATIENT MONITORING DASHBOARD")
    print("  http://127.0.0.1:5001")
    print("=" * 50)
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)
