# Mejoras Futuras para Keycloak

## Estado Actual

Keycloak esta integrado con:
- Password grant (OAuth2/OIDC) para autenticacion
- Validacion JWT con python-jose y JWKS
- 3 roles (admin, operator, viewer) en el token
- Proteccion a nivel de router (cualquier token valido accede a todo)
- Importacion automatica del realm desde JSON

## Mejoras Opcionales

### 1. Validacion por Rol por Endpoint

**Que es:** Actualmente cualquier usuario con un token valido (viewer, operator o admin) puede acceder a cualquier endpoint protegido. Esta mejora agrega verificacion de roles especificos por endpoint.

**Ejemplo de permisos:**

| Endpoint | admin | operator | viewer |
|----------|-------|----------|--------|
| GET /api/models | Si | Si | Si |
| POST /api/detections | Si | Si | No |
| GET /api/persons | Si | Si | Si |
| POST /api/persons | Si | Si | No |
| DELETE /api/persons/{id} | Si | No | No |
| POST /api/persons/{id}/embeddings | Si | Si | No |
| POST /api/face-recognition | Si | Si | No |

**Implementacion:** Funcion helper `require_role(role: str)` que se usa como dependencia:

```python
from fastapi import Depends, HTTPException
from .services.auth import verify_token

def require_role(role: str):
    def check_role(auth=Depends(verify_token)):
        if role not in auth["realm_roles"]:
            raise HTTPException(status_code=403, detail="Rol insuficiente")
        return auth
    return Depends(check_role)

# Uso en un endpoint:
@app.post("/api/detections", dependencies=[require_role("operator")])
async def create_detection(...):
    ...
```

**Cuando agregarlo:** Inmediatamente si la consigna de la entrega exige diferenciar permisos por usuario. Caso contrario, despues de la entrega cuando se definan los roles de cada integrante.

---

### 2. Authorization Code Flow (Frontend)

**Que es:** El flujo actual (`password grant`) envia usuario y contraseña directamente a la API. Esto es inseguro para un frontend web porque las credenciales viajan por la red y se almacenan en el navegador. El `authorization code flow` redirige al usuario a la pantalla de login de Keycloak y nunca expone la contraseña al frontend.

**Flujo:**
```
1. Usuario hace clic en "Login" en el frontend
2. Frontend redirige a Keycloak:
   GET /auth/realms/api-detection/protocol/openid-connect/auth
   ?client_id=api-backend
   &redirect_uri=https://frontend.com/callback
   &response_type=code
   &scope=openid

3. Keycloak muestra pantalla de login
4. Usuario ingresa user/pass
5. Keycloak redirige al frontend con un codigo:
   https://frontend.com/callback?code=abc123

6. Frontend canjea el codigo por un token:
   POST /auth/realms/api-detection/protocol/openid-connect/token
   client_id=api-backend
   code=abc123
   grant_type=authorization_code

7. Keycloak devuelve access_token + refresh_token
```

**Cuando agregarlo:** Cuando se desarrolle un frontend web. No tiene sentido antes porque no hay interfaz grafica que redirigir.

---

### 3. Vincular personId con Usuario de Keycloak

**Que es:** Actualmente la tabla `persons` de la BD no esta relacionada con los usuarios de Keycloak. Esta mejora vincula cada `personId` con un `userId` de Keycloak.

**Implementacion:**
- Agregar columna `keycloak_user_id VARCHAR` (nullable) en la tabla `persons`
- Al crear una persona via POST /api/persons, el middleware extrae el `sub` del token y lo guarda como `keycloak_user_id`
- Nuevo endpoint: `GET /api/persons/me` que retorna la persona asociada al token actual

**Beneficios:**
- Saber que usuario de Keycloak creo cada persona
- Filtros como "mostrar solo mis personas"
- Auditoria de quien creo/modifico cada registro

**Cuando agregarlo:** En una fase de refinamiento post-entrega, cuando se necesite trazabilidad de usuarios.

---

### 4. Single Sign-On (SSO)

**Que es:** Si en el futuro hay mas aplicaciones (ej: frontend de administracion, dashboard de metricas, app mobile), todas comparten el mismo Keycloak. El usuario se loguea una vez y accede a todas sin volver a ingresar credenciales.

**Escenario:**
```
Usuario logueado en frontend-admin (app1)
  -> Sin SSO: tiene que loguearse de nuevo en el dashboard (app2)
  -> Con SSO: Keycloak ya tiene la sesion, acceso automatico
```

**Cuando agregarlo:** Cuando existan 2 o mas aplicaciones independientes que compartan usuarios. Para un proyecto con una sola API REST no agrega valor.

---

### 5. Social Login / Identity Providers (IdP)

**Que es:** Permite que los usuarios se logueen con Google, GitHub, Facebook, etc. sin necesidad de registrarse manualmente en Keycloak.

**Implementacion en Keycloak:**
- `Identity Providers` > `Add provider` > `Google`
- Configurar client ID y client secret de Google OAuth
- El usuario ve un boton "Login with Google" en la pantalla de login

**Cuando agregarlo:** Cuando el proyecto tenga usuarios reales (no solo los 3 de prueba) y se quiera simplificar el registro. Para un proyecto academico con usuarios fijos no es necesario.

---

### 6. Autenticacion Facial como Segundo Factor

**Que es:** Usar el reconocimiento facial del servicio S5.3 como un factor de autenticacion adicional. El usuario se loguea con user/pass (primer factor) y luego se toma una foto que se verifica contra su embedding facial guardado (segundo factor).

**Flujo conceptual:**
```
1. POST /auth/realms/.../token (user + pass) -> obtiene token temporal
2. POST /api/auth/verify-face (token temporal + foto) -> verifica rostro
3. Si coincide -> devuelve token final con plenos permisos
```

**Requisitos:**
- El usuario debe tener un embedding facial guardado (S5.2)
- Custom authenticator SPI en Keycloak (extension Java)
- Nuevo endpoint en la API para el paso 2

**Cuando agregarlo:** Nunca a menos que la consigna lo exija explicitamente. Es una funcionalidad experimental que requiere desarrollo en Java (SPI de Keycloak) y solo tendria sentido si el proyecto requiere autenticacion biomotrica. No hay spec que lo pida.

## Recomendacion de Prioridades

| Prioridad | Mejora | Cuando | Esfuerzo |
|-----------|--------|--------|----------|
| 1 | Rol checking por endpoint | Antes de entregar (si pide permisos granulares) | Bajo (1 funcion helper) |
| 2 | Vincular personId con Keycloak | Post-entrega | Medio (migracion BD + endpoint) |
| 3 | Authorization Code flow | Cuando haya frontend | Medio (frontend + redirect) |
| 4 | SSO | Cuando haya 2 apps | Bajo (configuracion en Keycloak) |
| 5 | Social login | Cuando haya usuarios reales | Bajo (configuracion en Keycloak) |
| 6 | Autenticacion facial | Solo si la consigna lo exige | Alto (SPI Java + endpoint facial) |

## Resumen

| # | Mejora | Prioridad | Esfuerzo | Dependencia |
|---|--------|-----------|----------|-------------|
| 1 | Rol checking por endpoint | Alta | Bajo | Ninguna |
| 2 | Vincular personId con Keycloak | Media | Medio | BD migration |
| 3 | Authorization Code flow | Baja | Medio | Frontend |
| 4 | SSO | Baja | Bajo | 2 aplicaciones |
| 5 | Social login | Baja | Bajo | Usuarios reales |
| 6 | Autenticacion facial | Ninguna | Alto | Consigna explicita |
