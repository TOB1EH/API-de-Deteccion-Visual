import { createRouter, createWebHistory } from 'vue-router'
import { authState, hasAnyRole, isAdmin } from '../services/auth'

/*
 * Cada ruta puede tener un meta.roles que define quienes pueden acceder:
 *   - undefined/null: cualquier rol autenticado puede acceder
 *   - ['admin']: solo admin
 *   - ['admin', 'operator']: admin y operator (viewer no)
 * Si el usuario no tiene el rol requerido, se redirige a /home.
 */
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
    path: '/monitoreo',
    name: 'Monitoreo',
    component: () => import('../views/MonitoreoView.vue'),
    meta: { roles: ['admin', 'operator'] }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue')
  },
  {
    // Cargar imagen: solo admin y operator pueden procesar imagenes
    path: '/cargar',
    name: 'Cargar',
    component: () => import('../views/DashboardView.vue'),
    meta: { roles: ['admin', 'operator'] }
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
    // Personas: admin y operator pueden ver la lista; solo admin crea/edita/elimina
    path: '/personas',
    name: 'Personas',
    component: () => import('../views/PersonsView.vue'),
    meta: { roles: ['admin', 'operator'] }
  },
  // Ruta /persona/:id - Muestra el detalle completo de una persona
  // (nombre, email, metadatos, fechas). Accesible desde PersonasView
  // haciendo click en "Ver detalle" sobre una persona seleccionada.
  {
    path: '/persona/:id',
    name: 'PersonDetail',
    component: () => import('../views/PersonDetailView.vue'),
    meta: { roles: ['admin', 'operator'] }
  },
  // Ruta /modelo/:name - Muestra informacion detallada de un modelo
  // (tamano, tipo, ruta del archivo). Accesible desde HomeView haciendo
  // click en cualquier modelo de la lista "Modelos Activos".
  {
    path: '/modelo/:name',
    name: 'ModelDetail',
    component: () => import('../views/ModelDetailView.vue')
  },
  {
    // Facial: solo admin puede acceder al reconocimiento facial
    path: '/facial',
    name: 'Facial',
    component: () => import('../views/FaceRecognitionView.vue'),
    meta: { roles: ['admin'] }
  },
  {
    // Verificacion facial como segundo factor (2FA) post-login
    path: '/face-verify',
    name: 'FaceVerify',
    component: () => import('../views/FaceVerifyView.vue'),
    meta: { roles: ['admin', 'operator'] }
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

// Guard global: protege las rutas privadas y verifica roles
router.beforeEach((to, from, next) => {
  // Saltamos verificacion en modo demo (desarrollo local sin Keycloak)
  if (authState.isDemoMode) {
    next()
    return
  }
  // Mientras Keycloak inicializa, permitimos navegar
  if (authState.loading) {
    next()
    return
  }
  // La pagina de login siempre es accesible
  if (to.path === '/login') {
    next()
    return
  }
  // Si no esta autenticado, redirigir al login
  if (!authState.authenticated) {
    next('/login')
    return
  }
  // Si la ruta tiene restriccion de roles, verificar que el usuario tenga permiso
  if (to.meta.roles && !hasAnyRole(to.meta.roles)) {
    // Si no tiene el rol requerido, redirigir al inicio
    next('/home')
    return
  }
  next()
})

export default router
