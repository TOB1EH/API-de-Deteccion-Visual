# API de Deteccion Visual

## Plan de Organización del Equipo (MVP)

Teniendo en cuenta las fases del proyecto y la fecha límite de entrega (9 de junio de 2026), el desarrollo se divide en 4 roles para poder trabajar en paralelo sin bloqueos.

### Pasos Iniciales (Todo el Equipo)
**Fase 0 (Definición Tecnológica):**
1. Definir lenguaje de la API principal (ej. Java Spring Boot, JS/TS con Node, o Python con FastAPI).
2. Decidir si la IA (YOLO y Face Recognition) correrá integrada en el código o como un microservicio interno en Python.

---

### Distribución de Roles

#### 1. Miembro A: Infraestructura, DevOps y Pruebas (Fase 1 y Fase 7)
Se asegura de que el entorno local/remoto esté listo y prepara el empaquetado final.
- **Responsabilidades:** 
  - Configurar la Máquina Virtual (SSH, Firewall). 
  - Archivo `docker-compose.yml` para levantar PostgreSQL (pgvector), SeaweedFS y Nginx.
  - Dockerizar el código final de la API.
  - Configurar proxy inverso Nginx.
  - Recolectar endpoints de los demás para armar la colección unificada en Postman.

#### 2. Miembro B: Backend Core - Arquitectura e Ingesta (Fase 2 y Fase 3)
Crea la base del proyecto y el endpoint de inferencia principal (S2).
- **Responsabilidades:** 
  - Inicializar repo Backend y conexión a DB / S3 (SeaweedFS).
  - **S1:** Listar modelos locales (`GET /models`).
  - **S2:** Ingesta principal (imagen + metadatos). Guarda imagen en file system, ejecuta YOLO y persiste en BD (`POST /detections`).

#### 3. Miembro C: Backend Data - Búsqueda y Recuperación (Fase 4 y Fase 5.1)
Trabaja sobre los metadatos y la recuperación de imágenes.
- **Responsabilidades:** 
  - **S3:** Recuperar imagen y generar thumbnail en memoria (`GET /frames/{frameId}`).
  - **S4:** Consultas dinámicas sobre JSONB y geolocalización (`GET /frames/search`).
  - **S5.1:** CRUD lógico de Personas (`POST /persons`, `GET /persons/{id}`).

#### 4. Miembro D: Especialista IA y Face Recognition (Fase 5.2, Fase 6)
Especialista en integración de modelos predictivos y búsqueda vectorial.
- **Responsabilidades:**
  - Dar soporte a backend con la integración de YOLO.
  - **S5.2:** Detección de rostros, generación de embeddings (128/512 dim) y persistencia con `pgvector`.
  - **S5.3:** Endpoint que busca coincidencias en Base de Datos usando distancia coseno y umbral default de 0.8 (`POST /face-recognition`).

---

### Flujo de Trabajo Sugerido
- **Ramas Independientes:** Ramas de Git por área (ej. `feat/infra`, `feat/busqueda`).
- **Contratos (Mocks):** Acuerden primero la estructura JSON de cada endpoint para que los que dependen de ese dato puedan avanzar usando datos ficticios (Mocks).
- **Reuniones Cortas:** Charlas de 10 minutos para destrabar dependencias cruzadas y evitar conflictos al juntar partes.
