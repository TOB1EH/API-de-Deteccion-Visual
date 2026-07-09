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

PUBLIC_PATHS = [
    "/",
    "/health",
    "/setup_cliente.py",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/metrics",
    "/nginx-health",
]

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


def verify_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    if request.url.path in PUBLIC_PATHS:
        return {"sub": "anonymous", "roles": []}

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autorizacion requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        headers = jwt.get_unverified_header(token)
        kid = headers.get("kid")

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