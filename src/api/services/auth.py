from fastapi import Header, HTTPException, Request


def verify_token(authorization: str = Header(None), request: Request = None):
    paths_publicas = [
        "/", "/health", "/setup_cliente.py",
        "/api/docs", "/api/redoc", "/api/openapi.json",
        "/metrics", "/nginx-health",
    ]

    if request and request.url.path in paths_publicas:
        return {"sub": "anonymous", "roles": []}

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token requerido")

    return {"sub": "dev-user", "roles": ["admin"]}
