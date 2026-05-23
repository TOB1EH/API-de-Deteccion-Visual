# Plan de Implementación Detallado - Primera Entrega (MVP)
**Proyecto:** API de Detección Visual y Reconocimiento Facial (SOA 2026)
**Objetivo:** Completar hasta el punto 5.4 inclusive (Backend 100% REST, sin frontend).
**Fecha límite:** 9/6/2026

Este plan está diseñado considerando el uso de la máquina virtual (VM) remota, contenedores Docker, y las tecnologías mencionadas.

---

## Fase 0: Definición Arquitectónica y Stack Tecnológico
Antes de escribir código, se deben fijar las tecnologías para evitar refactorizaciones.

1. **Lenguaje y Framework API Principal:** Node.js (Express/NestJS) o Java (Spring Boot).
2. **Servicio de IA (Inferencia):** Python (FastAPI). Dado que YOLO y librerías de face recognition son nativas de Python, lo ideal es crear un microservicio de IA que sea consumido por la API principal, o bien hacer todo el backend unificado en Python (FastAPI).
3. **Base de Datos:** PostgreSQL con la extensión `pgvector`. Cubre las necesidades relacionales (metadatos, detecciones) y la búsqueda vectorial (embeddings faciales - S5.4), evitando añadir herramientas extra como FAISS.
4. **Almacenamiento de Objetos:** SeaweedFS (desplegado en Docker).
5. **Proxy Inverso:** Nginx para exponer la API de forma segura.

---

## Fase 1: Preparación de la Infraestructura (Máquina Virtual Remota)
Configurar el entorno donde correrá el sistema.

1. **Conexión y Seguridad:**
   - Acceder por SSH a la VM de la facultad.
   - Actualizar paquetes del sistema (`apt update && apt upgrade`).
2. **Instalación de Docker y Compose:**
   - Instalar Docker Engine y Docker Compose en la VM.
3. **Redes y Puertos:**
   - Configurar el firewall (UFW/iptables) para abrir puertos SSH (22), HTTP (80) y HTTPS (443).
4. **Docker Compose Base (`docker-compose.yml`):**
   - Crear el archivo para levantar los servicios de infraestructura:
     - `db`: Contenedor de PostgreSQL (imagen `pgvector/pgvector:pg16`).
     - `storage`: Contenedor de SeaweedFS (Master y Volume).
     - `nginx`: Contenedor de Nginx (puerto 80 mapeado al host).
   - Levantar la infraestructura base: `docker compose up -d`.

---

## Fase 2: Estructura del Backend y S1 (Gestión de Modelos)
Inicializar el proyecto y crear el primer servicio.

1. **Setup del Repositorio:**
   - Inicializar el proyecto Backend (Java o JS/Python).
   - Configurar conexión a la base de datos PostgreSQL y al cliente S3 (para SeaweedFS).
2. **Carpeta de Modelos:**
   - Crear un directorio local `./models` en el servidor/contenedor.
   - Descargar los pesos de YOLO sugeridos (ej. `yolo11n.pt`, `yolo11s.pt`) y guardarlos ahí.
3. **Desarrollo del Servicio 1 (S1):**
   - **Endpoint:** `GET /models`
   - **Lógica:** Leer el directorio `./models`, listar los archivos con extensión `.pt` o `.onnx` y retornar un array JSON.
4. **Validación:** Probar con Postman que retorna `["yolo11n.pt", "yolo11s.pt"]`.

---

## Fase 3: Núcleo de Detección (Servicio 2)
Es el servicio más crítico. Se divide en ingestión, inferencia y persistencia.

1. **Esquema de Base de Datos:**
   - Crear tabla `capturas`: `id` (UUID, PK), `metadata` (JSONB), `created_at` (Timestamp).
   - Crear tabla `detecciones`: `id` (UUID, PK), `captura_id` (FK), `detecciones` (JSONB).
   - Crear tabla `archivos`: `id` (UUID, PK), `captura_id` (FK), `tipo` (varchar), `path` (varchar).
2. **Desarrollo del Servicio 2 (S2):**
   - **Endpoint:** `POST /detections`
   - **Lógica paso a paso:**
     1. Recibir petición `multipart/form-data` (Imagen + JSON de metadatos + `modelId`).
     2. Validar que `latitud` y `longitud` existan en los metadatos y que `modelId` sea válido.
     3. Generar un `frameId` (UUID).
     4. **Almacenamiento:** Subir la imagen a SeaweedFS usando el protocolo S3. Guardar la ruta en la tabla `archivos`.
     5. **Inferencia:** Cargar la imagen y pasarla por el modelo YOLO seleccionado. Obtener el array de bounding boxes, clases y confianzas. *(Consideración: si se usa procesamiento asíncrono, enviar a una cola aquí y retornar estado 202 "Processing". Para el MVP inicial, se puede hacer síncrono).*
     6. **Persistencia DB:** Insertar el registro en `capturas` (con los metadatos) e insertar el resultado de la IA en la tabla `detecciones`.
