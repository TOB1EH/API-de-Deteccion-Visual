# Sistema de análisis de fotogramas con detección y reconocimiento facial

**SOA: 2026**

## Introducción

El presente trabajo propone una arquitectura de servicios backend orientada al procesamiento de imágenes mediante modelos de inferencia. La solución permite recibir fotogramas, ejecutar modelos de detección, almacenar los resultados obtenidos y consultar posteriormente la información procesada mediante criterios flexibles.

En una primera etapa, el sistema se plantea sin interfaz gráfica, exponiendo sus funcionalidades mediante APIs REST que podrán ser consumidas desde herramientas genéricas como Postman, curl o scripts automatizados. Esta decisión permite validar el funcionamiento de los servicios principales de forma desacoplada, priorizando la correcta definición de entradas, salidas, persistencia y trazabilidad de los datos.

La solución contempla además una extensión basada en reconocimiento facial, permitiendo registrar personas, asociar imágenes a dichas personas, generar embeddings faciales y reconocer individuos en nuevas imágenes cuando se supere un umbral mínimo de confianza.

Finalmente, se proyecta una segunda entrega en la que se incorporarán componentes adicionales de interfaz gráfica, seguridad mediante Keycloak, autenticación biométrica opcional y monitoreo del sistema mediante Telegraf y Grafana.

## Caso de uso general

### Contexto

Una organización necesita procesar imágenes capturadas desde distintas fuentes (por ejemplo: cámaras fijas, dispositivos móviles o sistemas embebidos) con el objetivo de:

- Detectar objetos o entidades dentro de los fotogramas.
- Almacenar dicha información junto con metadatos geográficos.
- Permitir consultas posteriores sobre los datos procesados.
- Identificar personas específicas dentro de las imágenes utilizando reconocimiento facial.

En esta primera etapa, el sistema no contará con interfaz gráfica (frontend). Toda la interacción se realizará mediante clientes genéricos de API (por ejemplo: Postman o curl).

### Flujo general del caso de uso

1. **Selección de modelo de detección**
   - Un cliente consulta los modelos disponibles mediante S1.
   - Selecciona uno de los modelos para ejecutar inferencia.

2. **Procesamiento de fotograma**
   - El cliente envía un fotograma junto con metadatos (latitud, longitud, etc.) y el modelo seleccionado al Servicio 2.
   - El sistema ejecuta la detección.
   - Se almacenan:
     - La imagen
     - Los metadatos
     - Las detecciones
   - Todo queda vinculado a un identificador único.

3. **Consulta posterior**
   - El cliente puede consultar los datos mediante S4 utilizando filtros:
     - Ubicación (lat/lon)
     - Clases detectadas
     - Metadatos adicionales
   - Obtiene una lista de resultados con referencias a las imágenes.

4. **Recuperación de imagen**
   - A partir del imageURL, el cliente consume el Servicio 3 para obtener la imagen completa o en formato thumbnail.

### Extensión: reconocimiento facial

5. **Registro de personas**
   - Se crean registros de personas en el sistema (nombre, apellido, email, etc.).

6. **Carga de imágenes y generación de embeddings**
   - Se asocian imágenes a una persona mediante el servicio correspondiente.
   - El sistema genera embeddings faciales y los almacena.

7. **Reconocimiento en nuevas imágenes**
   - Se envía una imagen al servicio de reconocimiento facial.
   - El sistema:
     - Detecta rostro
     - Genera embedding
     - Compara contra los almacenados
   - Si supera el umbral de confianza:
     - Retorna la persona identificada
   - Caso contrario:
     - Retorna resultado negativo

## Objetivo del sistema

Permitir la construcción de una plataforma backend capaz de:

- Procesar imágenes de forma desacoplada
- Persistir resultados de inferencia
- Consultar información de forma flexible
- Incorporar identificación de personas sin modificar el flujo base

## Resumen de servicios

A continuación se presenta una vista consolidada de los servicios definidos en el sistema, incluyendo sus principales responsabilidades, entradas y salidas:

