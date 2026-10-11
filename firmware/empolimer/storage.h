// SD-карта: журнал измерений и очередь неотправленных сообщений.
//
// /log/ГГГГ-ММ-ДД.csv - все измерения по дням (без часов - /log/no-time.csv);
// /queue.jsonl        - измерения, которые не ушли на сервер; отправляются после
//                       восстановления связи, сервер отбрасывает повторы.
#pragma once

#include <Arduino.h>

bool storageBegin();
void storageLog(time_t ts, float temperature, float humidity, float battery);

// Очередь: добавить строку JSON; прочитать следующую неотправленную; отметить её отправленной.
bool queuePush(const String& line);
bool queuePeek(String& line);
void queuePop();
uint32_t queueSize();
