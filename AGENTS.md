# AGENTS.md

## Directivas
- Respuestas en espanol. Sin emojis.

## Estado actual

### Primera entrega (MVP) - COMPLETADA (9/6/2026)

Todos los servicios S1-S5.3 implementados, desplegados y funcionales:

| S# | Endpoint | Estado |
|----|----------|--------|
| S1 | GET /api/models | OK |
| S2 | POST /api/detections | OK |
| S3 | GET /api/frames/{id}?thumbnail | OK |
| S4 | GET /api/frames/search | OK |
| S5.1 | POST/GET /api/persons | OK |
| S5.2 | POST /api/persons/{id}/embeddings | OK |
| S5.3 | POST /api/face-recognition | OK |

### Infraestructura actual

**Servidor remoto (bfts2026.mooo.com):**
- Nginx (HTTPS) redirige /api/ a FastAPI
- PostgreSQL 16 + pgvector
- SeaweedFS (almacenamiento de objetos)
- pgAdmin accesible en /pgadmin/
- Let's Encrypt SSL activo

**Nodo local (PC del usuario):**
- inference-server (Docker: YOLO + DeepFace) en puerto 8001
- CLI setup_cliente.py descargable desde GET /setup_cliente.py

### Stack tecnologico

| Componente | Tecnologia |
|---|---|
| Backend API | Python FastAPI |
| Deteccion | Ultralytics YOLO |
| Reconocimiento facial | DeepFace (Facenet) |
| BD | PostgreSQL 16 + pgvector |
| Storage | SeaweedFS |
| Proxy | Nginx + Let's Encrypt |

## Problemas conocidos (a corregir)

1. Reconocimiento facial: falla con fotos de distinto angulo/iluminacion. Solucion: multiples embeddings por persona.
2. Sin indice IVFFLAT en pgvector (degradara performance al crecer).
3. Dockerfile.api tiene dependencias obsoletas (libpq-dev, gcc).
4. Errores 404 del inference-server muestran traceback poco claro.
5. Docstring del CLI desactualizado.

## Proxima etapa: Segunda entrega

### Pendiente de implementar

| Modulo | Descripcion |
|---|---|
| Keycloak | Autenticacion OAuth2/JWT, roles admin/operator/viewer |
| Frontend | UI web (React/Vue) que consuma las APIs |
| Monitoreo | Telegraf + InfluxDB + Grafana |
| Auth biometrica | Login por reconocimiento facial (opcional) |

### Distribucion de trabajo

| Miembro | Tareas |
|---|---|
| A | Multiples embeddings + auth biometrica |
| B | Frontend web + indice pgvector + limpiar Dockerfile |
| C | Keycloak + Monitoreo (Grafana) |
| D | Errores CLI + docstring + ayudar integracion |

### Archivos de referencia en docs/

| Archivo | Contenido |
|---|---|
| FASE1_INFRAESTRUCTURA.md | Infraestructura completa |
| FASE2_SEGUNDA_ENTREGA.md | Plan detallado con tareas, codigo y archivos |
| DISTRIBUCION_TRABAJO.md | Roles, roadmap semanal y ramas Git |
| RESUMEN_FINAL.md | Resumen simple del desarrollo final |
| PRIMERA_ENTREGA.md | Alcance del MVP entregado |

### Acceso remoto

| Servicio | URL | Credenciales |
|---|---|---|
| API Health | https://bfts2026.mooo.com/ | - |
| Swagger UI | https://bfts2026.mooo.com/api/docs | - |
| pgAdmin | https://bfts2026.mooo.com/pgadmin/ | admin@bfts2026.mooo.com / bfts2026. |
| SeaweedFS | https://bfts2026.mooo.com/seaweed/ | - |
| Script CLI | https://bfts2026.mooo.com/setup_cliente.py | - |
