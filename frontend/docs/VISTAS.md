# Vistas

Cada pantalla de la aplicacion esta implementada como un archivo `.vue` en `src/views/`.

---

## LoginView.vue

Pantalla de ingreso con fondo gradiente (azul-violeta). Mientras Keycloak no este disponible, ofrece un boton "Ingresar en modo demo" que navega a `/cargar`.

### Componentes
- `v-card` con efecto glass (fondo semi-transparente + backdrop-filter)
- `v-alert` informativo sobre modo demo
- Boton Keycloak deshabilitado con label "proximamente"

### Props
Ninguna

### Eventos
- Click en "Ingresar en modo demo" -> navega a `/cargar` via router-link

### Estados
- Normal: muestra el formulario de login
- Keycloak no disponible: boton deshabilitado con mensaje

---

## DashboardView.vue (Cargar)

Pantalla principal de carga de fotogramas. Permite subir una imagen, configurar parametros de deteccion y visualizar el resultado.

### Elementos del formulario
- **Zona de drag & drop** con previsualizacion de imagen
- **Selector de modelo** (`v-select`) cargado desde `MOCK_MODELS`
- **Slider de confianza minima** (0 a 1, paso 0.05)
- **Campos de latitud / longitud** numericos
- **Camara (opcional)** campo de texto para identificar la camara origen
- **Limpiar imagen** boton para reiniciar la seleccion

### Comportamiento
1. El usuario arrastra o selecciona una imagen
2. Completa los datos del formulario
3. Presiona "Procesar fotograma"
4. Simulacion de carga de 1.5 segundos
5. Muestra resultado con frame_id, cantidad de detecciones y enlace "Ver detecciones"

### Estados
- **Vacio:** zona de upload con icono e instrucciones
- **Con imagen:** previsualizacion en miniatura
- **Cargando:** spinner en boton, inputs deshabilitados
- **Resultado:** card verde con resumen del procesamiento
- **Error:** `v-alert` de error (cuando ocurra)

### Datos mock usados
- `MOCK_MODELS` para el listado de modelos
- `MOCK_FRAME_RESULT` para el resultado del procesamiento

---

## SearchView.vue (Buscar)

Pantalla de busqueda de fotogramas con filtros combinados.

### Filtros
- **Clases** (texto, separado por coma): filtra fotogramas que contengan esas clases detectadas
- **Latitud min/max** (numerico): rango geografico
- **Longitud min/max** (numerico): rango geografico

Los filtros estan dentro de un `v-expansion-panel` colapsable. Cuando hay filtros activos, se muestra un chip "activos".

### Comportamiento
1. Usuario completa los filtros deseados
2. Presiona "Buscar" (con simulacion de 400ms)
3. Los resultados se filtran del lado del cliente contra `MOCK_SEARCH_RESULTS`
4. Se renderiza una grilla de `FrameCard` con los resultados

### Estados
- **Sin busqueda:** mensaje "Usa los filtros y presiona Buscar"
- **Con resultados:** grilla de tarjetas con contador
- **Sin resultados:** `v-empty-state` con icono y mensaje
- **Cargando:** spinner en boton de busqueda

### Filtrado (logica)
- Clases: matcheo parcial (`includes`) contra `detections[].class_name`
- Lat/Lon: comparacion numerica `>=` / `<=`

### Datos mock usados
- `MOCK_SEARCH_RESULTS`

---

## FrameDetailView.vue (Detalle de fotograma)

Vista de detalle de un fotograma individual con bounding boxes superpuestos.

### Layout
- **Columna izquierda (8/12):** imagen con overlay SVG de detecciones
- **Columna derecha (4/12):** metadatos y tabla de detecciones

### Overlay SVG
- `DetectionOverlay` recibe las detecciones y las dimensiones reales de la imagen
- Se activa cuando la imagen termina de cargar (`@load` -> `onImageLoad`)
- Cada bounding box tiene color segun la clase y tooltip nativo (`<title>`) con nombre y confianza

### Panel de metadatos
- Frame ID (monospace)
- Modelo usado
- Ubicacion (latitud, longitud)
- Cantidad de detecciones
- Fecha de creacion

### Tabla de detecciones
Columnas: Clase (chip con color), Confianza (porcentaje), Bounding box (coordenadas)

### Navegacion
Boton "Volver a busqueda" que navega a `/buscar`

### Datos mock usados
- `MOCK_FRAME_DETAIL`

---

## PersonsView.vue (Personas)

Gestion de personas registradas para reconocimiento facial.

### Tabla de personas
Columnas: Nombre, Apellido, Email, Registro, Rostros (icono check).

- Busqueda en vivo por nombre, apellido o email (`v-text-field` con filtro `computed`)
- Click en fila selecciona/deselecciona la persona
- Fila seleccionada tiene fondo resaltado

### Panel de detalle
Al seleccionar una persona, aparece un card con:
- Avatar con iniciales
- Nombre completo y email
- ID de persona
- Boton "Subir fotos faciales" (`<input type="file" multiple>`)

### Dialogo de nueva persona
- `v-dialog` con `PersonForm` incorporado
- Al guardar, se agrega al inicio del listado y se selecciona

### Datos mock usados
- `MOCK_PERSONS`

---

## FaceRecognitionView.vue (Facial)

Vista placeholder de reconocimiento facial. Actualmente en construccion.

### Contenido
- Icono grande de reconocimiento facial
- Titulo "Reconocimiento facial"
- Mensaje "Vista en construccion"

No tiene funcionalidad implementada. Se creo como esqueleto para mantener la navegacion completa.