3. **Validación:** Subir imagen con Postman. Verificar en DB y SeaweedFS que los datos existan vinculados al `frameId`.

---

## Fase 4: Consulta y Recuperación (Servicios 3 y 4)
Permitir a los usuarios acceder a la información procesada.

1. **Desarrollo del Servicio 3 (S3):**
   - **Endpoint:** `GET /frames/{frameId}?thumbnail=boolean`
   - **Lógica:**
     1. Buscar el `path` de la imagen en la tabla `archivos` usando el `frameId`.
     2. Descargar imagen de SeaweedFS.
     3. Si `thumbnail=true`, redimensionar imagen en memoria (usar librerías como Sharp en JS, OpenCV/Pillow en Python, o Thumbnailator en Java).
     4. Retornar los bytes de la imagen con el `Content-Type` adecuado.
2. **Desarrollo del Servicio 4 (S4):**
   - **Endpoint:** `GET /frames/search`
   - **Lógica:**
     1. Leer Query Params: `clases`, rangos de `latitud`/`longitud`, u otros metadatos.
     2. Construir la consulta SQL dinámica. Gracias a PostgreSQL (JSONB), se pueden hacer filtros complejos:
        - Filtrar por lat/lon extrayéndolos de la columna `metadata`.
        - Filtrar por clases usando operadores de contención JSON (`@>`) sobre la tabla `detecciones`.
     3. Formatear la respuesta adjuntando la URL de S3 generada para obtener la imagen.

---

## Fase 5: Gestión de Personas y Embeddings (S5.1 y S5.2)
Implementar la base del reconocimiento facial.

1. **Esquema de Base de Datos:**
   - Crear tabla `personas`: `personId` (UUID, PK), `nombre`, `apellido`, `email`, `extra` (JSONB).
   - Crear tabla `embeddings`: `embeddingId` (UUID, PK), `personId` (FK), `vector` (tipo `vector` de pgvector).
2. **Servicio 5.1 (CRUD Personas):**
   - **Endpoints:** `POST /persons` y `GET /persons/{personId}`.
   - **Lógica:** Inserción y lectura básica en la tabla `personas`.
3. **Servicio 5.2 (Generación de Embeddings):**
   - **Endpoint:** `POST /persons/{personId}/embeddings`
   - **Lógica:**
     1. Recibir array de imágenes.
     2. Por cada imagen, ejecutar modelo detector de rostros (ej. `face_recognition` o MTCNN).
     3. Si hay un único rostro, extraer el embedding (vector numérico de 128 o 512 dimensiones).
     4. Almacenar el vector en la tabla `embeddings` asociado al `personId`.
     5. *(Opcional)*: Almacenar las imágenes en SeaweedFS en un bucket de "rostros".
     6. Retornar contador de procesadas, válidas y rechazadas.

---

## Fase 6: Motor de Reconocimiento Facial (S5.3)
La cereza del MVP: buscar la coincidencia vectorial.

1. **Desarrollo del Servicio 5.3 (S5.3):**
   - **Endpoint:** `POST /face-recognition`
   - **Lógica:**
     1. Recibir imagen y parámetro `threshold` (default 0.8).
     2. Detectar el rostro en la imagen enviada y extraer su vector embedding.
     3. Ejecutar consulta en PostgreSQL usando la distancia coseno (`<=>` de pgvector) o producto punto contra todos los registros de la tabla `embeddings`.
        `SELECT personId, (1 - (vector <=> vector_input)) AS confidence FROM embeddings ORDER BY confidence DESC LIMIT 1;`
     4. Si el `confidence` >= `threshold`, buscar los datos en la tabla `personas` y retornar JSON de "reconocido".
     5. Caso contrario, retornar "no reconocido".

---

## Fase 7: Despliegue Final, Nginx y Postman
Cerrar el ciclo preparándolo para la evaluación.

1. **Configuración de Nginx:**
   - Crear archivo `nginx.conf` mapeando el puerto 80 del exterior hacia el puerto interno del contenedor Backend (ej. 3000 o 8080).
   - Configurar nombres de dominio o IP estática si aplica.
2. **Despliegue del Backend:**
   - Dockerizar el Backend (crear `Dockerfile`).
   - Añadir el Backend al `docker-compose.yml`.
   - `docker compose up --build -d`.
3. **Colección de Postman:**
   - Crear un Workspace en Postman.
   - Definir variables de entorno (`{{baseUrl}}`).
   - Crear carpetas por servicio (Modelos, Fotogramas, Facial).
   - Añadir requests con ejemplos funcionales para S1 hasta S5.3.
   - Exportar archivo `.json` de la colección para adjuntarlo a la entrega.
4. **Pruebas Integrales:**
   - Ejecutar el flujo completo descrito en el PDF (Caso de uso general de 6 pasos).
