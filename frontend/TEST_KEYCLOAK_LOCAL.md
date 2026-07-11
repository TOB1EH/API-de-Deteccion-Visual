# Prueba Local de Keycloak con el Frontend

## Requisitos

- Docker instalado (`docker --version`)
- Node.js 18+ instalado (`node --version`)
- Puerto 8081 libre (verificar con `ss -tlnp | grep 8081` o `lsof -ti :8081`)

---

## Paso 1: Levantar Keycloak con Docker

Ejecutar en la terminal **en cualquier directorio** (el comando usa la ruta absoluta):

```bash
docker run -d \
  --name api_detection_keycloak_local \
  -p 8081:8080 \
  -e KC_BOOTSTRAP_ADMIN_USERNAME=admin \
  -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin123 \
  -e KC_HOSTNAME=localhost \
  -e KC_HTTP_PORT=8080 \
  -e KC_HTTP_RELATIVE_PATH=/auth \
  -v /home/sofia/API-de-Deteccion-Visual/docker/keycloak/realm-export.json:/opt/keycloak/data/import/realm-export.json:ro \
  quay.io/keycloak/keycloak:26.6 \
  start-dev --import-realm
```

**Salida esperada:** un hash largo (ID del contenedor).

---

## Paso 2: Esperar que Keycloak termine de iniciar

```bash
docker logs -f api_detection_keycloak_local
```

Esperar hasta ver en la terminal algo como:

```
Realm 'api-detection' imported
...
Keycloak started in 30s
```

Una vez que veas eso, presiona **Ctrl+C** para salir del log.

> Si no ves el mensaje despues de 2 minutos, algo salio mal. Revisa los logs completos con `docker logs api_detection_keycloak_local`.

---

## Paso 3: Verificar que Keycloak responde

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/auth/realms/api-detection
```

**Salida esperada:** `200`

Si ves `000` o `Connection refused`, Keycloak no esta corriendo. Volve al Paso 1.

---

## Paso 4: Iniciar el frontend (Vite dev server)

Abre una **nueva terminal** (manteniendo la anterior abierta con Docker corriendo) y ejecuta:

```bash
cd ~/API-de-Deteccion-Visual/frontend
npm run dev
```

**Salida esperada:**

```
VITE v5.x  ready in XXX ms
  Local:   http://localhost:3000/
```

> Si ves `Port 3000 is in use, trying another one...`, primero mata el proceso anterior con `lsof -ti :3000 | xargs kill -9` y ejecuta `npm run dev` de nuevo.

---

## Paso 5: Probar el login desde el navegador

1. Abri `http://localhost:3000/` en el navegador
2. Hace clic en **"Iniciar sesion con Keycloak"**
3. El navegador te redirige al formulario de login de Keycloak en `http://localhost:8081/auth/...`
4. Inicia sesion con las credenciales de prueba:

   | Usuario | Contrasena | Roles |
   |---------|-----------|-------|
   | `admin` | `admin123` | admin, operator, viewer |
   | `operator1` | `op123` | operator, viewer |
   | `viewer1` | `view123` | viewer |

5. Keycloak te redirige de vuelta a `http://localhost:3000/cargar` autenticado
6. Deberias ver la barra de navegacion con tu nombre de usuario y el icono de logout

---

## Paso 6: Limpiar cuando termines

```bash
docker stop api_detection_keycloak_local
docker rm api_detection_keycloak_local
```

Para verificar que se detuvo:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/auth/realms/api-detection
```

**Salida esperada:** `000` (conexion rechazada, el contenedor ya no existe)

---

## Escenario A: Probar contra Keycloak remoto (bfts2026.mooo.com)

### Por que no funciona con `npm run dev`

Cuando ejecutas `npm run dev` en `localhost:3000`, `auth.js` detecta que estas en localhost y configura el proxy de Vite (`/auth` -> `localhost:8081`). Esto significa que Keycloak local (Docker) es el unico que se usa. Para usar el Keycloak remoto necesitas forzar la URL.

### Solucion: Variable de entorno

Ejecuta el frontend con la variable `VITE_KEYCLOAK_URL` apuntando al Keycloak remoto:

```bash
cd ~/API-de-Deteccion-Visual/frontend
VITE_KEYCLOAK_URL=https://bfts2026.mooo.com/auth npm run dev
```

**Salida esperada:**
```
VITE v5.x  ready in XXX ms
  Local:   http://localhost:3000/
```

### Paso 2: Login contra remoto

1. Abri `http://localhost:3000/` en el navegador
2. Hace clic en **"Iniciar sesion con Keycloak"**
3. Te redirige a `https://bfts2026.mooo.com/auth/realms/api-detection/...`
4. Ingresa con las credenciales:
   - `admin` / `admin123` (roles: admin, operator, viewer)
   - `operator1` / `op123` (roles: operator, viewer)
   - `viewer1` / `view123` (roles: viewer)
