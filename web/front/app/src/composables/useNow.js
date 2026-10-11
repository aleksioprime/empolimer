import { ref, onMounted, onUnmounted } from 'vue';

// Текущее время, обновляемое раз в interval мс: чтобы «5 мин назад» менялось само.
export function useNow(interval = 15000) {
  const now = ref(Date.now());
  let timer = null;
  onMounted(() => { timer = setInterval(() => { now.value = Date.now(); }, interval); });
  onUnmounted(() => clearInterval(timer));
  return now;
}
