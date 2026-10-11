<template>
  <v-btn variant="text" prepend-icon="mdi-arrow-left" :to="{ name: 'devices' }" class="mb-2 ms-n3">Все устройства</v-btn>

  <v-skeleton-loader v-if="!device && loading" type="heading, card" />
  <v-alert v-else-if="!device" type="warning" variant="tonal">Устройство не найдено или было удалено.</v-alert>

  <template v-else>
    <!-- Заголовок -->
    <div class="d-flex align-start flex-wrap ga-2 mb-4">
      <div>
        <div class="d-flex align-center ga-3">
          <h1 class="text-h5 font-weight-bold">{{ device.name }}</h1>
          <StateChip :device="device" />
        </div>
        <div class="text-body-2 text-medium-emphasis mt-1">
          <span v-if="device.description">{{ device.description }} · </span>
          <v-icon size="14">mdi-map-marker-outline</v-icon> {{ device.location || 'место не указано' }}
        </div>
      </div>
      <v-spacer />
      <v-menu v-if="canEdit">
        <template #activator="{ props }">
          <v-btn v-bind="props" variant="outlined" append-icon="mdi-chevron-down">Управление</v-btn>
        </template>
        <v-list density="compact">
          <v-list-item prepend-icon="mdi-pencil" title="Настройки и норма" @click="formOpen = true" />
          <v-list-item prepend-icon="mdi-broom" title="Очистить измерения" @click="confirm = 'clear'" />
          <v-list-item prepend-icon="mdi-delete" title="Удалить устройство" class="text-error" @click="confirm = 'delete'" />
        </v-list>
      </v-menu>
    </div>

    <!-- Что требует внимания -->
    <v-alert v-for="problem in device.problems" :key="problem.code" :type="PROBLEM_LEVELS[problem.level].type"
      variant="tonal" density="compact" class="mb-2">
      {{ problem.text }}
    </v-alert>

    <v-row class="mt-1">
      <!-- Текущие значения -->
      <v-col cols="12" md="8">
        <v-card class="h-100">
          <v-card-item>
            <v-card-title>Сейчас</v-card-title>
            <v-card-subtitle>
              <template v-if="device.last_data">
                измерено {{ formatDateTime(device.last_data.timestamp) }} ({{ timeAgo(device.last_data.timestamp, now) }})
              </template>
              <template v-else>измерений ещё не было</template>
            </v-card-subtitle>
          </v-card-item>
          <v-card-text class="d-flex flex-wrap ga-10">
            <MetricValue large label="Температура" icon="mdi-thermometer" unit="°C"
              :value="device.last_data?.temperature" :min="device.thresholds.temp_min" :max="device.thresholds.temp_max"
              :muted="!device.online" />
            <MetricValue large label="Влажность" icon="mdi-water-percent" unit="%"
              :value="device.last_data?.humidity" :min="device.thresholds.hum_min" :max="device.thresholds.hum_max"
              :muted="!device.online" />
            <MetricValue v-if="device.last_data?.battery != null" large label="Батарея" icon="mdi-battery" unit="В"
              :value="device.last_data.battery" :digits="2" />
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Состояние модулей -->
      <v-col cols="12" md="4">
        <v-card class="h-100">
          <v-card-item><v-card-title>Устройство</v-card-title></v-card-item>
          <v-list density="compact" class="py-0">
            <v-list-item v-for="row in modules" :key="row.label" :prepend-icon="row.icon">
              <v-list-item-title class="text-body-2">{{ row.label }}</v-list-item-title>
              <template #append>
                <span :class="['text-body-2', row.color ? `text-${row.color}` : 'text-medium-emphasis']">{{ row.value }}</span>
              </template>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>

    <!-- Графики за период -->
    <v-card class="mt-4">
      <v-card-item>
        <v-card-title>История</v-card-title>
        <v-card-subtitle v-if="series">
          {{ formatDateTime(series.start) }} - {{ formatDateTime(series.end) }} ·
          {{ series.stats.count }} измерений{{ series.bucket_seconds > 60 ? ` · точка = среднее за ${bucketText}` : '' }}
        </v-card-subtitle>
        <template #append>
          <v-btn variant="text" prepend-icon="mdi-microsoft-excel" :loading="downloading" @click="download">Excel</v-btn>
        </template>
      </v-card-item>

      <v-card-text>
        <div class="d-flex flex-wrap align-center ga-2 mb-4">
          <v-btn-toggle v-model="period" mandatory density="compact" variant="outlined" divided color="primary">
            <v-btn v-for="p in PERIODS" :key="p.key" :value="p.key">{{ p.label }}</v-btn>
          </v-btn-toggle>
          <template v-if="period === 'custom'">
            <v-text-field v-model="custom.start" type="datetime-local" label="С" density="compact" hide-details
              style="max-width: 220px" />
            <v-text-field v-model="custom.end" type="datetime-local" label="По" density="compact" hide-details
              style="max-width: 220px" />
          </template>
          <v-progress-circular v-if="seriesLoading" indeterminate size="20" width="2" color="primary" />
        </div>

        <v-alert v-if="seriesError" type="error" variant="tonal" density="compact">{{ seriesError }}</v-alert>
        <div v-else-if="series && !series.points.length" class="text-medium-emphasis text-center py-10">
          За этот период измерений нет
        </div>
        <v-row v-else-if="series">
          <v-col v-for="chart in charts" :key="chart.field" cols="12" lg="6">
            <div class="d-flex align-baseline mb-1">
              <span class="text-subtitle-1 font-weight-medium">{{ chart.title }}</span>
              <v-spacer />
              <span class="text-caption text-medium-emphasis">
                мин {{ formatNumber(series.stats[chart.field].min) }} ·
                ср {{ formatNumber(series.stats[chart.field].avg) }} ·
                макс {{ formatNumber(series.stats[chart.field].max) }} {{ chart.unit }}
              </span>
            </div>
            <SeriesChart :points="series.points" :field="chart.field" :unit="chart.unit" :color="chart.color"
              :bucket-seconds="series.bucket_seconds" :min="chart.min" :max="chart.max" :start="series.start"
              :end="series.end" />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Последние измерения -->
    <v-card class="mt-4">
      <v-card-item><v-card-title>Измерения</v-card-title></v-card-item>
      <v-data-table-server v-model:items-per-page="table.limit" v-model:page="table.page" :headers="headers"
        :items="table.items" :items-length="table.total" :loading="table.loading" density="compact"
        :items-per-page-options="[10, 25, 50, 100]" no-data-text="Измерений нет" loading-text="Загрузка…"
        @update:options="loadTable">
        <template #item.timestamp="{ value }">{{ formatDateTime(value) }}</template>
        <template #item.temperature="{ value }">{{ formatNumber(value) }}</template>
        <template #item.humidity="{ value }">{{ formatNumber(value) }}</template>
        <template #item.battery="{ value }">{{ formatNumber(value, 2) }}</template>
      </v-data-table-server>
    </v-card>
  </template>

  <DeviceFormDialog v-model="formOpen" :device="device" />

  <v-dialog :model-value="!!confirm" max-width="460" @update:model-value="confirm = null">
    <v-card :title="confirm === 'delete' ? 'Удалить устройство?' : 'Очистить измерения?'">
      <v-card-text>
        <template v-if="confirm === 'delete'">
          Устройство <b>{{ device?.name }}</b> и все его измерения будут удалены. Если устройство продолжит присылать
          данные, оно появится снова.
        </template>
        <template v-else>
          Все измерения устройства <b>{{ device?.name }}</b> будут удалены без возможности восстановления.
        </template>
        <div class="mt-3">Перед этим можно <a href="#" @click.prevent="downloadAll">скачать все данные в Excel</a>.</div>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="confirm = null">Отмена</v-btn>
        <v-btn color="error" variant="flat" :loading="working" @click="runConfirm">
          {{ confirm === 'delete' ? 'Удалить' : 'Очистить' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-snackbar v-model="toast.show" :color="toast.color" timeout="3000">{{ toast.text }}</v-snackbar>
</template>

<script setup>
import { computed, reactive, ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import StateChip from '@/components/StateChip.vue'
import MetricValue from '@/components/MetricValue.vue'
import SeriesChart from '@/components/SeriesChart.vue'
import DeviceFormDialog from '@/components/DeviceFormDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { useDeviceStore } from '@/stores/device'
import { PROBLEM_LEVELS } from '@/common/deviceState'
import { formatDateTime, formatNumber, timeAgo, toLocalInput, wifiQuality } from '@/common/helpers/format'
import { useNow } from '@/composables/useNow'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const deviceStore = useDeviceStore()
const now = useNow()

const id = computed(() => route.params.id)
const device = computed(() => deviceStore.byId(id.value))
const canEdit = computed(() => authStore.user?.is_admin || authStore.user?.is_superuser)
const loading = ref(true)
const formOpen = ref(false)
const confirm = ref(null)
const working = ref(false)
const downloading = ref(false)
const toast = reactive({ show: false, text: '', color: 'success' })
const notify = (text, color = 'success') => Object.assign(toast, { show: true, text, color })

// --- состояние модулей ---

const yesNo = (value, yes, no) => value === undefined || value === null
  ? { value: '-' }
  : { value: value ? yes : no, color: value ? 'success' : 'error' }

const modules = computed(() => {
  const s = device.value?.status || {}
  const online = device.value?.online
  const wifi = online ? wifiQuality(s.rssi) : null
  return [
    { label: 'Последний контакт', icon: 'mdi-clock-outline',
      value: device.value?.last_seen ? timeAgo(device.value.last_seen, now.value) : 'никогда',
      color: online ? 'success' : 'error' },
    { label: 'Wi-Fi', icon: wifi?.icon || 'mdi-wifi-off',
      value: wifi ? `${wifi.text}, ${s.rssi} дБм` : (online ? '-' : 'нет связи') },
    { label: 'Датчик', icon: 'mdi-thermometer', ...yesNo(s.sensor, 'работает', 'не отвечает') },
    { label: 'SD-карта', icon: 'mdi-sd', ...yesNo(s.sd, 'есть', 'нет') },
    { label: 'Часы', icon: 'mdi-clock-check-outline', ...yesNo(s.time, 'синхронизированы', 'не установлены') },
    { label: 'Подсветка', icon: 'mdi-lightbulb-outline',
      value: s.light === undefined ? '-' : `${s.light ? 'включена' : 'выключена'}${s.light_auto ? ' (расписание)' : ''}` },
    { label: 'Ждут отправки', icon: 'mdi-tray-full', value: s.queue ? `${s.queue} измерений` : 'нет' },
    { label: 'Измерение', icon: 'mdi-timer-outline', value: s.interval ? `раз в ${s.interval} с` : '-' },
    { label: 'Прошивка', icon: 'mdi-chip', value: s.fw ? `${s.fw} · ${s.board}` : '-' },
    { label: 'IP-адрес', icon: 'mdi-ip-network-outline', value: online && s.ip ? s.ip : '-' },
  ]
})

// --- графики ---

const PERIODS = [
  { key: '6h', label: '6 ч', hours: 6 },
  { key: '24h', label: 'Сутки', hours: 24 },
  { key: '7d', label: 'Неделя', hours: 24 * 7 },
  { key: '30d', label: 'Месяц', hours: 24 * 30 },
  { key: 'custom', label: 'Период' },
]
const period = ref('24h')
const custom = reactive({ start: toLocalInput(new Date(Date.now() - 86400000)), end: toLocalInput(new Date()) })
const series = ref(null)
const seriesLoading = ref(false)
const seriesError = ref('')

const range = () => {
  if (period.value === 'custom') {
    return { start: new Date(custom.start).toISOString(), end: new Date(custom.end).toISOString() }
  }
  const hours = PERIODS.find((p) => p.key === period.value).hours
  const end = new Date()
  return { start: new Date(end - hours * 3600000).toISOString(), end: end.toISOString() }
}

const loadSeries = async () => {
  const { start, end } = range()
  if (!(new Date(start) < new Date(end))) {
    seriesError.value = 'Начало периода должно быть раньше конца'
    return
  }
  seriesLoading.value = true
  const data = await deviceStore.loadSeries(id.value, { start, end, points: 240 })
  seriesLoading.value = false
  if (data) {
    series.value = data
    seriesError.value = ''
  } else if (!series.value) {
    seriesError.value = 'Не удалось загрузить график - повторим автоматически'
  }
}

const charts = computed(() => [
  { field: 'temperature', title: 'Температура', unit: '°C', color: '#e65100',
    min: device.value?.thresholds.temp_min, max: device.value?.thresholds.temp_max },
  { field: 'humidity', title: 'Влажность', unit: '%', color: '#1565c0',
    min: device.value?.thresholds.hum_min, max: device.value?.thresholds.hum_max },
])

const bucketText = computed(() => {
  const s = series.value?.bucket_seconds || 60
  return s < 3600 ? `${s / 60} мин` : `${s / 3600} ч`
})

watch(period, loadSeries)
watch(() => [custom.start, custom.end], () => period.value === 'custom' && loadSeries())

// --- таблица ---

const headers = [
  { title: 'Время', key: 'timestamp', sortable: false },
  { title: 'Температура, °C', key: 'temperature', sortable: false, align: 'end' },
  { title: 'Влажность, %', key: 'humidity', sortable: false, align: 'end' },
  { title: 'Батарея, В', key: 'battery', sortable: false, align: 'end' },
]
const table = reactive({ items: [], total: 0, page: 1, limit: 10, loading: false })

const loadTable = async () => {
  table.loading = true
  const data = await deviceStore.loadData(id.value, { limit: table.limit, offset: (table.page - 1) * table.limit })
  table.loading = false
  if (data) {
    table.items = data.items
    table.total = data.total
  }
}

// --- новые измерения: обновить график и таблицу, если смотрим «до сейчас» ---

watch(() => device.value?.last_data?.timestamp, (value, old) => {
  if (!old || !value || value === old) return
  if (period.value !== 'custom') loadSeries()
  if (table.page === 1) loadTable()
})

// --- выгрузка и действия ---

const saveFile = (blob, name) => {
  const url = URL.createObjectURL(new Blob([blob]))
  const link = Object.assign(document.createElement('a'), { href: url, download: name })
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

const fileDate = (iso) => iso.slice(0, 10)

const download = async () => {
  const { start, end } = range()
  downloading.value = true
  const blob = await deviceStore.downloadData(id.value, { start, end })
  downloading.value = false
  if (!blob) return notify('Не удалось скачать файл', 'error')
  saveFile(blob, `${device.value.name}_${fileDate(start)}_${fileDate(end)}.xlsx`)
}

const downloadAll = async () => {
  const blob = await deviceStore.downloadData(id.value, {})
  if (!blob) return notify('Не удалось скачать файл', 'error')
  saveFile(blob, `${device.value.name}_все_данные.xlsx`)
}

const runConfirm = async () => {
  working.value = true
  if (confirm.value === 'delete') {
    const ok = await deviceStore.deleteDevice(id.value)
    working.value = false
    if (!ok) return notify('Не удалось удалить устройство', 'error')
    confirm.value = null
    router.push({ name: 'devices' })
    return
  }
  const ok = await deviceStore.clearData(id.value)
  working.value = false
  confirm.value = null
  if (!ok) return notify('Не удалось очистить измерения', 'error')
  notify('Измерения удалены')
  await Promise.all([deviceStore.loadDevice(id.value), loadSeries(), loadTable()])
}

// Пока страница открыта, график «до сейчас» сдвигается раз в минуту
let timer = null
onMounted(async () => {
  if (!device.value) await deviceStore.loadDevice(id.value)
  loading.value = false
  if (device.value) loadSeries()
  timer = setInterval(() => period.value !== 'custom' && loadSeries(), 60000)
})
onUnmounted(() => clearInterval(timer))
</script>
