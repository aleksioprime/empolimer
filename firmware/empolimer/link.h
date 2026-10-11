// Связь с Raspberry по USB (Serial, 115200 бод), по строке на сообщение.
//
// ESP → Raspberry: JSON-объекты {"type":"data"|"status"|"ack", ...} и служебный
//                  журнал - строки, начинающиеся с "# ".
// Raspberry → ESP: текстовые команды (см. commands.h), например "LIGHT ON".
// Формат описан в docs/protocol.md.
#pragma once

#include <Arduino.h>

const uint32_t LINK_BAUD = 115200;

void linkBegin();
void linkPoll();                     // читает команды из порта
void linkSend(const String& json);   // одно сообщение - одна строка
void logf(const char* format, ...);  // журнал: "# ..." в порт
