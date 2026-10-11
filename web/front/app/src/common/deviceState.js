// Как показывать состояние устройства (state и problems приходят с сервера).

export const DEVICE_STATES = {
  ok: { text: 'В норме', color: 'success', icon: 'mdi-check-circle' },
  warning: { text: 'Требует внимания', color: 'warning', icon: 'mdi-alert' },
  offline: { text: 'Нет связи', color: 'error', icon: 'mdi-wifi-off' },
  new: { text: 'Ожидает данных', color: 'grey', icon: 'mdi-timer-sand' },
};

export const PROBLEM_LEVELS = {
  error: { type: 'error', icon: 'mdi-alert-octagon' },
  warning: { type: 'warning', icon: 'mdi-alert' },
  info: { type: 'info', icon: 'mdi-information' },
};

export const deviceState = (device) => DEVICE_STATES[device?.state] || DEVICE_STATES.new;

// Значение относительно нормы: ok, low, high или null (нет значения)
export const valueLevel = (value, min, max) => {
  if (value === null || value === undefined) return null;
  if (value < min) return 'low';
  if (value > max) return 'high';
  return 'ok';
};

export const LEVEL_COLORS = { ok: 'success', low: 'info', high: 'warning' };
export const LEVEL_TEXT = { ok: 'в норме', low: 'ниже нормы', high: 'выше нормы' };

// Устройства с проблемами - первыми, затем по имени
const ORDER = { offline: 0, warning: 1, new: 2, ok: 3 };
export const sortDevices = (devices) =>
  [...devices].sort((a, b) => (ORDER[a.state] ?? 9) - (ORDER[b.state] ?? 9) || a.name.localeCompare(b.name));