5. Keycloak te redirige de vuelta a `http://localhost:3000/home` autenticado

**Que deberias ver despues del login:**
- Barra superior con los botones: **Inicio, Cargar, Buscar, Personas, Facial, NOC**
- A la derecha: un chip con el nombre de usuario (`admin`) y un icono de salir
- Un switch para alternar modo oscuro/claro
- Contenido del HomeView con las 4 tarjetas KPI, feed de actividad y estado del servidor

**Nota:** Si ves el snackbar de error "No se pudo conectar con el servidor de autenticacion" despues de 5 segundos, verifica que el servidor remoto este accesible con `curl https://bfts2026.mooo.com/auth/`.

### Alternativa: Acceder directamente a la URL desplegada

El frontend ya esta desplegado en `https://bfts2026.mooo.com/`. Si accedes directamente desde ahi, `auth.js` detecta que NO estas en localhost y usa automaticamente `https://bfts2026.mooo.com/auth` como Keycloak. No necesita variable de entorno ni Docker.

---

## Pruebas funcionales

### 1. Login Keycloak

| Paso | Accion | Resultado esperado |
|------|--------|-------------------|
| 1.1 | Abrir `http://localhost:3000/` sin sesion | Redirige a `/login` con pantalla de login |
| 1.2 | Clic en "Iniciar sesion con Keycloak" | Redirige a Keycloak (remoto o local segun config) |
| 1.3 | Ingresar credenciales correctas | Vuelve a `/home` con barra de navegacion y nombre de usuario visible |
| 1.4 | Clic en "Cerrar sesion" (icono de salir) | Redirige a `/login`, barra de navegacion oculta |
| 1.5 | Clic en "Modo Demo" | Navega a `/home` con usuario "Developer Demo" |
| 1.6 | Recargar pagina estando autenticado | Mantiene la sesion (el guard de ruta lo redirige a `/home`) |
| 1.7 | Cerrar sesion, recargar, pegar URL `/home` | Redirige a `/login` |

**Que verificar:**
- El chip de usuario muestra el nombre correcto (`admin`, `operator1` o `viewer1`)
- El switch de tema funciona (claro/oscuro)
- La sesion persiste al recargar la pagina (F5)
- Con "Modo Demo" se usa `mock-token-desarrollador` como token

---

### 2. HomeView - Dashboard principal

| Paso | Accion | Resultado esperado |
|------|--------|-------------------|
| 2.1 | Ir a `/home` | Ver 4 tarjetas KPI: Frames Procesados, Detecciones, Personas Registradas, Modelos Disponibles |
| 2.2 | Ver feed de actividad | Lista de frames recientes con thumbnail, clase detectada, timestamp |
| 2.3 | Ver estado del servidor | Panel con indicadores: CPU, GPU, uso de disco, modelos activos |

**Que verificar:**
- Los KPI cargan numeros (reales del backend o mock si falla la API)
- El feed de actividad muestra thumbnails cuando existen
- El estado del servidor aparece sin errores
- Si la API remota devuelve 401 (token invalido), los datos mock aparecen en su lugar

---

### 3. Cargar fotograma (DashboardView)

| Paso | Accion | Resultado esperado |
|------|--------|-------------------|
| 3.1 | Ir a `/cargar` | Formulario con: selector de modelo, drag-drop de imagen, latitud, longitud, camara ID, confianza minima |
| 3.2 | Seleccionar un modelo | El dropdown lista modelos disponibles (descargados de `GET /api/models`) |
| 3.3 | Subir una imagen | Arrastrar o hacer clic para seleccionar. Preview de la imagen aparece |
| 3.4 | Completar lat/lon | Ingresar coordenadas (ej: `-34.6037`, `-58.3816`) |
| 3.5 | Clic en "Procesar fotograma" | Boton se pone en loading, luego muestra resultado con imagen procesada y bounding boxes |
| 3.6 | Ver detecciones | Tabla con clase, confianza, coordenadas del bbox |

**Que verificar:**
- El preview de la imagen se muestra correctamente
- El slider de confianza funciona (valor entre 0 y 1)
- Al enviar, el loading spinner aparece y desaparece
- Si la API responde, se ven los bounding boxes superpuestos (componente DetectionOverlay)
- Si la API falla, se muestran datos mock (resultado simulado)

---

### 4. Buscar fotogramas (SearchView)

