# Frontend - API de Deteccion Visual

Interfaz web para el sistema de deteccion de objetos y reconocimiento facial. Construida con Vue 3 + Vuetify 3.

## Stack tecnologico

| Tecnologia | Version | Proposito |
|---|---|---|
| Vue 3 | ^3.4 | Framework frontend con Composition API |
| Vuetify 3 | ^3.5 | Libreria de componentes Material Design |
| Vite | ^5 | Build tool y dev server |
| vue-router | ^4 | Enrutamiento SPA |
| axios | ^1 | Llamadas HTTP a la API (pendiente de integracion) |

## Inicio rapido

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
npm run build      # produccion en dist/
npm run preview    # previsualizar build
```

## Estructura del proyecto

```
frontend/
  index.html              Punto de entrada HTML
  package.json            Dependencias npm
  vite.config.js          Configuracion Vite (alias @, puerto 3000, host 0.0.0.0)
  PLAN_FRONTEND.md        Plan de trabajo original
  README.md               Este archivo
  docs/
    VISTAS.md             Documentacion de vistas
    COMPONENTES.md        Documentacion de componentes
    SERVICIOS.md          Documentacion de servicios y mocks
  src/
    main.js               Entry point: monta la app con Vuetify + Router
    App.vue               Componente raiz: barra de navegacion + router-view
    plugins/
      vuetify.js          Configuracion de Vuetify (tema oscuro/claro)
    router/
      index.js            Definicion de rutas (7 rutas)
    services/
      mock.js             Datos falsos para desarrollo sin backend real
    views/
      LoginView.vue       Pantalla de login con modo demo
      DashboardView.vue   Carga de fotogramas (drag & drop + formulario)
      SearchView.vue      Busqueda de fotogramas con filtros
      FrameDetailView.vue Detalle de fotograma con bounding boxes
      PersonsView.vue     Gestion de personas (CRUD)
      FaceRecognitionView.vue Placeholder de reconocimiento facial
    components/
      FrameCard.vue       Tarjeta de resultado para grilla de busqueda
      DetectionOverlay.vue Overlay SVG de bounding boxes
      PersonForm.vue      Formulario de registro de persona
```

## Mapa de rutas

| Ruta | Nombre | Vista | Nav |
|---|---|---|---|
| `/` | - | Redirige a `/cargar` | - |
| `/login` | Login | LoginView | No |
| `/cargar` | Cargar | DashboardView | Si |
| `/buscar` | Buscar | SearchView | Si |
| `/frame/:id` | FrameDetail | FrameDetailView | Si* |
| `/personas` | Personas | PersonsView | Si |
| `/facial` | Facial | FaceRecognitionView | Si |

\* Muestra la barra de navegacion (oculta solo en `/login`).

## Decisiones de diseno

### Dark mode por defecto
El tema oscuro es el predeterminado. El estado persiste en `localStorage('theme')` y se alterna con un boton en la AppBar.

### Navegacion con transicion
Se usa `<v-fade-transition hide-on-leave>` con `:key="$route.fullPath"` para que cada cambio de ruta reinicie completamente el componente, evitando que la transicion se congele. No se usa `<keep-alive>` para prevenir corrupcion de estado entre vistas.

### Datos mock
Todas las vistas funcionan con datos mock de `services/mock.js`. Cuando el backend este listo, se reemplazara la capa de servicios por llamadas HTTP reales via axios.

### Fuente Inter
Se carga la tipografia Inter desde Google Fonts y se aplica globalmente.

### Scroll personalizado
La barra de scroll tiene un estilo sutil semi-transparente para mantener la estetica oscura.

## Dependencias principales

```
vue, vue-router, vuetify, @mdi/font, axios
vite, @vitejs/plugin-vue, vite-plugin-vuetify
```
