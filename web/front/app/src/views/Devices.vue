<template>
  <v-snackbar v-model="wsStatus.show" :color="wsStatus.ok ? 'green' : 'red'" location="bottom right" :timeout="3000">
    <v-icon class="me-2" :color="wsStatus.ok ? 'white' : 'white'">
      {{ wsStatus.ok ? 'mdi-check-circle' : 'mdi-alert-circle' }}
    </v-icon>
    {{ wsStatus.msg }}
  </v-snackbar>

  <!-- Кнопка добавить устройство -->
  <v-row class="d-flex align-center">
    <v-col cols="auto">
      <v-btn color="primary" @click="openAddDialog" v-if="canEdit">
        <v-icon class="me-1">mdi-plus</v-icon>
        Добавить устройство
      </v-btn>
    </v-col>
    <v-spacer />
    <v-col cols="auto" class="d-flex justify-end">
      <v-chip :color="wsConnected ? 'green' : 'error'" small>
        <v-icon start size="16">{{ wsConnected ? 'mdi-check' : 'mdi-alert' }}</v-icon>
        {{ wsConnected ? 'Online' : 'Offline' }}
      </v-chip>
    </v-col>
  </v-row>

  <!-- Карточки устройств -->
  <v-row>
    <v-col v-for="device in devices" :key="device.id" cols="12" sm="6" md="4" lg="3">
      <v-card>
        <v-card-title class="d-flex align-center no-wrap-title">
          <v-icon class="me-2" :color="device.online ? 'green' : 'grey'">
            {{ device.online ? 'mdi-access-point' : 'mdi-access-point-off' }}
          </v-icon>
          {{ device.name }}
          <v-spacer />
          <v-menu offset-y>
            <template #activator="{ props }">
              <v-btn icon size="small" v-bind="props">
                <v-icon>mdi-dots-vertical</v-icon>
              </v-btn>
            </template>
            <v-list>
              <v-list-item @click="viewDevice(device)">
                <v-list-item-title>
                  <v-icon size="18" class="me-2">mdi-eye</v-icon>
                  Подробнее
                </v-list-item-title>
              </v-list-item>
              <v-list-item @click="openClearDataDialog(device)" v-if="canEdit">
                <v-list-item-title>
                  <v-icon size="18" class="me-2" color="orange">mdi-broom</v-icon>
                  Очистить данные
                </v-list-item-title>
              </v-list-item>
              <v-list-item @click="openEditDialog(device)" v-if="canEdit">
                <v-list-item-title>
                  <v-icon size="18" class="me-2">mdi-pencil</v-icon>
                  Редактировать
                </v-list-item-title>
              </v-list-item>
              <v-list-item @click="openDeleteDialog(device)" v-if="canEdit">
                <v-list-item-title class="text-error">
                  <v-icon size="18" class="me-2" color="error">mdi-delete</v-icon>
                  Удалить
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </v-card-title>
        <v-card-text>
          <div class="mb-2">
            <span>{{ device.description || '—' }}</span>
          </div>
          <div class="mb-2">
            <span class="font-weight-bold">Локация:&nbsp;</span>
            <span>{{ device.location || '—' }}</span>
          </div>
          <hr class="mb-2">
          <div class="mb-1" v-if="device.last_data">
            <v-icon class="me-1" color="blue">mdi-thermometer</v-icon>
            Температура: <b>{{ device.last_data.temperature }}°C</b>
            <v-btn size="x-small" variant="text" icon class="ms-1" @click="openChartDialog(device, 'temperature')"
              :title="'Показать график температуры'">
              <v-icon color="blue">mdi-chart-line</v-icon>
            </v-btn>
          </div>
          <div class="mb-2" v-if="device.last_data">
            <v-icon class="me-1" color="green">mdi-water-percent</v-icon>
            Влажность: <b>{{ device.last_data.humidity }}%</b>
            <v-btn size="x-small" variant="text" icon class="ms-1" @click="openChartDialog(device, 'humidity')"
              :title="'Показать график влажности'">
              <v-icon color="green">mdi-chart-line</v-icon>
            </v-btn>
          </div>
          <div class="mb-2" v-if="device.last_data">
            <v-icon class="me-1" color="orange">mdi-battery</v-icon>
            Батарея: <b>{{ device.last_data.battery ? device.last_data.battery + ' В' : '—' }}</b>
          </div>
          <v-btn size="small" class="ms-1 my-2" color="secondary" :title="'Скачать все данные устройства в Excel'"
            @click="downloadExcel(device)">
            <v-icon start>mdi-file-excel</v-icon>
            Скачать Excel
          </v-btn>
          <div class="d-flex align-center" v-if="device.last_data">
            <v-icon class="me-2" color="grey">mdi-clock-outline</v-icon>
            Обновлено:<span class="ms-1">{{ formatTime(device.last_data.timestamp) }}</span>
          </div>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>

  <!-- Диалог добавления/редактирования -->
  <v-dialog v-model="dialogVisible" persistent max-width="400">
    <v-card>
      <v-card-title>
        {{ editingDevice ? "Редактировать устройство" : "Добавить устройство" }}
      </v-card-title>
      <v-card-text>
        <v-form ref="deviceForm">
          <v-text-field class="mb-1" v-model="form.name" label="Название" :rules="nameRules" />
          <v-text-field class="mb-1" v-model="form.description" label="Описание" />
          <v-text-field class="mb-1" v-model="form.location" label="Местоположение" />
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn text @click="closeDialog">Отмена</v-btn>
        <v-btn color="primary" @click="saveDevice">Сохранить</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Диалог удаления -->
  <v-dialog v-model="deleteDialogVisible" max-width="400">
    <v-card>
      <v-card-title class="text-h6">Удалить устройство?</v-card-title>
      <v-card-text>
        Вы уверены, что хотите удалить <b>{{ deviceToDelete?.name }}</b>?
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn text @click="deleteDialogVisible = false">Отмена</v-btn>
        <v-btn color="error" @click="deleteDevice">Удалить</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Диалог детальной информации -->
  <v-dialog v-model="detailDialogVisible" max-width="500">
    <v-card>
      <v-card-title>
        Детали устройства: {{ deviceDetails?.name }}
      </v-card-title>
      <v-card-text v-if="deviceDetails">
        <div class="mb-1">{{ deviceDetails.description || "—" }}</div>
        <div class="mb-1"><b>Местоположение:</b> {{ deviceDetails.location || "—" }}</div>
        <div v-if="deviceDetails?.data && deviceDetails.data.length">
          <div class="my-2"><b>Графики последних измерений</b></div>
          <DeviceChart class="my-3" :data="deviceDetails.data" field="temperature" label="Температура (°C)"
            color="#ff5252" />
          <DeviceChart class="my-3" :data="deviceDetails.data" field="humidity" label="Влажность (%)" color="#43a047" />
        </div>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn text @click="detailDialogVisible = false">Закрыть</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Диалог вывода графика -->
  <v-dialog v-model="chartDialog.visible" max-width="600">
    <v-card>
      <v-card-title class="d-flex align-center">
        График {{ chartDialog.field === 'temperature' ? 'температуры' : 'влажности' }}
        <v-spacer />
        <v-btn icon variant="text" @click="chartDialog.visible = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="6">
            <v-text-field v-model="chartDialog.filter.start" label="Начальная дата" type="datetime-local" dense />
          </v-col>
          <v-col cols="6">
            <v-text-field v-model="chartDialog.filter.end" label="Конечная дата" type="datetime-local" dense />
          </v-col>
        </v-row>
        <DeviceChart v-if="chartDialog.data.length" :data="chartDialog.data" :field="chartDialog.field"
          :showControls="true" :label="chartDialog.field === 'temperature' ? 'Температура (°C)' : 'Влажность (%)'"
          :color="chartDialog.field === 'temperature' ? '#ff5252' : '#43a047'" />
        <div v-else class="text-grey mt-3">Нет данных за выбранный период</div>
      </v-card-text>
      <v-card-actions>
        <v-btn color="secondary" :loading="chartDialog.loading" @click="downloadExcel()"
          :disabled="!chartDialog.data.length" title="Скачать данные за выбранный период">
          <v-icon start>mdi-file-excel</v-icon>
          Скачать Excel
        </v-btn>
        <v-btn color="primary" @click="fetchChartData" :loading="chartDialog.loading">
          Обновить
        </v-btn>
        <v-spacer />
        <v-btn text @click="chartDialog.visible = false">Закрыть</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Диалог очистки данных выбранного устройства -->
  <v-dialog v-model="clearDataDialog.visible" max-width="480">
    <v-card>
      <v-card-title>Очистить все данные устройства?</v-card-title>
      <v-card-text>
        <div class="mb-2">
          Это действие <b>удалит все показания</b> устройства <b>{{ clearDataDialog.device?.name }}</b>.<br>
          <br>
          Рекомендуем <b>сначала скачать все данные</b> в Excel для резервного копирования.
        </div>
        <v-btn color="secondary" @click="downloadExcel(clearDataDialog.device)">
          <v-icon start>mdi-file-excel</v-icon>
          Скачать Excel
        </v-btn>
      </v-card-text>
      <v-card-actions class="justify-end">
        <v-btn @click="clearDataDialog.visible = false">Отмена</v-btn>
        <v-btn color="error" @click="confirmClearData">Очистить</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

