// Wi-Fi, часы (NTP) и MQTT. Ничего не блокирует loop(): при обрыве устройство
// продолжает измерять и писать на SD, а подключение повторяется в фоне.
//
// Топики (prefix из config.json, по умолчанию empolimer):
//   <prefix>/<id>/data   - измерение
//   <prefix>/<id>/status - состояние, retain; при обрыве брокер сам публикует {"online":false}
//   <prefix>/<id>/cmd    - команды устройству (см. commands.h)
//
// Точка доступа: если Wi-Fi не настроен или недоступен дольше минуты, устройство
// поднимает свою сеть EmPolimer-<id> (пароль ap.pass), страница - http://192.168.4.1.
// После подключения к Wi-Fi точка выключается, когда к ней никто не подключён.
#pragma once

#include <Arduino.h>

void networkBegin(void (*onMqttConnected)());
void networkLoop();
bool wifiConnected();
bool mqttConnected();
bool mqttPublish(const char* kind, const String& payload, bool retain = false);
String wifiAddress();
int wifiSignal();
bool apActive();
String apName();
String hostName();   // имя в сети: <hostName>.local