| Servicio | Nombre | Entrada principal | Salida principal | Persistencia |
|---|---|---|---|---|
| S1 | Listado de modelos | - | Lista de modelos disponibles | No aplica |
| S2 | Ejecución de detección | Fotograma + metadatos + modelo | ID del proceso / resultados de detección | Imagen (objeto), metadatos (BD), detecciones (BD) |
| S3 | Obtención de fotograma | frameId | Imagen (original o thumbnail) | Lectura desde almacenamiento de objetos |
| S4 | Consulta y filtrado | Filtros (clases, lat/lon, metadatos) | Lista de resultados con imageURL, metadata y detecciones | Lectura desde base de datos |
| S5.1 | Gestión de personas | Datos de persona | Registro de persona | Base de datos |
| S5.2 | Generación de embeddings | personId + imágenes | Embeddings generados | BD (embeddings) + opcional objetos (imágenes) |
| S5.3 | Reconocimiento facial | Imagen + threshold (opcional) | Persona identificada (si aplica) | Lectura de embeddings |

### Notas

- Todos los servicios se exponen mediante APIs REST.
- Los datos generados se vinculan mediante identificadores únicos (frameId, personId, etc.).

## Identificadores principales

El sistema utiliza identificadores únicos para mantener la trazabilidad entre imágenes, metadatos, resultados de detección, personas y embeddings faciales.

| Identificador | Descripción |
|---|---|
| frameId | Identifica de forma única un fotograma procesado por el sistema. |
| modelId | Identifica el modelo de inferencia utilizado para procesar un fotograma. |
| detectionId | Identifica el resultado de una ejecución de detección. |
| personId | Identifica de forma única una persona registrada. |
| embeddingId | Identifica una representación facial generada para una persona. |
| recognitionId | Identifica un intento o resultado de reconocimiento facial. |

Todos los datos persistidos deben poder relacionarse mediante estos identificadores, garantizando trazabilidad, consistencia y posibilidad de consulta posterior.

## Backend – Servicios de inferencia (detección)

El sistema debe componerse de un conjunto de servicios orientados exclusivamente a la ejecución de modelos de detección sobre fotogramas, junto con la gestión, almacenamiento y consulta de los resultados.

### 1. Gestión de modelos

El sistema debe disponer de un repositorio de modelos almacenados en una carpeta accesible por los servicios de inferencia.

#### S1 – Listado de modelos disponibles

Todos los servicios se exponen mediante APIs REST utilizando formato JSON.

**Endpoint**
- Método: GET
- URL: `/models`
- Descripción: Retorna la lista de modelos disponibles

Expone un endpoint que retorna la lista de modelos disponibles en dicha carpeta.

Ejemplo de respuesta:
```json
["yolo11n.pt", "yolo11s.pt"]
```

### 2. Procesamiento e inferencia

#### S2 – Ejecución de modelos de detección

Todos los servicios se exponen mediante APIs REST utilizando formato JSON.

**Endpoint**
- Método: POST
- URL: `/detections`
- Descripción: Ejecuta un modelo de detección sobre un fotograma y persiste los resultados

**Entrada**
- Un fotograma (imagen)
- Metadatos asociados
- Identificador del modelo a ejecutar (modelId) (debe pertenecer al conjunto retornado por S1)

**Funcionalidad**
- Ejecuta el modelo seleccionado sobre el fotograma recibido.
- Persiste la información generada según el siguiente esquema:

**Almacenamiento**
- **Fotograma:**
  - Almacenado en un sistema de almacenamiento de objetos (por ejemplo, SeaweedFS).
  - Se le asigna un identificador único (frameId).
- **Metadatos:**
  - Almacenados en una base de datos relacional.
  - Asociados al frameId.
  - Deben incluir como mínimo:
    - Latitud
    - Longitud
  - Se recomienda un esquema flexible mediante JSON para soportar metadatos adicionales variables.
- **Resultados de detección:**
  - Almacenados en la base de datos.
  - Asociados al frameId.
  - Formato sugerido: JSON con clases detectadas, bounding boxes, scores, etc.

**Identificación**
- Todos los elementos generados en el proceso (fotograma, metadatos y resultados de detección) deben estar vinculados mediante el identificador único frameId, permitiendo su trazabilidad y posterior consulta.

**Consideración de concurrencia (opcional)**
- Se valorará que la ejecución del modelo se procese de forma asíncrona (por ejemplo, mediante hilos secundarios o colas de trabajo) para mejorar la concurrencia del sistema.

### 3. Recuperación de datos

#### S3 – Obtención de fotograma

Todos los servicios se exponen mediante APIs REST utilizando formato JSON.

