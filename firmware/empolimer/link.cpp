#include "link.h"

#include <stdarg.h>

#include "commands.h"

namespace {

const size_t MAX_LINE = 128;
String buffer;

}  // namespace

void linkBegin() {
  Serial.begin(LINK_BAUD);
  buffer.reserve(MAX_LINE);
  Serial.println();  // отделить мусор загрузчика ESP8266 от первого сообщения
}

void linkPoll() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\r') continue;
    if (c != '\n') {
      if (buffer.length() < MAX_LINE) buffer += c;
      continue;
    }
    buffer.trim();
    if (buffer.length()) linkSend(runCommand(buffer));
    buffer = "";
  }
}

void linkSend(const String& json) {
  Serial.println(json);
}

void logf(const char* format, ...) {
  char text[160];
  va_list args;
  va_start(args, format);
  vsnprintf(text, sizeof(text), format, args);
  va_end(args);
  Serial.print("# ");
  Serial.println(text);
}
