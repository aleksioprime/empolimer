// Подсветка - адресная лента WS2812 (NeoPixel).
//
// Режим auto: по расписанию light.on/light.off из config.json (нужны часы);
// без расписания свет выключен. Команды on/off/яркость переводят в ручной режим
// до команды auto или перезагрузки.
#pragma once

#include <Arduino.h>

void lightBegin();
void lightTick();                // вызывается в loop(): применяет расписание
void lightOn(uint8_t brightness);
void lightOff();
void lightAuto();
bool lightIsOn();
bool lightIsAuto();
uint8_t lightBrightness();
