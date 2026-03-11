#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <SPI.h>
#include <SD.h>
#include <ArduinoJson.h>
#include <Adafruit_NeoPixel.h>

// ===== ПИНЫ =====
#define DHTPIN D4
#define DHTTYPE DHT11
#define LED_PIN D2
#define LED_COUNT 33
#define SD_CS D8
#define BATTERY_PIN A0

// ===== ОБЪЕКТЫ =====
DHT dht(DHTPIN, DHTTYPE);
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);
WiFiClient espClient;
PubSubClient mqtt(espClient);

// ===== CONFIG =====
String wifi_ssid, wifi_pass;
String mqtt_broker, mqtt_user, mqtt_pass, mqtt_topic, device_name;
int mqtt_port = 1883;

float R1=15800, R2=10000, ADC_REF=3.3;
int ADC_MAX = 1023;

unsigned long lastSensorRead = 0;
const unsigned long sensorInterval = 5000;

// ===== ЗАГРУЗКА CONFIG =====
void loadConfig() {
  File f = SD.open("/config.json", FILE_READ);
  if (!f) {
    Serial.println("config.json не найден");
    return;
  }

  StaticJsonDocument<512> doc;
  deserializeJson(doc, f);
  f.close();

  wifi_ssid   = doc["wifi"]["ssid"].as<String>();
  wifi_pass   = doc["wifi"]["pass"].as<String>();
  mqtt_broker = doc["mqtt"]["broker"].as<String>();
  mqtt_port   = doc["mqtt"]["port"];
  mqtt_user   = doc["mqtt"]["user"].as<String>();
  mqtt_pass   = doc["mqtt"]["pass"].as<String>();
  mqtt_topic  = doc["mqtt"]["topic"].as<String>();
  device_name = doc["device"]["name"].as<String>();
}

// ===== WIFI =====
void connectWiFi() {
  WiFi.begin(wifi_ssid.c_str(), wifi_pass.c_str());
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}

// ===== MQTT =====
void connectMQTT() {
  mqtt.setServer(mqtt_broker.c_str(), mqtt_port);
  while (!mqtt.connected()) {
    mqtt.connect(device_name.c_str(), mqtt_user.c_str(), mqtt_pass.c_str());
    delay(1000);
  }
}

// ===== БАТАРЕЯ =====
float getBatteryVoltage() {
  int adc = analogRead(BATTERY_PIN);
  return (adc * ADC_REF / ADC_MAX) * ((R1 + R2) / R2);
}

// ===== LED =====
void phytoLedOn() {
  for (int i=0;i<LED_COUNT;i++)
    strip.setPixelColor(i, strip.Color(200,0,180));
  strip.show();
}

void phytoLedOff() {
  strip.clear();
  strip.show();
}

void setup() {
  Serial.begin(115200);

  dht.begin();
  strip.begin();
  strip.show();

  if (!SD.begin(SD_CS)) {
    Serial.println("Ошибка SD");
    return;
  }

  loadConfig();
  connectWiFi();
  connectMQTT();

  if (!SD.exists("/data.csv")) {
    File f = SD.open("/data.csv", FILE_WRITE);
    if (f) {
      f.println("timestamp,temp,hum,bat");
      f.close();
    }
  }
}

void loop() {
  mqtt.loop();

  // ===== ПРИЁМ КОМАНД ОТ RPI =====
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "LED_ON") phytoLedOn();
    if (cmd == "LED_OFF") phytoLedOff();
  }

  unsigned long now = millis();
  if (now - lastSensorRead >= sensorInterval) {
    lastSensorRead = now;

    float h = dht.readHumidity();
    float t = dht.readTemperature();
    float bat = getBatteryVoltage();

    if (isnan(h) || isnan(t)) return;

    // ===== CSV =====
    File f = SD.open("/data.csv", FILE_WRITE);
    if (f) {
      f.printf("%lu,%.1f,%.1f,%.2f\n", now/1000, t, h, bat);
      f.close();
    }

    // ===== MQTT =====
    StaticJsonDocument<200> doc;
    doc["temp"] = t;
    doc["hum"] = h;
    doc["bat"] = bat;
    String payload;
    serializeJson(doc, payload);
    mqtt.publish(mqtt_topic.c_str(), payload.c_str());

    // ===== UART В RPI =====
    Serial.printf("DATA;%lu;%.1f;%.1f;%.2f\n", now/1000, t, h, bat);
  }
}
