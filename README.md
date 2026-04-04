# Remote Patient Monitoring via AI & Visual Sensors 🏥👁️

This repository contains the source code for an advanced IoT edge-computing project designed to monitor patient vitals and activity using conceptual Kaggle-trained Machine Learning models and classical Computer Vision (OpenCV).

## Features
*   **Edge Machine Learning:** Uses OpenCV to isolate patient movement and dynamically calculate bounding boxes.
*   **Privacy-First "Visual Sensors":** Never transmits raw video. The edge camera infers status locally and only transmits metadata.
*   **Fall Detection:** Uses geometric contour mapping to detect if a patient has fallen in real-time.
*   **Ambient Lighting Detection:** Dynamically adjusts to the room's luminance via HSV proxy mapping.
*   **Real-Time Dashboard:** A responsive HTML/JS vanilla web dashboard fed instantly by Paho-MQTT over WebSockets.

## Project Structure
*   `ai_camera_node.py` - The core AI vision node running locally (simulating a deployed Edge device).
*   `dashboard/` - Contains the Python Flask backend and HTML/CSS web portal.
*   `wokwi_simulation/` - (Optional) The original C++ ESP32 proxy architecture code.

## Tech Stack
*   **Language:** Python 3
*   **Computer Vision:** OpenCV (`cv2`)
*   **Connectivity:** MQTT (`paho-mqtt`) via `broker.hivemq.com`
*   **Dashboard:** Python Flask, HTML5, CSS3, Vanilla JS

## How to Run
1. Start the web server:
    ```bash
    cd dashboard
    python app.py
    ```
2. Open your browser to `http://localhost:5000`
3. In a new terminal, start the AI Vision Node:
    ```bash
    python ai_camera_node.py
    ```
