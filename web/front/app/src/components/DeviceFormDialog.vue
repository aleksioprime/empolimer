<template>
  <v-dialog :model-value="modelValue" max-width="520" persistent @update:model-value="emit('update:modelValue', $event)">
    <v-card :title="device ? 'Настройки устройства' : 'Новое устройство'">
      <v-card-text>
        <v-form ref="formRef" @submit.prevent="save">
          <v-text-field v-model="form.name" label="Идентификатор" :rules="nameRules" prepend-inner-icon="mdi-identifier"
            hint="Как device.id в config.json на SD-карте устройства" persistent-hint class="mb-3" />
          <v-text-field v-model="form.description" label="Описание" prepend-inner-icon="mdi-text" />
          <v-text-field v-model="form.location" label="Где установлено" prepend-inner-icon="mdi-map-marker-outline" />

          <div class="text-subtitle-2 mt-2">Норма</div>
          <div class="text-caption text-medium-emphasis mb-2">
            Пустые поля — значения по умолчанию сервера. Вне нормы устройство помечается «Требует внимания».
          </div>
          <v-row dense>
            <v-col cols="6"><v-text-field v-model="form.temp_min" label="Температура от, °C" type="number" :placeholder="placeholder('temp_min')" /></v-col>
            <v-col cols="6"><v-text-field v-model="form.temp_max" label="до, °C" type="number" :placeholder="placeholder('temp_max')" /></v-col>
            <v-col cols="6"><v-text-field v-model="form.hum_min" label="Влажность от, %" type="number" :placeholder="placeholder('hum_min')" /></v-col>
            <v-col cols="6"><v-text-field v-model="form.hum_max" label="до, %" type="number" :placeholder="placeholder('hum_max')" /></v-col>
          </v-row>
          <v-alert v-if="error" type="error" variant="tonal" density="compact">{{ error }}</v-alert>
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="emit('update:modelValue', false)">Отмена</v-btn>
        <v-btn color="primary" variant="flat" :loading="saving" @click="save">Сохранить</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { useDeviceStore } from '@/stores/device'

const props = defineProps({
  modelValue: Boolean,
  device: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'saved'])
const deviceStore = useDeviceStore()

const FIELDS = ['temp_min', 'temp_max', 'hum_min', 'hum_max']
const formRef = ref(null)
const saving = ref(false)
const error = ref('')
const form = reactive({ name: '', description: '', location: '', temp_min: '', temp_max: '', hum_min: '', hum_max: '' })

const nameRules = [
  v => !!v || 'Обязательное поле',
  v => /^[A-Za-z0-9_-]{1,32}$/.test(v) || 'Латиница, цифры, - и _ (до 32 символов)',
]

// Подсказка — текущая норма устройства (своя или по умолчанию)
const placeholder = (key) => props.device?.thresholds?.[key] ?? ''

watch(() => props.modelValue, (open) => {
  if (!open) return
  error.value = ''
  const d = props.device
  form.name = d?.name || ''
  form.description = d?.description || ''
  form.location = d?.location || ''
  // Свои границы показываем, только если они заданы для устройства
  FIELDS.forEach((key) => { form[key] = d?.custom_thresholds ? d.thresholds[key] : '' })
})

const number = (v) => (v === '' || v === null || v === undefined ? null : Number(v))

const save = async () => {
  const { valid } = await formRef.value.validate()
  if (!valid) return
  const body = {
    name: form.name,
    description: form.description || null,
    location: form.location || null,
    ...Object.fromEntries(FIELDS.map((key) => [key, number(form[key])])),
  }
  saving.value = true
  const res = props.device
    ? await deviceStore.updateDevice(props.device.id, body)
    : await deviceStore.createDevice(body)
  saving.value = false
  if (res.__state !== 'success') {
    error.value = res.data?.message || 'Не удалось сохранить'
    return
  }
  emit('saved', res.data)
  emit('update:modelValue', false)
}
</script>
