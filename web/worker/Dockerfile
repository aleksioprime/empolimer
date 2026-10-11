FROM python:3.12-slim

WORKDIR /usr/src/app

ENV PYTHONPATH=/usr/src/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Moscow

RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Живой - если файл heartbeat обновлялся за последние 90 секунд (есть связь с брокером).
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import os,sys,time; sys.exit(time.time() - os.path.getmtime('/tmp/worker-alive') > 90)"

CMD ["sh", "entrypoint.sh"]
