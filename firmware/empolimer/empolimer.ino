// ЕмПолимер — прошивка модульного устройства микроклимата.
//
// Платы: NodeMCU / ESP-12 (ESP8266) и ESP32. Модули: датчик DHT11/DHT22,
// адресная лента подсветки, SD-карта (настройки, журнал, очередь), Wi-Fi + MQTT,
// страница устройства в браузере, USB-порт для Raspberry. Любой модуль можно
// не подключать — остальные работают.
//
// Пины — board.h, настройки — /config.json на SD (пример в firmware/sd-card/),
// форматы сообщений — docs/protocol.md.

#include <ArduinoJson.h>
#include <DHT.h>
#include <time.h>

#include "board.h"
#include "commands.h"
#include "config.h"
#include "light.h"
#include "link.h"
#include "network.h"
#include "state.h"
#include "storage.h"
#include "web.h"

State state;

static const uint32_t STATUS_INTERVAL_MS = 60000;
static const uint8_t QUEUE_BATCH = 10;  // сколько накопленных измерений отправлять за один проход loop()

static DHT* dht = nullptr;
static uint32_t lastMeasureAttemptMs = 0;
static uint32_t lastStatusMs = 0;
static bool measureRequested = true;  // первое измерение — сразу после старта

static String defaultDeviceId() {
#if defined(ESP32)
  uint32_t chip = (uint32_t)ESP.getEfuseMac();
#else
  uint32_t chip = ESP.getChipId();
#endif
  char id[16];
  snprintf(id, sizeof(id), "esp-%06lx", (unsigned long)(chip & 0xFFFFFF));
  return String(id);
}

static float readBattery() {
  if (!cfg.batteryEnabled) return NAN;
  return analogRead(PIN_BATTERY) * cfg.adcRef / ADC_MAX * cfg.batteryDivider;
}

// Измерение в JSON. ts есть только при верных часах — иначе время поставит сервер.
static String dataJson(time_t ts, bool withType) {
  JsonDocument doc;
  if (withType) doc["type"] = "data";
  if (ts > 0) doc["ts"] = (long long)ts;
  doc["temp"] = serialized(String(state.temperature, 1));
  doc["hum"] = serialized(String(state.humidity, 1));
  if (!isnan(state.battery)) doc["bat"] = serialized(String(state.battery, 2));
  String out;
  serializeJson(doc, out);
  return out;
}

static String statusJson(bool withType) {
  JsonDocument doc;
  if (withType) doc["type"] = "status";
  doc["online"] = true;
  doc["id"] = cfg.deviceId;
  doc["fw"] = FIRMWARE_VERSION;
  doc["board"] = BOARD_NAME;
  doc["uptime"] = millis() / 1000;
  doc["interval"] = cfg.intervalSec;
  doc["wifi"] = wifiConnected();
  doc["mqtt"] = mqttConnected();
  if (wifiConnected()) {
    doc["ip"] = wifiAddress();
    doc["rssi"] = wifiSignal();
  }
  doc["host"] = hostName();
  doc["ap"] = apActive();
  doc["time"] = timeValid();
  doc["sd"] = state.sdReady;
  if (state.configError.length()) doc["config_error"] = state.configError;
  doc["sensor"] = state.sensorOk;
  doc["queue"] = state.queued;
  doc["light"] = lightIsOn();
  doc["light_auto"] = lightIsAuto();
  doc["brightness"] = lightBrightness();
  String out;
  serializeJson(doc, out);
  return out;
}

static void measure() {
  lastMeasureAttemptMs = millis();
  measureRequested = false;

  float temperature = dht->readTemperature();
  float humidity = dht->readHumidity();
  bool ok = !isnan(temperature) && !isnan(humidity);
  if (ok != state.sensorOk) {
    state.sensorOk = ok;
    if (!ok) logf("Датчик DHT%u не отвечает: проверьте провод на пине %d", cfg.dhtType, PIN_DHT);
    sendStatus();
  }
  if (!ok) return;

  state.temperature = temperature;
  state.humidity = humidity;
  state.battery = readBattery();
  state.lastMeasureMs = millis();
  webRecord(temperature, humidity);

  time_t ts = timeValid() ? time(nullptr) : 0;
  linkSend(dataJson(ts, true));
  storageLog(ts, temperature, humidity, state.battery);

  String payload = dataJson(ts, false);
  // Без часов измерение нельзя отправить позже с правильным временем, поэтому в очередь оно не идёт
  // (но остаётся в журнале на SD).
  if (ts == 0) {
    mqttPublish("data", payload);
    return;
  }
  // Пока очередь не пуста, новые измерения встают в её конец, чтобы данные шли по порядку.
  if (queueSize() == 0 && mqttPublish("data", payload)) return;
  if (cfg.mqttHost.length()) queuePush(payload);
}

static void flushQueue() {
  if (!mqttConnected()) return;
  String line;
  for (uint8_t i = 0; i < QUEUE_BATCH && queuePeek(line); i++) {
    if (!mqttPublish("data", line)) return;
    queuePop();
  }
}

static void onMqttConnected() {
  sendStatus();
}

bool timeValid() {
  return time(nullptr) > 1700000000;  // позже ноября 2023 — значит, часы установлены
}

void sendStatus() {
  lastStatusMs = millis();
  linkSend(statusJson(true));
  mqttPublish("status", statusJson(false), true);
}

void requestMeasure() {
  measureRequested = true;
}

void setup() {
  linkBegin();
  logf("ЕмПолимер %s, плата %s", FIRMWARE_VERSION, BOARD_NAME);

  if (storageBegin()) {
    if (!configLoad("/config.json", state.configError)) {
      logf("config.json: %s — работаю с настройками по умолчанию", state.configError.c_str());
    }
  } else {
    state.configError = "SD-карта не найдена";
    logf("SD-карта не найдена (CS на пине %d) — работаю без журнала и сети", PIN_SD_CS);
  }
  if (!cfg.deviceId.length()) cfg.deviceId = defaultDeviceId();
  logf("Устройство %s, измерение раз в %lu с", cfg.deviceId.c_str(), (unsigned long)cfg.intervalSec);

  dht = new DHT(PIN_DHT, cfg.dhtType);
  dht->begin();
  lightBegin();
  networkBegin(onMqttConnected);
  webBegin(statusJson);
  sendStatus();
}

void loop() {
  linkPoll();
  networkLoop();
  webLoop();
  lightTick();

  // DHT нельзя опрашивать чаще раза в 2 секунды.
  bool due = millis() - lastMeasureAttemptMs >= cfg.intervalSec * 1000UL;
  if ((due || measureRequested) && millis() - lastMeasureAttemptMs >= 2000) measure();

  flushQueue();
  if (millis() - lastStatusMs >= STATUS_INTERVAL_MS) sendStatus();
  delay(10);
}
