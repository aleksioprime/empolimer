// Команды устройства. Приходят из порта (от Raspberry) и из MQTT-топика
// <prefix>/<id>/cmd. Регистр не важен.
//
//   STATUS              - прислать состояние
//   READ                - измерить сейчас
//   LIGHT ON [0..255]   - включить подсветку (с яркостью)
//   LIGHT OFF           - выключить
//   LIGHT AUTO          - вернуть расписание из config.json
//   TIME <unix-время>   - установить часы (Raspberry делает это сама при подключении)
//   HELP                - список команд
#pragma once

#include <Arduino.h>

// Выполняет команду и возвращает ответ - строку JSON {"type":"ack", ...}.
String runCommand(const String& command);

// Реализованы в empolimer.ino.
void sendStatus();
void requestMeasure();