</template>

<script setup>
import { ref, reactive, watch, inject, computed, onMounted, onUnmounted } from 'vue'
import logger from '@/common/helpers/logger';
import debounce from 'lodash/debounce';
import { jwtDecode } from "jwt-decode";
import jwtService from "@/services/jwt/jwt.service";

import DeviceChart from '@/components/DeviceChart.vue'

// Инициализация стора авторизации
import { useAuthStore } from "@/stores/auth";
const authStore = useAuthStore();

// Метка доступности для редактирования текущему пользователю
const canEdit = computed(() =>
  authStore.user?.is_admin || authStore.user?.is_superuser
);

// Инициализация стора устройств
import { useDeviceStore } from "@/stores/device";
const deviceStore = useDeviceStore();

const devices = ref([]); // Список устройств

/**
 * Загружает список устройств из стора
 */
const loadDevices = async () => {
  devices.value = await deviceStore.loadDevices();
}

// --- POOLING ---

const poller = ref(null) // Таймер polling (интервал опроса API при потере WS)

const POLLING_INTERVAL = 5000 // Интервал polling, мс

/**
 * Запускает polling устройств, если не удалось подключиться к WebSocket
 */
const startPolling = () => {
  if (poller.value) return; // Polling уже активен
  poller.value = setInterval(() => {
    loadDevices()
  }, POLLING_INTERVAL)
  logger.info('Start polling')
}

