# Keycloak - Integracion Completa (Local y Remoto)

## Resumen de lo Implementado

Integracion de Keycloak 26.6 como proveedor OAuth2/OIDC para proteger todos los endpoints de la API REST. Se agregaron 3 usuarios de prueba con roles (admin, operator, viewer), middleware JWT en FastAPI, y proxy Nginx para el servicio Keycloak.

## Funcionalidades Probadas Localmente (20/20 tests OK)

| # | Prueba | Resultado |
|---|--------|-----------|
| 1a | admin obtiene token (roles: admin, operator, viewer) | OK |
| 1b | operator1 obtiene token (roles: operator, viewer) | OK |
| 1c | viewer1 obtiene token (roles: viewer) | OK |
| 2a | Password incorrecto es rechazado | OK |
| 2b | Token invalido/manipulado da 401 | OK |
| 3a | admin accede a /api/models | 200 OK |
| 3b | operator1 accede a /api/models | 200 OK |
| 3c | viewer1 accede a /api/models | 200 OK |
| 4a | GET /api/models con token de admin | 200 OK |
| 4b | GET /api/persons con token de admin | 200 OK |
| 4c | GET /api/frames/search con token de admin | 200 OK |
| 4d | GET /api/docs es publico (no pide token) | 200 OK |
| 5a | GET / es publico | 200 OK |
| 5b | GET /health es publico | 200 OK |
| 5c | GET /api/docs es publico | 200 OK |
| 5d | GET /api/redoc es publico | 200 OK |
| 6a | GET /api/models sin token da 401 | OK |
| 6b | GET /api/persons sin token da 401 | OK |
| 6c | GET /api/frames/search sin token da 401 | OK |
| 7a | Refresh token genera nuevo token valido | OK |

### Roles Verificados en Tokens

```
admin    -> ['viewer', 'admin', 'operator']
operator1 -> ['viewer', 'operator']
viewer1   -> ['viewer']
```

## Arquitectura

```
CLIENTE (curl/Postman/script)
  |
  | POST /auth/realms/api-detection/protocol/openid-connect/token
  | (obtener JWT via password grant)
  |
  v
NGINX (puerto 80 local / 443 remoto)
  |
  |-- /auth/* ---------> keycloak:8080
  |                        (POST /auth/realms/.../token)
  |                        (GET  /auth/realms/.../certs - JWKS)
  |
  |-- /api/* ----------> api:8000 (FastAPI)
                           |
                           verify_token()
                           |- Obtiene JWKS de keycloak:8080/auth/realms/.../certs
                           |- Valida firma RS256 del JWT
                           |- Extrae realm_roles del payload
                           |- Si no hay token o es invalido -> 401
```

## Realm: `api-detection`

Importado automaticamente desde `docker/keycloak/realm-export.json` al arrancar el contenedor Keycloak via `--import-realm`.

### Cliente: `api-backend`

| Propiedad | Valor |
|-----------|-------|
| Tipo | Publico (sin secret) |
| directAccessGrantsEnabled | true (password grant para CLI/curl) |
| standardFlowEnabled | true (para futuro frontend) |
| redirectUris | https://bfts2026.mooo.com/* |
| access.token.lifespan | 3600 segundos (1 hora) |

### Usuarios

| Username | Password | Roles |
|----------|----------|-------|
| admin | admin123 | admin, operator, viewer |
| operator1 | op123 | operator, viewer |
| viewer1 | view123 | viewer |

## Middleware JWT (`src/api/services/auth.py`)

- Implementado con `python-jose[cryptography]` (no PyJWT) por su soporte nativo de JWKS
- Obtiene las claves publicas desde `http://keycloak:8080/auth/realms/api-detection/protocol/openid-connect/certs`
- Valida firma RS256 del token usando `jwt.decode()`
- No valida `issuer` porque el token se emite con el hostname publico pero el JWKS se obtiene via HTTP interno
- Extrae `realm_roles` del payload (`realm_access.roles`)
- Se aplica a nivel de router en `main.py` via `dependencies=[Depends(verify_token)]`
- No requiere cambios en los route handlers individuales

### Endpoints

| Tipo | Endpoints |
|------|-----------|
| **Publicos** (sin token) | `/`, `/health`, `/setup_cliente.py`, `/api/docs`, `/api/redoc`, `/api/openapi.json` |
| **Protegidos** (requieren JWT) | `/api/models`, `/api/detections`, `/api/frames/*`, `/api/persons/*`, `/api/face-recognition` |

## Archivos del Proyecto

### Nuevos

