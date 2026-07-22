<template>
  <div class="landing-wrapper">
    <section class="hero-section">
      <v-container>
        <div class="hero-content">
          <v-avatar size="80" color="cyan-accent-3" class="mb-6" variant="tonal">
            <v-icon size="40" color="cyan-accent-3">mdi-shield-eye</v-icon>
          </v-avatar>
          <h1 class="hero-title">
            <span class="text-cyan-accent-3">API</span> Deteccion Visual
          </h1>
          <p class="hero-subtitle">
            Plataforma de Reconocimiento y Analisis de Fotogramas
          </p>
          <p class="hero-desc">
            Sistema de deteccion de objetos, reconocimiento facial y monitoreo en tiempo real.
            Procesa imagenes y video con modelos YOLO, busca fotogramas por contenido semantico
            y gestiona identidades biometricas.
          </p>
          <div class="hero-actions">
            <v-btn
              color="cyan-accent-3"
              size="x-large"
              class="text-none px-8 py-6"
              elevation="8"
              @click="router.push('/login')"
            >
              <v-icon start size="24">mdi-login</v-icon>
              Iniciar Sesion
            </v-btn>
            <v-btn
              variant="outlined"
              color="cyan-accent-3"
              size="x-large"
              class="text-none px-8 py-6 ml-4"
              @click="scrollTo('descargar')"
            >
              <v-icon start size="24">mdi-download</v-icon>
              Descargar Script
            </v-btn>
          </div>
        </div>
      </v-container>
      <div class="hero-wave">
        <svg viewBox="0 0 1440 100" preserveAspectRatio="none">
          <path fill="rgba(0, 229, 255, 0.05)" d="M0,50 C360,100 1080,0 1440,50 L1440,100 L0,100 Z" />
        </svg>
      </div>
    </section>

    <section class="how-section">
      <v-container>
        <h2 class="section-title">Como funciona</h2>
        <p class="section-desc">Tres pasos para empezar a usar el sistema</p>
        <v-row class="mt-6">
          <v-col cols="12" md="4">
            <v-card variant="outlined" class="step-card pa-6 text-center" :style="{ borderColor: 'rgba(0, 229, 255, 0.2)' }">
              <v-avatar size="64" color="cyan-darken-4" variant="tonal" class="mb-4">
                <span class="text-h5 font-weight-bold text-cyan-accent-3">1</span>
              </v-avatar>
              <h3 class="text-h6 font-weight-bold mb-2">Descarga el Script</h3>
              <p class="text-body-2 text-grey-lighten-1">
                Descarga <code>setup_cliente.py</code> y ejecutalo en tu computadora.
                El script instala automaticamente YOLO y DeepFace.
              </p>
            </v-card>
          </v-col>
          <v-col cols="12" md="4">
            <v-card variant="outlined" class="step-card pa-6 text-center" :style="{ borderColor: 'rgba(0, 229, 255, 0.2)' }">
              <v-avatar size="64" color="cyan-darken-4" variant="tonal" class="mb-4">
                <span class="text-h5 font-weight-bold text-cyan-accent-3">2</span>
              </v-avatar>
              <h3 class="text-h6 font-weight-bold mb-2">Ejecuta el Nodo Local</h3>
              <p class="text-body-2 text-grey-lighten-1">
                Corre <code>python3 setup_cliente.py install</code> para iniciar
                el servidor de reconocimiento facial en tu PC (puerto 8001).
              </p>
            </v-card>
          </v-col>
          <v-col cols="12" md="4">
            <v-card variant="outlined" class="step-card pa-6 text-center" :style="{ borderColor: 'rgba(0, 229, 255, 0.2)' }">
              <v-avatar size="64" color="cyan-darken-4" variant="tonal" class="mb-4">
                <span class="text-h5 font-weight-bold text-cyan-accent-3">3</span>
              </v-avatar>
              <h3 class="text-h6 font-weight-bold mb-2">Inicia Sesion y Usa</h3>
              <p class="text-body-2 text-grey-lighten-1">
                Inicia sesion con tu rostro o con Keycloak. Accede a deteccion,
                busqueda, monitoreo y administracion de personas.
              </p>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </section>

    <section class="node-section">
      <v-container>
        <h2 class="section-title">Estado del Nodo Local</h2>
        <p class="section-desc">
          El nodo local de reconocimiento facial debe estar corriendo en tu PC para usar
          autenticacion biometrica. El indicador en la esquina superior derecha muestra su estado.
        </p>
        <v-row class="mt-6" justify="center">
          <v-col cols="12" md="5">
            <v-card variant="outlined" class="pa-4 text-center" :style="{ borderColor: 'rgba(255, 82, 82, 0.3)' }">
              <v-img
                src="/img/nodo-desconectado.png"
                max-height="120"
                contain
                class="mb-3"
                style="border-radius: 8px;"
              />
              <h3 class="text-h6 font-weight-bold mb-1">Nodo Desconectado</h3>
              <p class="text-body-2 text-grey-lighten-1">
                El servidor local no esta corriendo. Descarga y ejecuta el script
                para habilitar reconocimiento facial.
              </p>
            </v-card>
          </v-col>
          <v-col cols="12" md="5">
            <v-card variant="outlined" class="pa-4 text-center" :style="{ borderColor: 'rgba(0, 200, 83, 0.3)' }">
              <v-img
                src="/img/nodo-conectado.png"
                max-height="120"
                contain
                class="mb-3"
                style="border-radius: 8px;"
              />
              <h3 class="text-h6 font-weight-bold mb-1">Nodo Conectado</h3>
              <p class="text-body-2 text-grey-lighten-1">
                El servidor local esta activo. Puedes usar inicio de sesion facial
                y registro biometrico.
              </p>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </section>

    <section id="descargar" class="download-section">
      <v-container>
        <v-card variant="outlined" class="download-card pa-8 text-center" :style="{ borderColor: 'rgba(0, 229, 255, 0.2)' }">
          <v-icon size="56" color="cyan-accent-3" class="mb-3">mdi-download-circle</v-icon>
          <h2 class="text-h4 font-weight-bold mb-2">Descargar Script de Instalacion</h2>
          <p class="text-body-1 text-grey-lighten-1 mb-6 max-width-text">
            Descarga <code>setup_cliente.py</code> para configurar el nodo de reconocimiento facial
            en tu computadora. Incluye YOLO para deteccion y DeepFace (Facenet + MTCNN) para
            reconocimiento facial.
          </p>
          <v-btn
            color="cyan-accent-3"
            size="x-large"
            class="text-none px-10 py-6"
            elevation="8"
            href="/setup_cliente.py"
            download
          >
            <v-icon start size="24">mdi-download</v-icon>
            Descargar setup_cliente.py
          </v-btn>
          <div class="mt-4">
            <v-chip variant="text" color="grey" size="small">
              <v-icon start size="14">mdi-console</v-icon>
              Luego ejecuta: python3 setup_cliente.py install
            </v-chip>
          </div>
        </v-card>
      </v-container>
    </section>

    <section class="features-section">
      <v-container>
        <h2 class="section-title">Funcionalidades</h2>
        <v-row class="mt-4">
          <v-col cols="12" sm="6" md="3" v-for="feat in features" :key="feat.title">
            <v-card variant="outlined" class="feature-card pa-4 text-center" :style="{ borderColor: 'rgba(0, 229, 255, 0.12)' }">
              <v-icon size="36" :color="feat.color" class="mb-3">{{ feat.icon }}</v-icon>
              <h3 class="text-subtitle-1 font-weight-bold">{{ feat.title }}</h3>
              <p class="text-caption text-grey-lighten-1">{{ feat.desc }}</p>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </section>

    <section class="tech-section">
      <v-container>
        <h2 class="section-title">Stack Tecnologico</h2>
        <v-row class="mt-4" justify="center">
          <v-col cols="6" sm="4" md="2" v-for="tech in techStack" :key="tech.name">
            <v-card variant="outlined" class="tech-card pa-3 text-center" :style="{ borderColor: 'rgba(0, 229, 255, 0.1)' }">
              <v-icon size="28" :color="tech.color" class="mb-2">{{ tech.icon }}</v-icon>
              <div class="text-caption font-weight-medium">{{ tech.name }}</div>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </section>

    <footer class="footer-section">
      <v-container>
        <v-divider class="mb-4" />
        <div class="d-flex flex-wrap align-center justify-center ga-4">
          <span class="text-caption text-grey-darken-1">
            API Deteccion Visual &mdash; Trabajo Integrador SOA 2026
          </span>
          <v-btn variant="text" size="small" color="grey" href="https://bfts2026.mooo.com/api/docs" target="_blank">
            <v-icon start size="14">mdi-api</v-icon>
            API Docs
          </v-btn>
          <v-btn variant="text" size="small" color="grey" href="https://github.com/TOB1EH/API-de-Deteccion-Visual" target="_blank">
            <v-icon start size="14">mdi-github</v-icon>
            GitHub
          </v-btn>
        </div>
      </v-container>
    </footer>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const features = [
  { title: 'Deteccion de Objetos', icon: 'mdi-target', color: 'cyan-accent-3', desc: 'Deteccion en tiempo real con modelos YOLO sobre imagenes y videos.' },
  { title: 'Reconocimiento Facial', icon: 'mdi-face-recognition', color: 'green-accent-3', desc: 'Identificacion biometrica con DeepFace (Facenet + MTCNN).' },
  { title: 'Busqueda Visual', icon: 'mdi-magnify', color: 'indigo-accent-3', desc: 'Busqueda de fotogramas por objetos detectados, fechas y filtros.' },
  { title: 'Monitoreo', icon: 'mdi-monitor-dashboard', color: 'amber', desc: 'Panel NOC con metricas, alertas y dashboards en tiempo real.' },
  { title: 'Autenticacion OAuth2', icon: 'mdi-shield-key', color: 'purple-accent-3', desc: 'Login con Keycloak, Google SSO y autenticacion biometrica facial.' },
  { title: 'Roles y Permisos', icon: 'mdi-account-group', color: 'orange-accent-3', desc: 'Control de acceso por roles: admin, operator y viewer.' },
  { title: 'Almacenamiento Escalable', icon: 'mdi-database', color: 'teal-accent-3', desc: 'PostgreSQL + pgvector + SeaweedFS para objetos multimedia.' },
  { title: 'API RESTful', icon: 'mdi-api', color: 'pink-accent-3', desc: 'Documentacion Swagger interactive en /api/docs.' },
]

