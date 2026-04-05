import cv2
import paho.mqtt.client as mqtt
import json
import time
import random
import numpy as np
import requests
from datetime import datetime

# --- Configuration ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "iot_fundamentals_project/patient_data"
DASHBOARD_URL = "http://127.0.0.1:5001/api/data"  # Local dashboard endpoint

print("=" * 60)
print("  AI PATIENT MONITORING - EDGE VISION NODE")
print("=" * 60)

# --- MQTT Setup ---
print("Connecting to MQTT Broker...")
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    print(f"[OK] MQTT Connected to {MQTT_BROKER}")
except Exception as e:
    print(f"[WARN] MQTT connection failed: {e} (continuing without MQTT)")
    client = None

# --- Camera Setup ---
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)

# Background Subtractor with stricter settings
backSub = cv2.createBackgroundSubtractorMOG2(history=700, varThreshold=80, detectShadows=False)

print("[OK] Camera initialized")
print("-" * 60)
print("  DEMO CONTROLS (press on the camera window):")
print("    [F] - Simulate Fall Alert")
print("    [R] - Reset to Normal")
print("    [H] - Toggle HUD Overlay")
print("    [Q] - Quit")
print("-" * 60)
print("")

# --- State ---
last_publish_time = time.time()
simulated_fall = False
show_hud = True
frame_count = 0
alert_flash_counter = 0

# Fall detection state - requires sustained detection
fall_confidence = 0           # Frames of sustained fall-like posture (0-30)
FALL_TRIGGER_THRESHOLD = 20   # Need 20 consecutive frames (~0.7 sec) to confirm fall
MIN_CONTOUR_AREA = 12000      # Much larger minimum to avoid noise
FALL_ASPECT_RATIO = 1.8       # Stricter: person must clearly be horizontal
fall_active_cv = False

# Smoothed vitals
smooth_hr = 72.0
smooth_temp = 36.6
smooth_spo2 = 98

# History for graphs
hr_history = []
temp_history = []

# Let background subtractor learn for the first 2 seconds
warmup_frames = 60


