from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'patient-monitor-iot'
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

# --- Simulation State ---
sim_state = {
    'fall': False,
    'high_hr': False,
    'high_temp': False
}
import random

@app.route('/api/simulate', methods=['POST'])
def toggle_simulation():
    """Toggle simulation states from dashboard controls."""
    data = request.get_json()
    if 'fall' in data:
        sim_state['fall'] = data['fall']
    if 'high_hr' in data:
        sim_state['high_hr'] = data['high_hr']
    if 'high_temp' in data:
        sim_state['high_temp'] = data['high_temp']
    return jsonify({"status": "ok", "state": sim_state}), 200

@app.route('/api/data', methods=['POST'])
def receive_data():
    """Receive data from the camera node and broadcast to all dashboard clients."""
    data = request.get_json()
    if data:
        # Override with simulation values if enabled
        if sim_state['fall']:
            data['alert'] = 1
        if sim_state['high_hr']:
            data['heartRate'] = random.randint(145, 170)
        if sim_state['high_temp']:
            data['temperature'] = round(random.uniform(38.8, 39.5), 1)

        socketio.emit('patient_data', data)
        return jsonify({"status": "ok"}), 200
    return jsonify({"status": "error"}), 400

if __name__ == '__main__':
    print("=" * 50)
    print("  PATIENT MONITORING DASHBOARD")
    print("  http://127.0.0.1:5001")
    print("=" * 50)
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)
