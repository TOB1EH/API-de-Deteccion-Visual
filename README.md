# API de Deteccion Visual

Plataforma integral de deteccion de objetos en imagenes (YOLO) y reconocimiento facial (DeepFace) con autenticacion OAuth2, monitoreo Grafana y frontend web. Proyecto integrador de Sistemas Operativos Avanzados (SOA) 2026.

---

## Indice

- [Arquitectura](#arquitectura)
- [Funcionalidades](#funcionalidades)
- [Stack tecnologico](#stack-tecnologico)
- [Flujo de datos](#flujo-de-datos)
- [Autenticacion y autorizacion](#autenticacion-y-autorizacion)
- [Frontend web](#frontend-web)
- [CLI de linea de comandos](#cli-de-linea-de-comandos)
- [Endpoints de la API](#endpoints-de-la-api)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Instalacion y uso](#instalacion-y-uso)
- [Despliegue](#despliegue)
- [Acceso remoto](#acceso-remoto)
- [Variables de entorno](#variables-de-entorno)

---

## Arquitectura

```
+---------------------------------------------------+
|                    CLIENTE                        |
|                                                   |
|  +---------------------------+   +--------------+ |
|  | Frontend Web (Vue 3)      |   | CLI Python   | |
|  | - Landing / Login / Auth  |   | setup_cliente| |
|  | - Dashboard / Buscar      |   | .py          | |
|  | - Personas / Facial       |   +--------------+ |
|  | - NOC Monitoreo (Grafana) |         |          |
|  +---------------------------+         |          |
|        |  HTTPS                         | HTTP    |
|        |  (Keycloak OAuth2)             |         |
|        v                                v         |
+---------------------------------------------------+
|               VM REMOTA (bfts2026.mooo.com)       |
|                                                   |
|  +-------------------------------------------+    |
|  | Nginx (proxy reverso HTTPS)               |    |
|  | +-> /api/ -> FastAPI :8000               |    |
|  | +-> /auth/ -> Keycloak :8080             |    |
|  | +-> /grafana/ -> Grafana :3000           |    |
|  | +-> /pgadmin/ -> pgAdmin                 |    |
|  | +-> /seaweed/ -> SeaweedFS :8080         |    |
|  +-------------------------------------------+    |
|                                                   |
|  +--------+  +----------+  +------------------+   |
|  |FastAPI |  | Keycloak |  | PostgreSQL 16    |   |
|  | :8000  |  | :8080    |  | + pgvector       |   |
|  +--------+  +----------+  +------------------+   |
|  +----------+  +---------+  +------------------+   |
|  |SeaweedFS |  | Grafana |  | InfluxDB         |   |
|  |Master+Vol|  | +Telegraf|  | :8086            |   |
|  +----------+  +---------+  +------------------+   |
+---------------------------------------------------+

+---------------------------------------------------+
|              NODO LOCAL (PC del usuario)           |
|                                                   |
|  inference-server (Docker)                        |
|  - YOLO (Ultralytics)                             |
|  - DeepFace (MTCNN + Facenet)                    |
|  - Puerto 8001                                    |
+---------------------------------------------------+
```

---

## Funcionalidades

### Deteccion de objetos
Inferencia local con modelos YOLO (ultralytics) sobre imagenes capturadas por el usuario. Las detecciones se persisten en el servidor remoto con bounding boxes, clases y niveles de confianza.

### Reconocimiento facial
Extraccion de embeddings faciales (DeepFace + Facenet) y busqueda por similitud coseno sobre vectores almacenados en PostgreSQL + pgvector. Soporta reconocimiento en tiempo real desde el nodo local.

### Busqueda visual
Filtrado de fotogramas por clases detectadas, rango de fechas, coordenadas geograficas (latitud/longitud opcionales) y otros metadatos.

### Autenticacion OAuth2
Integracion con Keycloak para inicio de sesion unificado con soporte de SSO e Identity Providers externos (Google, GitHub). Roles granularizados: admin, operator, viewer.

### Autenticacion biometrica (2FA)
Login facial como segundo factor de autenticacion. El usuario se registra con sus datos biometricos y puede autenticarse mediante reconocimiento facial desde la PC local.

### Frontend web SPA
Interfaz de usuario desarrollada en Vue 3 + Vuetify con panel de control, busqueda visual, gestion de personas, detalle de fotogramas, reconocimiento facial y mas.

### Monitoreo NOC
Centro de operaciones con dashboards Grafana embebidos que exponen metricas de infraestructura (CPU, RAM, red), rendimiento de base de datos y tiempos de inferencia del modelo YOLO.

### API RESTful documentada
Documentacion interactiva via Swagger UI y ReDoc. Autenticacion via JWT (Keycloak RS256 o token facial HS256). Control de acceso por roles en cada endpoint.

---

## Stack tecnologico

| Componente | Tecnologia | Version |
|---|---|---|
| Backend API | Python FastAPI | 3.12 / 0.115 |
| Frontend web | Vue 3 + Vuetify 3 + Vite | 3.5 / 3.7 |
| Autenticacion | Keycloak (OAuth2 / OpenID Connect) | 26.6 |
| Base de datos | PostgreSQL + pgvector | 16 |
| Deteccion de objetos | Ultralytics YOLO | 11n/s/m/l/x |
| Reconocimiento facial | DeepFace (MTCNN + Facenet) | 0.0.79 |
| Almacenamiento de objetos | SeaweedFS | latest |
| Proxy reverso | Nginx + Let's Encrypt | 1.31.1 |
| Monitoreo | Telegraf + InfluxDB + Grafana | 1.38 / 2.8 / latest |
| Contenedores | Docker Compose | 2.x |
| Cliente CLI | Python | 3.8+ |

---

## Flujo de datos

### Deteccion de objetos
1. El usuario captura una imagen en su PC o la sube desde el frontend web.
2. La imagen se envia al inference-server local (Docker con YOLO) en `localhost:8001`.
3. El inference-server devuelve las detecciones (bounding boxes, clases, confianzas).
4. La imagen y las detecciones se envian via HTTPS a la API remota (`POST /api/detections`).
5. La API persiste la imagen en SeaweedFS y los metadatos en PostgreSQL.
6. El usuario puede consultar, buscar y descargar los fotogramas desde el frontend o el CLI.

### Reconocimiento facial
1. **Registro**: Se extrae un embedding facial de una foto de referencia y se asocia a una persona.
2. **Busqueda**: Una foto de prueba se procesa localmente, se extrae su embedding y se compara contra la base de vectores (pgvector) mediante similitud coseno.
3. **Autenticacion biometrica**: El reconocimiento facial local verifica la identidad, luego la API emite un token JWT facial.

### Monitoreo
1. Telegraf recolecta metricas de CPU, RAM, disco, red y contenedores Docker.
2. Las metricas se almacenan en InfluxDB.
3. Grafana consulta InfluxDB y expone dashboards en `/grafana/`.
4. El frontend embebe los dashboards en modo kiosko para visualizacion NOC.

---

## Autenticacion y autorizacion

### Keycloak OAuth2 (primario)
- Proveedor OpenID Connect con flujo de redireccion.
- Tokens JWT firmados con RS256, validados via JWKS.
- Realm: `api-detection`. Client: `api-backend`.
- Identity Providers externos: Google SSO configurado.

### Token facial (secundario)
- Generado por `POST /api/auth/login/facial` tras verificacion biometrica local.
- JWT firmado con HS256, incluye roles del usuario extraidos de Keycloak.
- Almacenado en `localStorage` como respaldo si Keycloak no esta disponible.

### Roles y permisos

| Rol | Descripcion |
|---|---|
| `admin` | Acceso completo: creacion, edicion, eliminacion de recursos, monitoreo NOC, reconocimiento facial |
| `operator` | Operaciones de deteccion y consulta, sin eliminacion ni monitoreo NOC |
| `viewer` | Solo lectura: visualizar detecciones, fotogramas y personas |

### Matriz por endpoint

| Endpoint | Admin | Operator | Viewer |
|---|---|---|---|
| GET /api/models | Si | Si | Si |
| POST /api/detections | Si | Si | No |
| GET /api/frames | Si | Si | Si |
| GET /api/frames/search | Si | Si | Si |
| GET /api/persons | Si | Si | Si |
| POST /api/persons | Si | No | No |
| PUT/DELETE /api/persons/{id} | Si | No | No |
| POST /api/persons/{id}/embeddings | Si | Si | No |
| POST /api/face-recognition | Si | Si | No |
| Frontend /monitoreo | Si | No | No |

---

## Frontend web

Interfaz SPA desarrollada con Vue 3, Vuetify 3 y Vite.

| Ruta | Vista | Acceso |
|---|---|---|
| `/` | Landing page informativa con descarga del CLI | Publico |
| `/login` | Inicio de sesion Keycloak OAuth2 | Publico |
| `/login-facial` | Autenticacion biometrica facial | Publico |
| `/home` | Dashboard principal con resumen de actividad | Autenticado |
| `/cargar` | Subir imagen para deteccion | Autenticado |
| `/buscar` | Busqueda de fotogramas por filtros | Autenticado |
| `/frame/:id` | Detalle de un fotograma | Autenticado |
| `/personas` | Gestion de personas registradas | Admin / Operator |
| `/persona/:id` | Detalle de persona con embeddings | Admin / Operator |
| `/facial` | Reconocimiento facial por foto | Admin |
| `/face-verify` | Verificacion facial 2FA | Admin / Operator |
| `/modelo/:name` | Detalle de modelo YOLO | Autenticado |
| `/monitoreo` | Dashboards Grafana embebidos (NOC) | Admin |

---

## CLI de linea de comandos

El script `setup_cliente.py` permite interactuar con la plataforma desde la terminal.

```bash
# Descargar e instalar el nodo local
curl -O https://bfts2026.mooo.com/setup_cliente.py
python3 setup_cliente.py install

# Iniciar sesion (Keycloak o facial)
python3 setup_cliente.py faces login

# Inferir una imagen localmente y persistir resultados
python3 setup_cliente.py infer ~/foto.jpg --model yolo11n.pt [--lat -34.60 --lon -58.38]

# Listar modelos disponibles en el servidor
python3 setup_cliente.py models

# Consultar fotogramas
python3 setup_cliente.py frames list --clases person --limit 10
python3 setup_cliente.py frames get <frame_id> --thumbnail
python3 setup_cliente.py frames annotate <frame_id>

# Gestionar personas
python3 setup_cliente.py persons list
python3 setup_cliente.py persons create "Juan" "Perez"

# Registrar embedding facial
python3 setup_cliente.py faces embed <person_id> ~/foto_referencia.jpg

# Reconocer rostro
python3 setup_cliente.py faces recognize ~/foto_test.jpg --threshold 0.5
```

---

## Endpoints de la API

Base URL: `https://bfts2026.mooo.com/api`

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/` | Bienvenida e instrucciones de instalacion |
| GET | `/health` | Health check del servicio |
| GET | `/api/docs` | Documentacion Swagger UI |
| GET | `/setup_cliente.py` | Descarga del CLI |
| GET | `/api/models` | Lista modelos YOLO disponibles |
| GET | `/api/models/{name}/download` | Descarga un modelo YOLO |
| POST | `/api/detections` | Ejecuta deteccion y persiste resultados |
| GET | `/api/frames/{id}` | Descarga imagen de un fotograma (?thumbnail=true) |
| GET | `/api/frames/search` | Busca fotogramas con filtros |
| POST | `/api/persons` | Crea una persona |
| GET | `/api/persons` | Lista personas |
| GET | `/api/persons/{id}` | Obtiene una persona |
| PUT | `/api/persons/{id}` | Actualiza una persona |
| DELETE | `/api/persons/{id}` | Elimina una persona |
| POST | `/api/persons/{id}/embeddings` | Almacena embedding facial |
| POST | `/api/face-recognition` | Reconoce rostro por similitud coseno |
| POST | `/api/auth/login/facial` | Login biometrico (devuelve JWT) |
| POST | `/api/auth/register` | Registro de persona con foto facial |
| GET | `/api/metrics` | Metricas Prometheus |

---

## Estructura del repositorio

```
.
├── src/api/                    # Backend FastAPI
│   ├── main.py                 # Orquestador principal
│   ├── routes/                 # Endpoints (models, detections, frames, persons, ...)
│   ├── schemas/                # Modelos Pydantic
│   └── services/               # Conexion BD, SeaweedFS, auth
├── frontend/                   # Frontend Vue 3 + Vuetify
│   ├── src/
│   │   ├── views/              # Componentes de cada ruta
│   │   ├── components/         # Componentes reutilizables
│   │   ├── services/           # Servicio de autenticacion (Keycloak)
│   │   └── router/             # Definicion de rutas y guard
│   ├── nginx.conf              # Configuracion SPA para Docker
│   └── Dockerfile              # Build de imagen frontend
├── client/
│   ├── setup_cliente.py        # CLI de linea de comandos
│   └── README.md               # Documentacion del CLI
├── inference-server/           # Servidor YOLO + DeepFace (Docker)
├── docker/
│   ├── nginx.conf              # Configuracion Nginx produccion (HTTPS)
│   ├── nginx.local.conf        # Configuracion Nginx desarrollo (HTTP)
│   └── init-db.sql             # Inicializacion de BD (pgvector)
├── docs/
│   ├── API_REFERENCE.md        # Documentacion detallada de la API
│   ├── FASE1_INFRAESTRUCTURA.md
│   ├── FASE2_SEGUNDA_ENTREGA.md
│   ├── DISTRIBUCION_TRABAJO.md
│   ├── RESUMEN_FINAL.md
│   └── PRIMERA_ENTREGA.md
├── docker-compose.yml          # Despliegue remoto (HTTPS + SSL)
├── docker-compose.local.yml    # Despliegue local (HTTP)
├── Dockerfile.api              # Build de la API
├── AGENTS.md                   # Estado del proyecto y directivas
├── .env.example                # Plantilla de variables de entorno
└── models/                     # Pesos de modelos YOLO
```

---

## Instalacion y uso

### Usar la plataforma web

La plataforma web esta disponible en `https://bfts2026.mooo.com`. Simplemente inicie sesion con su cuenta de Keycloak o mediante reconocimiento facial.

Para usar el nodo de inferencia local (recomendado para deteccion y facial):

```bash
curl -O https://bfts2026.mooo.com/setup_cliente.py
python3 setup_cliente.py install
```

### Despliegue local (desarrollo)

```bash
git clone https://github.com/TOB1EH/API-de-Deteccion-Visual.git
cd API-de-Deteccion-Visual

# Configurar variables de entorno
cp .env.example .env
# Editar .env con sus credenciales locales

# Iniciar todos los servicios
docker compose -f docker-compose.local.yml up -d

# Servicios disponibles:
# - Frontend:  http://localhost:3000
# - API:       http://localhost:8000
# - Keycloak:  http://localhost:8081
# - Grafana:   http://localhost:3001
# - pgAdmin:   http://localhost/pgadmin/
```

### Despliegue remoto (produccion)

```bash
git clone https://github.com/TOB1EH/API-de-Deteccion-Visual.git
cd API-de-Deteccion-Visual

# Configurar certificados SSL y variables de entorno
cp .env.example .env
# Configurar credenciales de produccion

# Iniciar servicios
docker compose up -d
```

---

## Despliegue

### Local (desarrollo)

```bash
docker compose -f docker-compose.local.yml up -d --build
```

| Servicio | URL |
|---|---|
| Frontend web | `http://localhost:3000` |
| API (FastAPI) | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/api/docs` |
| Keycloak | `http://localhost:8081` |
| Grafana | `http://localhost:3001` |
| pgAdmin | `http://localhost/pgadmin/` |

### Remoto (produccion)

```bash
docker compose up -d --build
```

Requiere certificados SSL en `/etc/letsencrypt/live/bfts2026.mooo.com/` y dominio configurado.

| Servicio | URL |
|---|---|
| Frontend web | `https://bfts2026.mooo.com` |
| API (FastAPI) | `https://bfts2026.mooo.com/api/` |
| Swagger UI | `https://bfts2026.mooo.com/api/docs` |
| Keycloak | `https://bfts2026.mooo.com/auth/` |
| Grafana | `https://bfts2026.mooo.com/grafana/` |
| pgAdmin | `https://bfts2026.mooo.com/pgadmin/` |
| SeaweedFS | `https://bfts2026.mooo.com/seaweed/` |

---

## Acceso remoto

| Servicio | URL |
|---|---|
| Landing page / Frontend | `https://bfts2026.mooo.com` |
| API Health | `https://bfts2026.mooo.com/health` |
| Swagger UI | `https://bfts2026.mooo.com/api/docs` |
| Keycloak Admin Console | `https://bfts2026.mooo.com/auth/admin/` |
| pgAdmin | `https://bfts2026.mooo.com/pgadmin/` |
| Grafana | `https://bfts2026.mooo.com/grafana/` |
| SeaweedFS | `https://bfts2026.mooo.com/seaweed/` |
| Script CLI | `https://bfts2026.mooo.com/setup_cliente.py` |

---

## Variables de entorno

### Base de datos
| Variable | Default | Descripcion |
|---|---|---|
| `POSTGRES_USER` | `detections_user` | Usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | - | Contrasena de PostgreSQL |
| `POSTGRES_DB` | `detections_db` | Nombre de la base de datos |
| `DB_PORT` | `5433` | Puerto expuesto de PostgreSQL |

### Autenticacion (Keycloak)
| Variable | Default | Descripcion |
|---|---|---|
| `KEYCLOAK_ADMIN` | `admin` | Usuario admin de Keycloak |
| `KEYCLOAK_ADMIN_PASSWORD` | - | Contrasena admin de Keycloak |
| `KEYCLOAK_REALM` | `api-detection` | Realm de Keycloak |
| `KEYCLOAK_INTERNAL_URL` | `http://keycloak:8080` | URL interna de Keycloak |
| `KEYCLOAK_PUBLIC_URL` | `https://bfts2026.mooo.com/auth` | URL publica de Keycloak |
| `GOOGLE_CLIENT_ID` | - | Google SSO Client ID |
| `GOOGLE_CLIENT_SECRET` | - | Google SSO Client Secret |

### API
| Variable | Default | Descripcion |
|---|---|---|
| `API_PORT` | `8000` | Puerto del backend |
| `API_URL` | `https://bfts2026.mooo.com` | URL publica de la API |
| `INFERENCE_SERVER_URL` | `http://inference-server:8000` | URL del servidor de inferencia |

### Monitoreo
| Variable | Default | Descripcion |
|---|---|---|
| `INFLUXDB_TOKEN` | - | Token de autenticacion InfluxDB |
| `INFLUXDB_ORG` | `api-monitoring` | Organizacion InfluxDB |
| `INFLUXDB_BUCKET` | `api-deteccion-visual` | Bucket de metricas |
| `GRAFANA_USER` | `admin` | Usuario admin de Grafana |
| `GRAFANA_PASSWORD` | - | Contrasena admin de Grafana |
| `HOSTNAME` | `bfts2026` | Identificador del host en Grafana |

### Cliente CLI
| Variable | Default | Descripcion |
|---|---|---|
| `API_BASE` | `https://bfts2026.mooo.com` | URL base del backend |
| `INFER_URL` | `http://localhost:8001/infer` | Endpoint de inferencia local |

---

## Licencia

Proyecto academico - Trabajo Integrador Sistemas Operativos Avanzados (SOA) 2026.