**Endpoint**
- Método: GET
- URL: `/frames/{frameId}`
- Descripción: Retorna la imagen asociada a un identificador

**Parámetros**
- frameId: identificador único del fotograma
- thumbnail (opcional): booleano
  - true → retorna una versión de menor resolución
  - false o ausente → retorna la imagen original

**Entrada**
- Identificador único del fotograma (frameId)

**Salida**
- Imagen asociada al frameId

**Consideración**
- El parámetro opcional thumbnail permite solicitar una versión de menor resolución de la imagen, con el objetivo de optimizar la transferencia y visualización.

### 4. Consulta y filtrado

#### S4 – Servicio de consulta

Todos los servicios se exponen mediante APIs REST utilizando formato JSON.

**Endpoint**
- Método: GET
- URL: `/frames/search`

**Descripción**

Permite recuperar fotogramas previamente procesados en base a criterios de filtrado.

**Parámetros de consulta (filtros)**
- Clases detectadas
- Metadatos adicionales (estructura flexible)
- Latitud y longitud (obligatorios, con posibilidad de definir rangos)

**Salida**

Retorna una lista de resultados con el siguiente formato:
```json
[
  {
    "frameId": "uuid",
    "imageURL": "URL para obtener la imagen mediante S3",
    "metadata": {
      "...": "metadatos originales completos"
    },
    "detections": [
      {
        "...": "datos de detección generados por el modelo"
      }
    ]
  }
]
```

**Consideraciones adicionales**

Este servicio debe integrarse con la base de datos relacional para resolver consultas eficientes sobre metadatos y resultados de detección, manteniendo la coherencia con los identificadores únicos generados en el proceso de ingestión.

## Bocetos generales de servicios y flujo de datos (guía)

*(Diagramas visuales: Servicio 1 lista modelos disponibles en /modelos; Servicio 2 recibe fotograma + metadatos + modelo, ejecuta el modelo y almacena todo vinculado con un ID en SeaweedFS y base de datos relacional (tablas capturas, detecciones, archivos); Servicio 3 obtiene fotograma por ID desde SeaweedFS; Servicio 4 consulta de fotogramas por filtros contra la base de datos relacional.)*

**Resumen del flujo:**
1. Servicio 1 lista los modelos disponibles en /modelos.
2. Cliente elige un modelo y envía a Servicio 2: fotograma + metadatos + modelo.
3. Servicio 2 ejecuta el modelo y obtiene detecciones.
4. Servicio 2 almacena en SeaweedFS y en BD relacional, todo vinculado por un ID.

**Resumen (Servicios 3 y 4):**
1. Servicio 3 recibe un ID y retorna el fotograma almacenado en SeaweedFS.
2. Servicio 4 permite consultar por clases detectadas y metadatos (incluyendo lat/lon obligatorio) y retorna una lista con URL para obtener la imagen desde el Servicio 3, más todos los metadatos originales y las detecciones.

## Backend – Servicios de inferencia (se agrega reconocimiento facial)

El sistema se extiende incorporando capacidades de reconocimiento facial, permitiendo registrar personas, generar embeddings y realizar identificación a partir de imágenes.

### 5. Servicio de reconocimiento facial

#### 5.1. Modelo de datos de personas

Todos los servicios se exponen mediante APIs REST utilizando formato JSON.

**Endpoint**
- Método: POST
- URL: `/persons`
- Descripción: Crea una nueva persona

**(Opcional)**
- Método: GET
- URL: `/persons/{personId}`
- Descripción: Obtiene información de una persona

**Entidad: Persona**

**Estructura mínima**
- personId (UUID)
- nombre
- apellido
- email

**Extensibilidad**

Se permite agregar información adicional mediante un campo JSON:
```json
{
  "personId": "uuid",
  "nombre": "Juan",
  "apellido": "Pérez",
  "email": "juan@mail.com",
  "extra": {
    "...": "atributos adicionales"
  }
}
```

#### S5.2 – Carga y generación de embeddings

Todos los servicios se exponen mediante APIs REST utilizando formato JSON.

**Endpoint**
- Método: POST
- URL: `/persons/{personId}/embeddings`
- Descripción: permite asociar imágenes a una persona y generar las representaciones faciales (embeddings).

**Entrada**
```json
{
  "personId": "uuid",
  "images": ["imagen1", "imagen2"]
}
```

