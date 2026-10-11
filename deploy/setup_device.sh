#!/usr/bin/env bash
# Настройка Raspberry Pi для станции ЕмПолимер. Выполняется на самой плате
# (deploy/install.sh копирует его в ~/empolimer/.deploy/); можно запустить повторно.
set -euo pipefail

DEST="empolimer"
AUTOSTART=""
USB_CAMERA=0
CODE_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dest) DEST="$2"; shift ;;
    --autostart) AUTOSTART="$2"; shift ;;
    --usb-camera) USB_CAMERA=1 ;;
    --code-only) CODE_ONLY=1 ;;
  esac
  shift
done

APP="$HOME/$DEST"
TEMPLATES="$APP/.deploy/templates"
REBOOT=0

if [[ $CODE_ONLY -eq 0 ]]; then
  # PyQt5 и Picamera2 — только из apt: на Pi Zero их не собрать через pip.
  PACKAGES=(python3-pyqt5 python3-serial python3-picamera2 python3-qrcode fonts-dejavu-core)
  [[ $USB_CAMERA -eq 1 ]] && PACKAGES+=(python3-opencv)
  MISSING=()
  for package in "${PACKAGES[@]}"; do
    dpkg -s "$package" >/dev/null 2>&1 || MISSING+=("$package")
  done
  if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo "== Установка пакетов: ${MISSING[*]}"
    sudo apt-get update
    sudo apt-get install -y --no-install-recommends "${MISSING[@]}"
  fi

  # dialout — доступ к /dev/ttyUSB*, video — к камере.
  for group in dialout video; do
    if ! id -nG "$USER" | grep -qw "$group"; then
      sudo usermod -aG "$group" "$USER"
      REBOOT=1
    fi
  done
fi

if [[ ! -f "$APP/station.conf" ]]; then
  cp "$APP/station.conf.example" "$APP/station.conf"
  echo "== Создан $APP/station.conf"
fi

render() {
  sed -e "s|@APP@|$APP|g" "$1" > "$2"
}

mkdir -p "$HOME/Desktop"
render "$TEMPLATES/empolimer-station.desktop" "$HOME/Desktop/empolimer-station.desktop"
chmod +x "$HOME/Desktop/empolimer-station.desktop"

AUTOSTART_FILE="$HOME/.config/autostart/empolimer-station.desktop"
if [[ "$AUTOSTART" == "on" ]]; then
  mkdir -p "$(dirname "$AUTOSTART_FILE")"
  render "$TEMPLATES/empolimer-station.desktop" "$AUTOSTART_FILE"
  echo "== Автозапуск включён"
elif [[ "$AUTOSTART" == "off" ]]; then
  rm -f "$AUTOSTART_FILE"
  echo "== Автозапуск выключен"
fi

# Перезапустить станцию, если она уже работает: подхватит новый код.
if pgrep -f "$APP/station.py" >/dev/null; then
  pkill -f "$APP/station.py" || true
  sleep 1
  DISPLAY=:0 WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}" XDG_RUNTIME_DIR="/run/user/$(id -u)" \
    setsid -f python3 "$APP/station.py" >"$APP/station.log" 2>&1 </dev/null || true
  echo "== Станция перезапущена"
fi

echo "== Готово. Запуск: ярлык «Станция ЕмПолимер» на рабочем столе или python3 $APP/station.py"
if [[ $REBOOT -eq 1 ]]; then
  echo "!! Пользователь добавлен в группы dialout/video — перезагрузите плату: sudo reboot"
fi