| Archivo | Descripcion |
|---------|-------------|
| `docker/keycloak/realm-export.json` | Definicion del realm con client, roles y usuarios |
| `docker/keycloak/prueba_keycloak.sh` | Script de prueba local (20 tests) |
| `docker/keycloak/prueba_keycloak_remoto.sh` | Script de prueba remoto (20 tests) |
| `src/api/services/auth.py` | Middleware JWT con python-jose |
| `docs/FASE_KEYCLOAK.md` | Documentacion completa del proyecto |
| `docs/KEYCLOAK_LOCAL.md` | Este archivo |

### Modificados

| Archivo | Cambio |
|---------|--------|
| `docker-compose.yml` | Servicio keycloak agregado (produccion) |
| `docker-compose.local.yml` | Servicio keycloak agregado (local) |
| `docker/nginx.conf` | Location `/auth/` proxy a keycloak |
| `docker/nginx.local.conf` | Location `/auth/` proxy a keycloak |
| `src/api/main.py` | Import e inyeccion de verify_token en routers |
| `requirements.txt` | Agregado python-jose[cryptography]==3.3.0 |
| `.env.example` | Agregadas variables KEYCLOAK_* |

## Configuracion de Servicios Docker

### keycloak (local)

```yaml
keycloak:
  image: quay.io/keycloak/keycloak:26.6
  command: start-dev --import-realm
  environment:
    KC_BOOTSTRAP_ADMIN_USERNAME: admin
    KC_BOOTSTRAP_ADMIN_PASSWORD: admin123
    KC_DB: postgres
    KC_DB_URL: jdbc:postgresql://db:5432/detections_db
    KC_DB_USERNAME: ${POSTGRES_USER}
    KC_DB_PASSWORD: ${POSTGRES_PASSWORD}
    KC_HOSTNAME: localhost
    KC_HTTP_PORT: 8080
    KC_HTTP_RELATIVE_PATH: /auth
```

### keycloak (remoto/produccion)

```yaml
keycloak:
  image: quay.io/keycloak/keycloak:26.6
  command: start --import-realm
  environment:
    KC_BOOTSTRAP_ADMIN_USERNAME: admin
    KC_BOOTSTRAP_ADMIN_PASSWORD: admin123
    KC_DB: postgres
    KC_DB_URL: jdbc:postgresql://db:5432/detections_db
    KC_DB_USERNAME: ${POSTGRES_USER}
    KC_DB_PASSWORD: ${POSTGRES_PASSWORD}
    KC_HOSTNAME: bfts2026.mooo.com
    KC_HTTP_PORT: 8080
    KC_HTTP_ENABLED: "true"
    KC_HTTP_RELATIVE_PATH: /auth
    KC_PROXY_HEADERS: forwarded
    KC_HOSTNAME_STRICT: "false"
```

### Nginx (ambos)

```nginx
location /auth/ {
    proxy_pass http://keycloak:8080;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## Notas Tecnicas Importantes (Problemas Encontrados y Soluciones)

### 1. Keycloak 26 no usa `/auth/` por defecto

**Problema:** Keycloak 26 elimino el prefijo `/auth/` de todas sus rutas. Los endpoints son `/realms/...` en vez de `/auth/realms/...`.
**Solucion:** `KC_HTTP_RELATIVE_PATH=/auth` restaura el prefijo, manteniendo compatibilidad con Nginx y el middleware JWT.

### 2. `start` vs `start-dev`

**Problema:** `start` (produccion) requiere certificados SSL. En local no tenemos certificados.
**Solucion:** 
- Local: `command: start-dev --import-realm`
- Remoto: `command: start --import-realm` + `KC_HTTP_ENABLED=true` + `KC_PROXY_HEADERS=forwarded`

### 3. `createDatabaseIfNotExist=true` no funciona en PostgreSQL

**Problema:** Especificamos `keycloak_db?createDatabaseIfNotExist=true` pensando que PostgreSQL crearia la BD automaticamente. Eso solo funciona en MySQL.
**Solucion:** Usar la misma base de datos `detections_db` que ya existe. Keycloak crea sus propias tablas (EVENT_ENTITY, USER_ENTITY, etc.) sin conflicto con las tablas de la aplicacion.

### 4. Opciones deprecadas en Keycloak 26

| Opcion Antigua | Reemplazo | Estado |
|---------------|-----------|--------|
| `KC_PROXY=edge` | `KC_PROXY_HEADERS=forwarded` | `KC_PROXY` obsoleto |
| `KC_HOSTNAME_STRICT_HTTPS=false` | No necesario | Eliminado |

### 5. Middleware JWT: `jwt.decode()` vs `public_key.verify()`

**Problema:** La implementacion manual con `public_key.verify()` fallaba con error de tipos (`can only concatenate str (not "bytes") to str`).
**Solucion:** Usar `jwt.decode()` de python-jose que maneja correctamente la deserializacion de claves JWK y la verificacion de firma RS256.

## Como Probar Localmente

### Requisitos

- Docker y Docker Compose instalados
- Python 3 (para parsear JSON de tokens)
- Puerto 80, 8000 y 8081 libres

### Pasos

```bash
# 1. Ir al directorio del proyecto
cd ~/API-de-Deteccion-Visual

