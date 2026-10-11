#!/usr/bin/env bash
# Установка станции ЕмПолимер на Raspberry Pi по сети - запускается на компьютере.
#
#   deploy/install.sh pi@192.168.1.50 [параметры]
#
# Параметры описаны в deploy/README.md и в выводе --help.
set -euo pipefail

usage() {
  cat <<'EOF'
Использование: deploy/install.sh USER@HOST [параметры]

  --autostart       запускать станцию при входе в рабочий стол
  --no-autostart    убрать автозапуск
  --usb-camera      поставить OpenCV для USB-камеры (на Pi Zero ставится долго)
  --code-only       только скопировать код, без apt и настройки системы
  --dest DIR        каталог на плате (по умолчанию ~/empolimer)
  --port N          порт SSH
  --dry-run         показать команды, ничего не выполняя
EOF
}

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET=""
DEST="empolimer"
AUTOSTART=""
USB_CAMERA=0
CODE_ONLY=0
DRY_RUN=0
SSH_OPTS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --autostart) AUTOSTART=on ;;
    --no-autostart) AUTOSTART=off ;;
    --usb-camera) USB_CAMERA=1 ;;
    --code-only) CODE_ONLY=1 ;;
    --dest) DEST="$2"; shift ;;
    --port) SSH_OPTS+=(-p "$2"); shift ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "Неизвестный параметр: $1" >&2; usage; exit 1 ;;
    *) TARGET="$1" ;;
  esac
  shift
done

if [[ -z "$TARGET" ]]; then
  usage
  exit 1
fi

run() {
  echo "+ $*"
  if [[ $DRY_RUN -eq 0 ]]; then "$@"; fi
}

# Одно SSH-соединение на весь запуск: пароль спрашивается один раз.
CONTROL="$(mktemp -u /tmp/empolimer-ssh.XXXXXX)"
SSH_OPTS+=(-o ControlMaster=auto -o ControlPath="$CONTROL" -o ControlPersist=60)
trap 'ssh "${SSH_OPTS[@]}" -O exit "$TARGET" 2>/dev/null || true' EXIT

echo "== Копирование станции в ~/$DEST на $TARGET"
run ssh "${SSH_OPTS[@]}" "$TARGET" "mkdir -p ~/$DEST/.deploy"
run rsync -az --delete \
  -e "ssh ${SSH_OPTS[*]}" \
  --exclude station.conf --exclude station.log --exclude '__pycache__' --exclude '.deploy' \
  "$ROOT/rpi/" "$TARGET:~/$DEST/"
run rsync -az -e "ssh ${SSH_OPTS[*]}" \
  "$ROOT/deploy/setup_device.sh" "$ROOT/deploy/templates" "$TARGET:~/$DEST/.deploy/"

ARGS=(--dest "$DEST")
[[ -n "$AUTOSTART" ]] && ARGS+=(--autostart "$AUTOSTART")
[[ $USB_CAMERA -eq 1 ]] && ARGS+=(--usb-camera)
[[ $CODE_ONLY -eq 1 ]] && ARGS+=(--code-only)

echo "== Настройка платы"
run ssh -t "${SSH_OPTS[@]}" "$TARGET" "bash ~/$DEST/.deploy/setup_device.sh ${ARGS[*]}"
