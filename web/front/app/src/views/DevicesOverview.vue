<template>
  <div class="d-flex align-center flex-wrap ga-2 mb-4">
    <div>
      <h1 class="text-h5 font-weight-bold">Устройства</h1>
      <div class="text-body-2 text-medium-emphasis">
        Обновлено {{ deviceStore.lastUpdate ? timeAgo(deviceStore.lastUpdate, now) : '…' }}
      </div>
    </div>
    <v-spacer />
    <v-btn v-if="canEdit" color="primary" variant="flat" prepend-icon="mdi-plus" @click="formOpen = true">
      Добавить устройство
    </v-btn>
  </div>

  <!-- Сводка: клик — фильтр -->
  <v-row dense class="mb-2">
    <v-col v-for="tile in tiles" :key="tile.key" cols="6" md="3">
      <v-card :variant="filter === tile.key ? 'tonal' : 'elevated'" :color="filter === tile.key ? tile.color : undefined"
        @click="filter = filter === tile.key ? 'all' : tile.key">
        <v-card-text class="d-flex align-center">
          <v-avatar :color="tile.color" variant="tonal" class="me-3"><v-icon>{{ tile.icon }}</v-icon></v-avatar>
          <div>
            <div class="text-h5 font-weight-bold">{{ tile.value }}</div>
            <div class="text-caption text-medium-emphasis">{{ tile.label }}</div>
          </div>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>

  <v-text-field v-if="deviceStore.devices.length > 6" v-model="search" prepend-inner-icon="mdi-magnify"
    placeholder="Поиск по названию, описанию или месту" density="compact" variant="outlined" hide-details clearable
    class="mb-4" />

  <!-- Загрузка и пустые состояния -->
  <v-row v-if="!deviceStore.loaded && !deviceStore.error">
    <v-col v-for="n in 3" :key="n" cols="12" sm="6" lg="4"><v-skeleton-loader type="card" /></v-col>
  </v-row>

  <v-alert v-else-if="deviceStore.error && !deviceStore.devices.length" type="error" variant="tonal">
    {{ deviceStore.error }}. Повторим автоматически через несколько секунд.
  </v-alert>

  <v-card v-else-if="!deviceStore.devices.length" class="text-center pa-8">
    <v-icon size="56" color="primary" class="mb-3">mdi-access-point-network</v-icon>
    <div class="text-h6 mb-2">Устройств пока нет</div>
    <div class="text-body-2 text-medium-emphasis mx-auto" style="max-width: 520px">
      Запишите на SD-карту устройства <code>config.json</code> с адресом сервера — устройство появится здесь само
      после первого измерения. Его идентификатор — поле <code>device.id</code>.
    </div>
  </v-card>

  <div v-else-if="!visible.length" class="text-medium-emphasis text-center py-8">
    Нет устройств по выбранному фильтру
  </div>

  <v-row v-else>
    <v-col v-for="device in visible" :key="device.id" cols="12" sm="6" lg="4">
      <DeviceCard :device="device" :now="now" />
    </v-col>
  </v-row>

  <DeviceFormDialog v-model="formOpen" @saved="(d) => router.push({ name: 'device', params: { id: d.id } })" />
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import DeviceCard from '@/components/DeviceCard.vue'
import DeviceFormDialog from '@/components/DeviceFormDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { useDeviceStore } from '@/stores/device'
import { sortDevices } from '@/common/deviceState'
import { timeAgo } from '@/common/helpers/format'
import { useNow } from '@/composables/useNow'

const router = useRouter()
const authStore = useAuthStore()
const deviceStore = useDeviceStore()
const now = useNow()

const canEdit = computed(() => authStore.user?.is_admin || authStore.user?.is_superuser)
const formOpen = ref(false)
const filter = ref('all')
const search = ref('')

const tiles = computed(() => {
  const s = deviceStore.summary
  return [
    { key: 'all', label: 'Всего устройств', value: s.total, icon: 'mdi-devices', color: 'primary' },
    { key: 'online', label: 'На связи', value: s.online, icon: 'mdi-access-point', color: 'success' },
    { key: 'warning', label: 'Требуют внимания', value: s.warning, icon: 'mdi-alert', color: 'warning' },
    { key: 'offline', label: 'Нет связи', value: s.offline, icon: 'mdi-wifi-off', color: 'error' },
  ]
})

const visible = computed(() => {
  const query = (search.value || '').trim().toLowerCase()
  return sortDevices(deviceStore.devices).filter((d) => {
    if (filter.value === 'online' && !d.online) return false
    if (['warning', 'offline'].includes(filter.value) && d.state !== filter.value) return false
    if (!query) return true
    return [d.name, d.description, d.location].some((text) => text?.toLowerCase().includes(query))
  })
})
</script>
