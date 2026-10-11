// Текущее состояние устройства: его видят Raspberry (по порту) и сервер (в MQTT-статусе).
#pragma once

#include <Arduino.h>

struct State {
  bool sdReady = false;
  String configError;          // пусто - config.json прочитан без ошибок
  bool sensorOk = false;
  float temperature = NAN;
  float humidity = NAN;
  float battery = NAN;
  uint32_t lastMeasureMs = 0;  // millis() последнего удачного измерения; 0 - ещё не было
  uint32_t queued = 0;         // измерений ждут отправки на сервер
};

extern State state;

// Время синхронизировано (NTP или команда TIME от Raspberry).
bool timeValid();