const techStack = [
  { name: 'FastAPI', icon: 'mdi-language-python', color: 'cyan-accent-3' },
  { name: 'Vue 3', icon: 'mdi-vuejs', color: 'green-accent-3' },
  { name: 'PostgreSQL', icon: 'mdi-database', color: 'blue-accent-3' },
  { name: 'Keycloak', icon: 'mdi-shield-key', color: 'orange-accent-3' },
  { name: 'YOLO', icon: 'mdi-brain', color: 'red-accent-3' },
  { name: 'SeaweedFS', icon: 'mdi-server', color: 'teal-accent-3' },
  { name: 'Nginx', icon: 'mdi-nginx', color: 'green-darken-2' },
  { name: 'Docker', icon: 'mdi-docker', color: 'blue-darken-2' },
]

function scrollTo(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
}
</script>

<style scoped>
.landing-wrapper {
  min-height: 100vh;
}

.hero-section {
  position: relative;
  min-height: 85vh;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  background: linear-gradient(135deg, #0a0e1a 0%, #0f1a2e 40%, #162240 100%);
  overflow: hidden;
}

.hero-content {
  max-width: 720px;
  margin: 0 auto;
  padding: 2rem;
}

.hero-title {
  font-size: 3.2rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  margin-bottom: 1rem;
}

.hero-subtitle {
  font-size: 1.3rem;
  color: rgba(255, 255, 255, 0.7);
  font-weight: 500;
  margin-bottom: 1rem;
}

.hero-desc {
  font-size: 1.05rem;
  color: rgba(255, 255, 255, 0.55);
  line-height: 1.7;
  margin-bottom: 2.5rem;
}

.hero-actions {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.hero-wave {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  line-height: 0;
}

.how-section {
  padding: 5rem 0;
  background: rgba(10, 14, 26, 0.6);
}

.node-section {
  padding: 5rem 0;
  background: rgba(15, 26, 46, 0.5);
}

.download-section {
  padding: 5rem 0;
  background: rgba(10, 14, 26, 0.6);
}

.features-section {
  padding: 5rem 0;
  background: rgba(15, 26, 46, 0.3);
}

.tech-section {
  padding: 4rem 0;
  background: rgba(10, 14, 26, 0.4);
}

.footer-section {
  padding: 2rem 0;
  background: rgba(10, 14, 26, 0.8);
}

.section-title {
  text-align: center;
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.section-desc {
  text-align: center;
  color: rgba(255, 255, 255, 0.55);
  font-size: 1rem;
  max-width: 600px;
  margin: 0 auto;
}

.max-width-text {
  max-width: 560px;
  margin-left: auto;
  margin-right: auto;
}

.step-card {
  height: 100%;
  transition: all 0.25s ease;
  background: rgba(18, 18, 18, 0.7) !important;
}

.step-card:hover {
  transform: translateY(-4px);
  border-color: rgba(0, 229, 255, 0.4) !important;
  box-shadow: 0 8px 30px rgba(0, 229, 255, 0.08);
}

.download-card {
  max-width: 700px;
  margin: 0 auto;
  background: rgba(18, 18, 18, 0.7) !important;
}

.feature-card {
  height: 100%;
  transition: all 0.2s ease;
  background: rgba(18, 18, 18, 0.5) !important;
}

.feature-card:hover {
  border-color: rgba(0, 229, 255, 0.3) !important;
  transform: translateY(-2px);
}

.tech-card {
  background: rgba(18, 18, 18, 0.4) !important;
  transition: all 0.2s ease;
}

.tech-card:hover {
  border-color: rgba(0, 229, 255, 0.3) !important;
}

code {
  background: rgba(0, 229, 255, 0.1);
  color: #00e5ff;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}
</style>
