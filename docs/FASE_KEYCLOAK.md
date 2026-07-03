# Fase Keycloak - Integracion OAuth2/OIDC

## Objetivo

Proteger todos los endpoints de la API REST mediante autenticacion OAuth2/OIDC con Keycloak, usando tokens JWT firmados con RS256. Implementar 3 roles de acceso (admin, operator, viewer) y 3 usuarios de prueba.

## Arquitectura General

```
CLIENTE (curl, Postman, script Python)
  |
  | 1. POST /auth/realms/api-detection/protocol/openid-connect/token
  |    (envia client_id + username + password + grant_type=password)
  | 2. Recibe JWT (access_token + refresh_token)
  |
  v
NGINX Proxy (bfts2026.mooo.com:443 HTTPS / localhost:80 HTTP)
  |
  |-- /auth/* ---------> keycloak:8080
  |                        |-- POST .../token  (emite JWT)
  |                        |-- GET  .../certs  (JWKS - claves publicas)
  |
  |-- /api/* ----------> api:8000 (FastAPI)
                           |
                           verify_token() [middleware]
                           |- Toma el header "Authorization: Bearer <token>"
                           |- Obtiene JWKS desde keycloak:8080/auth/realms/.../certs
                           |- Decodifica y verifica firma RS256
                           |- Extrae realm_roles del payload
                           |- Si token invalido/expirado/ausente -> HTTP 401
                           |- Si valido -> pasa la request al handler
```

## Decisiones Tecnicas

| Decision | Opcion Elegida | Justificacion |
|----------|---------------|---------------|
| **Version Keycloak** | 26.6 (quay.io/keycloak/keycloak:26.6) | Ultima estable con soporte LTS |
| **Ubicacion** | Mismo dominio bajo `/auth/` | Reutiliza SSL de Nginx, sin DNS adicional |
| **Base de datos** | Mismo PostgreSQL (`detections_db`) | Evita crear BD separada, Keycloak usa tablas propias |
| **Importacion** | Realm desde JSON (`--import-realm`) | Configurable,版本able, sin depender de admin console |
| **Tipo de client** | Publico (sin secret) | Password grant no requiere secret |
| **Grant type** | `directAccessGrantsEnabled: true` | Permite login con user/pass desde CLI |
| **Libreria JWT** | python-jose[cryptography] | Soporte nativo de JWKS, RS256 |
| **Proteccion** | Router-level (`dependencies=[Depends(verify_token)]`) | Un solo punto de cambio, no tocar handlers |
| **Roles** | Realm-level (no client-level) | Simples de administrar y verificar |
| **Prefijo rutas** | `KC_HTTP_RELATIVE_PATH=/auth` | Compatibilidad con Nginx y codigo existente |

## Realm: `api-detection`

Definido en `docker/keycloak/realm-export.json`.

### Cliente: `api-backend`

```json
{
  "clientId": "api-backend",
  "publicClient": true,
  "directAccessGrantsEnabled": true,
  "standardFlowEnabled": true,
  "redirectUris": ["https://bfts2026.mooo.com/*"],
  "attributes": {
    "access.token.lifespan": "3600"
  }
}
```

- **Publico**: no requiere client_secret
- **Password grant**: login directo con username + password
- **Standard flow**: preparado para futuro frontend con redirect
- **Token lifespan**: 1 hora

### Roles

| Rol | Descripcion | Permisos Tipicos |
|-----|-------------|------------------|
| `admin` | Acceso completo | CRUD en todos los recursos |
| `operator` | Ejecucion de detecciones | POST /detections, GET /models, GET /frames |
| `viewer` | Solo lectura | GET /models, GET /frames, GET /persons |

### Usuarios de Prueba

| Username | Password | Roles | Email |
|----------|----------|-------|-------|
| admin | admin123 | admin, operator, viewer | admin@bfts2026.mooo.com |
| operator1 | op123 | operator, viewer | operator1@bfts2026.mooo.com |
| viewer1 | view123 | viewer | viewer1@bfts2026.mooo.com |

## Endpoints: Protegidos vs Publicos

### Publicos (no requieren autenticacion)

| Metodo | Ruta | Proposito |
|--------|------|-----------|
| GET | `/` | Pagina principal con instrucciones |
| GET | `/health` | Healthcheck del servicio |
| GET | `/setup_cliente.py` | Descarga del script cliente |
| GET | `/api/docs` | Documentacion Swagger UI |
| GET | `/api/redoc` | Documentacion ReDoc |
| GET | `/api/openapi.json` | Esquema OpenAPI |

### Protegidos (requieren `Authorization: Bearer <JWT>`)

