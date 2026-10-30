import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index.js'
import { initTheme } from './theme.js'
import './assets/styles.css'
import './assets/x.css'

initTheme()
createApp(App).use(router).mount('#app')
