#include "network.h"

#include <PubSubClient.h>
#include <time.h>

#if defined(ESP32)
  #include <WiFi.h>
#else
  #include <ESP8266WiFi.h>
#endif

#include "commands.h"
#include "config.h"
#include "link.h"

namespace {

const uint32_t WIFI_ATTEMPT_MS = 20000;  // сколько ждать одну сеть перед переходом к следующей
const uint32_t MQTT_BACKOFF_MIN_MS = 2000;
const uint32_t MQTT_BACKOFF_MAX_MS = 60000;
const char* OFFLINE_STATUS = "{\"online\":false}";

WiFiClient tcp;
PubSubClient mqtt(tcp);
void (*mqttConnectedHandler)() = nullptr;

uint8_t wifiIndex = 0;
uint32_t wifiAttemptMs = 0;
bool wifiWasConnected = false;
bool ntpStarted = false;

uint32_t mqttAttemptMs = 0;
uint32_t mqttBackoffMs = 0;

String topic(const char* kind) {
  return cfg.mqttPrefix + "/" + cfg.deviceId + "/" + kind;
}

void onMessage(char* topicName, byte* payload, unsigned int length) {
  String command;
  command.reserve(length);
  for (unsigned int i = 0; i < length; i++) command += (char)payload[i];
  logf("MQTT-команда: %s", command.c_str());
  linkSend(runCommand(command));
}

void startNtp() {
#if defined(ESP32)
  configTzTime(cfg.timezone.c_str(), "pool.ntp.org", "time.google.com");
#else
  configTime(cfg.timezone.c_str(), "pool.ntp.org", "time.google.com");
#endif
  ntpStarted = true;
}

void wifiLoop() {
  if (cfg.wifiCount == 0) return;

  bool connected = WiFi.status() == WL_CONNECTED;
  if (connected != wifiWasConnected) {
    wifiWasConnected = connected;
    if (connected) {
      logf("Wi-Fi: %s, IP %s", WiFi.SSID().c_str(), WiFi.localIP().toString().c_str());
      if (!ntpStarted) startNtp();
    } else {
      logf("Wi-Fi: связь потеряна");
    }
  }
  if (connected) return;

  if (wifiAttemptMs && millis() - wifiAttemptMs < WIFI_ATTEMPT_MS) return;
  wifiAttemptMs = millis();
  const WifiNetwork& net = cfg.wifi[wifiIndex];
  wifiIndex = (wifiIndex + 1) % cfg.wifiCount;
  logf("Wi-Fi: подключение к %s", net.ssid.c_str());
  WiFi.disconnect();
  WiFi.begin(net.ssid.c_str(), net.pass.c_str());
}

void mqttLoop() {
  if (!cfg.mqttHost.length() || WiFi.status() != WL_CONNECTED) return;
  if (mqtt.connected()) {
    mqtt.loop();
    return;
  }
  if (mqttAttemptMs && millis() - mqttAttemptMs < mqttBackoffMs) return;
  mqttAttemptMs = millis();

  String clientId = "empolimer-" + cfg.deviceId;
  String willTopic = topic("status");
  const char* user = cfg.mqttUser.length() ? cfg.mqttUser.c_str() : nullptr;
  const char* pass = cfg.mqttPass.length() ? cfg.mqttPass.c_str() : nullptr;
  if (mqtt.connect(clientId.c_str(), user, pass, willTopic.c_str(), 1, true, OFFLINE_STATUS)) {
    logf("MQTT: подключено к %s:%u", cfg.mqttHost.c_str(), cfg.mqttPort);
    mqttBackoffMs = MQTT_BACKOFF_MIN_MS;
    mqtt.subscribe(topic("cmd").c_str());
    if (mqttConnectedHandler) mqttConnectedHandler();
  } else {
    mqttBackoffMs = constrain(mqttBackoffMs * 2, MQTT_BACKOFF_MIN_MS, MQTT_BACKOFF_MAX_MS);
    logf("MQTT: ошибка %d, повтор через %lu с", mqtt.state(), (unsigned long)(mqttBackoffMs / 1000));
  }
}

}  // namespace

void networkBegin(void (*onMqttConnected)()) {
  mqttConnectedHandler = onMqttConnected;

  // Часовой пояс нужен и без сети: часы может установить Raspberry командой TIME.
  setenv("TZ", cfg.timezone.c_str(), 1);
  tzset();

  WiFi.persistent(false);  // не изнашивать flash настройками — они живут на SD
  WiFi.mode(cfg.wifiCount ? WIFI_STA : WIFI_OFF);
  WiFi.setAutoReconnect(true);

  mqtt.setServer(cfg.mqttHost.c_str(), cfg.mqttPort);
  mqtt.setCallback(onMessage);
  mqtt.setBufferSize(512);
  mqtt.setSocketTimeout(5);
  tcp.setTimeout(5000);
  mqttBackoffMs = MQTT_BACKOFF_MIN_MS;
}

void networkLoop() {
  wifiLoop();
  mqttLoop();
}

bool wifiConnected() {
  return WiFi.status() == WL_CONNECTED;
}

bool mqttConnected() {
  return mqtt.connected();
}

bool mqttPublish(const char* kind, const String& payload, bool retain) {
  if (!mqtt.connected()) return false;
  return mqtt.publish(topic(kind).c_str(), payload.c_str(), retain);
}

String wifiAddress() {
  return wifiConnected() ? WiFi.localIP().toString() : String();
}

int wifiSignal() {
  return wifiConnected() ? WiFi.RSSI() : 0;
}
