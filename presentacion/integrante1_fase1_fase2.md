# Integrante 1 -- Fase 1 (Infraestructura) + Fase 2 (S1: Listar Modelos)

---

## Fase 1: Infraestructura

### Objetivo
Desplegar la infraestructura base del sistema sobre una maquina virtual remota usando contenedores Docker. Todos los servicios se comunican a traves de una red privada aislada.

### Arquitectura General

```
   CLIENTE EXTERNO (Internet)
           |
           | HTTPS (puerto 443)
           v
   +------------------+
   |     NGINX        |  Proxy reverso + SSL
   | bfts2026.mooo.com|
   +------------------+
           |
           | Red Docker interna: api-detection-net
           |
   +--------+---------+--------+---------+
   |        |         |        |         |
   v        v         v        v         v
  API     pgAdmin   SeaweedFS SeaweedFS BD
 :8000     :80       Master   Volume  :5432
 (FastAPI)           :9333    :8080   (pgvector)
```

### Tecnologias Utilizadas

| Componente | Tecnologia | Proposito |
|---|---|---|
| Base de Datos | PostgreSQL 16 + pgvector | Datos relacionales + busqueda vectorial nativa |
| Almacenamiento | SeaweedFS (Master + Volume) | Almacenamiento de objetos distribuido |
| Proxy | Nginx 1.31.1 | Proxy reverso, SSL/TLS, ruteo de locations |
| Gestion BD | pgAdmin 4 | Interfaz web para administrar PostgreSQL |
| Contenedores | Docker Compose v3.9 | Orquestacion de servicios |
| Red | api-detection-net (bridge) | Comunicacion interna entre contenedores |
| SSL | Let's Encrypt + Certbot | Certificados TLS auto-renovables |

### Servicios Docker

#### 1. PostgreSQL + pgvector (`db`)
- Imagen oficial `pgvector/pgvector:pg16`
- Almacena: frames, detecciones, personas, embeddings faciales
- Extension pgvector permite el tipo de dato `vector(128)` para busquedas por similitud coseno
- Script `init-db.sql` ejecutado al iniciar por primera vez, creando tablas e indices
- Volumen persistente: `./volumes/pg_data/`

#### 2. SeaweedFS (`seaweed-master` + `seaweed-volume`)
- Sistema de almacenamiento de objetos distribuido (alternativa ligera a S3)
- **Master**: Coordinador, mantiene el estado de los volumenes (puerto 9333)
- **Volume**: Almacena los archivos fisicos (puerto 8080)
- Las imagenes se suben via POST al Master, que las distribuye entre los Volumes
- Volumenes persistentes: `./volumes/seaweed_master/` y `./volumes/seaweed_volume/`

#### 3. Nginx (`nginx`)
- Proxy reverso que unifica todos los servicios bajo un mismo dominio
- Redirecciona HTTP (80) a HTTPS (443) automaticamente
- Location `/api/` -> API Backend (FastAPI en puerto 8000)
- Location `/pgadmin/` -> pgAdmin
- Location `/seaweed/` -> SeaweedFS Volume (para descargar imagenes)
- Location `/seaweed-master/` -> SeaweedFS Master (monitoreo)
- Certificados SSL de Let's Encrypt montados como volumen read-only

#### 4. pgAdmin (`pgadmin`)
- Interfaz web para gestionar PostgreSQL
- Accesible en `https://bfts2026.mooo.com/pgadmin/`
- Credenciales configuradas via variables de entorno

#### 5. API Backend (`api`)
- Construido con Dockerfile propio (Python 3.11 + FastAPI)
- Se conecta a `db:5432` para PostgreSQL y `seaweed-volume:8080` para SeaweedFS
- Codigo montado como volumen para desarrollo (live reload)

### Red Docker

- Nombre: `api-detection-net`
- Driver: `bridge`
- Los contenedores se comunican por nombre de servicio (`db`, `seaweed-volume`, `api`, etc.)
- Aislada del host: solo los puertos mapeados son accesibles desde afuera

### Seguridad

- Firewall UFW: solo puertos 22 (SSH), 80 (HTTP), 443 (HTTPS), 5432 (PostgreSQL), 9333/8080 (SeaweedFS)
- Todo el trafico externo via HTTPS con Let's Encrypt
- Certificados SSL se renuevan automaticamente via Certbot
- Red Docker aislada: los contenedores no se exponen directamente a internet

### Flujo de una Peticion Tipica

1. Cliente envia `GET https://bfts2026.mooo.com/api/models`
2. DNS resuelve `bfts2026.mooo.com` a la IP del servidor (143.0.100.211)
3. Nginx recibe la peticion en puerto 443 (HTTPS)
4. Nginx valida el certificado SSL y termina el cifrado TLS
5. Nginx hace proxy_pass a `http://api:8000/api/models`
6. API procesa la peticion, consulta DB o filesystem segun corresponda
7. Respuesta viaja de vuelta: API -> Nginx -> Cliente

---

## Fase 2: Endpoint S1 -- GET /api/models

### Objetivo
Listar los modelos YOLO disponibles en el servidor para que el cliente sepa que modelo usar al ejecutar detecciones.

### Ubicacion en el codigo
- `src/api/routes/models.py`
- `src/api/schemas/models.py`

### Input
Ninguno (GET sin parametros).

### Output
```json
{
  "total": 2,
  "models": [
    {
      "name": "yolo11n.pt",
      "size": 4712345,
      "type": "yolo",
      "path": "models/local/yolo11n.pt"
    },
    {
      "name": "yolo11s.pt",
      "size": 18123456,
      "type": "yolo",
      "path": "models/local/yolo11s.pt"
    }
  ]
}
```

### Logica Interna
1. Lee el directorio `./models/local/` usando `Path.iterdir()`
2. Filtra archivos por extension: `.pt`, `.weights`, `.onnx`
3. Para cada archivo, obtiene: nombre, tamanio en bytes, tipo (deducido de la extension)
4. Ordena alfabeticamente por nombre
5. Retorna lista JSON

### Endpoints Adicionales
- `GET /api/models/{model_name}` -- Informacion detallada de un modelo individual
- `GET /api/models/{model_name}/download` -- Descarga binaria del archivo del modelo (usado por el cliente `setup_cliente.py install`)

### Tecnologias
- FastAPI (framework web)
- Pydantic (validacion de schemas)
- Pathlib (operaciones de filesystem)

### Dependencias
- No requiere Base de Datos ni SeaweedFS
- Solo lectura del sistema de archivos local
- Los modelos se almacenan fisicamente en `./models/local/` dentro del contenedor

### Prueba desde Cliente
```bash
# Via curl
curl -X GET https://bfts2026.mooo.com/api/models

# Via cliente CLI
python3 client/setup_cliente.py models list
```

### Integracion con el Ecosistema
El endpoint S1 es el punto de entrada logico del sistema:
- El cliente consulta que modelos estan disponibles
- Selecciona un modelo (ej: `yolo11n.pt`)
- Lo usa para el paso siguiente: S2 (ejecutar deteccion)

### Ejemplo de Uso Real
Un cliente CLI se conecta al servidor, lista los modelos disponibles, descarga uno, ejecuta inferencia YOLO localmente y luego sube los resultados al servidor (S2). Todo comienza con S1.
