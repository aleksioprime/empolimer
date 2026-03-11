/*
ESP8266 принимает данные от Arduino по UART (9600 бод)
в формате: DATA;datetime;temp;hum;bat

Пример:
DATA;2025-02-18T15:00:00;23.5;50.0;3.88

После получения:
1. Подключается к Wi-Fi
2. Подключается к MQTT брокеру
3. Формирует JSON:
   {"datetime":"...","temp":23.5,"hum":50.0,"bat":3.88}
4. Публикует в топик:
   devices/exp/air
5. Отправляет в UART ответ:
   ACK;OK / ACK;PARSE_FAIL / ACK;MQTT_DOWN и т.д.

Тесты:
- отправить PING (ответ: PONG)
- отправить DATA;2025-02-18T15:00:00;25.0;40.0;3.91 (ответ ACK;OK).
- отправить: DATA;none;25.0;40.0;3.91 (ответ ACK;OK).

Для проверки отправки нужно подключиться к MQTT-серверу через mosquitto_sub:
mosquitto_sub -h empolimer.ru -p 1883 -u empolimer -P Techno2025 -t devices/exp/air
*/

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <time.h>

// ---------- WiFi ----------
const char* WIFI_SSID = "IG_ForTeacher";
const char* WIFI_PASS = "SKTeacher2025";

// ---------- MQTT ----------
const char* broker   = "empolimer.ru";
const int   port     = 1883;
const char* mqttUser = "empolimer";
const char* mqttPass = "Techno2025";

const char* deviceName = "exp";
const char* clientId   = "device_exp_esp";

// ---------- UART ----------
const uint32_t UART_BAUD = 9600;

// ---------- NTP ----------
const long GMT_OFFSET_SEC = 3 * 3600; // МСК +3
const int  DAYLIGHT_OFFSET_SEC = 0;

// ---------- Clients ----------
WiFiClient espClient;
PubSubClient mqtt(espClient);

// ---------- UART buffer ----------
String line;

// ---------- Timers / state ----------
unsigned long lastWifiTry = 0;
unsigned long lastMqttTry = 0;
bool ntpConfigured = false;

const unsigned long WIFI_TRY_INTERVAL_MS = 5000;
const unsigned long MQTT_TRY_INTERVAL_MS = 3000;

// ========================= ACK / debug =========================
void ack(const String& msg) {
  Serial.println("ACK;" + msg);
}

// ========================= WiFi / MQTT =========================
void wifiEnsure() {
  if (WiFi.status() == WL_CONNECTED) return;

  unsigned long now = millis();
  if (now - lastWifiTry < WIFI_TRY_INTERVAL_MS) return;
  lastWifiTry = now;

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
}

void mqttEnsure() {
  if (WiFi.status() != WL_CONNECTED) return;
  if (mqtt.connected()) return;

  unsigned long now = millis();
  if (now - lastMqttTry < MQTT_TRY_INTERVAL_MS) return;
  lastMqttTry = now;

  mqtt.setServer(broker, port);
  mqtt.connect(clientId, mqttUser, mqttPass);
}

// ========================= NTP time =========================
void ntpEnsureConfigured() {
  if (ntpConfigured) return;
  if (WiFi.status() != WL_CONNECTED) return;

  // НЕ ждём синхронизацию, просто запускаем
  configTime(GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC, "pool.ntp.org", "time.nist.gov");
  ntpConfigured = true;
}

bool timeReady() {
  return time(nullptr) > 1700000000; // примерно 2023+
}

String nowIso8601() {
  time_t raw = time(nullptr);
  struct tm* ti = localtime(&raw);
  char buf[32];

  // Если меняешь GMT_OFFSET_SEC, лучше поменять и +03:00 здесь.
  snprintf(buf, sizeof(buf),
           "%04d-%02d-%02dT%02d:%02d:%02d+03:00",
           ti->tm_year + 1900, ti->tm_mon + 1, ti->tm_mday,
           ti->tm_hour, ti->tm_min, ti->tm_sec);

  return String(buf);
}

// ========================= Parsing =========================
bool parseDataLine(const String& s, String& dt, float& t, float& h, float& bat) {
  // ожидаем: DATA;dt;t;h;bat
  if (!s.startsWith("DATA;")) return false;

  int p1 = s.indexOf(';');
  int p2 = s.indexOf(';', p1 + 1);
  int p3 = s.indexOf(';', p2 + 1);
  int p4 = s.indexOf(';', p3 + 1);
  if (p1 < 0 || p2 < 0 || p3 < 0 || p4 < 0) return false;

  dt  = s.substring(p1 + 1, p2);
  t   = s.substring(p2 + 1, p3).toFloat();
  h   = s.substring(p3 + 1, p4).toFloat();
  bat = s.substring(p4 + 1).toFloat();
  return true;
}

// ========================= MQTT publish =========================
bool publishToMqtt(String dt, float t, float h, float bat) {
  // Время подставляем ТОЛЬКО если пришло "none" И NTP уже готов.
  // Никаких ожиданий/запросов тут!
  if ((dt == "none" || dt.length() == 0) && timeReady()) {
    dt = nowIso8601();
  }

  String payload = String("{\"datetime\":\"") + dt +
                   String("\",\"temp\":") + String(t, 1) +
                   String(",\"hum\":") + String(h, 1) +
                   String(",\"bat\":") + String(bat, 2) + "}";

  String topic = String("devices/") + deviceName + "/air";
  return mqtt.publish(topic.c_str(), payload.c_str());
}

// ========================= Command handler =========================
void handleLine(const String& s) {
  if (s == "PING") {
    Serial.println("PONG");
    return;
  }

  String dt; float t, h, bat;
  if (!parseDataLine(s, dt, t, h, bat)) {
    ack("PARSE_FAIL");
    return;
  }

  if (WiFi.status() != WL_CONNECTED) {
    ack("WIFI_DOWN");
    return;
  }

  if (!mqtt.connected()) {
    ack("MQTT_DOWN");
    return;
  }

  bool ok = publishToMqtt(dt, t, h, bat);
  if (ok) ack("OK");
  else    ack("MQTT_FAIL");
}

// ========================= Setup / Loop =========================
void setup() {
  Serial.begin(UART_BAUD);
  delay(100);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  mqtt.setServer(broker, port);

  Serial.println("ESP_READY");
}

void loop() {
  // 1) Поддерживаем соединения (неблокирующе)
  wifiEnsure();
  mqttEnsure();
  ntpEnsureConfigured();

  // 2) MQTT loop (безопасно даже когда не connected)
  mqtt.loop();

  // 3) Читаем UART построчно
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      line.trim();
      if (line.length()) handleLine(line);
      line = "";
    } else {
      if (line.length() < 220) line += c;
      else line = ""; // защита от мусора
    }
  }
}