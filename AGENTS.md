# AGENTS.md - Guía para Agentes en Procesamiento de Imágenes y Reconocimiento Facial

## Directivas principales

- **Respuestas en español**: Toda la comunicación, comentarios y respuestas debe estar en español.
- **Sin emojis**: No usar emojis en respuestas, código ni comentarios.

## Visión del proyecto

Sistema backend SOA para procesamiento de fotogramas con detección y reconocimiento facial. La arquitectura se divide en dos etapas:

**Etapa 1 (Actual)**: Backend sin interfaz gráfica, funcionalidad expuesta mediante APIs REST.
- Detección de objetos en fotogramas
- Almacenamiento de imágenes, metadatos y resultados
- Consultas flexibles sobre datos procesados
- Reconocimiento facial con embeddings

**Etapa 2 (Futura)**: Interfaz gráfica, autenticación con Keycloak, biometría y monitoreo (Telegraf/Grafana).

## Servicios definidos

El sistema proporciona cinco servicios principales descritos en el especificación:

| Servicio | Nombre | Entrada | Salida | Persistencia |
|----------|--------|---------|--------|--------------|
| S1 | Listado de modelos | - | Lista de modelos disponibles | No |
| S2 | Ejecución de detección | Fotograma + metadatos + modelo | ID proceso / detecciones | Imagen + BD |
| S3 | Obtención de fotograma | frameId | Imagen (original/thumbnail) | Lectura objetos |
| S4 | Consulta y filtrado | Filtros (clases, lat/lon) | Lista con imageURL y detecciones | Lectura BD |
| S5.1 | Gestión de personas | Datos persona | Registro persona | BD |
| S5.2 | Generación de embeddings | personId + imágenes | Embeddings generados | BD + objetos |
| S5.3 | Reconocimiento facial | Imagen | Persona identificada o negativo | Comparación embeddings |

## Arquitectura de datos

- **Almacenamiento de objetos**: Imágenes (originales y thumbnails)
- **Base de datos**: Metadatos, detecciones, personas, embeddings faciales
- **Trazabilidad**: Cada procesamiento vinculado a identificador único

## Flujo crítico de detección (S2)

1. Cliente envía fotograma + metadatos (lat/lon) + modelo seleccionado
2. Sistema ejecuta detección mediante modelo especificado
3. Se persisten: imagen, metadatos, resultados de detección
4. Retorna ID del proceso para posteriores consultas

## Flujo de reconocimiento facial (S5)

1. Registro de personas (nombre, apellido, email, etc.)
2. Asociación de imágenes a persona y generación de embeddings
3. Envío de imagen desconocida al servicio de reconocimiento
4. Detección de rostro, generación de embedding y comparación
5. Retorna persona si supera umbral de confianza, sino resultado negativo

## Estructura esperada del repositorio

La estructura se define en función de los servicios y módulos core:

- Servicios REST (S1-S5) con sus handlers y rutas
- Modelos de detección (integración e inferencia)
- Gestión de almacenamiento de objetos (imágenes)
- Capa de persistencia (BD)
- Módulo de reconocimiento facial (embeddings y comparación)
- Especificación: archivo `Trabajo Integrador SOA 2026.pdf` en raíz

## Consideraciones para agentes

- **Múltiples lenguajes**: El proyecto usa múltiples lenguajes según módulo (precisar en implementación específica)
- **Sin interfaz gráfica en Etapa 1**: Validar funcionalidad exclusivamente mediante APIs REST
- **Desacoplamiento**: Servicios deben ser independientes y consumibles vía HTTP
- **Metadatos geográficos**: Lat/lon son campos obligatorios en procesamiento de frames
- **Umbral de confianza facial**: Configurar y documentar en reconocimiento facial
- **Documentación de especificación**: El archivo PDF contiene definición completa; consultarlo ante ambigüedades