| Metodo | Ruta | Servicio |
|--------|------|----------|
| GET | `/api/models` | S1 - Listar modelos |
| POST | `/api/detections` | S2 - Ejecutar deteccion |
| GET | `/api/frames/{id}` | S3 - Obtener fotograma |
| GET | `/api/frames/search` | S4 - Buscar fotogramas |
| POST | `/api/persons` | S5.1 - Crear persona |
| GET | `/api/persons/{id}` | S5.1 - Obtener persona |
| GET | `/api/persons` | S5.1 - Listar personas |
| POST | `/api/persons/{id}/embeddings` | S5.2 - Generar embedding facial |
| POST | `/api/face-recognition` | S5.3 - Reconocimiento facial |

## Middleware JWT (`src/api/services/auth.py`)

```python
from jose import jwk, jwt
from jose.constants import Algorithms

def verify_token(credentials: HTTPAuthorizationCredentials) -> dict:
    # 1. Obtener header del token (para extraer kid)
    headers = jwt.get_unverified_header(token)

    # 2. Fetch JWKS desde Keycloak (cacheado)
    jwks = _fetch_jwks()

    # 3. Buscar la key RSA por kid
    rsa_key = _find_rsa_key(jwks, kid)

    # 4. Construir clave publica desde JWK
    public_key = jwk.construct(rsa_key)

    # 5. Decodificar y verificar firma RS256
    payload = jwt.decode(token, public_key, algorithms=[Algorithms.RS256],
                         options={"verify_iss": False, "verify_aud": False})

    # 6. Extraer roles
    realm_roles = payload.get("realm_access", {}).get("roles", [])

    return {"sub": ..., "preferred_username": ..., "realm_roles": realm_roles}
```

### Por que `jwt.decode()` y no manual?

La implementacion manual con `public_key.verify(message.encode(), decoded_sig)` fallaba con:
```
can only concatenate str (not "bytes") to str
```

Usar `jwt.decode()` de python-jose maneja correctamente:
- Deserializacion de claves JWK
- Verificacion de firma RS256
- Validacion de expiracion (`exp`)
- Manejo de algoritmos

## Problemas Encontrados y Soluciones

### 1. Tag de imagen incorrecto

**Error:** `manifest for quay.io/keycloak/keycloak:26 not found`
**Solucion:** Usar `26.6` (semantico) en vez de `26` (major-only).

### 2. `start` requiere certificados SSL

**Error:** `Key material not provided to setup HTTPS`
**Solucion:**
- Local: usar `start-dev` (modo desarrollo, no requiere SSL)
- Remoto: usar `start` con `KC_HTTP_ENABLED=true` (detras de Nginx que maneja SSL)

### 3. `createDatabaseIfNotExist=true` no funciona

**Error:** `FATAL: database "keycloak_db" does not exist`
**Solucion:** Usar la BD existente `detections_db` en vez de crear una separada. Keycloak crea sus tablas sin conflictos.

### 4. Opciones deprecadas de hostname v1

**Warning:** `Hostname v1 options [proxy, hostname-strict-https] are still in use`

| Deprecado | Reemplazo |
|-----------|-----------|
| `KC_PROXY=edge` | `KC_PROXY_HEADERS=forwarded` |
| `KC_HOSTNAME_STRICT_HTTPS=false` | Eliminar, no necesario |

### 5. Keycloak 26 sin prefijo `/auth/`

**Problema:** Keycloak 26 eliminó el prefijo `/auth/` de todas las rutas.
**Solucion:** `KC_HTTP_RELATIVE_PATH=/auth` restaura el prefijo.

### 6. Bug en middleware: tipos str vs bytes

**Error:** `can only concatenate str (not "bytes") to str`
**Solucion:** Usar `jwt.decode()` en lugar de `public_key.verify()` manual. Ver explicacion arriba.

## Archivos del Proyecto

### Archivos Nuevos

| Ruta | Descripcion | Relevante para |
|------|-------------|----------------|
| `docker/keycloak/realm-export.json` | Definicion del realm (client, roles, usuarios) | Todos |
| `docker/keycloak/prueba_keycloak.sh` | Script de prueba local (20 tests) | Testing |
| `docker/keycloak/prueba_keycloak_remoto.sh` | Script de prueba remoto (20 tests) | Testing |
| `src/api/services/auth.py` | Middleware JWT (verify_token) | Backend |
| `docs/FASE_KEYCLOAK.md` | Esta documentacion | Todos |
| `docs/KEYCLOAK_LOCAL.md` | Guia local + remoto paso a paso | Todos |

### Archivos Modificados

| Ruta | Cambio |
|------|--------|
| `docker-compose.yml` | Servicio `keycloak` agregado con config de produccion |
| `docker-compose.local.yml` | Servicio `keycloak` agregado con config de desarrollo |
| `docker/nginx.conf` | Location `/auth/` proxy a keycloak:8080 |
| `docker/nginx.local.conf` | Location `/auth/` proxy a keycloak:8080 |
| `src/api/main.py` | `from .services.auth import verify_token` + `dependencies=[Depends(verify_token)]` en cada router |
| `requirements.txt` | `python-jose[cryptography]==3.3.0` |
| `.env.example` | `KEYCLOAK_ADMIN`, `KEYCLOAK_ADMIN_PASSWORD`, `KEYCLOAK_REALM`, `KEYCLOAK_INTERNAL_URL` |

