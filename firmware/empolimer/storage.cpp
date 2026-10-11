#include "storage.h"

#include <SD.h>
#include <SPI.h>

#include "board.h"
#include "state.h"

// На ESP32 FILE_WRITE перезаписывает файл, на ESP8266 — дописывает в конец.
#if defined(ESP32)
  #define SD_APPEND FILE_APPEND
#else
  #define SD_APPEND FILE_WRITE
#endif

namespace {

const char* QUEUE_PATH = "/queue.jsonl";
const uint32_t QUEUE_MAX_BYTES = 2UL * 1024 * 1024;  // ~ 30 000 измерений; дальше только журнал

uint32_t queueOffset = 0;  // позиция первой неотправленной строки
uint32_t queueCount = 0;   // число неотправленных строк

void countQueue() {
  queueCount = 0;
  File file = SD.open(QUEUE_PATH, FILE_READ);
  if (!file) return;
  while (file.available()) {
    if (file.read() == '\n') queueCount++;
  }
  file.close();
}

}  // namespace

bool storageBegin() {
  state.sdReady = SD.begin(PIN_SD_CS);
  if (state.sdReady) {
    if (!SD.exists("/log")) SD.mkdir("/log");
    countQueue();
    state.queued = queueCount;
  }
  return state.sdReady;
}

void storageLog(time_t ts, float temperature, float humidity, float battery) {
  if (!state.sdReady) return;

  char path[24] = "/log/no-time.csv";
  char when[24] = "";
  if (ts > 0) {
    struct tm local;
    localtime_r(&ts, &local);
    strftime(path, sizeof(path), "/log/%Y-%m-%d.csv", &local);
    strftime(when, sizeof(when), "%Y-%m-%d %H:%M:%S", &local);
  }

  bool isNew = !SD.exists(path);
  File file = SD.open(path, SD_APPEND);
  if (!file) {
    state.sdReady = false;  // карту вынули или она повреждена
    return;
  }
  if (isNew) file.println("time,uptime_s,temperature,humidity,battery");
  file.printf("%s,%lu,%.1f,%.1f,", when, (unsigned long)(millis() / 1000), temperature, humidity);
  if (!isnan(battery)) file.printf("%.2f", battery);
  file.println();
  file.close();
}

bool queuePush(const String& line) {
  if (!state.sdReady) return false;
  File file = SD.open(QUEUE_PATH, SD_APPEND);
  if (!file) return false;
  bool ok = file.size() < QUEUE_MAX_BYTES && file.println(line) > 0;
  file.close();
  if (ok) state.queued = ++queueCount;
  return ok;
}

bool queuePeek(String& line) {
  if (!state.sdReady || queueCount == 0) return false;
  File file = SD.open(QUEUE_PATH, FILE_READ);
  if (!file) return false;
  file.seek(queueOffset);
  line = file.readStringUntil('\n');
  line.trim();
  file.close();
  return line.length() > 0;
}

void queuePop() {
  if (queueCount == 0) return;
  File file = SD.open(QUEUE_PATH, FILE_READ);
  if (!file) return;
  file.seek(queueOffset);
  file.readStringUntil('\n');
  queueOffset = file.position();
  bool done = !file.available();
  file.close();

  queueCount--;
  if (done || queueCount == 0) {
    // Всё отправлено — очищаем очередь, чтобы файл не рос.
    SD.remove(QUEUE_PATH);
    queueOffset = 0;
    queueCount = 0;
  }
  state.queued = queueCount;
}

uint32_t queueSize() {
  return queueCount;
}
