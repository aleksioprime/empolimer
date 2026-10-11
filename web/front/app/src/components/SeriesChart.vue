<template>
  <div style="position: relative; height: 260px">
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart, Tooltip, Filler, LineElement, PointElement, LinearScale,
} from 'chart.js'

Chart.register(Tooltip, Filler, LineElement, PointElement, LinearScale)

const props = defineProps({
  points: { type: Array, required: true },   // точки /series/: timestamp, <field>, <field>_min, <field>_max
  field: { type: String, required: true },   // temperature | humidity
  unit: { type: String, default: '' },
  color: { type: String, default: '#1565c0' },
  bucketSeconds: { type: Number, default: 60 },
  min: Number,                                // граница нормы
  max: Number,
  start: String,
  end: String,
})

// Если между точками пропуск больше двух отрезков - разрываем линию: устройство не присылало данные.
const withGaps = computed(() => {
  const result = []
  const gap = props.bucketSeconds * 2000
  props.points.forEach((p, i) => {
    const x = new Date(p.timestamp).getTime()
    if (i > 0 && x - result[result.length - 1].x > gap) result.push({ x: x - 1, empty: true })
    result.push({ x, p })
  })
  return result
})

const series = (key) => withGaps.value.map(({ x, p, empty }) => ({ x, y: empty ? null : p[key] }))

const chartData = computed(() => ({
  datasets: [
    { label: 'max', data: series(`${props.field}_max`), borderWidth: 0, pointRadius: 0, fill: false },
    {
      label: 'min', data: series(`${props.field}_min`), borderWidth: 0, pointRadius: 0,
      fill: '-1', backgroundColor: `${props.color}22`,
    },
    {
      label: 'Среднее', data: series(props.field), borderColor: props.color, backgroundColor: props.color,
      borderWidth: 2, pointRadius: props.points.length < 60 ? 2 : 0, tension: 0.25,
    },
    ...[props.min, props.max].filter((v) => v !== undefined && v !== null).map((value) => ({
      label: 'Граница нормы',
      data: [{ x: new Date(props.start).getTime(), y: value }, { x: new Date(props.end).getTime(), y: value }],
      borderColor: '#9e9e9e', borderDash: [6, 4], borderWidth: 1, pointRadius: 0,
    })),
  ],
}))

const formatTick = (ms) => {
  const date = new Date(ms)
  const spanHours = (new Date(props.end) - new Date(props.start)) / 3600000
  return spanHours <= 36
    ? date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
    : date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })
}

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  spanGaps: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: { display: false },
    tooltip: {
      filter: (item) => item.dataset.label === 'Среднее' && item.raw.y !== null,
      callbacks: {
        title: (items) => new Date(items[0].raw.x).toLocaleString('ru-RU', {
          day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
        }),
        label: (item) => {
          const point = withGaps.value[item.dataIndex]?.p
          const value = `${item.raw.y.toFixed(1)} ${props.unit}`
          if (!point || point.count <= 1) return value
          return `${value} (от ${point[`${props.field}_min`].toFixed(1)} до ${point[`${props.field}_max`].toFixed(1)}, измерений: ${point.count})`
        },
      },
    },
  },
  scales: {
    x: {
      type: 'linear',
      min: new Date(props.start).getTime(),
      max: new Date(props.end).getTime(),
      ticks: { callback: formatTick, maxTicksLimit: 8, maxRotation: 0 },
      grid: { display: false },
    },
    y: {
      ticks: { callback: (v) => `${v} ${props.unit}` },
      grace: '5%',
    },
  },
}))
</script>