## Variables de Entorno

Agregar a `.env`:

```bash
# Keycloak
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=admin123
KEYCLOAK_REALM=api-detection
KEYCLOAK_INTERNAL_URL=http://keycloak:8080
```

## Configuracion Docker Compose

### Local (`docker-compose.local.yml`)

```yaml
keycloak:
  image: quay.io/keycloak/keycloak:26.6
  container_name: api_detection_keycloak_local
  command: start-dev --import-realm
  environment:
    KC_BOOTSTRAP_ADMIN_USERNAME: ${KEYCLOAK_ADMIN:-admin}
    KC_BOOTSTRAP_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD:-admin123}
    KC_DB: postgres
    KC_DB_URL: jdbc:postgresql://db:5432/${POSTGRES_DB}
    KC_DB_USERNAME: ${POSTGRES_USER}
    KC_DB_PASSWORD: ${POSTGRES_PASSWORD}
    KC_HOSTNAME: localhost
    KC_HTTP_PORT: 8080
    KC_HTTP_RELATIVE_PATH: /auth
  ports:
    - "8081:8080"
  volumes:
    - ./docker/keycloak/realm-export.json:/opt/keycloak/data/import/realm-export.json:ro
  depends_on:
    - db
```

### Remoto (`docker-compose.yml`)

```yaml
keycloak:
  image: quay.io/keycloak/keycloak:26.6
  container_name: api_detection_keycloak
  command: start --import-realm
  environment:
    KC_BOOTSTRAP_ADMIN_USERNAME: ${KEYCLOAK_ADMIN:-admin}
    KC_BOOTSTRAP_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD:-admin123}
    KC_DB: postgres
    KC_DB_URL: jdbc:postgresql://db:5432/${POSTGRES_DB}
    KC_DB_USERNAME: ${POSTGRES_USER}
    KC_DB_PASSWORD: ${POSTGRES_PASSWORD}
    KC_HOSTNAME: bfts2026.mooo.com
    KC_HTTP_PORT: 8080
    KC_HTTP_ENABLED: "true"
    KC_HTTP_RELATIVE_PATH: /auth
    KC_PROXY_HEADERS: forwarded
    KC_HOSTNAME_STRICT: "false"
  ports:
    - "8081:8080"
  volumes:
    - ./docker/keycloak/realm-export.json:/opt/keycloak/data/import/realm-export.json:ro
  depends_on:
    - db
```

## Como Probar

### Local

```bash
# 1. Asegurar variables de entorno
cp .env.example .env

# 2. Reconstruir API (tiene nueva dependencia python-jose)
docker compose -f docker-compose.local.yml build api

# 3. Levantar todo
docker compose -f docker-compose.local.yml up -d

# 4. Esperar que Keycloak importe el realm (~30-60s)
docker logs -f api_detection_keycloak_local
# Buscar: "Realm 'api-detection' imported"

# 5. Ejecutar tests
bash docker/keycloak/prueba_keycloak.sh
```

### Remoto (bfts2026.mooo.com)

```bash
# 1. Subir cambios
rsync -avz --exclude 'volumes/' --exclude '.env' --exclude '__pycache__' \
  ./ iwei4a2o25@143.0.100.211:~/API-de-Deteccion-Visual/

# 2. SSH y deploy
ssh iwei4a2o25@143.0.100.211
cd ~/API-de-Deteccion-Visual
docker compose build api
docker compose up -d --force-recreate keycloak nginx api

# 3. Probar
bash docker/keycloak/prueba_keycloak_remoto.sh
```

## Scripts de Prueba

### `docker/keycloak/prueba_keycloak.sh`

Ejecuta 20 tests contra localhost:
1. Obtiene tokens de admin, operator1, viewer1
2. Verifica que cada token tenga los roles correctos
3. Prueba password incorrecto (espera error)
4. Prueba token invalido (espera 401)
5. Prueba 3 endpoints protegidos con token (200)
6. Prueba 4 endpoints publicos sin token (200)
7. Prueba 3 endpoints protegidos sin token (401)
8. Prueba refresh token

### `docker/keycloak/prueba_keycloak_remoto.sh`

Mismos 20 tests pero contra `https://bfts2026.mooo.com`.

## Referencias

- Keycloak 26: https://www.keycloak.org/docs/latest/
- python-jose: https://github.com/mpdavis/python-jose
- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
- JWKS RFC 7517: https://datatracker.ietf.org/doc/html/rfc7517
