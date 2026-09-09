/** The entrypoint: mount the app and its stylesheet. */
import { createApp } from 'vue'

import App from './App.vue'
import './styles/main.css'

createApp(App).mount('#app')
