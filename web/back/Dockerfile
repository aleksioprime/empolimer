FROM python:3.12-slim

WORKDIR /usr/src/app

ENV PYTHONPATH=/usr/src/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Moscow

RUN apt-get update && apt-get install -y --no-install-recommends netcat-openbsd tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /usr/src/app/entrypoint.sh

HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/ping/', timeout=4)"

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
