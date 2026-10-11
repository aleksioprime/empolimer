<template>
  <v-app>
    <router-view />
  </v-app>
</template>

<script setup>
import { watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

watch(
  () => route.name,
  () => {
    document.title = route.meta.title
      ? `${route.meta.title} · ЕмПолимер`
      : 'ЕмПолимер';
  },
  { immediate: true }
)
</script>