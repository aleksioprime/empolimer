<template>
  <v-app-bar color="primary" density="comfortable" flat>
    <v-app-bar-nav-icon class="d-md-none" @click="drawer = !drawer" />
    <v-app-bar-title>
      <router-link :to="{ name: 'devices' }" class="d-flex align-center text-white text-decoration-none">
        <v-img :src="logo" width="32" height="32" class="me-2 flex-grow-0 rounded" />
        <span class="font-weight-bold">ЕмПолимер</span>
        <span class="ms-2 text-white-50 d-none d-sm-inline">мониторинг микроклимата</span>
      </router-link>
    </v-app-bar-title>

    <div class="d-none d-md-flex">
      <v-btn v-for="item in nav" :key="item.name" :to="{ name: item.name }" variant="text" :prepend-icon="item.icon">
        {{ item.title }}
      </v-btn>
    </div>

    <v-tooltip location="bottom" :text="connectionInfo.hint">
      <template #activator="{ props }">
        <v-chip v-bind="props" class="mx-2" size="small" variant="flat" :color="connectionInfo.color">
          <v-icon start size="14">{{ connectionInfo.icon }}</v-icon>
          <span class="d-none d-sm-inline">{{ connectionInfo.text }}</span>
        </v-chip>
      </template>
    </v-tooltip>

    <v-menu>
      <template #activator="{ props }">
        <v-btn v-bind="props" icon="mdi-account-circle" />
      </template>
      <v-list density="compact">
        <v-list-item :subtitle="authStore.user?.email" :title="userName" />
        <v-divider />
        <v-list-item prepend-icon="mdi-account" title="Профиль" :to="{ name: 'profile' }" />
        <v-list-item prepend-icon="mdi-logout" title="Выйти" @click="logout" />
      </v-list>
    </v-menu>
  </v-app-bar>

  <v-navigation-drawer v-model="drawer" temporary class="d-md-none">
    <v-list nav>
      <v-list-item v-for="item in nav" :key="item.name" :to="{ name: item.name }" :prepend-icon="item.icon"
        :title="item.title" />
    </v-list>
  </v-navigation-drawer>

  <v-main>
    <v-banner v-if="deviceStore.connection === 'offline'" color="error" icon="mdi-cloud-off-outline" lines="one"
      class="text-body-2">
      Нет связи с сервером.
      <template v-if="deviceStore.lastUpdate">Показаны данные на {{ formatTime(deviceStore.lastUpdate) }} - </template>
      страница обновится сама, когда связь восстановится.
    </v-banner>
    <v-container class="py-6" style="max-width: 1400px">
      <router-view />
    </v-container>
  </v-main>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import logo from '@/assets/img/logo.png'
import { useAuthStore } from "@/stores/auth";
import { useDeviceStore } from "@/stores/device";
import { formatTime } from '@/common/helpers/format';

const router = useRouter()
const authStore = useAuthStore();
const deviceStore = useDeviceStore();
const drawer = ref(false)

const canEdit = computed(() => authStore.user?.is_admin || authStore.user?.is_superuser);
const userName = computed(() =>
  [authStore.user?.first_name, authStore.user?.last_name].filter(Boolean).join(' ') || authStore.user?.username
);

const nav = computed(() => [
  { name: 'devices', title: 'Устройства', icon: 'mdi-view-dashboard-outline' },
  ...(canEdit.value ? [{ name: 'users', title: 'Пользователи', icon: 'mdi-account-group-outline' }] : []),
]);

const CONNECTION = {
  connecting: { text: 'Подключение…', color: 'grey-lighten-1', icon: 'mdi-loading mdi-spin', hint: 'Подключение к серверу' },
  live: { text: 'Онлайн', color: 'green-lighten-1', icon: 'mdi-circle', hint: 'Данные обновляются сразу, как приходят с устройств' },
  polling: { text: 'Обновление раз в 10 с', color: 'amber-lighten-1', icon: 'mdi-sync', hint: 'Живой канал недоступен - данные запрашиваются раз в 10 секунд' },
  offline: { text: 'Нет связи', color: 'red-lighten-1', icon: 'mdi-cloud-off-outline', hint: 'Сервер недоступен - показаны последние полученные данные' },
};
const connectionInfo = computed(() => CONNECTION[deviceStore.connection] || CONNECTION.connecting);

onMounted(() => deviceStore.startLive());
onUnmounted(() => deviceStore.stopLive());

const logout = async () => {
  deviceStore.stopLive();
  await authStore.logout();
  router.push({ name: 'login' });
};
</script>
