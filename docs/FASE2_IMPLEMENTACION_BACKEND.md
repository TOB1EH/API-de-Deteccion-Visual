# Informe de Progreso: Fase 2 - Implementacion Endpoints S1 y S2

Este documento detalla la implementacion, arquitectura y decisiones tecnicas tomadas durante el desarrollo de la Fase 2 del sistema de Deteccion Visual. El objetivo principal fue construir la logica de negocio en el backend para listar modelos disponibles y, sobre todo, procesar y persistir las detecciones generadas por el cliente local.

## 1. Arquitectura del Backend y Estructura de Archivos

Se opto por **FastAPI** (Python 3.11) por su alto rendimiento, soporte asincrono nativo y validacion automatica de datos mediante Pydantic. La estructura del proyecto sigue un patron de diseño modular y escalable:

```text
src/
└── api/
    ├── main.py                 # Entry point, definicion de la aplicacion y middlewares
    ├── routes/                 # Controladores (Endpoints)
    │   ├── detections.py       # POST /api/detections
    │   └── models.py           # GET /api/models
    ├── schemas/                # Validacion de datos (Pydantic Models)
    │   ├── detection.py        
    │   └── model.py            
    └── services/               # Capa de Logica de Negocio y Datos
        ├── db_service.py       # Transacciones con PostgreSQL
        └── seaweedfs_client.py # Cliente REST para almacenamiento en SeaweedFS
```

### ¿Por que esta estructura?
Separar responsabilidades (Routes, Schemas, Services) permite que las rutas solo orquesten peticiones, Pydantic se encargue exclusivamente de validar los JSON de entrada/salida, y los servicios manejen las conexiones a sistemas externos. Esto facilita el testing y el mantenimiento a largo plazo.

## 2. Desarrollo de Endpoints (Routers)

### GET /api/models (S1)
Explora de manera dinamica el directorio `models/local/` buscando pesos de redes neuronales (ej. `yolo11n.pt`).
*   **Utilidad:** Permite que cualquier cliente consulte que modelos estan disponibles para inferencia antes de enviar peticiones, evitando *hardcodear* nombres en el lado del cliente.

### POST /api/detections (S2)
Es el nucleo transaccional del sistema. Su flujo de ejecucion fue diseñado para garantizar la integridad de los datos:
1.  Recibe el payload validado.
2.  Interactua con el servicio de Storage para guardar la imagen fisica.
3.  Registra los metadatos globales en la base de datos (Frame).
4.  Realiza un *batch insert* (insercion por lotes) de las coordenadas detectadas.

**Snippet de Orquestacion en `detections.py`:**
```python
# 1. Subir imagen a SeaweedFS
image_url = seaweedfs_client.upload_image(request.image_base64, frame_id)

# 2. Guardar frame en PostgreSQL
frame_saved = db_service.save_frame(
    frame_id=frame_id, model_id=request.model_id, 
    latitude=request.latitude, longitude=request.longitude, 
    image_url=image_url, detections_count=len(request.detections)
)

# 3. Guardar detecciones asociadas (Batch)
detections_saved = db_service.save_detections_batch(frame_id, detections_data)
```

## 3. Validacion Estricta de Datos (Schemas)

Se utilizaron modelos Pydantic (`schemas/detection.py`) para evitar inyeccion de datos erroneos y ahorrar procesamiento en el controlador. 

Por ejemplo, la validacion de confianza (confidence) y la correccion del namespace interno de Pydantic:

```python
class SingleDetectionRequest(BaseModel):
    class_name: str                             
    class_id: int                               
    confidence: float = Field(..., ge=0, le=1)  # Obliga a estar entre 0.0 y 1.0
    bbox: BboxSchema                            

class DetectionRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=()) # Evita el warning 'model_'
    image_base64: str                          
    model_id: str                              
    latitude: float                            
    longitude: float                           
    detections: List[SingleDetectionRequest]   
```

## 4. Diseño y Despliegue de Base de Datos

Se requeria persistir datos relacionales espaciales y, a futuro, vectores de busqueda facial. Se configuro un script de inicializacion automatica `docker/init-db.sql`.

### Diseño Relacional
*   **Tabla `frames`:** Entidad principal. Contiene `frame_id` (PK UUID), `model_id`, geolocalizacion (`latitude`, `longitude`) y la `image_url` obtenida de SeaweedFS.
*   **Tabla `detections`:** Entidad debil. Contiene la clave foranea `frame_id` vinculada en cascada. Almacena `class_name`, `confidence` y las coordenadas absolutas del Bounding Box.

### Extensiones e Integridad
*   Se habilito `uuid-ossp` para generar UUIDs nativamente y la extension `vector` preparando el entorno para la Fase 5 (reconocimiento facial).
*   **Constraints:** Se crearon chequeos geometricos directos en la BD para evitar basura.
```sql
ALTER TABLE detections 
    ADD CONSTRAINT check_bbox_valid 
    CHECK (bbox_x_min < bbox_x_max AND bbox_y_min < bbox_y_max);
```
*   **Automatizacion:** Este script SQL fue mapeado en el `docker-compose.yml` al directorio `/docker-entrypoint-initdb.d/`. De esta forma, Docker inicializa y puebla el esquema automaticamente en ambientes nuevos.

