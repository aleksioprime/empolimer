// Пины модулей для каждой поддерживаемой платы.
// Любой пин можно переопределить флагом сборки, например -DPIN_DHT=5.
#pragma once

#include <Arduino.h>

#if defined(ESP32)
  #define BOARD_NAME "esp32"
  #ifndef PIN_DHT
    #define PIN_DHT 4        // датчик температуры и влажности
  #endif
  #ifndef PIN_LIGHT
    #define PIN_LIGHT 13     // адресная лента (вход DIN)
  #endif
  #ifndef PIN_SD_CS
    #define PIN_SD_CS 5      // SD: SCK 18, MISO 19, MOSI 23
  #endif
  #ifndef PIN_BATTERY
    #define PIN_BATTERY 34   // делитель напряжения батареи (только вход)
  #endif
  #define ADC_MAX 4095
#elif defined(ESP8266)
  // NodeMCU v2 / v3 (модуль ESP-12E); номера GPIO, в скобках - подписи на плате.
  #define BOARD_NAME "esp8266"
  #ifndef PIN_DHT
    #define PIN_DHT 2        // GPIO2 (D4)
  #endif
  #ifndef PIN_LIGHT
    #define PIN_LIGHT 4      // GPIO4 (D2)
  #endif
  #ifndef PIN_SD_CS
    #define PIN_SD_CS 15     // GPIO15 (D8); SD: SCK 14 (D5), MISO 12 (D6), MOSI 13 (D7)
  #endif
  #ifndef PIN_BATTERY
    #define PIN_BATTERY A0
  #endif
  #define ADC_MAX 1023
#else
  #error "Прошивка поддерживает только NodeMCU ESP8266 и ESP32 DevKit"
#endif

#define FIRMWARE_VERSION "2.1.0"
