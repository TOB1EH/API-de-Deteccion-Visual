# Guia de Presentacion y Demo

Proyecto Integrador - Sistemas Operativos Avanzados (SOA) 2026
API de Deteccion Visual

---

## Indice

- [Estructura de la presentacion](#estructura-de-la-presentacion)
- [Seccion 1: Introduccion](#seccion-1-introduccion)
- [Seccion 2: Arquitectura](#seccion-2-arquitectura)
- [Seccion 3: Demo Web](#seccion-3-demo-web)
- [Seccion 4: Demo CLI](#seccion-4-demo-cli)
- [Seccion 5: Autenticacion y Roles](#seccion-5-autenticacion-y-roles)
- [Seccion 6: Infraestructura](#seccion-6-infraestructura)
- [Seccion 7: Cierre](#seccion-7-cierre)
- [Tips para la demo](#tips-para-la-demo)
- [Comandos rapidos para la demo](#comandos-rapidos-para-la-demo)

---

## Estructura de la presentacion

| Seccion | Duracion | Que cubrir |
|---|---|---|
| 1. Introduccion | 2 min | Que es el proyecto, problema que resuelve |
| 2. Arquitectura | 4 min | Componentes, clientes vs servidor, flujo de datos |
| 3. Demo: Web | 8 min | Login, Dashboard, Cargar/Buscar, Personas, Facial, Monitoreo |
| 4. Demo: CLI | 3 min | Descargar/inicializar nodo, inferir, facial |
| 5. Autenticacion y Roles | 3 min | Keycloak OAuth2, login facial, matriz de permisos |
| 6. Infraestructura | 3 min | Docker, Nginx, BD, SeaweedFS, Monitoreo |
| 7. Cierre | 2 min | Logros, desafios, preguntas |

**Total estimado: 25 minutos.**

---

## Seccion 1: Introduccion

### Discurso sugerido

> "Este proyecto integrador de SOA consiste en una plataforma de deteccion de objetos y reconocimiento facial con persistencia distribuida, autenticacion OAuth2 y monitoreo en tiempo real.
>
> El sistema permite a un usuario capturar una imagen desde su PC, detectar objetos usando YOLO, reconocer rostros con DeepFace, y persistir todo en un servidor remoto con PostgreSQL y almacenamiento distribuido SeaweedFS.
>
> La plataforma incluye un frontend web SPA, un CLI de terminal, y un nodo de inferencia local que procesa las imagenes sin depender del servidor remoto para la carga computacional."

### Conceptos clave

- Procesamiento local (nodo del usuario) + almacenamiento y autenticacion remotos
- Dos pipelines principales: deteccion de objetos (YOLO) y reconocimiento facial (DeepFace + pgvector)
- Acceso por web (SPA) y por terminal (CLI)
- Autenticacion OAuth2 con Keycloak y login biometrico alternativo
- Monitoreo NOC con Grafana, InfluxDB y Telegraf

---

## Seccion 2: Arquitectura

### Diagrama

```
+---------------------------------------------------+
|                    CLIENTE                        |
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
|  +-------------------------------------------+    |
|  | Nginx (proxy reverso HTTPS)               |    |
|  | +-> /api/ -> FastAPI :8000               |    |
|  | +-> /auth/ -> Keycloak :8080             |    |
|  | +-> /grafana/ -> Grafana :3000           |    |
|  | +-> /pgadmin/ -> pgAdmin                 |    |
|  | +-> /seaweed/ -> SeaweedFS :8080         |    |
|  +-------------------------------------------+    |
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
|  inference-server (Docker)                        |
|  - YOLO (Ultralytics)                             |
|  - DeepFace (MTCNN + Facenet)                    |
|  - Puerto 8001                                    |
+---------------------------------------------------+
```

### Explicacion por capas

**Cliente (lo que ve el usuario):**
- Frontend Vue 3 + Vuetify con 13 rutas (landing publica, login, dashboard, busqueda, detalle, personas, facial, monitoreo, etc.)
- CLI `setup_cliente.py` para operaciones desde terminal
- `inference-server` en Docker local con YOLO + DeepFace para procesamiento local de imagenes

**Servidor remoto (`bfts2026.mooo.com`):**
- **Nginx** como proxy reverso HTTPS con Let's Encrypt, enruta cada servicio por subruta
- **FastAPI** como backend REST con 7 routers y 15 endpoints documentados
- **Keycloak** como proveedor OAuth2/OpenID Connect con roles admin/operator/viewer
- **PostgreSQL 16 + pgvector** para metadatos y embeddings faciales (busqueda por similitud coseno)
- **SeaweedFS** para almacenamiento distribuido de imagenes
- **Grafana + InfluxDB + Telegraf** para monitoreo NOC

**Nodo local:**
- Inference-server en Docker con modelos YOLO descargables y DeepFace (MTCNN + Facenet)
- Se comunica con la API remota via HTTPS para persistir resultados

### Flujo basico de datos

```
1. Usuario sube foto (web o CLI)
2. Inference-server local procesa con YOLO (bounding boxes, clases, confianzas)
3. Resultados + imagen se envian a POST /api/detections
4. API persiste imagen en SeaweedFS, metadatos en PostgreSQL
5. Para facial: extrae embedding con DeepFace, almacena en pgvector
6. Busqueda: compara embedding contra BD por similitud coseno
```

---

## Seccion 3: Demo Web

### 3a. Landing Page (`/`)

**URL:** `https://bfts2026.mooo.com`

**Que mostrar:**
- Hero: titulo, subtitulo, botones de accion
- "Como funciona": 3 pasos (descargar CLI, instalar nodo, iniciar sesion)
- Indicador de estado del nodo local (conectado/desconectado, se actualiza cada 15s)
- Seccion de descarga del CLI
- 8 tarjetas de funcionalidades (Deteccion, Facial, Busqueda, Monitoreo, etc.)
- 8 tarjetas del stack tecnologico (FastAPI, Vue 3, PostgreSQL, Keycloak, YOLO, etc.)
- Footer con enlaces a Swagger UI y GitHub

> "La landing page es publica y presenta el sistema. El indicador de nodo local verifica cada 15 segundos si el inference-server esta corriendo en la PC del usuario. Desde aca se puede descargar el CLI o iniciar sesion."

---

### 3b. Login (`/login`)

**URL:** `https://bfts2026.mooo.com/login`

**Que mostrar:**
- Click "Iniciar Sesion" -> redirige a Keycloak
- Formulario de login de Keycloak (usuario/contraseña)
- Alternativa: boton "Google SSO" (si esta configurado)
- Opcional: mostrar `/login-facial` como alternativa biometrica

> "La autenticacion usa Keycloak como proveedor OpenID Connect. Cuando el usuario inicia sesion, Keycloak emite un token JWT firmado con RS256 que contiene los roles del usuario. La API valida este token contra la clave publica JWKS de Keycloak en cada request."

---

### 3c. Dashboard (`/home`)

**URL:** `https://bfts2026.mooo.com/home`

**Que mostrar:**
- 4 tarjetas KPI: frames procesados, personas registradas, detecciones totales, modelos activos
- Cada tarjeta con tendencia vs mes anterior (flecha verde/roja)
- Tabla de actividad reciente (ultimas detecciones)
- Barra de navegacion superior con acceso a todas las vistas

> "El dashboard principal muestra indicadores clave del sistema. Los datos se obtienen de la API en tiempo real. Cada tarjeta KPI incluye la tendencia respecto al mes anterior."

---

### 3d. Cargar imagen (`/cargar`)

**URL:** `https://bfts2026.mooo.com/cargar`

**Que mostrar:**
- Zona de drag & drop para la imagen
- Selector de modelo YOLO (lista obtenida de `GET /api/models`)
- Slider de confianza minima (0 a 1, step 0.05)
- Campos opcionales: latitud, longitud, camara ID
- Click "Procesar" -> muestra loading
- Al finalizar: muestra enlace al detalle del fotograma

> "El formulario de carga permite subir una imagen, seleccionar el modelo YOLO y ajustar el umbral de confianza. Las coordenadas geograficas son opcionales. La imagen se envia a la API, que la pasa al inference-server para deteccion. Los resultados (bounding boxes, clases, confianzas) se persisten y se puede ver el detalle."

---

### 3e. Detalle de fotograma (`/frame/:id`)

**URL:** `https://bfts2026.mooo.com/frame/[id]`

**Que mostrar:**
- Imagen con bounding boxes superpuestas (componente DetectionOverlay)
- Informacion detallada: clases detectadas, nivel de confianza, fecha, ubicacion
- Botones de descarga: imagen original, thumbnail, version anotada
- Navegacion "Volver a busqueda"

> "El detalle del fotograma muestra la imagen con las detecciones graficadas como bounding boxes. Cada caja tiene el color segun la clase y muestra la etiqueta con el nivel de confianza. Se puede descargar la imagen en distintos formatos."

---

### 3f. Busqueda (`/buscar`)

**URL:** `https://bfts2026.mooo.com/buscar`

**Que mostrar:**
- Panel de filtros expandible: clases (separadas por coma), rangos de latitud/longitud, camara, fuente
- Boton "Buscar" y "Limpiar filtros"
- Resultados con miniaturas, paginados
- Click en resultado -> detalle del fotograma

> "La busqueda permite filtrar fotogramas por clases detectadas, ubicacion geografica, camara y otros metadatos. Las clases se separan por coma. Los resultados se muestran con miniaturas y se puede acceder al detalle de cada uno."

---

### 3g. Personas (`/personas`)

**URL:** `https://bfts2026.mooo.com/personas`

**Que mostrar:**
- Tabla con columnas: Nombre, Apellido, Email, Roles, Fecha de registro, Cantidad de rostros
- Busqueda por texto
- Boton "Nueva persona" (solo visible para admin)
- Al hacer click en una fila: detalle de la persona con sus embeddings faciales

> "El modulo de personas permite registrar identidades y asociarles embeddings faciales. Estos embeddings son vectores de 128 dimensiones generados por DeepFace/Facenet, almacenados en pgvector para busqueda por similitud coseno."

---

### 3h. Reconocimiento Facial (`/facial`)

**URL:** `https://bfts2026.mooo.com/facial`

**Que mostrar:**
- Zona de drag & drop para la foto
- Ajuste de threshold (confianza minima)
- Resultado: persona identificada + porcentaje de confianza
- Listado de coincidencias con puntajes

> "El reconocimiento facial sube la foto, el inference-server local extrae el embedding con DeepFace, y la API lo compara contra la base de vectores usando pgvector con distancia coseno. Devuelve la persona mas similar si supera el umbral de confianza."

---

### 3i. Login Facial (`/login-facial`)

**URL:** `https://bfts2026.mooo.com/login-facial`

**Que mostrar:**
- Captura con webcam o subir foto
- Verifica que el nodo local este activo
- Click "Iniciar sesion" -> reconoce el rostro
- Redirige al dashboard autenticado

> "El login biometrico permite autenticarse sin contrasena. La foto se procesa localmente con DeepFace, se identifica a la persona comparando contra los embeddings almacenados, y la API emite un token JWT facial. Esto funciona como segundo factor de autenticacion o como metodo principal si Keycloak no esta disponible."

---

### 3j. Monitoreo NOC (`/monitoreo`) -- solo admin

**URL:** `https://bfts2026.mooo.com/monitoreo` (visible solo para admin)

**Que mostrar:**
- 3 pestanas con dashboards Grafana embebidos:
  1. **Infraestructura (Host):** CPU, RAM, red, disco
  2. **Base de Datos & API:** rendimiento PostgreSQL, requests FastAPI
  3. **Metricas del Modelo YOLO:** frames procesados, tiempos de inferencia
- Indicadores de estado: Telegraf, Grafana, inferencia IA
- Boton "Forzar Recarga de Tableros"

> "El centro de monitoreo embebe dashboards de Grafana en modo kiosko. Telegraf recolecta metricas del sistema cada 10 segundos (CPU, RAM, red, contenedores Docker), las almacena en InfluxDB, y Grafana las visualiza en dashboards interactivos."

---

## Seccion 4: Demo CLI

### 4a. Descargar e instalar el nodo local

```bash
curl -O https://bfts2026.mooo.com/setup_cliente.py
python3 setup_cliente.py install
```

> "El CLI se puede descargar directamente desde el servidor remoto. El comando `install` descarga la imagen Docker del inference-server con YOLO y DeepFace, y levanta el contenedor en el puerto 8001. Esto permite procesar imagenes localmente sin depender del servidor remoto para la carga computacional."

### 4b. Iniciar sesion

```bash
python3 setup_cliente.py faces login
```

### 4c. Inferir una imagen

```bash
python3 setup_cliente.py infer ~/foto.jpg --model yolo11n.pt
```

> "El comando `infer` envia la imagen al inference-server local (localhost:8001), que la procesa con YOLO y devuelve las detecciones. Luego sube automaticamente los resultados a la API remota via `POST /api/detections` para persistirlos."

### 4d. Consultar fotogramas

```bash
python3 setup_cliente.py frames list --clases person --limit 5
python3 setup_cliente.py frames get [id] --thumbnail
python3 setup_cliente.py frames annotate [id]
```

### 4e. Gestionar personas

```bash
python3 setup_cliente.py persons list
python3 setup_cliente.py persons create "Juan" "Perez"
```

### 4f. Reconocimiento facial

```bash
python3 setup_cliente.py faces embed [person_id] ~/foto_referencia.jpg
python3 setup_cliente.py faces recognize ~/foto_test.jpg --threshold 0.5
```

---

## Seccion 5: Autenticacion y Roles

### Explicacion tecnica

> "La autenticacion funciona en dos niveles."

**Nivel 1 -- Keycloak OAuth2 (primario):**
- Proveedor OpenID Connect con flujo de redireccion
- Tokens JWT firmados con RS256, validados via JWKS (`verify_token` en `src/api/services/auth.py`)
- Realm: `api-detection`. Client: `api-backend`
- Roles extraidos del campo `realm_access.roles` del JWT
- Identity Providers externos: Google SSO configurado
- Integracion con frontend via `keycloak-js`

**Nivel 2 -- Token Facial (secundario):**
- Generado por `POST /api/auth/login/facial` tras verificacion biometrica local
- JWT firmado con HS256, incluye roles del usuario consultando Keycloak internamente
- Almacenado en `localStorage` como respaldo si Keycloak no esta disponible

### Matriz de permisos

| Endpoint | Admin | Operator | Viewer |
|---|---|---|---|
| GET /api/models | Si | Si | Si |
| GET /api/models/{name}/download | Si | Si | No |
| POST /api/detections | Si | Si | No |
| GET /api/frames/{id} | Si | Si | Si |
| GET /api/frames/search | Si | Si | Si |
| GET /api/persons | Si | Si | Si |
| POST /api/persons | Si | No | No |
| PUT /api/persons/{id} | Si | No | No |
| DELETE /api/persons/{id} | Si | No | No |
| POST /api/persons/{id}/embeddings | Si | Si | No |
| POST /api/face-recognition | Si | Si | No |
| Frontend /monitoreo (NOC) | Si | No | No |
| POST /api/auth/register | Publico | Publico | Publico |
| POST /api/auth/login/facial | Publico | Publico | Publico |

### Control de acceso en frontend

> "El frontend implementa dos capas de proteccion:
>
> 1. **Router guard global** (`beforeEach` en `router/index.js`): verifica que el usuario este autenticado y tenga el rol requerido por la ruta. Si no, redirige a `/home`.
>
> 2. **Filtrado de navegacion** (`App.vue`): los items de la barra de navegacion se filtran segun los roles del usuario. Un operador no ve el boton "NOC" ni "Facial"."

---

## Seccion 6: Infraestructura

### Servicios Docker (11 en produccion)

| Servicio | Funcion |
|---|---|
| `db` | PostgreSQL 16 + pgvector |
| `api` | FastAPI backend |
| `frontend` | Vue 3 SPA (Nginx) |
| `nginx` | Proxy reverso HTTPS + Let's Encrypt |
| `keycloak` | Autenticacion OAuth2/JWT |
| `seaweed-master` | Coordinador SeaweedFS |
| `seaweed-volume` | Almacenamiento de objetos |
| `pgadmin` | Gestion PostgreSQL |
| `inference-server` | YOLO + DeepFace (remoto) |
| `influxdb` | Base de datos de metricas (time-series) |
| `telegraf` | Recoleccion de metricas del host |
| `grafana` | Dashboards de monitoreo |

### Puntos clave para mencionar

**Nginx:**
- Proxy reverso con SSL/TLS (Let's Encrypt)
- Enruta cada servicio por subruta (`/api/`, `/auth/`, `/grafana/`, etc.)
- Resuelve servicios por nombre Docker con resolver DNS dinamico (evita 502 al recrear contenedores)

**PostgreSQL + pgvector:**
- Los embeddings faciales se almacenan como vectores de 128 dimensiones
- La busqueda por similitud usa distancia coseno
- pgvector permite busqueda eficiente sin necesidad de servicios externos

**SeaweedFS:**
- Almacenamiento de objetos distribuido
- Las imagenes se almacenan con un ID unico referenciado desde PostgreSQL
- Escalable horizontalmente

**Keycloak:**
- Configurado con realm `api-detection`, client `api-backend`
- Roles: admin, operator, viewer
- Identity Providers: Google SSO
- Integracion con frontend via adapter JS

**Monitoreo:**
- Telegraf recolecta metricas de CPU, RAM, disco, red y contenedores Docker
- InfluxDB almacena series temporales
- Grafana visualiza dashboards en tiempo real
- Datasource: InfluxDB Bucket `api-deteccion-visual`

**Nodo local:**
- Inference-server en Docker con GPU si disponible
- Detector: MTCNN | Modelo: Facenet | Normalizacion: Facenet
- Modelos YOLO descargables (11n, 11s, 11m, 11l, 11x)

---

## Seccion 7: Cierre

### Logros del proyecto

- 11 servicios Docker orquestados con Docker Compose
- Frontend SPA con 13 rutas y control de acceso por roles
- API REST con 15 endpoints documentados (Swagger UI + ReDoc)
- Autenticacion OAuth2 con Keycloak + login biometrico alternativo
- Monitoreo NOC con Grafana, InfluxDB y Telegraf
- CLI completo para terminal con 6 subcomandos
- Persistencia distribuida (PostgreSQL + SeaweedFS)
- HTTPS con Let's Encrypt y auto-renewal
- Indicador de estado del nodo local en tiempo real
- Coordenadas geograficas opcionales en detecciones

### Desafios tecnicos superados

- Integracion de Keycloak con JWT y validacion JWKS en FastAPI
- Proxy de Nginx con resolucion dinamica de DNS para tolerar recreacion de contenedores
- Sincronizacion entre el token facial y los roles de Keycloak
- Embebido de dashboards Grafana en modo kiosko con autenticacion
- Comunicacion bidireccional entre nodo local y servidor remoto
- Manejo de sesion con Keycloak en SPA (check-sso, silentCheckSsoFallback)

### Posibles mejoras futuras

- Indice IVFFLAT en pgvector para busqueda mas rapida al escalar
- Multiples embeddings por persona (distintos angulos, iluminaciones)
- Login biometrico como segundo factor obligatorio post-login Keycloak
- Pipeline de video en tiempo real (no solo fotogramas individuales)
- Cache de resultados con Redis

---

## Tips para la demo

### Preparacion

1. **Tener datos de ejemplo cargados:**
   - 2-3 fotogramas procesados con detecciones
   - Al menos una persona registrada con embedding facial
   - Algunos frames en la busqueda

2. **Verificar conectividad antes de empezar:**
   ```bash
   curl -s https://bfts2026.mooo.com/health
   ```
   - Confirmar que el frontend carga en `https://bfts2026.mooo.com`
   - Verificar que el nodo local esta activo: `curl http://localhost:8001/health`

3. **Tener la terminal preparada:**
   - Comandos pre-escritos para copy-paste
   - Ventana dividida: navegador + terminal

4. **Credenciales a mano:**
   - Usuario admin para mostrar monitoreo
   - Usuario operator para mostrar restriccion

### Durante la demo

1. **Elegir un rol especifico y mostrar la diferencia:**
   - Iniciar sesion como admin: mostrar que ve NOC y Facial
   - Cerrar sesion, iniciar como operator: mostrar que NOC desaparece

2. **Mostrar error handling:**
   - Subir una imagen sin rostro en reconocimiento facial y mostrar el mensaje
   - Intentar acceder a `/monitoreo` como operator y ver la redireccion a `/home`

3. **CLI en vivo:**
   - Tener una imagen de ejemplo lista en el escritorio
   - Ejecutar `python3 setup_cliente.py infer` y mostrar el resultado

4. **Keycloak:**
   - Tener abierta la consola admin de Keycloak en `https://bfts2026.mooo.com/auth/admin/`
   - Mostrar la configuracion del realm, clients y roles

5. **Plan de contingencia:**
   - Si falla internet: tener el frontend local (`http://localhost:3000`) como respaldo
   - Si falla Keycloak: mostrar el modo demo o el login facial
   - Si falla el nodo local: el indicador en la landing debe mostrar "desconectado"

### Posibles preguntas y respuestas

| Pregunta | Respuesta |
|---|---|
| Por que procesar localmente y no en el servidor? | Para distribuir la carga computacional. El YOLO y DeepFace requieren GPU, y el servidor remoto no tiene una dedicada. |
| Que pasa si el nodo local no esta disponible? | El sistema sigue funcionando para consultas, busqueda y monitoreo. Solo la deteccion y facial requieren el nodo local. |
| Como se protegen las imagenes? | Autenticacion JWT en cada request, HTTPS para transmision, almacenamiento en SeaweedFS con ACL. |
| Que tan preciso es el reconocimiento facial? | Con buenas condiciones de iluminacion y frente a la camara, supera el 95%. Fallas con angulos extremos se mitigan con multiples embeddings. |
| Se puede escalar? | Si. pgvector soporta indices, SeaweedFS es distribuido, y FastAPI permite workers multiples. |
| Por que Keycloak y no Auth0/Firebase? | Es open source, self-hosted, y se integra con el ecosistema Docker. Permite control total sobre los datos. |

---

## Comandos rapidos para la demo

### Verificar servicios
```bash
# Health check de la API
curl https://bfts2026.mooo.com/health

# Listar contenedores en produccion
docker ps

# Ver logs de nginx
docker logs api_detection_nginx --tail 20
```

### CLI
```bash
# Descargar e instalar nodo local
curl -O https://bfts2026.mooo.com/setup_cliente.py
python3 setup_cliente.py install

# Iniciar sesion
python3 setup_cliente.py faces login

# Inferir imagen localmente
python3 setup_cliente.py infer ~/foto.jpg --model yolo11n.pt

# Listar fotogramas
python3 setup_cliente.py frames list --clases person --limit 5

# Ver detalle de fotograma
python3 setup_cliente.py frames get [id] --thumbnail

# Descargar version anotada
python3 setup_cliente.py frames annotate [id]

# Crear persona
python3 setup_cliente.py persons create "Juan" "Perez"

# Registrar embedding facial
python3 setup_cliente.py faces embed [person_id] ~/foto_referencia.jpg

# Reconocer rostro
python3 setup_cliente.py faces recognize ~/foto_test.jpg --threshold 0.5
```

### Despliegue (si preguntan)
```bash
# Despliegue local
docker compose -f docker-compose.local.yml up -d --build

# Despliegue remoto
docker compose up -d --build

# Actualizar frontend
docker compose up -d --build frontend

# Reiniciar nginx
docker compose restart nginx
```
