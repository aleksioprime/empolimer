#define TINY_GSM_MODEM_SIM800  // Модем SIM800
#define BATTERY_PIN A0         // Аналоговый пин для делителя напряжения

#include <TinyGsmClient.h>      // Работа с GPRS-модемом по AT-командам
#include <PubSubClient.h>       // MQTT-клиент
#include <TroykaDHT.h>          // Работа с датчиком температуры и влажности DHT
#include <SoftwareSerial.h>     // Работа с программным последовательным портом (UART)
#include <Adafruit_NeoPixel.h>  // Работа со светодиодной адресной лентой

// --- Делитель напряжения ---
const float R1 = 15800.0;       // Первый резистор, Ом
const float R2 = 10000.0;       // Второй резистор, Ом
const float VOLTAGE_DIV = (R1 + R2) / R2;  // Коэффициент делителя
const float ADC_REF = 5.0;      // Опорное напряжение Arduino
const int ADC_MAX = 1023;

// --- Светодиодная адресная лента WS2812 ---
#define LED_PIN 6
#define LED_COUNT 33
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

// --- Датчик температуры и влажности ---
#define DHTPIN 8
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// --- Программный последовательный порт для Raspberry Pi ---
SoftwareSerial PiSerial(9, 10);

// --- Программный последовательный порт для ESP8266 ---
SoftwareSerial EspSerial(2, 3); // RX=2, TX=3 (Arduino)

// --- Аппаратный Serial1 для модема (TX1=1, RX1=0 на Micro Pro) ---
TinyGsm modem(Serial1);
TinyGsmClient gsmClient(modem);
PubSubClient mqtt(gsmClient);

// --- Настройки устройства и MQTT ---
const char* deviceName = "exp";
const char* broker = "empolimer.ru";
const int port = 1883;
const char* mqttUser = "empolimer";
const char* mqttPass = "Techno2025";
const char* clientId = "device_exp";

// --- GPRS параметры ---
const char* apn = "internet.beeline.ru";
const char* gprsUser = "beeline";
const char* gprsPass = "beeline";

// --- Интервалы ---
const unsigned long sensorInterval = 30000;      // Опрос DHT (мс)
const unsigned long mqttInterval = 60000;       // Публикация MQTT (мс)
const unsigned long gprsTimeout = 10000;        // Таймаут подключения к GPRS (мс)
const unsigned long gprsRetryInterval = 20000;  // Интервал попыток переподключения (мс)
const unsigned long mqttTryInterval = 7000;     // Интервал попыток MQTT connect (мс)

// --- Состояния ---
enum GprsState { GPRS_INIT,
                 GPRS_CONNECTING,
                 GPRS_CONNECTED,
                 GPRS_ERROR };
GprsState gprsState = GPRS_INIT;

// --- Глобальные переменные ---
float t = 0, h = 0;  // Температура, влажность
unsigned long lastSensorRead = 0, lastMqttSend = 0, lastMqttTry = 0;
unsigned long gprsStartTime = 0, lastGprsRetry = 0;
bool dataReady = false;


void setup() {
  Serial.begin(9600);
  PiSerial.begin(9600);
  EspSerial.begin(9600);
  Serial1.begin(9600);

  // Подготовка пина для мониторинга заряда
  pinMode(BATTERY_PIN, INPUT);

  // Инициализация GPRS-модуля
  modem.restart();

  // Инициализация датчика температуры и влажности
  dht.begin();

  // Инициализация светодиодной ленты
  strip.begin();
  strip.show();

  // Обновление времени через сеть
  modem.sendAT("+CLTS=1");
  modem.sendAT("+CFUN=1");
}

