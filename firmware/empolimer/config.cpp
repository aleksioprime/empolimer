#include "config.h"

#include <ArduinoJson.h>
#include <SD.h>

Config cfg;

namespace {

// "07:30" → 450; ошибка или пустая строка → -1.
int16_t parseMinutes(const char* value) {
  if (!value || !*value) return -1;
  int h = 0, m = 0;
  if (sscanf(value, "%d:%d", &h, &m) != 2 || h < 0 || h > 23 || m < 0 || m > 59) return -1;
  return h * 60 + m;
}

// "#C800B4" или "C800B4" → 0xC800B4.
uint32_t parseColor(const char* value, uint32_t fallback) {
  if (!value || !*value) return fallback;
  if (*value == '#') value++;
  char* end = nullptr;
  uint32_t color = strtoul(value, &end, 16);
  return (end && *end == '\0') ? color : fallback;
}

bool validDeviceId(const String& id) {
  if (id.length() == 0 || id.length() > 32) return false;
  for (char c : id) {
    if (!isalnum(c) && c != '-' && c != '_') return false;
  }
  return true;
}

}  // namespace

bool configLoad(const char* path, String& error) {
  File file = SD.open(path, FILE_READ);
  if (!file) {
    error = String("нет файла ") + path;
    return false;
  }

  JsonDocument doc;
  DeserializationError result = deserializeJson(doc, file);
  file.close();
  if (result) {
    error = String("ошибка JSON: ") + result.c_str();
    return false;
  }

  String id = doc["device"]["id"] | "";
  if (id.length() && !validDeviceId(id)) {
    error = "device.id: только латиница, цифры, - и _ (до 32 символов)";
  } else {
    cfg.deviceId = id;
  }
  cfg.intervalSec = max<uint32_t>(doc["device"]["interval"] | cfg.intervalSec, 5);

  // wifi - одна сеть {ssid, pass} или список; устройство перебирает их, пока не подключится.
  cfg.wifiCount = 0;
  auto addNetwork = [](JsonObjectConst net) {
    String ssid = net["ssid"] | "";
    if (!ssid.length() || cfg.wifiCount >= MAX_WIFI_NETWORKS) return;
    cfg.wifi[cfg.wifiCount].ssid = ssid;
    cfg.wifi[cfg.wifiCount].pass = net["pass"] | "";
    cfg.wifiCount++;
  };
  if (doc["wifi"].is<JsonArrayConst>()) {
    for (JsonObjectConst net : doc["wifi"].as<JsonArrayConst>()) addNetwork(net);
  } else if (doc["wifi"].is<JsonObjectConst>()) {
    addNetwork(doc["wifi"].as<JsonObjectConst>());
  }

  cfg.mqttHost = doc["mqtt"]["host"] | "";
  cfg.mqttPort = doc["mqtt"]["port"] | cfg.mqttPort;
  cfg.mqttUser = doc["mqtt"]["user"] | "";
  cfg.mqttPass = doc["mqtt"]["pass"] | "";
  cfg.mqttPrefix = doc["mqtt"]["prefix"] | cfg.mqttPrefix.c_str();

  cfg.timezone = doc["time"]["tz"] | cfg.timezone.c_str();

  uint8_t dhtType = doc["sensor"]["type"] | cfg.dhtType;
  cfg.dhtType = (dhtType == 22) ? 22 : 11;

  cfg.lightCount = doc["light"]["count"] | cfg.lightCount;
  cfg.lightColor = parseColor(doc["light"]["color"] | "", cfg.lightColor);
  cfg.lightBrightness = doc["light"]["brightness"] | cfg.lightBrightness;
  cfg.lightOnMinute = parseMinutes(doc["light"]["on"] | "");
  cfg.lightOffMinute = parseMinutes(doc["light"]["off"] | "");

  cfg.webEnabled = doc["web"]["enabled"] | cfg.webEnabled;
  cfg.webControl = doc["web"]["control"] | cfg.webControl;
  cfg.apEnabled = doc["ap"]["enabled"] | cfg.apEnabled;
  cfg.apPass = doc["ap"]["pass"] | cfg.apPass.c_str();
  if (cfg.apPass.length() && cfg.apPass.length() < 8) {
    error = "ap.pass: не меньше 8 символов (или пусто - открытая сеть)";
    cfg.apPass = "empolimer";
  }

  cfg.tempMin = doc["norm"]["temp_min"] | cfg.tempMin;
  cfg.tempMax = doc["norm"]["temp_max"] | cfg.tempMax;
  cfg.humMin = doc["norm"]["hum_min"] | cfg.humMin;
  cfg.humMax = doc["norm"]["hum_max"] | cfg.humMax;

  cfg.batteryEnabled = doc["battery"]["enabled"] | cfg.batteryEnabled;
  cfg.batteryDivider = doc["battery"]["divider"] | cfg.batteryDivider;
  cfg.adcRef = doc["battery"]["adc_ref"] | cfg.adcRef;

  return error.length() == 0;
}
