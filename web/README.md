# Веб-мониторинг

Сервер, куда устройства ЕмПолимер присылают измерения, и веб-интерфейс для
наблюдения за ними.

```text
ESP ──MQTT──► Mosquitto ──► worker ──► PostgreSQL ◄── backend (FastAPI) ◄── frontend (Vue + Vuetify, nginx)
```

| Каталог | Назначение |
| --- | --- |
| [worker/](worker/) | принимает MQTT, сохраняет измерения и состояние устройств; новые устройства регистрирует сам |
| [back/](back/) | API: устройства, их состояние и замечания, графики, выгрузка в Excel, пользователи; WebSocket для живого обновления |
| [front/](front/) | веб-интерфейс; в продакшне nginx раздаёт сборку и проксирует `/api` |
| [mosquitto/](mosquitto/) | брокер для локальной разработки |

Форматы сообщений - [docs/protocol.md](../docs/protocol.md).

## Что видно в интерфейсе

- **Обзор**: сколько устройств на связи, требуют внимания, без связи (клик -
  фильтр); карточки с текущими значениями, цветом относительно нормы и главной
  проблемой простыми словами. Проблемные устройства - первыми.
- **Устройство**: что не так и что проверить; текущие значения; состояние
  модулей (Wi-Fi, датчик, SD, часы, подсветка, очередь, прошивка); графики за
  6 ч / сутки / неделю / месяц / свой период со средним, разбросом и
  границами нормы, сводка мин/ср/макс; таблица измерений; Excel за период.
- **Норма** задаётся для каждого устройства (иначе - значения по умолчанию
  `DEFAULT_*`).

## Отказоустойчивость

- **Устройство без связи** копит измерения на SD и досылает их; сервер
  отбрасывает повторы (уникальный индекс устройство + время).
- **Обрыв устройства** виден сразу: брокер публикует Last Will
  `{"online":false}`; без него - по отсутствию сообщений дольше трёх периодов
  измерений.
- **worker** переподключается к брокеру с нарастающей паузой, сообщение при
  недоступной базе повторяет, неправдоподобные значения (сбой датчика) и
  время из будущего отбрасывает. Healthcheck - по связи с брокером.
- **backend** не роняет рассылку из-за «мёртвых» WebSocket-соединений,
  рассылает только изменения (и раз в 30 с - для контроля связи).
- **Браузер**: WebSocket с переподключением; пока его нет - опрос раз в 10 с;
  без связи с сервером - баннер и последние данные. Сессия не сбрасывается,
  если сервер недоступен в момент обновления токена.
- Контейнеры с healthcheck, `restart: unless-stopped`; nginx стартует и
  находит бэкенд даже после его перезапуска.

## Локальный запуск

```bash
cd web
cp .env.example .env
docker compose -p empolimer up -d --build
docker compose -p empolimer exec backend python scripts/create_superuser.py \
  --username admin --password <пароль> --email admin@example.com
```

- веб - http://localhost:8202
- API - http://localhost:8201/api/openapi
- adminer - http://localhost:8203
- MQTT - `localhost:1883` без пароля

Проверить приём данных без устройства:

```bash
docker compose -p empolimer exec mosquitto mosquitto_pub -t empolimer/test-1/data \
  -m "{\"ts\":$(date +%s),\"temp\":23.4,\"hum\":45}"
```

Устройство `test-1` появится в интерфейсе само.

Миграции применяются при старте бэкенда. Новая миграция:

```bash
docker compose -p empolimer exec backend alembic revision --autogenerate -m "описание"
```

Тесты:

```bash
cd web/back && python -m unittest discover -s tests -t .     # нужны зависимости из requirements.txt
cd web/worker && python -m unittest discover -s tests -t .
```

## Продакшн (Coolify)

1. При пуше в `main` с изменениями в `web/` workflow
   [build.yml](../.github/workflows/build.yml) запускает тесты, собирает образы
   `empolimer-backend`, `empolimer-worker`, `empolimer-frontend`, пушит их в
   GHCR, выставляет теги `*_IMAGE_TAG` в Coolify и запускает деплой.
2. Coolify разворачивает [docker-compose.prod.yaml](docker-compose.prod.yaml).
   Домен и TLS - на стороне Coolify, наружу смотрит только `frontend` (порт 80).
3. Брокер MQTT - отдельный сервис в сети `iot`; worker подключается к нему по
   `MQTT_BROKER`.

Переменные окружения задаются в Coolify, список - [.env.example](.env.example).
Секреты GitHub: `COOLIFY_API`, `COOLIFY_TOKEN`, `COOLIFY_APP`.

Полезное на сервере:

```bash
docker compose logs -f worker                    # что приходит от устройств
docker compose exec backend alembic upgrade head # миграции вручную
```

Объём данных: одна запись ≈ 100 байт с индексами; при измерении раз в минуту
одно устройство даёт ~50 МБ в год.
