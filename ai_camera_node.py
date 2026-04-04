import cv2
import paho.mqtt.client as mqtt
import json
import time
import random

# --- MQTT Configuration ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "iot_fundamentals_project/patient_data"

print("Connecting to MQTT Broker...")
# Added Callback API param to fix depreciation warning
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

# --- Camera Setup ---
cap = cv2.VideoCapture(0)

# Create a Background Subtractor to isolate moving people (Classical Computer Vision AI)
backSub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=False)

print("Starting AI Vision Node...")

last_time = time.time()

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Apply background subtraction
    fgMask = backSub.apply(frame)
    
    # Filter out small noise
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    fgMask = cv2.morphologyEx(fgMask, cv2.MORPH_OPEN, kernel)
    
    # Find moving objects (contours)
    contours, _ = cv2.findContours(fgMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    movement_detected = 0
    alert_status = 0
    
    # Draw logic on original frame
    for contour in contours:
        # Only care about large objects (like a person)
        if cv2.contourArea(contour) > 5000:
            movement_detected = 1
            x, y, w, h = cv2.boundingRect(contour)
            
            # Bounding box coordinates
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, "Active Patient", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # Simple Fall Logic Training concept: 
            # If the bounding box width is much larger than height (person fell horizontally)
            # and is located low on the camera angle
            if w > h * 1.5:
                alert_status = 1
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 4)
                cv2.putText(frame, "CRITICAL: FALL DETECTED", (x, y-30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

    # Calculate Actual Ambient Room Light from Camera Feed (Brightness)
    # By converting the frame to HSV, the 3rd channel (V) represents exact brightness from 0 to 255
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mean_brightness = hsv_frame[:,:,2].mean()
    # Map the brightness (0-255) to a dashboard "Lux Proxy" value (0-4000)
    calculated_light_proxy = int((mean_brightness / 255.0) * 4000)
    
    # Publish MQTT data every 0.5 seconds
    if time.time() - last_time > 0.5:
        payload = {
            "movement": movement_detected,
            "alert": alert_status,
            "light": calculated_light_proxy,        # Real light data from Camera!
            "temperature": round(random.uniform(36.5, 37.0), 1), # Good temp
            "heartRate": random.randint(70, 75)     # Good HR
        }
        
        # Publish
        client.publish(MQTT_TOPIC, json.dumps(payload))
        last_time = time.time()

    # Show video feed
    cv2.imshow('AI Patient Monitor (Edge Vision)', frame)

    # Press 'q' to quit
    if cv2.waitKey(30) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
client.loop_stop()
client.disconnect()
