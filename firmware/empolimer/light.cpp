#include "light.h"

#include <Adafruit_NeoPixel.h>
#include <time.h>

#include "board.h"
#include "config.h"
#include "state.h"

namespace {

Adafruit_NeoPixel* strip = nullptr;
bool isOn = false;
bool autoMode = true;
uint8_t brightness = 0;
uint32_t lastTickMs = 0;

void show(bool on, uint8_t level) {
  isOn = on && level > 0;
  brightness = level;
  if (!strip) return;
  strip->setBrightness(isOn ? level : 0);
  strip->fill(isOn ? cfg.lightColor : 0);
  strip->show();
}

// Должен ли свет гореть сейчас по расписанию; расписание через полночь тоже работает.
bool scheduledOn() {
  if (cfg.lightOnMinute < 0 || cfg.lightOffMinute < 0 || !timeValid()) return false;
  time_t now = time(nullptr);
  struct tm local;
  localtime_r(&now, &local);
  int minute = local.tm_hour * 60 + local.tm_min;
  if (cfg.lightOnMinute <= cfg.lightOffMinute) {
    return minute >= cfg.lightOnMinute && minute < cfg.lightOffMinute;
  }
  return minute >= cfg.lightOnMinute || minute < cfg.lightOffMinute;
}

}  // namespace

void lightBegin() {
  if (cfg.lightCount == 0) return;
  strip = new Adafruit_NeoPixel(cfg.lightCount, PIN_LIGHT, NEO_GRB + NEO_KHZ800);
  strip->begin();
  show(false, 0);
}

void lightTick() {
  if (!autoMode || millis() - lastTickMs < 1000) return;
  lastTickMs = millis();
  bool want = scheduledOn();
  if (want != isOn) show(want, cfg.lightBrightness);
}

void lightOn(uint8_t level) {
  autoMode = false;
  show(true, level);
}

void lightOff() {
  autoMode = false;
  show(false, brightness);
}

void lightAuto() {
  autoMode = true;
  show(scheduledOn(), cfg.lightBrightness);
}

bool lightIsOn() { return isOn; }
bool lightIsAuto() { return autoMode; }
uint8_t lightBrightness() { return isOn ? brightness : 0; }