void loop() {
  unsigned long now = millis();

  // --- Управление лентой через PiSerial ---
  if (PiSerial.available()) {
    String cmd = PiSerial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "LED_ON") phytoLedOn();
    if (cmd == "LED_OFF") phytoLedOff();
  }

  // --- Управление лентой через EspSerial ---
  if (EspSerial.available()) {
    String cmd = EspSerial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "LED_ON") phytoLedOn();
    if (cmd == "LED_OFF") phytoLedOff();
  }

  // FSM для GPRS
  switch (gprsState) {
    case GPRS_INIT:
      modem.gprsConnect(apn, gprsUser, gprsPass);
      gprsState = GPRS_CONNECTING;
      gprsStartTime = now;
      break;
    case GPRS_CONNECTING:
      if (modem.isGprsConnected()) {
        gprsState = GPRS_CONNECTED;
        mqtt.setServer(broker, port);
      } else if (now - gprsStartTime > gprsTimeout) {
        gprsState = GPRS_ERROR;
        lastGprsRetry = now;
      }
      break;
    case GPRS_ERROR:
      if (now - lastGprsRetry > gprsRetryInterval) {
        modem.restart();
        delay(1000);
        modem.gprsDisconnect();
        delay(1000);
        gprsState = GPRS_INIT;
      }
      break;
    case GPRS_CONNECTED:
      if (!modem.testAT()) {
        gprsState = GPRS_ERROR;
        break;
      }
      if (!mqtt.connected()) mqttReconnect();
      mqtt.loop();

      // --- Публикация данных ---
      if (dataReady && mqtt.connected() && (now - lastMqttSend >= mqttInterval)) {
        lastMqttSend = now;
        String dt = getGsmTime();
        float batt = getBatteryVoltage();

        // Данные для MQTT в формате JSON
        String payload = "{\"datetime\":\"" + dt + "\",\"temp\":" + String(t, 1) + ",\"hum\":" + String(h, 1) + ",\"bat\":" + String(batt, 2) + "}";
        String topic = "devices/" + String(deviceName) + "/air";
        bool ok = mqtt.publish(topic.c_str(), payload.c_str());

        // Данные для Serial в формате для парсинга: 2024-06-26T18:44:15.123+00:00;23.5;53.1
        String serialLine = "DATA;" + dt + ";" + String(t, 1) + ";" + String(h, 1) + ";" + String(batt, 2);
        Serial.println(serialLine);
        PiSerial.println(serialLine);
        EspSerial.println(serialLine);

        dataReady = false;
      }
      break;
  }

  // --- Опрос датчика температуры и влажности ---
  if (now - lastSensorRead >= sensorInterval) {
    lastSensorRead = now;
    dht.read();
    dataReady = (dht.getState() == DHT_OK);
    if (dataReady) {
      t = dht.getTemperatureC();
      h = dht.getHumidity();
    }
  }
}

// Чтение напряжения батареи через делитель
float getBatteryVoltage() {
  int adc = analogRead(BATTERY_PIN);
  return (adc * ADC_REF / ADC_MAX) * VOLTAGE_DIV;
}

// Получение времени из GSM-модуля
String getGsmTime() {
  String s = "";
  modem.sendAT(GF("+CCLK?"));
  if (modem.waitResponse(1000L, s) == 1) {
    int idx = s.indexOf("+CCLK: ");
    if (idx >= 0) {
      int st = idx + 8, en = s.indexOf("\r", st);
      String dt = s.substring(st, en);
      dt.replace("\"", "");
      return dt;
    }
  }
  return "";
}

// Подключение к MQTT
void mqttReconnect() {
  if (!modem.testAT()) {
    gprsState = GPRS_ERROR;
    return;
  }
  if (millis() - lastMqttTry < mqttTryInterval) return;
  lastMqttTry = millis();
  mqtt.connect(clientId, mqttUser, mqttPass);
}

// Включение светодиодной ленты
void phytoLedOn() {
  for (int i = 0; i < LED_COUNT; i++)
    strip.setPixelColor(i, strip.Color(200, 0, 180));  // Фиолетовый
  strip.show();
}

// Выключение светодиодной ленты
void phytoLedOff() {
  strip.clear();
  strip.show();
}