def draw_hud_panel(frame, x, y, w, h, title, value, unit, accent_color, status="Normal"):
    """Draw a semi-transparent HUD panel."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), (20, 20, 30), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
    cv2.rectangle(frame, (x, y), (x + w, y + h), accent_color, 1)
    cv2.rectangle(frame, (x, y), (x + w, y + 3), accent_color, -1)

    cv2.putText(frame, title, (x + 10, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 160, 180), 1, cv2.LINE_AA)
    cv2.putText(frame, str(value), (x + 10, y + 52), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2, cv2.LINE_AA)

    val_w = cv2.getTextSize(str(value), cv2.FONT_HERSHEY_SIMPLEX, 0.85, 2)[0][0]
    cv2.putText(frame, unit, (x + 15 + val_w, y + 52), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (130, 140, 160), 1, cv2.LINE_AA)

    dot_color = (0, 200, 120) if status == "Normal" else (0, 80, 255)
    cv2.circle(frame, (x + w - 14, y + 16), 4, dot_color, -1)


def draw_sparkline(frame, x, y, w, h, data, color):
    """Draw a small sparkline graph."""
    if len(data) < 2:
        return
    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), (15, 15, 25), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

    d_min = min(data) - 2
    d_max = max(data) + 2
    d_range = d_max - d_min if d_max != d_min else 1

    pts = []
    for i, val in enumerate(data):
        px = x + int(i * w / (len(data) - 1))
        py = y + h - int((val - d_min) / d_range * h)
        pts.append((px, py))
    for i in range(len(pts) - 1):
        cv2.line(frame, pts[i], pts[i + 1], color, 2, cv2.LINE_AA)


def send_to_dashboard(payload):
    """Send data to the local dashboard via HTTP POST."""
    try:
        requests.post(DASHBOARD_URL, json=payload, timeout=0.3)
    except Exception:
        pass  # Dashboard might not be running yet


while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    h_frame, w_frame = frame.shape[:2]

    # --- Motion Detection ---
    fgMask = backSub.apply(frame)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    fgMask = cv2.morphologyEx(fgMask, cv2.MORPH_OPEN, kernel)
    fgMask = cv2.morphologyEx(fgMask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(fgMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    movement_detected = 0
    largest_contour = None
    largest_area = 0

    # Skip during warmup (let background model stabilize)
    if frame_count > warmup_frames:
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 5000:
                movement_detected = 1
                if area > largest_area:
                    largest_area = area
                    largest_contour = contour

    # --- Fall Detection (Strict, Multi-Frame Confirmation) ---
    current_frame_fall_like = False

    if largest_contour is not None and largest_area > MIN_CONTOUR_AREA:
        x, y_pos, w_box, h_box = cv2.boundingRect(largest_contour)
        aspect_ratio = w_box / h_box if h_box > 0 else 0

        # Draw tracking bracket corners
        cl = 20  # corner length
        if fall_active_cv or simulated_fall:
            box_color = (0, 0, 255)
        else:
            box_color = (0, 220, 100)

        # Top-left
        cv2.line(frame, (x, y_pos), (x + cl, y_pos), box_color, 2)
        cv2.line(frame, (x, y_pos), (x, y_pos + cl), box_color, 2)
        # Top-right
        cv2.line(frame, (x + w_box, y_pos), (x + w_box - cl, y_pos), box_color, 2)
        cv2.line(frame, (x + w_box, y_pos), (x + w_box, y_pos + cl), box_color, 2)
        # Bottom-left
        cv2.line(frame, (x, y_pos + h_box), (x + cl, y_pos + h_box), box_color, 2)
        cv2.line(frame, (x, y_pos + h_box), (x, y_pos + h_box - cl), box_color, 2)
        # Bottom-right
        cv2.line(frame, (x + w_box, y_pos + h_box), (x + w_box - cl, y_pos + h_box), box_color, 2)
        cv2.line(frame, (x + w_box, y_pos + h_box), (x + w_box, y_pos + h_box - cl), box_color, 2)

        # Label
        label = f"Patient | AR:{aspect_ratio:.1f} | Area:{largest_area}"
        ls = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)[0]
        cv2.rectangle(frame, (x, y_pos - 22), (x + ls[0] + 10, y_pos - 3), (0, 0, 0), -1)
        cv2.putText(frame, label, (x + 5, y_pos - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, box_color, 1, cv2.LINE_AA)

        # Check if this frame looks like a fall
        if aspect_ratio > FALL_ASPECT_RATIO:
            current_frame_fall_like = True

    # Update fall confidence counter
    if current_frame_fall_like:
        fall_confidence = min(fall_confidence + 1, FALL_TRIGGER_THRESHOLD + 10)
    else:
        fall_confidence = max(fall_confidence - 2, 0)  # Decay slowly

    # CV-based fall triggers only after sustained confidence
    if fall_confidence >= FALL_TRIGGER_THRESHOLD:
        fall_active_cv = True
    elif fall_confidence <= 3:
        fall_active_cv = False

    # --- Show confidence bar when building up ---
    if 0 < fall_confidence < FALL_TRIGGER_THRESHOLD and not simulated_fall:
        bar_x, bar_y = 10, 45
        bar_w = 200
        bar_h = 16
        fill_w = int((fall_confidence / FALL_TRIGGER_THRESHOLD) * bar_w)
        ov = frame.copy()
        cv2.rectangle(ov, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (30, 30, 40), -1)
        cv2.addWeighted(ov, 0.7, frame, 0.3, 0, frame)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), (0, 100, 255), -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (80, 80, 100), 1)
        cv2.putText(frame, "Fall Confidence", (bar_x + 5, bar_y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 220), 1, cv2.LINE_AA)

    # --- Combined alert state ---
    alert_status = 1 if (fall_active_cv or simulated_fall) else 0

    # --- Alert Visual Effects ---
    if alert_status:
        alert_flash_counter += 1

        # Red vignette
        ov = frame.copy()
        cv2.rectangle(ov, (0, 0), (w_frame, h_frame), (0, 0, 160), -1)
        cv2.addWeighted(ov, 0.12, frame, 0.88, 0, frame)

        # Pulsing red border
        thick = 3 + int(2 * abs(np.sin(alert_flash_counter * 0.12)))
        cv2.rectangle(frame, (0, 0), (w_frame - 1, h_frame - 1), (0, 0, 255), thick)

        # Top banner
        bh = 40
        ov2 = frame.copy()
        cv2.rectangle(ov2, (0, 0), (w_frame, bh), (0, 0, 180), -1)
        cv2.addWeighted(ov2, 0.75, frame, 0.25, 0, frame)
        txt = "!! FALL DETECTED - IMMEDIATE ATTENTION REQUIRED !!"
        tw = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)[0][0]
        cv2.putText(frame, txt, ((w_frame - tw) // 2, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)

        # Simulate stressed vitals
        smooth_hr = min(155, smooth_hr + random.uniform(0.8, 2.5))
        smooth_temp = min(38.3, smooth_temp + random.uniform(0.01, 0.025))
    else:
        alert_flash_counter = 0
        # Gradually return to normal
        smooth_hr += (72.0 - smooth_hr) * 0.03 + random.uniform(-0.3, 0.3)
        smooth_temp += (36.6 - smooth_temp) * 0.02 + random.uniform(-0.015, 0.015)

    smooth_hr = max(62, min(175, smooth_hr))
    smooth_temp = max(36.3, min(39.0, smooth_temp))

    # --- Calculate ambient light from camera ---
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    brightness = hsv[:, :, 2].mean()
    calculated_light = int((brightness / 255.0) * 4000)

    # --- HUD Overlay ---
    if show_hud:
        # Title bar
        tb = frame.copy()
        cv2.rectangle(tb, (5, 5), (330, 38), (15, 15, 25), -1)
        cv2.addWeighted(tb, 0.7, frame, 0.3, 0, frame)
        cv2.putText(frame, "AI PATIENT MONITOR", (15, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 175, 255), 2, cv2.LINE_AA)

        # Recording dot (blink)
        if frame_count % 30 < 20:
            cv2.circle(frame, (w_frame - 115, 22), 5, (0, 0, 255), -1)

        # Timestamp
        cv2.putText(frame, datetime.now().strftime("%H:%M:%S"), (w_frame - 100, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 130, 150), 1, cv2.LINE_AA)

        # Bottom vitals panels
        py = h_frame - 82
        pw, ph, gap = 135, 68, 8
        sx = 10

        hr_d = int(smooth_hr)
        hr_s = "Normal" if 60 <= hr_d <= 100 else "Alert"
        hr_c = (0, 200, 120) if hr_s == "Normal" else (0, 80, 255)
        draw_hud_panel(frame, sx, py, pw, ph, "HEART RATE", hr_d, "BPM", hr_c, hr_s)

        temp_d = round(smooth_temp, 1)
        temp_s = "Normal" if temp_d <= 37.5 else "Alert"
        temp_c = (0, 200, 120) if temp_s == "Normal" else (0, 80, 255)
        draw_hud_panel(frame, sx + pw + gap, py, pw, ph, "BODY TEMP", temp_d, "C", temp_c, temp_s)

        spo2_d = random.randint(96, 99) if not alert_status else random.randint(89, 93)
        spo2_s = "Normal" if spo2_d >= 95 else "Alert"
        spo2_c = (0, 200, 120) if spo2_s == "Normal" else (0, 80, 255)
        draw_hud_panel(frame, sx + 2 * (pw + gap), py, pw, ph, "SpO2", spo2_d, "%", spo2_c, spo2_s)

        mv_txt = "Active" if movement_detected else "Idle"
        mv_c = (200, 180, 0) if movement_detected else (0, 200, 120)
        draw_hud_panel(frame, sx + 3 * (pw + gap), py, pw, ph, "ACTIVITY", mv_txt, "", mv_c, "Normal")

        lx_lbl = "Bright" if calculated_light > 2000 else "Dim"
        lx_c = (0, 200, 200) if calculated_light > 2000 else (200, 150, 0)
        draw_hud_panel(frame, sx + 4 * (pw + gap), py, pw + 15, ph, "AMBIENT", calculated_light, "lux", lx_c, "Normal")

        # Sparklines
        hr_history.append(hr_d)
        temp_history.append(temp_d)
        if len(hr_history) > 60:
            hr_history.pop(0)
        if len(temp_history) > 60:
            temp_history.pop(0)

        draw_sparkline(frame, w_frame - 165, 48, 150, 45, hr_history, (80, 180, 255))
        cv2.putText(frame, "HR Trend", (w_frame - 165, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (110, 120, 140), 1, cv2.LINE_AA)

        draw_sparkline(frame, w_frame - 165, 112, 150, 45, temp_history, (100, 200, 120))
        cv2.putText(frame, "Temp Trend", (w_frame - 165, 109), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (110, 120, 140), 1, cv2.LINE_AA)

        # Controls hint
        cy = h_frame - 90
        co = frame.copy()
        cv2.rectangle(co, (w_frame - 180, cy), (w_frame - 5, cy + 76), (15, 15, 25), -1)
        cv2.addWeighted(co, 0.7, frame, 0.3, 0, frame)
        cv2.putText(frame, "DEMO CONTROLS", (w_frame - 170, cy + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (90, 110, 150), 1, cv2.LINE_AA)
        cv2.putText(frame, "[F] Simulate Fall", (w_frame - 170, cy + 33), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (170, 170, 190), 1, cv2.LINE_AA)
        cv2.putText(frame, "[R] Reset Normal", (w_frame - 170, cy + 48), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (170, 170, 190), 1, cv2.LINE_AA)
        cv2.putText(frame, "[H] Toggle HUD", (w_frame - 170, cy + 63), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (170, 170, 190), 1, cv2.LINE_AA)

    # --- Publish data every 0.5 seconds ---
    if time.time() - last_publish_time > 0.5:
        payload = {
            "movement": movement_detected,
            "alert": alert_status,
            "light": calculated_light,
            "temperature": round(smooth_temp, 1),
            "heartRate": int(smooth_hr)
        }

        # Send to local dashboard (instant, reliable)
        send_to_dashboard(payload)

        # Also publish to MQTT (for IoT demonstration)
        if client:
            try:
                client.publish(MQTT_TOPIC, json.dumps(payload))
            except Exception:
                pass

        last_publish_time = time.time()

    # --- Display ---
    cv2.imshow('AI Patient Monitor - Edge Vision Node', frame)

    # --- Keyboard Controls ---
    key = cv2.waitKey(30) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('f'):
        simulated_fall = True
        fall_confidence = 0
        print("[ALERT] Fall simulation ACTIVATED (press R to reset)")
    elif key == ord('r'):
        simulated_fall = False
        fall_active_cv = False
        fall_confidence = 0
        smooth_hr = 72.0
        smooth_temp = 36.6
        print("[OK] Reset to normal state")
    elif key == ord('h'):
        show_hud = not show_hud
        print(f"[HUD] {'ON' if show_hud else 'OFF'}")

# Cleanup
cap.release()
cv2.destroyAllWindows()
if client:
    client.loop_stop()
    client.disconnect()
print("\n[OK] AI Vision Node stopped.")
