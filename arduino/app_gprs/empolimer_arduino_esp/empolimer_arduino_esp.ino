/*
=========================================================
Arduino + DHT11 + WS2812 + UART (Pi + ESP)

Назначение:
- Считывает температуру/влажность с DHT11 (каждые 30 сек).
- Считывает напряжение батареи через делитель на A0.
- Отправляет строку DATA;... по UART в:
  - EspSerial (ESP8266, пины 2/3) — дальше ESP сам шлёт в MQTT
  - PiSerial (Raspberry Pi, пины 9/10)
  - USB Serial (для отладки)

Управление лентой:
- Команды LED_ON / LED_OFF принимаются из PiSerial и EspSerial.

Формат:
  DATA;ts_ms;temp;hum;bat
Пример:
  DATA;1234567;23.5;50.2;3.91
=========================================================
*/

#define BATTERY_PIN A0

#include <TroykaDHT.h>
#include <SoftwareSerial.h>
#include <Adafruit_NeoPixel.h>

// --- Делитель напряжения ---
const float R1 = 15800.0;
const float R2 = 10000.0;
const float VOLTAGE_DIV = (R1 + R2) / R2;
const float ADC_REF = 5.0;
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
SoftwareSerial PiSerial(9, 10);   // RX=9, TX=10 (Arduino)

// --- Программный последовательный порт для ESP8266 ---
SoftwareSerial EspSerial(2, 3);   // RX=2, TX=3 (Arduino)

// --- Интервалы ---
const unsigned long sensorInterval = 30000;  // 30 сек
unsigned long lastSensorRead = 0;

// --- Глобальные переменные ---
float t = 0, h = 0;

float getBatteryVoltage();
void phytoLedOn();
void phytoLedOff();

void setup() {
  Serial.begin(9600);
  PiSerial.begin(9600);
  EspSerial.begin(9600);

  pinMode(BATTERY_PIN, INPUT);

  dht.begin();

  strip.begin();
  strip.show();
}

void loop() {
  unsigned long now = millis();

  // --- Команды для ленты от Raspberry Pi ---
  if (PiSerial.available()) {
    String cmd = PiSerial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "LED_ON")  phytoLedOn();
    if (cmd == "LED_OFF") phytoLedOff();
  }

  // --- Команды для ленты от ESP8266 ---
  if (EspSerial.available()) {
    String cmd = EspSerial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "LED_ON")  phytoLedOn();
    if (cmd == "LED_OFF") phytoLedOff();
  }

  // --- Опрос датчика и отправка данных в ESP/Pi ---
  if (now - lastSensorRead >= sensorInterval) {
    lastSensorRead = now;

    dht.read();
    bool ok = (dht.getState() == DHT_OK);

    if (ok) {
      t = dht.getTemperatureC();
      h = dht.getHumidity();
      float batt = getBatteryVoltage();

      // Формируем строку для отправки по UART (не вставляем now, т.к. Arduino может не знать реального времени)
      String serialLine = "DATA;none;" +
                    String(t, 1) + ";" +
                    String(h, 1) + ";" +
                    String(batt, 2);

      // Отладка/ПК
      Serial.println(serialLine);

      // Raspberry Pi
      PiSerial.println(serialLine);

      // ESP8266 (он дальше отправит в MQTT)
      EspSerial.println(serialLine);
    } else {
      Serial.print("DHT: FAIL state=");
      Serial.println(dht.getState());
    }
  }
}

// Чтение напряжения батареи через делитель
float getBatteryVoltage() {
  int adc = analogRead(BATTERY_PIN);
  return (adc * ADC_REF / ADC_MAX) * VOLTAGE_DIV;
}

// Включение светодиодной ленты
void phytoLedOn() {
  for (int i = 0; i < LED_COUNT; i++) {
    strip.setPixelColor(i, strip.Color(200, 0, 180));  // Фиолетовый
  }
  strip.show();
}

// Выключение светодиодной ленты
void phytoLedOff() {
  strip.clear();
  strip.show();
}
