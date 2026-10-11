// Настройки устройства: читаются из /config.json на SD-карте.
// Без карты или файла устройство работает со значениями по умолчанию:
// измеряет, управляет светом и общается с Raspberry, но не выходит в интернет.
#pragma once

#include <Arduino.h>

const uint8_t MAX_WIFI_NETWORKS = 4;

struct WifiNetwork {
  String ssid;
  String pass;
};

struct Config {
  String deviceId;                 // латиница, цифры, - и _; пусто - "esp-<chip id>"
  uint32_t intervalSec = 60;       // период измерений

  WifiNetwork wifi[MAX_WIFI_NETWORKS];
  uint8_t wifiCount = 0;

  String mqttHost;                 // пусто - данные только на SD и в Raspberry
  uint16_t mqttPort = 1883;
  String mqttUser;
  String mqttPass;
  String mqttPrefix = "empolimer";

  String timezone = "MSK-3";       // POSIX TZ: MSK-3, <+07>-7 и т. п.

  uint8_t dhtType = 11;            // 11 или 22

  uint16_t lightCount = 30;
  uint32_t lightColor = 0xC800B4;  // фиолетовый - для растений
  uint8_t lightBrightness = 200;
  int16_t lightOnMinute = -1;      // расписание, минуты от полуночи; -1 - нет
  int16_t lightOffMinute = -1;

  bool webEnabled = true;          // страница устройства на порту 80
  bool webControl = true;          // управление подсветкой со страницы
  String apPass = "empolimer";     // пароль своей точки доступа (8+ символов; пусто - открытая)
  bool apEnabled = true;           // поднимать точку доступа, если Wi-Fi недоступен

  float tempMin = 18, tempMax = 28;  // норма для подсветки значений на странице
  float humMin = 40, humMax = 70;

  bool batteryEnabled = false;
  float batteryDivider = 2.58;     // (R1 + R2) / R2
  float adcRef = 3.3;
};

extern Config cfg;

// Заполняет cfg из файла; при ошибке оставляет значения по умолчанию и пишет причину в error.
bool configLoad(const char* path, String& error);
