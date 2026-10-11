// Форматирование чисел, дат и «сколько прошло» для мониторинга.

export const formatNumber = (value, digits = 1) =>
  value === null || value === undefined || Number.isNaN(Number(value))
    ? '—'
    : Number(value).toLocaleString('ru-RU', { minimumFractionDigits: digits, maximumFractionDigits: digits });

export const formatDateTime = (value) => {
  if (!value) return '—';
  const date = new Date(value);
  return date.toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
};

export const formatTime = (value) => {
  if (!value) return '—';
  return new Date(value).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
};

const plural = (n, one, few, many) => {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few;
  return many;
};

// «только что», «5 мин назад», «3 ч назад», «2 дня назад»
export const timeAgo = (value, now = Date.now()) => {
  if (!value) return 'никогда';
  const seconds = Math.max(0, Math.round((now - new Date(value).getTime()) / 1000));
  if (seconds < 45) return 'только что';
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} мин назад`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} ч назад`;
  const days = Math.round(hours / 24);
  return `${days} ${plural(days, 'день', 'дня', 'дней')} назад`;
};

// Дата для <input type="datetime-local"> в часовом поясе браузера
export const toLocalInput = (date) => {
  const z = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${z(date.getMonth() + 1)}-${z(date.getDate())}T${z(date.getHours())}:${z(date.getMinutes())}`;
};

export const wifiQuality = (rssi) => {
  if (rssi === null || rssi === undefined) return null;
  if (rssi >= -60) return { text: 'отличный', icon: 'mdi-wifi-strength-4' };
  if (rssi >= -70) return { text: 'хороший', icon: 'mdi-wifi-strength-3' };
  if (rssi >= -80) return { text: 'слабый', icon: 'mdi-wifi-strength-2' };
  return { text: 'очень слабый', icon: 'mdi-wifi-strength-1' };
};
