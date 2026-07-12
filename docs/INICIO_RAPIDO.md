# Inicio Rapido - Stack Local

## Requisitos

- Docker + Docker Compose
- Node.js 18+ y npm (para frontend con Vite)
- Python 3.10+ (para CLI)

## 1. Variables de entorno

El archivo `.env` en la raiz del proyecto debe tener:

```env
POSTGRES_USER=detections_user
POSTGRES_PASSWORD=bfts2026.
POSTGRES_DB=detections_db
```

## 2. Limpiar contenedores viejos (solo primera vez o tras errores)

```bash
docker compose -f docker-compose.local.yml down
docker rm api_detection_keycloak_local 2>/dev/null || true
```

## 3. Levantar toda la infraestructura

```bash
docker compose -f docker-compose.local.yml up -d
```

Esto levanta: `db`, `seaweed-master`, `seaweed-volume`, `inference-server`, `api`, `keycloak`, `pgadmin`, `nginx`, `influxdb`, `grafana`, `telegraf`, `frontend`.

## 4. Conectar Keycloak a la red Docker

Keycloak se ejecuta como contenedor standalone pero necesita comunicarse con la API via la red de Docker:

```bash
docker network connect --alias keycloak api-de-deteccion-visual_api-detection-net-local api_detection_keycloak_local
```

## 5. Verificar que todo este corriendo

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

Deben aparecer todos como `Up`. Si alguno falta, iniciarlo manualmente:

```bash
docker start <nombre_del_contenedor>
```

## 6. Iniciar frontend (Vite dev server)

```bash
cd frontend && npm run dev
```

Abre `http://localhost:3000` en el navegador.

## 7. Probar login con Keycloak

1. Abri `http://localhost:3000`
2. Click en **Iniciar sesion** (NO en modo demo)
3. En la pantalla de Keycloak, usa:
   - Usuario: `admin`
   - Contrasena: `admin123`
4. Despues del login, anda a **Cargar**, selecciona una imagen, completa los datos y subela
5. Anda a **Buscar** para ver los frames subidos
6. Click en un frame para ver el detalle con bounding boxes

## 8. URLs del stack local

| Servicio | URL |
|---|---|
| Frontend (Vite) | http://localhost:3000 |
| API FastAPI | http://localhost:8000 |
| Swagger UI | http://localhost:8000/api/docs |
| Keycloak | http://localhost:8081/auth |
| SeaweedFS Volume | http://localhost:8090 |
| pgAdmin | http://localhost:5050 |
| Grafana | http://localhost:3001 |

## 9. Probar con CLI (alternativa)

```bash
# Usar la API local
export API_BASE=http://localhost:8000

# Obtener token
TOKEN=$(curl -s -X POST http://localhost:8081/auth/realms/api-detection/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=api-backend&username=admin&password=admin123&grant_type=password" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Subir imagen
python3 client/setup_cliente.py infer ruta/imagen.jpg --model pelotas.pt
```

## 10. Troubleshooting

| Problema | Solucion |
|---|---|
| `frontend:80` host not found en nginx | Ignorar si usas Vite dev server. El contenedor `frontend` conflictua con el puerto 3000 del Vite. |
| Keycloak no termina de iniciar (`health: starting`) | Esperar 1-2 min. Si persiste, reiniciar: `docker restart api_detection_keycloak_local` |
| API devuelve 401 | No estas usando modo demo. Logeate via Keycloak primero. |
| `docker compose up -d` falla por puerto en uso | `docker rm -f <contenedor>` y reintentar. |
| La imagen subida no se ve en el detalle | Verificar que `SEAWEED_PUBLIC_URL` apunte a `http://localhost:8090` en `docker-compose.local.yml`. |
