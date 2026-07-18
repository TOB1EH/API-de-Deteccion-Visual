import logging
import os
import requests
from typing import Optional

logger = logging.getLogger(__name__)

KEYCLOAK_INTERNAL_URL = os.getenv("KEYCLOAK_INTERNAL_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "api-detection")
KEYCLOAK_ADMIN_USER = os.getenv("KEYCLOAK_ADMIN", "admin")
KEYCLOAK_ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin123")
CLIENT_ID = "api-backend"


def _get_admin_token() -> str:
    resp = requests.post(
        f"{KEYCLOAK_INTERNAL_URL}/auth/realms/master/protocol/openid-connect/token",
        data={
            "client_id": "admin-cli",
            "username": KEYCLOAK_ADMIN_USER,
            "password": KEYCLOAK_ADMIN_PASSWORD,
            "grant_type": "password",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def create_keycloak_user(username: str, email: str, password: str) -> str:
    token = _get_admin_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "username": username,
        "email": email,
        "emailVerified": True,
        "enabled": True,
        "credentials": [{"type": "password", "value": password, "temporary": False}],
    }
    resp = requests.post(
        f"{KEYCLOAK_INTERNAL_URL}/auth/admin/realms/{KEYCLOAK_REALM}/users",
        json=payload,
        headers=headers,
        timeout=10,
    )
    if resp.status_code == 409:
        raise ValueError(f"El usuario {username} ya existe en Keycloak")
    resp.raise_for_status()
    location = resp.headers.get("Location", "")
    user_id = location.rstrip("/").split("/")[-1] if location else ""
    return user_id


def assign_realm_role_to_user(user_id: str, role_name: str) -> None:
    token = _get_admin_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    roles_resp = requests.get(
        f"{KEYCLOAK_INTERNAL_URL}/auth/admin/realms/{KEYCLOAK_REALM}/roles",
        headers=headers,
        timeout=10,
    )
    roles_resp.raise_for_status()
    roles = roles_resp.json()
    role = next((r for r in roles if r["name"] == role_name), None)
    if not role:
        logger.warning("Rol %s no encontrado en Keycloak, omitiendo asignacion", role_name)
        return
    resp = requests.post(
        f"{KEYCLOAK_INTERNAL_URL}/auth/admin/realms/{KEYCLOAK_REALM}/users/{user_id}/role-mappings/realm",
        json=[role],
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()


def get_user_token(email: str, password: str) -> dict:
    resp = requests.post(
        f"{KEYCLOAK_INTERNAL_URL}/auth/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token",
        data={
            "client_id": CLIENT_ID,
            "username": email,
            "password": password,
            "grant_type": "password",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()