# 2. Crear .env (o copiar desde .env.example)
cp .env.example .env
# Editar .env con valores reales:
#   POSTGRES_USER=detections_user
#   POSTGRES_PASSWORD=secure_pwd_local
#   POSTGRES_DB=detections_db
#   DB_PORT=15432
#   PGADMIN_EMAIL=admin@bfts2026.mooo.com
#   PGADMIN_PASSWORD=bfts2026.
#   KEYCLOAK_ADMIN=admin
#   KEYCLOAK_ADMIN_PASSWORD=admin123

# 3. Reconstruir la API (ahora requiere python-jose)
docker compose -f docker-compose.local.yml build api

# 4. Levantar todos los servicios
docker compose -f docker-compose.local.yml up -d

# 5. Esperar a que Keycloak importe el realm (~30-60s)
docker logs -f api_detection_keycloak_local
# Buscar: "Realm 'api-detection' imported"
# Buscar: "started in"

# 6. Ejecutar el script de prueba completo (20 tests)
bash docker/keycloak/prueba_keycloak.sh

# 7. O manualmente:
# Obtener token
TOKEN=$(curl -s -X POST "http://localhost/auth/realms/api-detection/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=api-backend" \
  -d "username=admin" \
  -d "password=admin123" \
  -d "grant_type=password" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Probar endpoint protegido
curl -s -H "Authorization: Bearer $TOKEN" http://localhost/api/models

# Probar sin token (debe dar 401)
curl -s -o /dev/null -w "%{http_code}\n" http://localhost/api/models
```

## Como Desplegar en Remoto (bfts2026.mooo.com)

### 1. Subir cambios a la VM

```bash
rsync -avz --exclude 'volumes/' --exclude '.env' --exclude '__pycache__' --exclude '*.pyc' \
  ./ iwei4a2o25@143.0.100.211:~/API-de-Deteccion-Visual/
```

### 2. Desplegar en la VM

```bash
ssh iwei4a2o25@143.0.100.211
cd ~/API-de-Deteccion-Visual

# Reconstruir la API (requiere python-jose)
docker compose build api

# Levantar Keycloak y reiniciar nginx+api
docker compose up -d --force-recreate keycloak nginx api

# Ver logs de Keycloak (~60s hasta que importe el realm)
docker logs -f api_detection_keycloak
# Buscar: "Realm 'api-detection' imported"
# Buscar: "Keycloak started in"
```

### 3. Probar en remoto

```bash
# Ejecutar script de prueba
bash docker/keycloak/prueba_keycloak_remoto.sh

# O manualmente:
TOKEN=$(curl -s -X POST "https://bfts2026.mooo.com/auth/realms/api-detection/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=api-backend" \
  -d "username=admin" \
  -d "password=admin123" \
  -d "grant_type=password" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s -H "Authorization: Bearer $TOKEN" "https://bfts2026.mooo.com/api/models"

# Sin token (debe dar 401)
curl -s -o /dev/null -w "%{http_code}\n" "https://bfts2026.mooo.com/api/models"

# Endpoint publico
curl -s "https://bfts2026.mooo.com/health"
```

### 4. Consola de Administracion

```
URL:    https://bfts2026.mooo.com/auth/admin/
Usuario: admin
Password: admin123
```

### 5. Ver Roles en Token

```bash
echo $TOKEN | cut -d. -f2 | python3 -c "
import sys, base64, json
data = sys.stdin.read().strip()
padding = 4 - len(data) % 4 if len(data) % 4 else 0
payload = json.loads(base64.urlsafe_b64decode(data + '=' * padding))
print('Usuario:', payload.get('preferred_username'))
print('Roles:', payload.get('realm_access', {}).get('roles', []))
print('Email:', payload.get('email'))
"
```

## Scripts de Prueba Incluidos

| Script | Descripcion |
|--------|-------------|
| `docker/keycloak/prueba_keycloak.sh` | Prueba local (20 tests, usar con contenedores locales) |
| `docker/keycloak/prueba_keycloak_remoto.sh` | Prueba remota (20 tests, usar contra bfts2026.mooo.com) |

Ambos scripts prueban:
- Obtencion de tokens para los 3 usuarios
- Verificacion de roles en el token decodeado
- Password incorrecto (rechazado)
- Token invalido (401)
- 3 endpoints protegidos con token (models, persons, frames/search)
- 4 endpoints publicos sin token (/, /health, /api/docs, /api/redoc)
- 3 endpoints protegidos sin token (401)
- Refresh token
