#include "commands.h"

#include <ArduinoJson.h>
#include <sys/time.h>

#include "config.h"
#include "light.h"
#include "link.h"
#include "state.h"

namespace {

String ack(const String& command, bool ok, const char* error = nullptr) {
  JsonDocument doc;
  doc["type"] = "ack";
  doc["cmd"] = command;
  doc["ok"] = ok;
  if (error) doc["error"] = error;
  String out;
  serializeJson(doc, out);
  return out;
}

bool parseByte(const String& text, uint8_t& value) {
  if (!text.length()) return false;
  for (char c : text) {
    if (!isdigit(c)) return false;
  }
  long number = text.toInt();
  if (number < 0 || number > 255) return false;
  value = (uint8_t)number;
  return true;
}

String lightCommand(const String& command, const String& arg) {
  if (arg == "OFF") {
    lightOff();
    return ack(command, true);
  }
  if (arg == "AUTO") {
    lightAuto();
    return ack(command, true);
  }
  uint8_t level = cfg.lightBrightness;
  String value = arg.startsWith("ON") ? arg.substring(2) : arg;
  value.trim();
  if (value.length() && !parseByte(value, level)) {
    return ack(command, false, "яркость — число от 0 до 255");
  }
  if (level == 0) lightOff();
  else lightOn(level);
  return ack(command, true);
}

}  // namespace

String runCommand(const String& raw) {
  String command = raw;
  command.trim();
  command.toUpperCase();

  int space = command.indexOf(' ');
  String name = space < 0 ? command : command.substring(0, space);
  String arg = space < 0 ? "" : command.substring(space + 1);
  arg.trim();

  if (name == "STATUS") {
    sendStatus();
    return ack(command, true);
  }
  if (name == "READ") {
    requestMeasure();
    return ack(command, true);
  }
  if (name == "LIGHT" && arg.length()) {
    return lightCommand(command, arg);
  }
  if (name == "TIME") {
    long long epoch = atoll(arg.c_str());
    if (epoch < 1700000000LL) return ack(command, false, "нужно unix-время в секундах");
    struct timeval tv = {(time_t)epoch, 0};
    settimeofday(&tv, nullptr);
    logf("Часы установлены командой TIME");
    return ack(command, true);
  }
  if (name == "HELP") {
    logf("Команды: STATUS, READ, LIGHT ON [0..255], LIGHT OFF, LIGHT AUTO, TIME <unix>");
    return ack(command, true);
  }
  return ack(command, false, "неизвестная команда, см. HELP");
}
