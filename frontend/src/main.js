import { createApp } from 'vue'
import App from './App.vue'
import vuetify from './plugins/vuetify'
import router from './router'
import { authService } from './services/auth'

// La app NO se monta hasta que Keycloak termine de inicializarse
// Esto evita que se vean rutas protegidas antes de saber si hay sesion
authService.init().then(() => {
  const app = createApp(App)
  app.use(vuetify)
  app.use(router)
  app.mount('#app')
})
