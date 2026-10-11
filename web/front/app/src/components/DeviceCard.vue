<template>
  <v-card :to="{ name: 'device', params: { id: device.id } }" class="device-card h-100 d-flex flex-column"
    :style="{ borderLeftColor: `rgb(var(--v-theme-${state.color === 'grey' ? 'secondary' : state.color}))` }">
    <v-card-item>
      <v-card-title class="d-flex align-center">
        <span class="text-truncate">{{ device.name }}</span>
        <v-spacer />
        <StateChip :device="device" />
      </v-card-title>
      <v-card-subtitle>
        <v-icon size="14" class="me-1">mdi-map-marker-outline</v-icon>{{ device.location || 'место не указано' }}
      </v-card-subtitle>
    </v-card-item>

    <v-card-text class="flex-grow-1">
      <div v-if="device.last_data" class="d-flex ga-6 mb-3">
        <MetricValue label="Температура" icon="mdi-thermometer" unit="°C" :value="device.last_data.temperature"
          :min="device.thresholds.temp_min" :max="device.thresholds.temp_max" :muted="!device.online" />
        <MetricValue label="Влажность" icon="mdi-water-percent" unit="%" :value="device.last_data.humidity"
          :min="device.thresholds.hum_min" :max="device.thresholds.hum_max" :muted="!device.online" />
      </div>
      <div v-else class="text-medium-emphasis mb-3">Измерений пока нет</div>

      <div v-if="mainProblem" :class="['text-body-2 d-flex', `text-${problemColor}`]">
        <v-icon size="18" class="me-1 mt-n1">{{ PROBLEM_LEVELS[mainProblem.level].icon }}</v-icon>
        <span>{{ mainProblem.text }}<span v-if="device.problems.length > 1"> (+{{ device.problems.length - 1 }})</span></span>
      </div>
    </v-card-text>

    <v-divider />
    <v-card-actions class="text-caption text-medium-emphasis px-4">
      <v-icon size="16" class="me-1">mdi-clock-outline</v-icon>
      {{ device.last_seen ? `последний контакт ${timeAgo(device.last_seen, now)}` : 'ещё не выходило на связь' }}
      <v-spacer />
      <v-icon v-if="wifi" size="18" :title="`Wi-Fi: ${wifi.text}`">{{ wifi.icon }}</v-icon>
      <v-icon v-if="status.light" size="18" color="purple" title="Подсветка включена" class="ms-1">mdi-lightbulb-on</v-icon>
      <v-icon v-if="status.sd === false" size="18" color="warning" title="Нет SD-карты" class="ms-1">mdi-sd</v-icon>
    </v-card-actions>
  </v-card>
</template>

<script setup>
import { computed } from 'vue'
import StateChip from '@/components/StateChip.vue'
import MetricValue from '@/components/MetricValue.vue'
import { deviceState, PROBLEM_LEVELS } from '@/common/deviceState'
import { timeAgo, wifiQuality } from '@/common/helpers/format'

const props = defineProps({
  device: { type: Object, required: true },
  now: { type: Number, default: () => Date.now() },
})

const state = computed(() => deviceState(props.device))
const status = computed(() => props.device.status || {})
const wifi = computed(() => props.device.online ? wifiQuality(status.value.rssi) : null)
const mainProblem = computed(() => props.device.problems?.[0])
const problemColor = computed(() => mainProblem.value?.level === 'info' ? 'info' : PROBLEM_LEVELS[mainProblem.value?.level]?.type)
</script>

<style scoped>
.device-card {
  border-left: 4px solid;
}
</style>