## 5. Integracion de Storage (SeaweedFS Client)

La API debe subir imagenes crudas codificadas en Base64. Se creo `seaweedfs_client.py` usando `requests`. 
El principal reto resuelto fue la correcta comunicacion con la arquitectura Master/Volume de SeaweedFS. Se configuro la URL de subida (`/submit`) apuntando obligatoriamente al Master Node (puerto 9333), ya que este es quien orquesta en que Volume Node se guardara el archivo.

**Snippet de asignacion (seaweedfs_client.py):**
```python
# El envio se realiza al Master Server, quien rutea y devuelve el FID final.
response = requests.post(
    f"{self.seaweed_master_url}/submit",
    files={'file': (f"{frame_id}.jpg", BytesIO(image_bytes), 'image/jpeg')},
    timeout=30
)
if response.status_code in (200, 201):
    file_id = response.json().get('fid')
    return f"{self.seaweed_public_url}/{file_id}.jpg"
```

## 6. Dockerizacion y Entorno Dual

Se aislo la API en un entorno Docker usando un `Dockerfile.api` eficiente basado en `python:3.11-slim`. Se crearon configuraciones duales para simplificar el ciclo de desarrollo/produccion:

*   **Entorno Local (`docker-compose.local.yml`):** Expone puertos locales, Nginx en puerto 80 sin HTTPS. SeaweedFS Volume en 8090 para evitar conflictos con otras herramientas del host (como Label Studio).
*   **Proxy Nginx (`docker/nginx.local.conf`):** Unifica los endpoints. `/api/` redirige al backend FastAPI, `/seaweed/` directamente al Storage, y `/pgadmin/` al gestor SQL. Esto simula el comportamiento CORS y de enrutamiento que habra en la maquina virtual remota.

## 7. Testing Automatizado

Se evito la dependencia exclusiva de herramientas como Postman creando un script de pruebas unitarias/integrales: `tests/test_api.py`.

### ¿Que hace el test y de que sirve?
El script simula un cliente en el entorno productivo:
1.  Verifica salud del contenedor (Health Check).
2.  Descarga un asset desde internet (`cataas.com`), lo codifica a Base64 y emula una deteccion YOLO insertando Bounding Boxes ficticios de un Gato, un Auto y una Persona.
3.  Envia el payload a `POST /api/detections`.
4.  **Validacion Bidireccional:** El script se conecta directamente a PostgreSQL (bypaseando la API) para validar que los registros se escribieron correctamente, e intenta descargar la imagen recien generada desde SeaweedFS.

**Resultados obtenidos:**
El flujo es completamente funcional. La base de datos es poblada exitosamente y los archivos fisicos son accesibles via Nginx de forma estandarizada.

```text
Iniciando validacion Fase 2 (Entorno: local)

[*] Verificando conexion a http://localhost...
  ✓ Health Check

[*] Probando GET /models...
  ✓ GET /models

[*] Descargando imagen de prueba...
  ✓ Imagen descargada (21457 bytes)

[*] Probando POST /detections (nucleo S2)...
  ✓ POST /detections

[*] Verificando persistencia en PostgreSQL (frame_id: a40b995e-8f6d-4f13-850a...)...
  ✓ BD: Frame guardado
  ✓ BD: Detecciones guardadas

[*] Verificando persistencia de imagen en SeaweedFS...
  ✓ SeaweedFS: Imagen accesible

=== RESUMEN DE PRUEBAS ===
Total:  6
Pasados: 6
Fallados: 0
Success Rate: 100.0%
```

## 8. Instrucciones para Ejecutar el Backend

### Requisitos Previos
- Docker y Docker Compose instalados
- Puerto 80, 5433, 8000, 8090, 9333 disponibles en el host local

### Pasos para levantar el entorno local

1.  **Clonar el repositorio (si no se hizo aun):**
    ```bash
    git clone <url-del-repo>
    cd API_de_Deteccion_Visual
    ```

2.  **Configurar variables de entorno:**
    ```bash
    cp .env.example .env
    # Editar .env con los valores correspondientes
    # Para local, dejar DB_PORT=5433 (evita conflicto con PostgreSQL nativo)
    ```

3.  **Inicializar y levantar todos los servicios:**
    ```bash
    docker compose -f docker-compose.local.yml up -d
    ```
    Este comando levanta 6 contenedores: PostgreSQL, SeaweedFS Master, SeaweedFS Volume, API, Nginx y pgAdmin.
    PostgreSQL ejecutara automaticamente `docker/init-db.sql` creando las tablas e indices.

4.  **Verificar que todo este corriendo:**
    ```bash
    docker compose -f docker-compose.local.yml ps
    ```
    Todos los servicios deben mostrar estado `Up`.