| Paso | Accion | Resultado esperado |
|------|--------|-------------------|
| 4.1 | Ir a `/buscar` | Pagina con panel de filtros expandible y resultados en grilla |
| 4.2 | Expandir filtros | Clic en el panel para mostrar filtros: clase, latitud, longitud, camara, fuente |
| 4.3 | Filtrar por clase | Ingresar "person" y presionar "Buscar" |
| 4.4 | Ver resultados | Grid de tarjetas (FrameCard) con thumbnail, clase, confianza, coordenadas |
| 4.5 | Cambiar paginacion | Selector 6/12/24/48 items por pagina |
| 4.6 | Paginar | Clic en `v-pagination` para navegar entre paginas |
| 4.7 | Clic en resultado | Navega a `/frame/{id}` con el detalle |

**Que verificar:**
- Los filtros se aplican correctamente (el query param cambia)
- La paginacion muestra el total de resultados (`total` del backend)
- Cada FrameCard tiene: imagen thumbnail, clase, confianza, enlace a detalle
- Sin filtros, busca todos los frames

---

### 5. Detalle de fotograma (FrameDetailView)

| Paso | Accion | Resultado esperado |
|------|--------|-------------------|
| 5.1 | Ir a `/frame/{id}` | Imagen del fotograma con bounding boxes superpuestos (SVG overlay) |
| 5.2 | Ver metadata | Panel con: frame ID, modelo, fecha, coordenadas, camara |
| 5.3 | Ver tabla de detecciones | Lista con clase, confianza, coordenadas del bbox |
| 5.4 | Hover sobre bounding box | Tooltip con nombre de clase y confianza |
| 5.5 | Clic en descargar | Descarga la imagen original |

**Que verificar:**
- La imagen carga correctamente
- Los bounding boxes se renderizan en las posiciones correctas
- Los colores de los boxes varian segun la clase
- El tooltip nativo `<title>` aparece al hacer hover
- Los datos de metadata coinciden con lo esperado

---

### 6. Personas (PersonsView)

| Paso | Accion | Resultado esperado |
|------|--------|-------------------|
| 6.1 | Ir a `/personas` | Tabla con personas registradas, busqueda por nombre |
| 6.2 | Buscar persona | Escribir en el campo de busqueda, la tabla se filtra |
| 6.3 | Clic en "Nueva persona" | Dialogo modal con formulario (nombre, apellido, email) |
| 6.4 | Crear persona | Completar nombre+apellido y guardar. Aparece en la tabla |
| 6.5 | Seleccionar persona | Click en fila -> se expande detalle con foto facial cargada y boton "Agregar foto facial" |
| 6.6 | Subir foto facial | Seleccionar imagen, se envia a API de embeddings |
| 6.7 | Ver embeddings | Muestra si se proceso correctamente o si se rechazo |

**Que verificar:**
- Validacion de formulario: nombre y apellido son obligatorios
- Email opcional con validacion de formato
- Al crear, la persona aparece inmediatamente en la tabla
- La foto facial se sube correctamente
- Si falla la API (sin inference-server), muestra error controlado

---

### 7. Reconocimiento facial (FaceRecognitionView)

**Actual:** Siempre usa mock (resultado aleatorio con 1.5s de delay).

| Paso | Accion | Resultado esperado |
|------|--------|-------------------|
| 7.1 | Ir a `/facial` | Drag-drop para subir foto, slider de threshold (0.0 - 1.0) |
| 7.2 | Subir imagen | Preview de la foto |
| 7.3 | Ajustar threshold | Deslizar a 0.5 |
| 7.4 | Clic en "Reconocer rostro" | Loading de 1.5s, luego resultado aleatorio: verde (reconocido) o rojo (no reconocido) |
| 7.5 | Resultado positivo | Tarjeta verde con nombre, apellido y confianza |
| 7.6 | Resultado negativo | Tarjeta roja con "No se reconocio ningun rostro" |

> **Nota:** La integracion con la API real (enviar imagen -> inference-server -> embedding -> POST /api/face-recognition) esta pendiente. Actualmente todo es mock.

---

### 8. Monitoreo (MonitoreoView)

| Paso | Accion | Resultado esperado |
|------|--------|-------------------|
| 8.1 | Ir a `/monitoreo` | Panel NOC con 3 pestañas: Infraestructura, BD & API, Metricas YOLO |
| 8.2 | Ver estado de servicios | Chips: "Telegraf: Activo", "Grafana Server: Conectado", "Inferencia IA: Operando" |
| 8.3 | Pestaña "Infraestructura" | Iframe con dashboard Grafana de infraestructura |
| 8.4 | Pestaña "BD & API" | Iframe con dashboard de base de datos y API |
| 8.5 | Pestaña "Metricas YOLO" | Iframe con dashboard de inferencia YOLO |
| 8.6 | Clic en "Forzar Recarga" | Los 3 iframes se recargan |

