import logging
import os
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwk, jwt
from jose.constants import Algorithms
import requests

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

KEYCLOAK_INTERNAL_URL = os.getenv(
    "KEYCLOAK_INTERNAL_URL",
    "http://keycloak:8080",
)
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "api-detection")
JWKS_URL = f"{KEYCLOAK_INTERNAL_URL}/auth/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
FACIAL_JWT_SECRET = os.getenv("FACIAL_JWT_SECRET", "facial-jwt-secret-change-in-production")
FACIAL_JWT_ALGORITHM = "HS256"

PUBLIC_PATHS = [
    "/",
    "/health",
    "/setup_cliente.py",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/metrics",
    "/nginx-health",
    "/api/face-recognition",
    "/api/auth/register",
    "/api/auth/login/facial",
]

# Rutas internas que no requieren autenticacion cuando la llamada
# proviene de la red interna de Docker (inference-server, etc.)
INTERNAL_PATHS = [
    "/api/persons/",
    "/api/face-recognition",
]


def _is_internal_request(request: Request) -> bool:
    """Detecta si la request viene de la red interna de Docker (172.x.x.x o 10.x.x.x)"""
    client_host = request.client.host if request.client else ""
    return client_host.startswith("172.") or client_host.startswith("10.") or client_host == "127.0.0.1"

_jwks_cache = None


def _fetch_jwks() -> list[dict]:
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    try:
        resp = requests.get(JWKS_URL, timeout=5)
        resp.raise_for_status()
        _jwks_cache = resp.json().get("keys", [])
        logger.info("JWKS fetched successfully (%d keys)", len(_jwks_cache))
        return _jwks_cache
    except requests.RequestException as e:
        logger.warning("Failed to fetch JWKS: %s", e)
        return []


def _find_rsa_key(jwks: list[dict], kid: str | None) -> dict | None:
    for key in jwks:
        if key.get("kid") == kid:
            return key
    if jwks:
        return jwks[0]
    return None


def create_facial_token(person_id: str, email: str, roles: list[str], keycloak_user_id: str | None = None) -> str:
    from datetime import datetime, timezone, timedelta
    payload = {
        "sub": keycloak_user_id or person_id,
        "person_id": person_id,
        "email": email,
        "preferred_username": email,
        "realm_access": {"roles": roles},
        "iss": "api-deteccion-visual",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, FACIAL_JWT_SECRET, algorithm=FACIAL_JWT_ALGORITHM)


def verify_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    path = request.url.path

    if path in PUBLIC_PATHS:
        return {"sub": "anonymous", "roles": []}

    if credentials is None:
        # Permitir llamadas internas (inference-server) a rutas especificas
        for internal_path in INTERNAL_PATHS:
            if path.startswith(internal_path) and _is_internal_request(request):
                return {"sub": "internal", "roles": ["internal"]}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autorizacion requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        headers = jwt.get_unverified_header(token)
        kid = headers.get("kid")

        # Si tiene kid, es token de Keycloak (RS256 via JWKS)
        if kid:
            jwks = _fetch_jwks()
            if not jwks:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="No se pudieron obtener claves de Keycloak",
                )
            rsa_key = _find_rsa_key(jwks, kid)
            if rsa_key is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Clave RSA no encontrada en JWKS",
                )
            public_key = jwk.construct(rsa_key)
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[Algorithms.RS256],
                options={"verify_iss": False, "verify_aud": False},
            )
        else:
            # Sin kid: es token facial firmado con HS256
            payload = jwt.decode(
                token,
                FACIAL_JWT_SECRET,
                algorithms=[FACIAL_JWT_ALGORITHM],
                options={"verify_iss": False, "verify_aud": False},
            )

        realm_roles = payload.get("realm_access", {}).get("roles", [])
        return {
            "sub": payload.get("sub"),
            "preferred_username": payload.get("preferred_username"),
            "email": payload.get("email"),
            "realm_roles": realm_roles,
            "payload": payload,
        }

    except jwt.JWTError as e:
        logger.warning("JWT invalido: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token invalido: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error validando token JWT")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token invalido: {str(e)}",
        )


def require_role(roles: list[str]):
    """
    Dependencia de FastAPI que verifica que el token autenticado tenga al menos
    uno de los roles especificados. Se usa como dependencia adicional en rutas
    que requieren permisos especificos.

    Uso:
        @router.post("/api/detections", dependencies=[Depends(require_role(["admin", "operator"]))])
        async def create_detection(...):
            ...

    Args:
        roles: Lista de roles permitidos (ej: ["admin"], ["admin", "operator"])

    Retorna:
        dict con los datos del token si el rol es valido

    Lanza:
        403 Forbidden si el token no tiene ningun rol requerido
    """
    def _role_checker(auth_data: dict = Depends(verify_token)):
        # Extraer roles del token JWT
        user_roles = auth_data.get("realm_roles", [])
        # Verificar si algun rol requerido esta presente
        if not any(role in user_roles for role in roles):
            logger.warning(
                "Acceso denegado por rol. Usuario: %s, roles: %s, requeridos: %s",
                auth_data.get("preferred_username"),
                user_roles,
                roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere uno de estos roles: {', '.join(roles)}",
            )
        return auth_data
    return _role_checker