# AGENTS.md

## Directivas
- Respuestas en espanol. Sin emojis.

## Estado del repositorio
No hay codigo implementado. El repo contiene solo:
- `PRIMERA_ENTREGA.md` -- alcance detallado del MVP (entrega **9/6/2026**)
- `Trabajo Integrador SOA 2026.pdf` -- especificacion completa
- `README.md` placeholder

## Servicios (endpoints exactos)

| # | Metodo | Ruta | Descripcion |
|---|--------|------|-------------|
| S1 | GET | `/models` | Lista modelos desde carpeta local |
| S2 | POST | `/detections` | Ejecuta deteccion sobre fotograma |
| S3 | GET | `/frames/{frameId}?thumbnail=true` | Obtiene fotograma |
| S4 | GET | `/frames/search?clases=&lat=&lon=` | Consulta y filtrado |
| S5.1 | POST | `/persons` | Crear persona |
| S5.1 | GET | `/persons/{personId}` | Obtener persona |
| S5.2 | POST | `/persons/{personId}/embeddings` | Generar embeddings faciales |
| S5.3 | POST | `/face-recognition` | Reconocimiento facial |

## Decisiones tecnicas pendientes (definir antes de codificar)
- Lenguaje(s), framework web, base de datos, almacenamiento de objetos
- Modelo de deteccion (ejemplos usan YOLO: `yolo11n.pt`, `yolo11s.pt`)
- Libreria de reconocimiento facial

## Hechos duros
- **S2 es el nucleo**. Entrada: imagen + lat/lon (obligatorio) + modelId. Persiste: imagen (object store), metadatos y detecciones (BD). Todo vinculado a un `frameId`.
- **S5.3**: threshold default `0.8`. Solo retorna persona si confidence > threshold.
- Sin interfaz grafica. Todo REST. Validar con curl/Postman.
- Identificadores unicos: `frameId`, `personId`, `detectionId`.
- Procesamiento asincrono en S2: opcional pero valorado.
- Almacenamiento de objetos sugerido: SeaweedFS (alternativa: filesystem local).
- Busqueda vectorial (punto 5.4): FAISS o pgvector, opcional.