**Proceso**
- Validación de la persona (personId)
- Detección de rostro en cada imagen
- Generación de embeddings
- Asociación de los embeddings con la persona

**Salida**
```json
{
  "personId": "uuid",
  "processedImages": 5,
  "validEmbeddings": 4,
  "rejectedImages": 1
}
```

**Almacenamiento**

Imágenes (opcional, recomendado):
- Almacenamiento en sistema de objetos (ej. SeaweedFS), consistente con el almacenamiento de fotogramas del sistema principal.

Embeddings:
- Base de datos (relacional o vectorial).
```json
{
  "embeddingId": "uuid",
  "personId": "uuid",
  "vector": [...]
}
```

**Consideración de concurrencia (opcional)**

Se recomienda procesar la generación de embeddings de forma asíncrona (proceso secundario o cola), para mejorar la capacidad de respuesta del sistema.

#### S5.3 – Reconocimiento facial

Todos los servicios se exponen mediante APIs REST utilizando formato JSON.

**Endpoint**
- Método: POST
- URL: `/face-recognition`
- Descripción: Identifica una persona a partir de una imagen

**Entrada**
```json
{
  "image": "imagen",
  "threshold": 0.8
}
```

**Proceso**
- Detección de rostro
- Generación de embedding
- Comparación contra embeddings almacenados
- Selección del mejor candidato

**Salida (reconocido)**
```json
{
  "personId": "uuid",
  "nombre": "Juan",
  "apellido": "Pérez",
  "confidence": 0.87
}
```

**Salida (no reconocido)**
```json
{
  "personId": null,
  "confidence": 0.45
}
```

**Condición**

Se retorna una persona únicamente si el nivel de confianza (confidence) supera el umbral definido (threshold).

#### 5.4. Consideraciones (opcionales)

- Optimización mediante índices vectoriales (FAISS, Milvus, pgvector).
- Procesamiento concurrente para cargas masivas.
- Validación de calidad de imágenes (resolución, rostro único).
- Integración con servicios de detección para enriquecer resultados.

## Bocetos generales de servicios y flujo de datos (guía)

*(Diagrama: Backend – Servicios de inferencia con reconocimiento facial. Se agregan servicios para registrar personas, generar embeddings faciales y realizar reconocimiento a partir de imágenes. Incluye: 5.1 Modelo de datos de personas; 5.2 Servicio de carga y generación de embeddings; 5.3 Servicio de reconocimiento facial; 5.4 Consideraciones opcionales (optimización con índices vectoriales, concurrencia, calidad de imágenes, integración con servicios existentes); 5.5 Trazabilidad opcional mediante eventos. Incluye también esquema de almacenamiento: sistema de objetos SeaweedFS para imágenes de personas, y base de datos relacional/vectorial con tablas de personas, embeddings y recognition_events.)*

## 6. Evolución del sistema – Segunda entrega

La segunda entrega tiene como objetivo extender la arquitectura actual incorporando:

- Interfaz gráfica de usuario (UI)
- Mecanismos de autenticación y autorización
- Capacidades de monitoreo y observabilidad

### 6.1. Incorporación de interfaz gráfica (Frontend)

Se desarrollará una interfaz gráfica que permitirá interactuar con los servicios backend de forma más accesible.

**Objetivos**
- Facilitar la carga de imágenes (fotogramas)
- Visualizar resultados de detección
- Consultar datos filtrados
- Administrar personas para reconocimiento facial

**Funcionalidades esperadas**
- Selección de modelos de detección
- Envío de imágenes con metadatos
- Visualización de resultados (detecciones y reconocimiento)
- Consulta avanzada mediante filtros (clases, ubicación, metadatos)
- Gestión de personas:
  - Alta / baja / modificación
  - Carga de imágenes para generación de embeddings

**Consideraciones**
- El frontend será un cliente desacoplado que consumirá exclusivamente APIs REST existentes.
- No se incorporará lógica de negocio en la interfaz.

*(Boceto recomendado de frontend: dashboard "VisionAI" con secciones de Dashboard, Detecciones, Consultas, Mapa, Personas, Modelos, Subir imagen, Monitoreo, Configuración. Muestra métricas totales, gráficos de detecciones por clase, mapa de detecciones, últimas detecciones, consultas recientes y acciones rápidas.)*

### 6.2. Autenticación biométrica (opcional)

