<template>
  <div>
    <div class="text-caption text-medium-emphasis d-flex align-center">
      <v-icon size="16" class="me-1">{{ icon }}</v-icon>{{ label }}
    </div>
    <div :class="['font-weight-bold', large ? 'text-h3' : 'text-h5', `text-${color}`]">
      {{ formatNumber(value, digits) }}<span v-if="value !== null && value !== undefined" class="text-body-1 ms-1">{{ unit }}</span>
    </div>
    <div v-if="min !== undefined" :class="['text-caption', level && level !== 'ok' ? `text-${color}` : 'text-medium-emphasis']">
      <template v-if="level && level !== 'ok'">{{ LEVEL_TEXT[level] }} · </template>норма {{ min }}–{{ max }} {{ unit }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatNumber } from '@/common/helpers/format'
import { valueLevel, LEVEL_COLORS, LEVEL_TEXT } from '@/common/deviceState'

const props = defineProps({
  label: String,
  icon: String,
  value: Number,
  unit: String,
  digits: { type: Number, default: 1 },
  min: Number,
  max: Number,
  large: Boolean,
  muted: Boolean, // устройство не на связи — значение устарело, без цветовой оценки
})

const level = computed(() => props.min === undefined ? null : valueLevel(props.value, props.min, props.max))
const color = computed(() => props.muted || !level.value ? 'medium-emphasis' : LEVEL_COLORS[level.value])
</script>
