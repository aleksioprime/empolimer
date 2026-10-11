# Станция на Raspberry Pi

Программа выводит на дисплей изображение с камеры и показания ESP, которая
подключена к Raspberry USB-кабелем, и управляет подсветкой. Работает на
Raspberry Pi Zero / Zero 2 W и Pi 3 с Raspberry Pi OS Bookworm (с рабочим
столом).

![Экран станции](../docs/images/station.png)

- **Показания** — температура и влажность; значения вне нормы подсвечиваются,
  при отсутствии новых данных пишется, сколько времени прошло.
- **Состояние ESP** — Wi-Fi, связь с сервером (и сколько измерений ждут
  отправки), SD-карта, часы.
- **Подсветка** — кнопки «Вкл», «Выкл», «Авто» (расписание из `config.json` на SD).
- **Камера** — модуль камеры Raspberry (Picamera2) или USB-камера.

Каждая часть переживает обрыв: ESP можно отключить и подключить, камера
переподключается сама, без камеры показания всё равно выводятся.
Если часы Raspberry синхронизированы по интернету, станция раз в час
устанавливает время на ESP — тогда журнал на SD ведётся с датами даже без
Wi-Fi у самой ESP.

## Установка

С компьютера по сети — [deploy/README.md](../deploy/README.md):

```bash
deploy/install.sh pi@192.168.1.50 --autostart
```

Вручную на плате:

```bash
sudo apt install python3-pyqt5 python3-serial python3-picamera2
sudo usermod -aG dialout,video $USER   # затем перезагрузка
cp station.conf.example station.conf
python3 station.py
```

## Запуск

```bash
python3 station.py                       # полноэкранно, порт и камера — автоматически
python3 station.py --window              # в окне
python3 station.py --port /dev/ttyACM0   # порт ESP вручную
python3 station.py --camera none         # без камеры
```

`F11` — окно/полный экран, `Ctrl+Q` — выход.

## Настройки: `station.conf`

| Ключ | По умолчанию | Что задаёт |
| --- | --- | --- |
| `port` | `auto` | порт ESP; `auto` — первый `/dev/ttyUSB*` или `/dev/ttyACM*` |
| `camera` | `auto` | `picamera`, `usb`, `none`; `auto` пробует модуль камеры, затем USB |
| `camera_size` | `640x480` | размер кадра |
| `fps` | `10` | кадров в секунду; на Pi Zero — 5–10 |
| `fullscreen` | `yes` | полноэкранный режим |
| `temp_min`, `temp_max` | `18`, `28` | норма температуры, °C |
| `hum_min`, `hum_max` | `40`, `70` | норма влажности, % |

## Устройство программы

| Файл | Назначение |
| --- | --- |
| [station.py](station.py) | запуск |
| [station/serial_link.py](station/serial_link.py) | связь с ESP в отдельном потоке, переподключение, синхронизация часов |
| [station/protocol.py](station/protocol.py) | разбор сообщений ESP и команды ([docs/protocol.md](../docs/protocol.md)) |
| [station/camera.py](station/camera.py) | камера в отдельном потоке |
| [station/ui.py](station/ui.py), [station/view.py](station/view.py) | экран |
| [station/config.py](station/config.py) | настройки |

Тесты (без оборудования и без Qt):

```bash
cd rpi
python3 -m unittest discover -s tests -t .
```
