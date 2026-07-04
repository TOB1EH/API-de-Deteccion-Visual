import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/cargar'
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

export default router
