// Страница устройства на порту 80: показания, график последних измерений, состояние
// модулей, подсветка и журналы с SD-карты. Открывается по http://<hostName>.local,
// по IP-адресу в Wi-Fi или http://192.168.4.1 через точку доступа устройства.
//
//   GET  /              страница (web_page.h)
//   GET  /api/state     состояние и последние значения
//   GET  /api/history   последние измерения из памяти (до HISTORY_SIZE)
//   GET  /api/files     список журналов /log на SD
//   GET  /log/<файл>    скачать журнал
//   POST /api/light     mode=on|off|auto — если web.control в config.json
#pragma once

#include <Arduino.h>

const uint16_t HISTORY_SIZE = 240;  // при измерении раз в минуту — последние 4 часа

void webBegin(String (*statusJson)(bool));
void webLoop();
void webRecord(float temperature, float humidity);
