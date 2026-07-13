import { createRouter, createWebHistory } from 'vue-router'
import { authState } from '../services/auth'

const routes = [
  {
    path: '/',
    redirect: '/home'
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('../views/HomeView.vue')
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
    component: () => import('../views/FrameDetailView.vue')
  },
  {
    path: '/personas',
    name: 'Personas',
    component: () => import('../views/PersonsView.vue')
  },
  {
    path: '/persona/:id',
    name: 'PersonDetail',
    component: () => import('../views/PersonDetailView.vue')
  },
  {
    path: '/modelo/:name',
    name: 'ModelDetail',
    component: () => import('../views/ModelDetailView.vue')
  },
  {
    path: '/facial',
    name: 'Facial',
    component: () => import('../views/FaceRecognitionView.vue')
  },
  {
    path: '/monitoreo',
    name: 'Monitoreo',
    component: () => import('../views/MonitoreoView.vue')
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
router.beforeEach((to, from, next) => {
  if (authState.isDemoMode) {
    next()
    return
  }
  if (authState.loading) {
    next()
    return
  }
  if (to.path === '/login') {
    next()
  } else if (!authState.authenticated) {
    next('/login')
  } else {
    next()
  }
})

export default router
