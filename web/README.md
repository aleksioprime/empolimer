# Веб-приложение

## Запуск для разработчика

Скачайте репозиторий:
```
git clone https://github.com/aleksioprime/sk-empolimer.git
cd empolimer
```

Запустите сервис локально:
```
cd web
docker-compose -p empolimer up -d --build
```

Если выходит ошибка `exec /usr/src/app/entrypoint.sh: permission denied`, то нужно вручную установить флаг выполнения для entrypoint.sh в локальной системе:
```
chmod +x backend/entrypoint.sh
chmod +x auth/entrypoint.sh
```

Создание миграциий:
```shell
docker exec -it empolimer-backend alembic revision --autogenerate -m "init migration"
```

Применение миграции (при перезапуске сервиса делается автоматически):
```shell
docker exec -it empolimer-backend alembic upgrade head
```

Создание суперпользователя:
```shell
docker-compose -p empolimer exec backend python scripts/create_superuser.py --username superuser --password 1q2w3e --email admin@empolimer.ru
```

### Проверка:

1. Установите утилиту mosquitto:

```
brew install mosquitto
```

2. Подпишитесь на топик в одном терминале:

```
mosquitto_sub -h localhost -p 1883 -t "devices/551b1578-2f39-49d5-b44e-0d0b42454b24/air" -i sub_test -u empolimer -P Techno2025 -v
```

3. Отправьте сообщение в топик в другом терминале:
```
mosquitto_pub -h localhost -p 1883 -t "devices/demo_2/air" -i pub_test -u empolimer -P Techno2025 -m '{"datetime":"2025-06-26T21:41:38+12","temp":15.3,"hum":15.0}'
```


# Запуск на сервере:

## Подготовка сервера

Установите сервер с ОС Ubuntu 22.04+

Выполните обновление пакетов:
```
sudo apt update && sudo apt upgrade -y
```

Установите Docker:
```
sudo apt update && sudo apt install -y docker.io
```

Установите Compose-плагин:
```
DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
mkdir -p $DOCKER_CONFIG/cli-plugins
curl -SL https://github.com/docker/compose/releases/download/v2.32.4/docker-compose-linux-x86_64 -o $DOCKER_CONFIG/cli-plugins/docker-compose
chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose
```

Проверьте установку
```
docker compose version
```

## Переменные окружения

Переменные окружения берутся из репозитория.

Для загрузки контейнеров в Docker Hub используется:
```
DOCKER_HUB_USERNAME=<логин пользователя Docker Hub>
DOCKER_HUB_ACCESS_TOKEN=<access-токен, который был выдан в DockerHub>
```

Для деплоя приложения из репозитория на сервер используется:
```
SERVER_HOST=<IP-адрес сервера>
SERVER_SSH_KEY=<Приватный ключ для подключения к серверу по SSH>
SERVER_USER=<Имя пользователя сервера>
```

Для сервиса создаётся переменная `ENV_VARS`, куда записываются все переменные из `.env.example`

## Добавление бесплатного SSL-сертификата

В контейнер фронтенда добавлен CertBot, с помощью которого происходит регистрация сертификата

Проверьте установку:
```
docker exec -it empolimer-front certbot --version
```

Запустите CertBot для получения сертификатов
```
docker exec -it empolimer-front certbot --nginx -d empolimer.ru -d www.empolimer.ru
ls -l /etc/letsencrypt/live/empolimer.ru/
```

Добавьте автообновление сертификатов (каждые 90 дней). Для этого откройте crontab:
```
sudo crontab -e
```

Добавьте строку:
```
0 3 * * * docker exec empolimer-front certbot renew --quiet && docker exec empolimer-front nginx -s reload
```

В случае необхожимости можно удалить сертификаты:
```
docker exec -it empolimer-front rm -rf /etc/letsencrypt/renewal/empolimer.ru.conf
docker exec -it empolimer-front rm -rf /etc/letsencrypt/live/empolimer.ru
docker exec -it empolimer-front rm -rf /etc/letsencrypt/archive/empolimer.ru
```

Проверьте логи на сервере

```
docker compose -p empolimer logs
docker logs empolimer-nodered
```

Сделать ручные миграции на сервере:

```
docker exec -it empolimer-back alembic upgrade head
```

Добавье администратора на сервер

```
docker exec empolimer-back python scripts/create_superuser.py \
  --username superuser \
  --password 1qaz@WSX \
  --email admin@empolimer.ru
```

Проверьте mqtt-публикацию на сервер:

```
mosquitto_pub -h empolimer.ru -p 1883 -t "devices/demo/air" -i pub_test -u empolimer -P Techno2025 -m '{"datetime":"2025-06-26T21:41:38+12","temp":15.3,"hum":15.0}'
```

Подключитесь к базе данных:

```
docker exec -it empolimer-postgres bash
psql -U admin -d empolimer
```

Удалить все данные устройства по его имени:

```
DELETE FROM device_data
WHERE device_id IN (
    SELECT id FROM devices WHERE name = 'demo'
);
```

Посмотреть размеры образов:

```
df -h
docker system df -v
```

Удалить неиспользуемые образы на сервере:

```
docker image prune -a
```

Рассчёт записи данных с датчиков:

Всего ~48 байт чистых данных на 1 запись.

Съёмки раз в минуту:

- В сутки: 60 × 24 = 1440 записей
- За год: 525 600 записей
- За год данных с одного датчика: 525 600 × 80 байт ≈ 42 МБ
- За год данных со 100 датчиков: 4,2 ГБ