5.  **Ejecutar tests automatizados:**
    ```bash
    python3 tests/test_api.py --env local
    ```
    Deberia mostrar 6/6 tests pasados.

6.  **Detener el entorno:**
    ```bash
    docker compose -f docker-compose.local.yml down
    ```
    Para detener y eliminar tambien los volumenes (borra datos de BD y SeaweedFS):
    ```bash
    docker compose -f docker-compose.local.yml down -v
    ```

### Estructura de Archivos Relevante

```text
.
├── .env                        # Variables de entorno (IGNORADO por git)
├── .env.example                # Plantilla para .env (PUBLICO)
├── docker-compose.local.yml    # Configuracion Docker para desarrollo local
├── docker-compose.yml          # Configuracion Docker para VM remota (HTTPS)
├── Dockerfile.api              # Build de la imagen de la API
├── docker/
│   ├── nginx.local.conf        # Nginx para entorno local (HTTP)
│   ├── nginx.conf              # Nginx para VM remota (HTTPS + SSL)
│   └── init-db.sql             # Script SQL ejecutado automaticamente por PostgreSQL
├── src/api/                    # Codigo fuente de la API
│   ├── main.py
│   ├── routes/
│   │   ├── models.py           # GET /api/models
│   │   └── detections.py       # POST /api/detections
│   ├── schemas/
│   │   ├── model.py
│   │   └── detection.py
│   └── services/
│       ├── db_service.py
│       └── seaweedfs_client.py
├── tests/
│   ├── __init__.py
│   └── test_api.py             # Script de pruebas automatizadas
├── models/local/               # Directorio con los modelos YOLO
└── requirements.txt
```

## 9. Prueba Manual con Bruno (o Postman)

Bruno (alternativa open-source a Postman) permite probar los endpoints de forma interactiva. Al igual que Postman, soporta **variables de entorno** para cambiar entre local y remoto sin modificar las rutas.

### Configurar Variables de Entorno

En Bruno, crear dos entornos:

**Entorno: Local**
| Variable    | Valor                |
|-------------|----------------------|
| `base_url`  | `http://localhost`   |
| `host`      | `localhost`          |

**Entorno: Remoto**
| Variable    | Valor                           |
|-------------|---------------------------------|
| `base_url`  | `https://bfts2026.mooo.com`     |
| `host`      | `bfts2026.mooo.com`             |

En Postman se configura igual, en la pestana "Environments".

### Endpoints para Probar

#### S1 - GET /api/models
- **Metodo:** GET
- **URL:** `{{base_url}}/api/models`
- **Body:** Ninguno
- **Respuesta esperada:**
  ```json
  {
    "total": 1,
    "models": [
      {
        "name": "yolo11n.pt",
        "size": 5613764,
        "type": "yolo",
        "path": "models/local/yolo11n.pt"
      }
    ]
  }
  ```

#### S2 - POST /api/detections
- **Metodo:** POST
- **URL:** `{{base_url}}/api/detections`
- **Headers:** `Content-Type: application/json`
- **Body (JSON):**
  ```json
  {
    "image_base64": "data:image/jpeg;base64,/9j/4AAQ...",
    "model_id": "yolo11n.pt",
    "latitude": -34.6037,
    "longitude": -58.3816,
    "detections": [
      {
        "class_name": "person",
        "class_id": 0,
        "confidence": 0.85,
        "bbox": {
          "x_min": 10, "y_min": 20,
          "x_max": 200, "y_max": 600
        }
      }
    ],
    "metadata": {
      "camera_id": "test-cam-01",
      "source": "bruno-client"
    }
  }
  ```
- **Respuesta esperada:**
  ```json
  {
    "frame_id": "a40b995e-8f6d-4f13-850a-27e50de1e2fb",
    "image_url": "http://localhost/seaweed/5,08fc6dcf55.jpg",
    "detections_count": 1,
    "status": "processed",
    "message": "Se procesaron 1 detecciones",
    "timestamp": "2026-05-27T18:00:00.000Z"
  }
  ```

### Obtener un Base64 rapido para pruebas

```bash
# Convertir una imagen local a base64 y mostrar en pantalla
base64 -w 0 ruta/a/tu/imagen.jpg
# Copiar el output y anteponer: data:image/jpeg;base64,
```

### Cambiar entre Local y Remoto

En Bruno, para cambiar de entorno basta con seleccionar "Local" o "Remoto" en el desplegable superior derecho. La variable `{{base_url}}` se resuelve automaticamente a `http://localhost` o `https://bfts2026.mooo.com`. Esto permite probar el mismo endpoint contra diferentes servidores sin modificar la URL manualmente.

En Postman el mecanismo es identico usando "Environments" y variables con doble llave `{{variable}}`.

## Conclusion Fase 2
El sistema backend esta 100% operativo. Recibe cargas pesadas (imagenes), se integra asincronamente con el almacenamiento distribuido y respeta un modelo relacional riguroso en base de datos. Se encuentra listo para el despliegue en la infraestructura remota y para dar inicio a la construccion de la Fase 3 (Endpoints de Busqueda y Filtrado).
