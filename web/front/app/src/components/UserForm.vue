<template>
  <v-form ref="formRef" @submit.prevent="onSubmit" v-model="isFormValid">
    <v-text-field v-model="form.username" label="Логин" :rules="usernameRules" required clearable />
    <div v-if="isCreate" class="my-3">
      <v-text-field v-model="form.password" label="Пароль" :type="'password'" :rules="passwordRules" required
        clearable />
      <v-text-field v-model="form.repeat_password" label="Повторите пароль" :type="'password'"
        :rules="repeatPasswordRules(form.password)" required clearable />
    </div>
    <v-text-field v-model="form.first_name" label="Имя" :rules="nameRules" required clearable />
    <v-text-field v-model="form.last_name" label="Фамилия" :rules="nameRules" required clearable />
    <v-text-field v-model="form.email" label="E-Mail" :rules="emailRules" required clearable />
    <v-checkbox v-if="canEditIsAdmin" v-model="form.is_admin" label="Администратор" :true-value="true"
      :false-value="false" />
  </v-form>
</template>

<script setup>
import { ref, reactive, computed, watch } from "vue";
import rules from "@/common/helpers/rules";

import { useAuthStore } from "@/stores/auth";
const authStore = useAuthStore();

// Текущий пользователь - суперпользователь?
const canEditIsAdmin = computed(() => authStore.user?.is_superuser);

const props = defineProps({
  modelValue: { type: Object, required: false, default: () => ({}) },
  isCreate: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue"]);

// Локальное состояние формы
const form = reactive({
  first_name: "",
  last_name: "",
  email: "",
  username: "",
  password: "",
  repeat_password: "",
  is_admin: "",
});

const isFormValid = ref(true);

// Валидация полей
const nameRules = [rules.required, rules.minLength(2), rules.maxLength(30), rules.onlyLetters];
const emailRules = [rules.required, rules.email];
const usernameRules = [rules.required, rules.username, rules.minLength(3), rules.maxLength(20)];
const passwordRules = [rules.required, rules.minLength(6)];
const repeatPasswordRules = (password) => [rules.required, rules.sameAs(password, "Пароли не совпадают")];

// Синхронизация изменения внешнего modelValue с внутренним
watch(() => props.modelValue, (newVal) => {
  if (newVal) Object.assign(form, newVal);
}, { immediate: true });

// Синхронизация изменения внутренего modelValue с внешним
watch(form, () => {
  emit("update:modelValue", { ...form });
}, { deep: true });

// Отправка формы
const formRef = ref();

const onSubmit = async () => {
  const { valid } = await formRef.value?.validate();
  return valid
};

defineExpose({ submit: onSubmit });
</script>