Se evaluará la incorporación de autenticación basada en reconocimiento facial.

**Descripción**

Permite autenticar usuarios mediante una imagen, utilizando los servicios de reconocimiento facial ya definidos.

**Flujo propuesto**
1. El cliente envía una imagen al sistema.
2. Se ejecuta el servicio de reconocimiento facial.
3. Si se identifica una persona válida:
   - Se considera autenticado el usuario
4. En caso contrario:
   - Se rechaza el acceso

**Consideraciones**
- El umbral de confianza debe ser configurable.
- Puede utilizarse como mecanismo complementario (ej. segundo factor).
- Su uso debe limitarse a contextos controlados.

*(Diagrama: Autenticación biométrica basada en reconocimiento facial. El usuario se autentica mediante su rostro. Se recomienda ejecutar challenges de prueba de vida antes del intento de login. Pasos: 1. Iniciar autenticación; 2. Prueba de vida (liveness); 3. Captura y reconocimiento; 4. Resultado (autenticación exitosa o fallida). Consideraciones: umbral de confianza configurable, puede combinarse con 2FA, registrar intentos exitosos y fallidos, asociar personId con usuario en Keycloak, limitar intentos y aplicar bloqueos ante actividad sospechosa. Integración con el sistema: Cliente (Frontend/App) → Servicio de reconocimiento facial → Base de datos (embeddings de personas) → ¿Confianza >= umbral? → Sí: Autenticado, token JWT emitido por Keycloak / No: Acceso denegado. Notas importantes: el reconocimiento facial se utiliza únicamente para autenticación, no para identificar automáticamente en este flujo; se recomienda usar iluminación adecuada y una cámara frontal de buena calidad; las imágenes y embeddings se procesan de forma segura y no se exponen fuera del sistema.)*

### 6.3. Seguridad – Integración con Keycloak

Se incorporará un sistema de gestión de identidad y acceso utilizando **Keycloak**.

**Objetivos**
- Centralizar autenticación y autorización
- Proteger los servicios backend
- Gestionar usuarios, roles y permisos

**Implementación**
- Uso de OAuth2 / OpenID Connect
- Emisión de tokens JWT
- Validación de tokens en cada servicio backend

**Protección de servicios**

Todos los endpoints deberán requerir autenticación.

**Ejemplo de roles**
- admin: gestión completa del sistema
- operator: carga de imágenes y consultas
- viewer: acceso de solo lectura

**Integración con reconocimiento facial**
- Posibilidad de asociar personId con usuarios de Keycloak
- Uso del reconocimiento facial como mecanismo adicional de autenticación

*(Diagrama: Autenticación y autorización con Keycloak. Keycloak gestiona usuarios, roles y emite tokens que protegen los servicios. Flujo: 1. El cliente se redirige a Keycloak para autenticarse; 2. Keycloak valida las credenciales y autentica al usuario; 3. Keycloak emite un JWT (access token); 4. El cliente incluye el token en cada petición a los servicios; 5. Los servicios validan el token (y roles/permisos) antes de procesar la solicitud. Servicios backend protegidos: S1 Listado de modelos, S2 Detección, S3 Obtención de fotograma, S4 Consulta y filtrado, S5.2 Carga embeddings, S5.3 Reconocimiento facial. Roles de ejemplo: admin (acceso total), operator (carga y consulta), viewer (solo lectura). Estándares y protocolos: OAuth2/OpenID Connect, Tokens JWT, RBAC (Role Based Access Control), validación de tokens en cada servicio.)*

### 6.4. Monitoreo y observabilidad

Se incorporarán herramientas para monitorear el estado del sistema y analizar su comportamiento.

**Stack tecnológico**
- Telegraf: recolección de métricas
- Grafana: visualización
- (Opcional) InfluxDB como almacenamiento de métricas

#### 6.4.1. Métricas a recolectar

**Servicios de detección**
- Tiempo de procesamiento por inferencia
- Cantidad de requests
- Tasa de errores

**Servicios de reconocimiento facial**
- Tiempo de generación de embeddings
- Tiempo de comparación
- Cantidad de reconocimientos exitosos vs fallidos

**Sistema general**
- Uso de CPU y memoria
- Latencia de servicios
- Throughput

#### 6.4.2. Visualización en Grafana

