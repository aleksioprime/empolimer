// Живое обновление списка устройств.
//
// Основной канал — WebSocket. Если он недоступен, данные загружаются запросами раз в
// POLL_MS, а WebSocket переподключается с нарастающей паузой. Если от сервера долго
// нет сообщений, соединение считается зависшим и переоткрывается.
import { jwtDecode } from 'jwt-decode';
import jwtService from '@/services/jwt/jwt.service';
import { handleTokenRefresh } from '@/services/api/token.service';
import logger from '@/common/helpers/logger';

const POLL_MS = 10000;
const PING_MS = 25000;
const SILENCE_MS = 75000; // сервер шлёт данные не реже раза в 30 с
const RECONNECT_MAX_MS = 30000;

const tokenExpiresSoon = (token) => {
  try {
    return jwtDecode(token).exp - Date.now() / 1000 < 30;
  } catch {
    return true;
  }
};

export class LiveConnection {
  /**
   * onDevices(devices) — пришёл список устройств;
   * onStatus(status) — 'connecting' | 'live' | 'polling' | 'offline';
   * poll() — загрузить список запросом, вернуть true при успехе.
   */
  constructor({ onDevices, onStatus, poll }) {
    this.onDevices = onDevices;
    this.onStatus = onStatus;
    this.poll = poll;
    this.ws = null;
    this.stopped = true;
    this.attempt = 0;
    this.timers = {};
    this.lastMessage = 0;
    this.onVisibility = () => {
      if (document.visibilityState === 'visible' && !this.stopped && this.ws?.readyState !== WebSocket.OPEN) {
        this._connectNow();
      }
    };
  }

  start() {
    if (!this.stopped) return;
    this.stopped = false;
    document.addEventListener('visibilitychange', this.onVisibility);
    this.onStatus('connecting');
    this._connect();
  }

  stop() {
    this.stopped = true;
    document.removeEventListener('visibilitychange', this.onVisibility);
    Object.values(this.timers).forEach((timer) => { clearTimeout(timer); clearInterval(timer); });
    this.timers = {};
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
  }

  async _connect() {
    if (this.stopped) return;
    let token = jwtService.getAccessToken();
    if (!token || tokenExpiresSoon(token)) {
      token = await handleTokenRefresh();
      if (token === false) {
        // Сессия закончилась — на страницу входа
        window.location.href = '/login';
        return;
      }
    }
    if (!token) {
      this._fallback();
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${protocol}://${window.location.host}/api/v1/devices/ws/?token=${token}`);
    this.ws = ws;

    ws.onopen = () => {
      logger.info('WS: подключено');
      this.attempt = 0;
      this.lastMessage = Date.now();
      this._stopPolling();
      this.onStatus('live');
      this.timers.ping = setInterval(() => ws.readyState === WebSocket.OPEN && ws.send('ping'), PING_MS);
      this.timers.watchdog = setInterval(() => {
        if (Date.now() - this.lastMessage > SILENCE_MS) {
          logger.info('WS: нет сообщений, переподключение');
          ws.close();
        }
      }, 10000);
    };

    ws.onmessage = (event) => {
      this.lastMessage = Date.now();
      if (event.data === 'pong') return;
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'devices_update' && Array.isArray(data.devices)) this.onDevices(data.devices);
      } catch {
        // некорректное сообщение пропускаем
      }
    };

    ws.onclose = () => {
      clearInterval(this.timers.ping);
      clearInterval(this.timers.watchdog);
      if (this.ws === ws) this.ws = null;
      if (!this.stopped) this._fallback();
    };
  }

  _connectNow() {
    clearTimeout(this.timers.reconnect);
    this._connect();
  }

  // WebSocket недоступен: опрос запросами + повтор подключения с нарастающей паузой
  _fallback() {
    this._startPolling();
    const delay = Math.min(RECONNECT_MAX_MS, 2000 * 2 ** this.attempt);
    this.attempt += 1;
    clearTimeout(this.timers.reconnect);
    this.timers.reconnect = setTimeout(() => this._connect(), delay);
  }

  _startPolling() {
    if (this.timers.poll) return;
    const tick = async () => {
      const ok = await this.poll();
      if (this.ws?.readyState !== WebSocket.OPEN) this.onStatus(ok ? 'polling' : 'offline');
    };
    tick();
    this.timers.poll = setInterval(tick, POLL_MS);
  }

  _stopPolling() {
    clearInterval(this.timers.poll);
    delete this.timers.poll;
  }
}
