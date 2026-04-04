# Presentation Outline: Remote Patient Monitoring and Analytics using Visual Sensors

*This outline provides a slide-by-slide guide for your PowerPoint presentation, incorporating the Wokwi simulation and Kaggle dataset integration.*

---

## Slide 1: Title Slide
- **Title:** Remote Patient Monitoring and Analytics using Visual Sensors
- **Subtitle:** IoT Fundamentals Project
- **Information:** Your Name, Course Name, Date

## Slide 2: Introduction
- **The Context:** The rising aging population and the growing need for out-of-hospital continuous healthcare.
- **The Concept:** Utilizing non-intrusive "visual sensors" (or visual proxies like motion clustering) to monitor patient activity, detect falls, and track sleep environments.
- **The IoT Role:** Edge computing devices capture visual/spatial data and transmit critical alerts to cloud dashboards instantly.

## Slide 3: Problem Statement & Objectives
- **Problem:** Current medical monitoring is often intrusive (wearables that patients forget or refuse to wear). 
- **Objective:** Design a completely ambient, non-wearable remote monitoring system.
- **Goal:** To securely transmit patient telemetry and detect emergencies (like falls or lack of movement) in real-time using simulated Edge AI configurations.

## Slide 4: Real-World AI Integration (Kaggle & Vision)
- **The AI Pipeline:** To move from simulated proxy sensors to true visual sensors, we implement a Machine Learning pipeline.
- **Kaggle Database Training:** We download a massive annotated dataset from Kaggle (e.g., "UR Fall Detection Dataset" or "Human Activity Recognition").
- **Model Training:** We train a Deep Learning model (like YOLOv8 or MediaPipe Pose) on this dataset to classify frames into activities: *Lying, Sitting, Walking, Falling*.
- **The Edge Node:** The trained AI model is deployed directly onto an Edge vision node (like a Raspberry Pi with a Camera Module or an ESP32-CAM) to ensure privacy—no videos are sent to the cloud, only the AI's conclusions (e.g., "Status: Sleeping").

## Slide 5: The System Architecture (Edge + Cloud)
- **Edge Vision Node:** A local PC or Raspberry Pi acts as the Edge device. It uses an integrated webcam to gather environmental and movement data without recording raw video. 
- **Communication Protocol:** MQTT over WebSockets. Fast, low-latency, and standard for IoT infrastructure.
- **Cloud Dashboard:** A web-based analytics portal that visualizes activity levels, ambient hospital room lighting, and immediate emergency alerts.

## Slide 6: Edge AI Software Implementation 
- **The Intelligence (Python & OpenCV):** 
  - Uses `cv2` (OpenCV) to apply geometric contour detection and background subtraction.
  - Dynamically calculates the ambient room lighting by analyzing the camera's HSV limits.
- **The Connectivity (Paho-MQTT):**
  - AI events (Movement, Light levels, Fall detection) are packaged into tiny JSON strings.
  - Broadcasts instantaneously to `broker.hivemq.com` on a private channel.

## Slide 7: The Patient Analytics Dashboard
- **Web App Technologies:** Built with **Python (Flask)**, custom CSS, and **HTML/Vanilla JS**.
- **Real-Time Responsiveness:**
  - Uses JavaScript `Paho-MQTT` to subscribe to the live data feed directly over WebSockets.
  - Updates critical UI components (like Body Temperature or Fall Alerts) dynamically without refreshing the page.

## Slide 8: Live Demonstration
- *Include a screenshot or record a video of the active Dashboard next to the Camera feed.*
- **Talking Points during Demo:**
  - Show how waving at the camera instantly updates the dashboard to "Active".
  - Show how covering the camera perfectly drops the "Lux" room lighting value.
  - Show a simulated "Fall" (ducking down) and how the AI immediately pushes a "CRITICAL: FALL DETECTED" alert to the dashboard.

## Slide 9: Future Scope
- **Hardware Upgrade:** Replacing the ESP32/PIR proxy with an actual **ESP32-CAM** or **Raspberry Pi** running TensorFlow Lite.
- **Advanced Privacy:** Using infrared cameras or edge-blurred vision to maintain patient dignity while monitoring posture.
- **Predictive Analytics:** Feeding real-time telemetry back into Kaggle models to predict health deterioration *before* emergencies happen.

## Slide 10: Conclusion
- Summarize the success of the simulation.
- Mention that IoT coupled with robust analytics pipelines provides a scalable, affordable, and lifesaving addition to modern healthcare.
- **Questions?**