Se deberán construir dashboards que permitan:
- Monitoreo en tiempo real
- Detección de cuellos de botella
- Análisis de uso del sistema

**Ejemplos de paneles**
- Tiempo promedio de inferencia
- Cantidad de imágenes procesadas por minuto
- Ratio de reconocimiento exitoso
- Uso de recursos por servicio

*(Diagrama: Monitoreo y observabilidad con Telegraf + Grafana. Recolección, almacenamiento y visualización de métricas del sistema. Servicios del sistema (Servicio 1, Servicio 2, Servicio 3 Reconocimiento facial, Base de datos MongoDB, Infraestructura CPU/Memoria/Disco) → Telegraf (Agente/Recolector: CPU/Memoria, Requests/errores, Tiempos de inferencia, Reconocimientos, Embeddings, Latencia de servicios, Uso de disco/red) → InfluxDB (Almacenamiento: series de tiempo, retención de datos configurable, alta escritura y consulta rápida) → Grafana (Visualización: Dashboards, Exploración de métricas, Panel en tiempo real, Alertas, Reportes) → Usuarios/Operadores (Visualización en tiempo real, Análisis de performance, Detección de problemas, Toma de decisiones). Ejemplos de dashboards en Grafana: Tiempo promedio de inferencia, Imágenes procesadas por minuto, Reconocimiento facial (Éxitos vs Fallidos), Uso de recursos (últimas 24h), Errores por servicio. Alertas (ejemplos): Alto tiempo de inferencia (>500ms, Crítica), Alta tasa de errores (>5%, Advertencia), Fallo en servicio (Servicio 2 no disponible, OK), Uso de memoria alto (>85%, Crítica), Espacio en disco bajo (<10% libre, Advertencia).)*

### 6.5. Consideraciones de arquitectura

- Se mantiene una arquitectura desacoplada basada en servicios.
- El frontend consume APIs existentes sin alterar la lógica de negocio.
- Seguridad transversal mediante Keycloak.
- Observabilidad integrada como componente clave de operación.

### 6.6. Resultado esperado

Al finalizar la segunda entrega, el sistema contará con:

- Interfaz gráfica para interacción operativa
- Control de acceso seguro mediante autenticación y autorización
- Capacidades de monitoreo y análisis en tiempo real
- Mayor facilidad de uso sin comprometer la arquitectura backend existente

## Criterios de evaluación (orientativos)

La evaluación del trabajo considerará de forma integral los siguientes aspectos:

**Arquitectura y diseño**
- Coherencia general de la solución.
- Correcta separación de responsabilidades entre servicios.
- Uso adecuado de una arquitectura desacoplada basada en APIs.

**Funcionalidad**
- Implementación completa de los servicios definidos.
- Correcto manejo de inputs y outputs.
- Flujo funcional de procesamiento, almacenamiento y consulta.

**Persistencia y manejo de datos**
- Diseño adecuado del almacenamiento (objetos, base relacional, JSON).
- Correcta vinculación de entidades mediante identificadores únicos.
- Flexibilidad para manejar metadatos variables.

**Reconocimiento facial**
- Implementación del flujo de generación de embeddings.
- Correcto funcionamiento del reconocimiento basado en umbral de confianza.
- Integración con el resto del sistema.

**Seguridad (si aplica)**
- Uso adecuado de autenticación y autorización.
- Integración con herramientas como Keycloak.
- Protección de endpoints.

**Monitoreo (si aplica)**
- Recolección de métricas relevantes.
- Visualización clara mediante dashboards.
- Capacidad de análisis del comportamiento del sistema.

**Calidad general**
- Claridad en la documentación.
- Consistencia en el diseño de APIs.
- Manejo adecuado de errores.
- Código mantenible y bien estructurado.

**Extras valorados**
- Uso de procesamiento asíncrono.
- Consideraciones de escalabilidad.
- Extensiones o mejoras sobre la solución base.

## Entregas

**Primera entrega:**
- Hasta punto 5.4 inclusive
- Fecha de entrega: 9/6/2026
- Restricción: ausencia de frontend

En esta etapa:
- No existe interfaz gráfica
- Todos los servicios deben exponerse como APIs REST
- Deben poder ser consumidos mediante:
  - Postman
  - curl
  - scripts automatizados

**Segunda entrega (final):**
- Desde punto 6) completo y haber salvado posibles observaciones anteriores
