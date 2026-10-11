<template>
  <v-chip :color="state.color" :prepend-icon="state.icon" :size="size" variant="tonal" label>
    {{ state.text }}
  </v-chip>
</template>

<script setup>
import { computed } from 'vue'
import { deviceState } from '@/common/deviceState'

const props = defineProps({
  device: { type: Object, required: true },
  size: { type: String, default: 'small' },
})
const state = computed(() => deviceState(props.device))
</script>
