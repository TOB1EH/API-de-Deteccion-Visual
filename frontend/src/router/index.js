import { createRouter, createWebHistory } from 'vue-router'
import { authState } from '../services/auth'

const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue')
  },
  {
    path: '/cargar',
    name: 'Cargar',
    component: () => import('../views/DashboardView.vue')
  },
  {
    path: '/buscar',
    name: 'Buscar',
    component: () => import('../views/SearchView.vue')
  },
  {
    path: '/frame/:id',
    name: 'FrameDetail',
    component: () => import('../views/FrameDetailView.vue'),
    props: true
  },
  {
    path: '/personas',
    name: 'Personas',
    component: () => import('../views/PersonsView.vue')
  },
  {
    path: '/facial',
    name: 'Facial',
    component: () => import('../views/FaceRecognitionView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

// Guard global: protege las rutas privadas
// Si el usuario no esta autenticado via Keycloak, redirige a /login
// La ruta /login esta siempre abierta
router.beforeEach((to, from, next) => {
  if (to.path === '/login' || to.path === '/') {
    next()
  } else if (!authState.authenticated) {
    next('/login')
  } else {
    next()
  }
})

export default router