**Que verificar:**
- Las pestañas cambian correctamente
- Cada iframe carga lazy (solo se renderiza la pestaña activa)
- Si Grafana requiere autenticacion, muestra la pantalla de login de Grafana dentro del iframe
- El boton de recarga fuerza la recarga de todos los tableros

> **Nota:** Los dashboards de Grafana requieren que Miembro C haya configurado `allow_embedding = true` en Grafana. Si ves pantalla en blanco o error de conexion, Grafana puede no estar accesible desde el frontend.

---

### 9. Cerrar sesion

| Paso | Accion | Resultado esperado |
|------|--------|-------------------|
| 9.1 | Clic en el icono de salir (esquina superior derecha) | `authService.logout()` se ejecuta |
| 9.2 | Si es Keycloak real | Redirige a Keycloak logout, luego vuelve a `/login` |
| 9.3 | Si es Modo Demo | Vuelve a `/login` inmediatamente |
| 9.4 | Intentar navegar a `/home` | Redirige a `/login` (sesion terminada) |

---

## Solucion de problemas

### Error: `Port 8081 is already in use`

Otro contenedor o proceso esta usando el puerto 8081. Liberalo con:

```bash
# Si es un contenedor Docker
docker stop api_detection_keycloak_local && docker rm api_detection_keycloak_local

# Si es otro proceso
lsof -ti :8081 | xargs kill -9
```

### Error: `Realm 'api-detection' imported` no aparece

El archivo `realm-export.json` no se esta montando correctamente. Verifica la ruta:

```bash
ls -la /home/sofia/API-de-Deteccion-Visual/docker/keycloak/realm-export.json
```

### Error: Al hacer clic en Keycloak login no pasa nada (aparece snackbar rojo)

1. Verifica que Keycloak este corriendo: `curl http://localhost:8081/auth/realms/api-detection`
2. Verifica que el frontend este en `http://localhost:3000`
3. Revisa la consola del navegador (F12) por errores de CORS o conexion

### Error: `"parametro no valido: redirect_uri"` en la pagina de Keycloak

El `realm-export.json` no tiene `http://localhost:3000/*` en `redirectUris`. Verifica el archivo:

```bash
grep redirectUris /home/sofia/API-de-Deteccion-Visual/docker/keycloak/realm-export.json
```

Debe mostrar: `"redirectUris": ["https://bfts2026.mooo.com/*", "http://localhost:3000/*"]`

### Modo Demo siempre funciona

Si Keycloak no esta disponible, podes usar el boton **"Ingresar en Modo Demo (Bypass)"** que no requiere Keycloak y funciona con datos mock.

### Los iframes de Grafana no cargan

1. Verificar que Grafana este corriendo: `curl https://bfts2026.mooo.com/grafana/`
2. Confirmar que `allow_embedding = true` esta configurado en `grafana.ini`
3. Revisar la consola del navegador (F12) por errores CSP o `X-Frame-Options`

### La API devuelve 401 (Unauthorized)

**Causa:** El token JWT de Keycloak local no es valido para el servidor remoto.

**Comportamiento esperado:** El interceptor de `api.js` detecta 401 y muestra datos mock (funciona igual, solo que los datos no son reales).

**Para usar API real:** Necesitas autenticarte contra el Keycloak remoto (Escenario A) para obtener un token valido.

### La imagen en DashboardView no se procesa

1. Verificar que el inference-server este corriendo (en remoto o local)
2. Revisar la consola del navegador por errores de red
3. Si falla la API, los datos mock se usan automaticamente

### El boton "Forzar Recarga" no funciona

Verificar que los iframes tengan `:key` bindeado (ya corregido en la version actual). Si el problema persiste, cerrar sesion y volver a entrar.

---

## Resumen de lo que deberias ver en cada pantalla

| Pantalla | Ruta | Elementos clave |
|----------|------|-----------------|
| Login | `/login` | Boton Keycloak + boton Demo |
| Home | `/home` | 4 KPIs, feed actividad, estado servidor |
| Cargar | `/cargar` | Dropzone, modelo, lat/lon, slider confianza, submit |
| Buscar | `/buscar` | Filtros, grilla de frames, paginacion |
| Frame | `/frame/:id` | Imagen + SVG overlays, metadata, tabla detecciones |
| Personas | `/personas` | Tabla, busqueda, dialogo crear, subir foto facial |
| Facial | `/facial` | Dropzone, slider threshold, resultado mock |
| NOC | `/monitoreo` | 3 tabs con iframes de Grafana |
