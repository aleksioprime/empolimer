# Прошивка устройства

Одна программа для **NodeMCU**, **ESP-12** (ESP8266) и **ESP32**. Устройство
модульное: датчик температуры и влажности, подсветка, SD-карта, Wi-Fi и связь
с Raspberry работают независимо — если модуль не подключён, остальные
продолжают работать. Подключение модулей — [docs/hardware.md](../docs/hardware.md),
форматы сообщений — [docs/protocol.md](../docs/protocol.md).

| Файл | Что внутри |
| --- | --- |
| [empolimer.ino](empolimer/empolimer.ino) | запуск, измерения, состояние |
| [board.h](empolimer/board.h) | пины для каждой платы |
| [config.cpp](empolimer/config.cpp) | чтение `config.json` с SD |
| [storage.cpp](empolimer/storage.cpp) | журнал на SD и очередь неотправленных данных |
| [network.cpp](empolimer/network.cpp) | Wi-Fi, часы (NTP), MQTT |
| [light.cpp](empolimer/light.cpp) | подсветка и её расписание |
| [link.cpp](empolimer/link.cpp), [commands.cpp](empolimer/commands.cpp) | связь с Raspberry и команды |

## Загрузка

### Arduino IDE

1. Поддержка плат: *Файл → Настройки → Дополнительные ссылки для менеджера плат*:
   - ESP8266: `https://arduino.esp8266.com/stable/package_esp8266com_index.json`
   - ESP32: `https://espressif.github.io/arduino-esp32/package_esp32_index.json`

   затем *Инструменты → Плата → Менеджер плат*: `esp8266` и/или `esp32`.
2. Библиотеки (*Скетч → Подключить библиотеку → Управлять библиотеками*):
   `DHT sensor library` (Adafruit, с зависимостью Adafruit Unified Sensor),
   `Adafruit NeoPixel`, `PubSubClient`, `ArduinoJson` (версия 7).
3. Откройте `firmware/empolimer/empolimer.ino` и выберите плату:

   | Устройство | Плата в Arduino IDE |
   | --- | --- |
   | NodeMCU | NodeMCU 1.0 (ESP-12E Module) |
   | ESP-12 / Troyka Wi-Fi | Generic ESP8266 Module |
   | ESP32 | ESP32 Dev Module |

4. Скорость монитора порта — **115200**.

Голый ESP-12 (например, Troyka Wi-Fi от Амперки) прошивается через
USB-UART-переходник: отключите питание, зажмите `PROG`, подайте питание,
отпустите `PROG` и запустите загрузку.

### PlatformIO

```bash
cd firmware
pio run -e nodemcu -t upload      # или esp12, esp32
pio device monitor
```

## Настройки на SD-карте

Скопируйте [sd-card/config.json](sd-card/config.json) в корень карты (FAT32)
и поправьте:

| Ключ | Что задаёт |
| --- | --- |
| `device.id` | имя устройства на сервере: латиница, цифры, `-`, `_` (без него — `esp-<номер чипа>`) |
| `device.interval` | период измерений, секунды (не меньше 5) |
| `wifi` | одна сеть `{ssid, pass}` или список — устройство перебирает их, пока не подключится |
| `mqtt` | брокер; без `host` данные пишутся только на SD и уходят в Raspberry |
| `time.tz` | часовой пояс в формате POSIX: `MSK-3` — Москва, `<+07>-7` — UTC+7 |
| `sensor.type` | `11` (DHT11) или `22` (DHT22) |
| `light` | число светодиодов, цвет, яркость 0–255, расписание `on`/`off` (`ЧЧ:ММ`); без расписания свет включается только командой |
| `battery` | измерять напряжение батареи через делитель: `divider` = (R1 + R2) / R2 |

Без карты или с ошибкой в файле устройство стартует с настройками по
умолчанию, а причину пишет в журнал порта и в состояние (`config_error`).

## Что пишется на карту

- `/log/ГГГГ-ММ-ДД.csv` — все измерения по дням, открываются в Excel;
  до первой синхронизации часов — в `/log/no-time.csv`.
- `/queue.jsonl` — измерения, которые не удалось отправить на сервер. После
  восстановления связи они уходят с исходным временем, файл удаляется.
  После перезагрузки очередь отправляется с начала: повторы сервер отбрасывает.

## Проверка в мониторе порта

После старта устройство пишет журнал (`# ...`), состояние и измерения в JSON.
Команды можно вводить вручную (окончание строки — «Новая строка»):

```text
STATUS
READ
LIGHT ON 120
LIGHT AUTO
```

Полный список — `HELP` или [docs/protocol.md](../docs/protocol.md).
