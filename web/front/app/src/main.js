// Импортируем стили приложения
import '@/assets/style.css'
// Импортируем функцию для создания приложения Vue
import { createApp } from 'vue'
// Импортируем главный компонент App.vue
import App from "@/App.vue";

// Импорт модуля хранилища Pinia
import { createPinia } from 'pinia'

// Импорт модуля навигации Vue Router
import router from "@/router";

// Импортируем стили, компоненты и директивы Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as vuetifyComponents from 'vuetify/components'
import * as directives from 'vuetify/directives'

// Импортируем иконки Material Design Icons
import '@mdi/font/css/materialdesignicons.css'
// Импортируем алиасы и набор иконок MDI для Vuetify
import { aliases, mdi } from 'vuetify/iconsets/mdi'

// Создаём экземпляр Vuetify с нужными настройками
const vuetify = createVuetify({
	components: vuetifyComponents,
	directives,
	theme: {
		defaultTheme: 'empolimer',
		themes: {
			empolimer: {
				dark: false,
				colors: {
					background: '#f4f6f8',
					surface: '#ffffff',
					primary: '#2e7d5b',
					secondary: '#455a64',
					success: '#2e7d32',
					warning: '#ef6c00',
					error: '#c62828',
					info: '#1565c0',
				},
			},
		},
	},
	defaults: {
		VCard: { rounded: 'lg' },
		VBtn: { style: 'text-transform: none; letter-spacing: normal;' },
	},
	// Настройка иконок для приложения
	icons: {
		defaultSet: 'mdi',
		aliases,
		sets: {
			mdi,
		},
	},
})

// Создаём Vue-приложение, передавая главный компонент App
const app = createApp(App);
// Подключаем Vuetify для быстрого дизайна
app.use(vuetify);
// Подключаем Pinia для общего хранилища
app.use(createPinia())
// Подключем Vue Router для навигации
app.use(router);
// Монтируем приложение в элемент с id="app"
app.mount("#app");
