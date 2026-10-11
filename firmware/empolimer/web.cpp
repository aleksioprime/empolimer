#include "web.h"

#include <ArduinoJson.h>
#include <SD.h>

#if defined(ESP32)
  #include <WebServer.h>
  using HttpServer = WebServer;
#else
  #include <ESP8266WebServer.h>
  using HttpServer = ESP8266WebServer;
#endif

#include "commands.h"
#include "config.h"
#include "link.h"
#include "state.h"
#include "web_page.h"

namespace {

struct Point {
  uint32_t ms;   // millis() измерения: работает и без часов
  int16_t t10;   // температура × 10
  int16_t h10;   // влажность × 10
};

HttpServer server(80);
String (*buildStatus)(bool) = nullptr;
Point history[HISTORY_SIZE];
uint16_t historyHead = 0;   // куда писать следующую точку
uint16_t historyCount = 0;

void sendJson(int code, JsonDocument& doc) {
  String body;
  serializeJson(doc, body);
  server.sendHeader("Cache-Control", "no-store");
  server.send(code, "application/json; charset=utf-8", body);
}

void sendError(int code, const char* message) {
  JsonDocument doc;
  doc["detail"] = message;
  sendJson(code, doc);
}

void handlePage() {
#if defined(ESP32)
  server.send(200, "text/html; charset=utf-8", PAGE);
#else
  server.send_P(200, "text/html; charset=utf-8", PAGE);
#endif
}

void handleState() {
  JsonDocument doc;
  deserializeJson(doc, buildStatus(false));
  JsonObject reading = doc["reading"].to<JsonObject>();
  if (state.lastMeasureMs) {
    reading["temp"] = serialized(String(state.temperature, 1));
    reading["hum"] = serialized(String(state.humidity, 1));
    if (!isnan(state.battery)) reading["bat"] = serialized(String(state.battery, 2));
    reading["age"] = (millis() - state.lastMeasureMs) / 1000;
  }
  JsonObject norm = doc["norm"].to<JsonObject>();
  norm["temp_min"] = cfg.tempMin;
  norm["temp_max"] = cfg.tempMax;
  norm["hum_min"] = cfg.humMin;
  norm["hum_max"] = cfg.humMax;
  doc["control"] = cfg.webControl;
  if (timeValid()) doc["now"] = (long long)time(nullptr);
  sendJson(200, doc);
}

// Точки отдаются частями, чтобы не собирать всю историю в одной строке (у ESP8266 мало памяти).
void handleHistory() {
  server.sendHeader("Cache-Control", "no-store");
  server.setContentLength(CONTENT_LENGTH_UNKNOWN);
  server.send(200, "application/json", "");
  uint32_t now = millis();
  String chunk = "{\"interval\":" + String(cfg.intervalSec) + ",\"points\":[";
  uint16_t start = (historyHead + HISTORY_SIZE - historyCount) % HISTORY_SIZE;
  for (uint16_t i = 0; i < historyCount; i++) {
    const Point& p = history[(start + i) % HISTORY_SIZE];
    if (i) chunk += ',';
    // [сколько секунд назад, температура, влажность]
    chunk += '[' + String((now - p.ms) / 1000) + ',' + String(p.t10 / 10.0, 1) + ',' + String(p.h10 / 10.0, 1) + ']';
    if (chunk.length() > 512) {
      server.sendContent(chunk);
      chunk = "";
    }
  }
  chunk += "]}";
  server.sendContent(chunk);
  server.sendContent("");
}

String baseName(const char* path) {
  String name = path;
  int slash = name.lastIndexOf('/');
  return slash >= 0 ? name.substring(slash + 1) : name;
}

void handleFiles() {
  JsonDocument doc;
  JsonArray files = doc["files"].to<JsonArray>();
  doc["sd"] = state.sdReady;
  if (state.sdReady) {
    File dir = SD.open("/log");
    if (dir) {
      for (File file = dir.openNextFile(); file; file = dir.openNextFile()) {
        if (!file.isDirectory()) {
          JsonObject item = files.add<JsonObject>();
          item["name"] = baseName(file.name());
          item["size"] = file.size();
        }
        file.close();
      }
      dir.close();
    }
  }
  sendJson(200, doc);
}

// Только имена журналов вида 2026-10-11.csv или no-time.csv - без путей.
bool safeLogName(const String& name) {
  if (!name.endsWith(".csv") || name.length() > 20) return false;
  for (char c : name) {
    if (!isalnum(c) && c != '-' && c != '.') return false;
  }
  return name.indexOf("..") < 0;
}

void handleNotFound() {
  String uri = server.uri();
  if (server.method() == HTTP_GET && uri.startsWith("/log/")) {
    String name = uri.substring(5);
    if (!state.sdReady || !safeLogName(name)) return sendError(404, "Файл не найден");
    File file = SD.open("/log/" + name, FILE_READ);
    if (!file) return sendError(404, "Файл не найден");
    server.sendHeader("Content-Disposition", "attachment; filename=\"" + name + "\"");
    server.streamFile(file, "text/csv");
    file.close();
    return;
  }
  sendError(404, "Не найдено");
}

void handleLight() {
  if (!cfg.webControl) return sendError(403, "Управление со страницы выключено (web.control)");
  String mode = server.arg("mode");
  mode.toUpperCase();
  if (mode != "ON" && mode != "OFF" && mode != "AUTO") return sendError(400, "mode: on, off или auto");
  String result = runCommand("LIGHT " + mode);
  linkSend(result);
  sendStatus();  // Raspberry и сервер сразу узнают новое состояние
  server.send(200, "application/json", result);
}

}  // namespace

void webBegin(String (*statusJson)(bool)) {
  buildStatus = statusJson;
  if (!cfg.webEnabled) return;
  server.on("/", HTTP_GET, handlePage);
  server.on("/api/state", HTTP_GET, handleState);
  server.on("/api/history", HTTP_GET, handleHistory);
  server.on("/api/files", HTTP_GET, handleFiles);
  server.on("/api/light", HTTP_POST, handleLight);
  server.onNotFound(handleNotFound);
  server.begin();
  logf("Страница устройства: порт 80");
}

void webLoop() {
  if (cfg.webEnabled) server.handleClient();
}

void webRecord(float temperature, float humidity) {
  history[historyHead] = {millis(), (int16_t)lroundf(temperature * 10), (int16_t)lroundf(humidity * 10)};
  historyHead = (historyHead + 1) % HISTORY_SIZE;
  if (historyCount < HISTORY_SIZE) historyCount++;
}
