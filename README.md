# ЕмПолимер — мониторинг микроклимата

Модульное устройство на ESP измеряет температуру и влажность, управляет
подсветкой, пишет данные на SD-карту и отправляет их на сервер. Raspberry Pi
рядом с устройством показывает на дисплее изображение с камеры и показания,
а веб-интерфейс собирает данные со всех устройств.

```text
 Raspberry Pi ◄─USB─► ESP + датчик + подсветка + SD ──Wi-Fi/MQTT──► сервер ──► веб-мониторинг
 камера, дисплей
```

## Структура

| Каталог | Назначение |
| --- | --- |
| [firmware/](firmware/README.md) | **прошивка ESP** (NodeMCU ESP8266, ESP32 DevKit), страница устройства в браузере и пример `config.json` для SD-карты |
| [rpi/](rpi/README.md) | **станция на Raspberry Pi** (Zero / 3): камера и показания ESP на дисплее, управление подсветкой |
| [deploy/](deploy/README.md) | установка станции на Raspberry по сети |
| [web/](web/README.md) | **сервер и веб-мониторинг**: MQTT → worker → PostgreSQL → API → интерфейс; развёрнут в Coolify |
| [docs/](docs/) | [схемы подключения](docs/hardware.md) для каждой платы, [протоколы обмена](docs/protocol.md) |

## Быстрый старт

1. Соберите устройство по [docs/hardware.md](docs/hardware.md) и прошейте
   [firmware/](firmware/README.md).
2. Запишите на SD-карту `config.json` из
   [firmware/sd-card/](firmware/sd-card/config.json): имя устройства, Wi-Fi,
   адрес брокера MQTT.
3. Включите устройство — через минуту оно появится в веб-интерфейсе. Его
   собственная страница — `http://empolimer-<id>.local`; без Wi-Fi устройство
   поднимает сеть `EmPolimer-<id>`, страница — `http://192.168.4.1`.
4. Для станции с камерой подключите ESP к Raspberry по USB и установите
   программу с компьютера:

   ```bash
   deploy/install.sh pi@192.168.1.50 --autostart
   ```

## Проверки

```bash
cd rpi && python3 -m unittest discover -s tests -t .           # станция, без оборудования
cd web/worker && python3 -m unittest discover -s tests -t .    # разбор MQTT-сообщений
cd firmware && pio run                                         # сборка прошивки под все платы
```

Тесты бэкенда, сборка фронтенда и прошивки также выполняются в GitHub Actions.

Предыдущая история проекта (скетчи для Arduino UNO, GPRS/SIM800L, Node-RED,
деплой через Docker Hub) сохранена в ветке `archive`.