/**
 * Останавливает polling
 */
const stopPolling = () => {
  if (poller.value) {
    clearInterval(poller.value)
    poller.value = null
    logger.info('Stop polling')
  }
}

// --- WEBSOCKET ---

let ws = null // WebSocket-соединение
const wsConnected = ref(false); // Состояние WebSocket-соединения

/**
 * Для всплывающих уведомлений статуса WS (плашка внизу)
 */
const wsStatus = reactive({
  show: false,
  ok: true,
  msg: '',
})

/**
 * Отображает всплывающий статус WS
 */
const showWsStatus = (msg, ok = true) => {
  wsStatus.msg = msg;
  wsStatus.ok = ok;
  wsStatus.show = true;
}


const shouldReconnect = ref(true);

/**
 * Подключается к WebSocket с текущим токеном из стора.
 * Если не удалось — переходит на polling.
 */
const connectWebSocket = async () => {

  // Если токена нет или скоро истекает, делаем refresh
  if (needRefresh(jwtService.getAccessToken())) {
    logger.info('AccessToken почти истёк, обновляем...');
    const refreshed = await authStore.refresh();
    if (!refreshed) {
      logger.error('Обновление не получилось');
      return;
    }
  }

  if (ws) ws.close(); // Закрыть старое соединение, если было

  if (!authStore.user) return;

  const token = jwtService.getAccessToken()
  // Адрес WS: явный VITE_WS_URL, иначе текущий origin страницы (wss/ws).
  const WS_BASE_URL = import.meta.env.VITE_WS_URL
    || `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
  const wsUrl = `${WS_BASE_URL}/api/v1/devices/ws/?token=${token}`
  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    logger.info('WS OPENED');
    wsConnected.value = true;
    stopPolling();
    showWsStatus('WS соединение установлено', true);
  }

  ws.onmessage = (event) => {
    // Обрабатываем входящие сообщения (например, обновление списка устройств)
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'devices_update' && Array.isArray(data.devices)) {
        devices.value = data.devices
      }
    } catch (e) {
      // Некорректные данные игнорируем
    }
  }

  ws.onerror = (e) => {
    logger.info('WS ERROR')
    wsConnected.value = false
    showWsStatus('Ошибка WS соединения, перехожу на polling', false)
    startPolling()
  }

  ws.onclose = () => {
    logger.info('WS CLOSED');
    wsConnected.value = false;
    showWsStatus('WS соединение разорвано, перехожу на polling', false)
    if (shouldReconnect.value) {
      startPolling();
      setTimeout(connectWebSocket, 3000);
    }
  }
}

/**
 * Закрывает WebSocket-соединение
 */
const stopSocket = () => {
  shouldReconnect.value = false;

  if (ws) {
    ws.close();
    ws = null;
  }
}

// --- СОЗДАНИЕ И РЕДАКТИРОВАНИЕ УСТРОЙСТВ ---

// Модель для формы создания/редактирования устройства
const form = reactive({
  name: '',
  description: '',
  location: ''
})

const dialogVisible = ref(false) // Диалог добавления/редактирования устройства
const editingDevice = ref(null) // Текущее редактируемое устройство
const deviceForm = ref(null) // Ссылка на форму устройства

/**
 * Открывает диалог добавления нового устройства
 */
const openAddDialog = () => {
  editingDevice.value = null
  form.name = ''
  form.description = ''
  form.location = ''
  dialogVisible.value = true
}

/**
 * Открывает диалог редактирования существующего устройства
 */
const openEditDialog = (device) => {
  editingDevice.value = device
  form.name = device.name
  form.description = device.description
  form.location = device.location
  dialogVisible.value = true
}

/**
 * Закрывает диалог добавления/редактирования
 */
const closeDialog = () => {
  dialogVisible.value = false
}

// --- Валидация имени устройства ---
const nameRules = [
  v => !!v || 'Обязательное поле',
  v => /^[a-z0-9_]{1,8}$/.test(v) || 'Строчные латинские буквы, цифры и _ (до 8)'
]

/**
 * Сохраняет (создаёт/обновляет) устройство по данным формы
 */
const saveDevice = async () => {
  const { valid } = await deviceForm.value.validate();
  if (!valid) return;

  if (editingDevice.value) {
    // Обновление устройства
    await deviceStore.updateDevice(editingDevice.value.id, {
      name: form.name,
      description: form.description,
      location: form.location
    })
  } else {
    // Добавление нового устройства
    await deviceStore.createDevice({
      name: form.name,
      description: form.description,
      location: form.location
    })
  }
  dialogVisible.value = false

  devices.value = await deviceStore.loadDevices();
}

// --- УДАЛЕНИЕ УСТРОЙСТВА ---

const deleteDialogVisible = ref(false) // Диалог подтверждения удаления
const deviceToDelete = ref(null) // Устройство, выбранное для удаления

/**
 * Открывает диалог подтверждения удаления устройства
 */
const openDeleteDialog = (device) => {
  deviceToDelete.value = device
  deleteDialogVisible.value = true
}

/**
 * Удаляет выбранное устройство
 */
const deleteDevice = async () => {
  const deleted = await deviceStore.deleteDevice(deviceToDelete.value.id)
  if (deleted) {
    devices.value = devices.value.filter(d => d.id !== deviceToDelete.value.id)
  }
  deleteDialogVisible.value = false
  devices.value = await deviceStore.loadDevices();
}

// --- ДЕТАЛЬНАЯ ИНФОРМАЦИЯ ОБ УСТРОЙСТВЕ ---

const detailDialogVisible = ref(false) // Диалог детальной информации
const deviceDetails = ref(null) // Детальная информация по устройству

/**
 * Открывает диалог с информацией устройства и загружает данные для графиков
 */
const viewDevice = async (device) => {
  deviceDetails.value = await deviceStore.loadDeviceDetailed(device.id)
  detailDialogVisible.value = true
}

// --- ВЫВОД ГРАФИКА ---

const chartDialog = reactive({
  visible: false,
  device: null,
  field: 'temperature', // или 'humidity'
  data: [],
  loading: false,
  filter: {
    start: '', // строка вида '2025-07-01'
    end: '',   // строка вида '2025-07-04'
  }
})

const openChartDialog = async (device, field) => {
  chartDialog.device = device;
  chartDialog.field = field;
  chartDialog.visible = true;
  // По умолчанию — неделя назад и сейчас
  const now = new Date();
  const weekAgo = new Date();
  weekAgo.setDate(now.getDate() - 7);

  // Формат YYYY-MM-DDTHH:mm (чтобы совпадало с HTML5 datetime-local)
  const toLocalISO = (date) => {
    const z = n => n < 10 ? '0' + n : n;
    return `${date.getFullYear()}-${z(date.getMonth() + 1)}-${z(date.getDate())}T${z(date.getHours())}:${z(date.getMinutes())}`;
  };

  chartDialog.filter.start = toLocalISO(weekAgo);
  chartDialog.filter.end = toLocalISO(now);
  await fetchChartData();
}

const fetchChartData = async () => {
  chartDialog.loading = true;
  logger.info("Запрос с параметрами: ", chartDialog)

  const config = {
    params: {
      start: chartDialog.filter.start,
      end: chartDialog.filter.end,
      field: chartDialog.field,
    }
  }

  const response = await deviceStore.loadDeviceDataChart(chartDialog.device.id, config);
  chartDialog.data = Array.isArray(response) ? response : (response.items || []);

  chartDialog.loading = false;
}

const fetchChartDataDebounced = debounce(fetchChartData, 400);

// Отслеживание изменение дат и обновление графика
watch(
  () => ({ ...chartDialog.filter }),
  async (newVal, oldVal) => {
    if (oldVal.start && oldVal.end && newVal.start && newVal.end) {
      await fetchChartDataDebounced();
    }
  },
  { deep: true }
);

// --- СКАЧИВАНИЕ ДАННЫХ ---

const downloadExcel = async (device) => {
  let device_id = device?.id
  let config = {}

  if (chartDialog.visible) {
    device_id = chartDialog.device.id
    config = {
      params: {
        start: chartDialog.filter.start,
        end: chartDialog.filter.end,
        field: chartDialog.field,
      }
    };
  }

  const result = await deviceStore.downloadDeviceData(device_id, config)

  if (!result) {
    wsStatus.show = true
    wsStatus.ok = false
    wsStatus.msg = 'Ошибка скачивания файла'
    return
  }
  // Для браузера создаём ссылку
  const url = window.URL.createObjectURL(new Blob([result.blob]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', result.filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

// --- ОЧИСТКА ДАННЫХ УСТРОЙСТВА ---

// Диалог очистки данных
const clearDataDialog = ref({
  visible: false,
  device: null,
});

// Открыть диалог очистки данных
const openClearDataDialog = (device) => {
  clearDataDialog.value.device = device;
  clearDataDialog.value.visible = true;
};

// Подтвердить очистку данных
const confirmClearData = async () => {
  const device = clearDataDialog.value.device;
  if (!device) return;

  const result = await deviceStore.clearDeviceData(device.id);

  if (!result) {
    showWsStatus('Ошибка удаления данных', false);
    return;
  }

  devices.value = await deviceStore.loadDevices();
  clearDataDialog.value.visible = false;

  showWsStatus('Данные успешно удалены', true);
};

// --- ДРУГИЕ ФУНКЦИИ ---

/**
 * Проверяет, что токен скоро истекает
 */
const needRefresh = (token) => {
  if (!token) return true;
  try {
    const decoded = jwtDecode(token);
    const now = Math.floor(Date.now() / 1000);
    return (decoded.exp - now) < 30;
  } catch (e) {
    return true;
  }
}

/**
 * Форматирует дату в удобный вид (например, "14:32 27.06.25")
 */
const formatTime = (date) => {
  if (!date) return '-'
  const d = new Date(date) // Автоматически учитывает временную зону браузера
  return (
    d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) +
    ' ' +
    d.toLocaleDateString('ru-RU')
  )
}

// --- ЖИЗНЕННЫЙ ЦИКЛ КОМПОНЕНТА ---

const stopSocketVar = inject('stopSocket')

// При монтировании компонента: загрузить устройства и подключиться к WebSocket
onMounted(async () => {
  loadDevices();
  connectWebSocket();
  stopSocketVar.value = myLocalStopSocket;
});

// При размонтировании: закрыть соединения и polling
onUnmounted(() => {
  stopSocket();
  stopPolling();
  stopSocketVar.value = () => { };
});

function myLocalStopSocket() {
  shouldReconnect.value = false;
  if (ws) {
    ws.close();
    ws = null;
  }
}
</script>
