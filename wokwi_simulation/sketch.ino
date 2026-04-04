#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

// Wokwi provides a free virtual WiFi network
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// Public MQTT Broker
const char* mqtt_server = "broker.hivemq.com";
const char* mqtt_topic_publish = "iot_fundamentals_project/patient_data";

WiFiClient espClient;
PubSubClient client(espClient);

// Sensor Pins
const int pirPin = 15;     // PIR Motion Sensor (Proxy for Visual tracking)
const int ldrPin = 34;     // Light Dependent Resistor (Analog)
const int buttonPin = 4;   // Push Button (Fall Alert)
const int hrPin = 35;      // Potentiometer for Heart Rate

#define DHTPIN 13
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

// Variables to keep track of state
int pirState = LOW;
int lastPirState = LOW;
int alertState = 0;

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Create a random client ID
    String clientId = "ESP32Client-";
    clientId += String(random(0xffff), HEX);
    // Attempt to connect
    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  
  pinMode(pirPin, INPUT);
  pinMode(buttonPin, INPUT_PULLUP);
  dht.begin();
  
  // Setup WiFi and MQTT
  setup_wifi();
  client.setServer(mqtt_server, 1883);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Read sensors
  int currentPirState = digitalRead(pirPin);
  int currentLdrValue = analogRead(ldrPin);
  
  float temp = dht.readTemperature();
  if (isnan(temp)) temp = 24.0; // Fallback
  
  int hrRaw = analogRead(hrPin);
  int bpm = map(hrRaw, 0, 4095, 40, 180); // Map to realistic BPM
  
  // Button is active LOW due to pullup
  int buttonPressed = (digitalRead(buttonPin) == LOW) ? 1 : 0;
  
  if (buttonPressed) {
    alertState = 1; // Latch the alert
  } else {
    // Basic mechanism to clear alert if no longer pressed (for simulation purposes)
    alertState = 0;
  }

  // Simple logic to detect movement changes
  int movementActive = 0;
  if (currentPirState == HIGH) {
    movementActive = 1;
    if (lastPirState == LOW) {
      Serial.println("Movement detected!");
      lastPirState = HIGH;
    }
  } else {
    if (lastPirState == HIGH) {
      Serial.println("Movement ended.");
      lastPirState = LOW;
    }
  }

  // To avoid spamming the broker, we'll send data every 2 seconds
  static unsigned long lastMsg = 0;
  unsigned long now = millis();
  if (now - lastMsg > 2000) {
    lastMsg = now;
    
    // Construct JSON String manually for simplicity
    String payload = "{";
    payload += "\"movement\": " + String(movementActive) + ", ";
    payload += "\"light\": " + String(currentLdrValue) + ", ";
    payload += "\"alert\": " + String(alertState) + ", ";
    payload += "\"temperature\": " + String(temp, 1) + ", ";
    payload += "\"heartRate\": " + String(bpm);
    payload += "}";

    Serial.print("Publishing message: ");
    Serial.println(payload);
    
    client.publish(mqtt_topic_publish, payload.c_str());
  }
}
