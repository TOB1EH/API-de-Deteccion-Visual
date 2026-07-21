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


def list_keycloak_users() -> list[dict]:
    token = _get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    users = []
    first = 0
    max_results = 100
    while True:
        resp = requests.get(
            f"{KEYCLOAK_INTERNAL_URL}/auth/admin/realms/{KEYCLOAK_REALM}/users",
            params={"first": first, "max": max_results},
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        users.extend(batch)
        first += len(batch)
    return users


def update_keycloak_user(user_id: str, first_name: str, last_name: str, email: str) -> None:
    token = _get_admin_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "firstName": first_name,
        "lastName": last_name,
        "email": email,
    }
    resp = requests.put(
        f"{KEYCLOAK_INTERNAL_URL}/auth/admin/realms/{KEYCLOAK_REALM}/users/{user_id}",
        json=payload,
        headers=headers,
        timeout=10,
    )
    if resp.status_code >= 400:
        logger.error("Keycloak update user error %s: %s", resp.status_code, resp.text)
    resp.raise_for_status()


def get_user_realm_roles(user_id: str) -> list[str]:
    token = _get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(
        f"{KEYCLOAK_INTERNAL_URL}/auth/admin/realms/{KEYCLOAK_REALM}/users/{user_id}/role-mappings/realm",
        headers=headers,
        timeout=10,
    )
    if resp.status_code >= 400:
        logger.warning("Error fetching roles for user %s: %s", user_id, resp.status_code)
        return []
    roles = resp.json()
    return [r["name"] for r in roles if not r["name"].startswith("default-roles-")]


def execute_actions_email(user_id: str, actions: list[str] | None = None) -> None:
    if actions is None:
        actions = ["UPDATE_PASSWORD"]
    token = _get_admin_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    params = {
        "lifespan": 43200,
        "redirect_uri": "https://bfts2026.mooo.com/",
        "client_id": "api-backend",
    }
    resp = requests.put(
        f"{KEYCLOAK_INTERNAL_URL}/auth/admin/realms/{KEYCLOAK_REALM}/users/{user_id}/execute-actions-email",
        json=actions,
        params=params,
        headers=headers,
        timeout=10,
    )
    if resp.status_code >= 400:
        logger.error("Keycloak execute-actions-email error %s: %s", resp.status_code, resp.text)
    resp.raise_for_status()


def find_user_by_email(email: str) -> Optional[str]:
    token = _get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(
        f"{KEYCLOAK_INTERNAL_URL}/auth/admin/realms/{KEYCLOAK_REALM}/users?email={email}&exact=true",
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    users = resp.json()
    if users:
        return users[0].get("id")
    return None


def delete_keycloak_user(user_id: str) -> None:
    token = _get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.delete(
        f"{KEYCLOAK_INTERNAL_URL}/auth/admin/realms/{KEYCLOAK_REALM}/users/{user_id}",
        headers=headers,
        timeout=10,
    )
    if resp.status_code not in (204, 404):
        logger.warning("Error eliminando usuario Keycloak %s: %s", user_id, resp.status_code)


def set_user_password(user_id: str, password: str) -> None:
    token = _get_admin_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"type": "password", "value": password, "temporary": False}
    resp = requests.put(
        f"{KEYCLOAK_INTERNAL_URL}/auth/admin/realms/{KEYCLOAK_REALM}/users/{user_id}/reset-password",
        json=payload,
        headers=headers,
        timeout=10,
    )
    if resp.status_code >= 400:
        logger.error("Keycloak set password error %s: %s", resp.status_code, resp.text)
    resp.raise_for_status()


def clear_user_required_actions(user_id: str) -> None:
    token = _get_admin_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.get(
        f"{KEYCLOAK_INTERNAL_URL}/auth/admin/realms/{KEYCLOAK_REALM}/users/{user_id}",
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    user = resp.json()
    if not user.get("requiredActions"):
        return
    user["requiredActions"] = []
    resp = requests.put(
        f"{KEYCLOAK_INTERNAL_URL}/auth/admin/realms/{KEYCLOAK_REALM}/users/{user_id}",
        json=user,
        headers=headers,
        timeout=10,
    )
    if resp.status_code >= 400:
        logger.error("Keycloak clear requiredActions error %s: %s", resp.status_code, resp.text)
    resp.raise_for_status()


def create_keycloak_user(username: str, email: str, password: str | None = None,
                        send_email: bool = False,
                        first_name: str = "", last_name: str = "") -> str:
    existing = find_user_by_email(email)
    if existing:
        raise ValueError(f"El usuario {username} ya existe en Keycloak")

    token = _get_admin_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "username": username,
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
        "emailVerified": True,
        "enabled": True,
        "requiredActions": [],
    }
    if send_email:
        payload["requiredActions"] = ["UPDATE_PASSWORD"]

    resp = requests.post(
        f"{KEYCLOAK_INTERNAL_URL}/auth/admin/realms/{KEYCLOAK_REALM}/users",
        json=payload,
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    location = resp.headers.get("Location", "")
    user_id = location.rstrip("/").split("/")[-1] if location else ""
    if not user_id:
        user_id = find_user_by_email(email) or ""

    if user_id:
        if send_email:
            try:
                execute_actions_email(user_id, ["UPDATE_PASSWORD"])
            except Exception as e:
                logger.warning("No se pudo enviar email a %s: %s", email, e)
            return user_id
        try:
            set_user_password(user_id, password)
            try:
                clear_user_required_actions(user_id)
            except Exception as e:
                logger.warning("No se pudieron limpiar requiredActions del usuario %s: %s", user_id, e)
        except Exception:
            delete_keycloak_user(user_id)
            raise

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
    if resp.status_code >= 400:
        logger.error("Error asignando rol %s a usuario %s: %s %s", role_name, user_id, resp.status_code, resp.text)
    resp.raise_for_status()
    logger.info("Rol %s asignado a usuario %s correctamente", role_name, user_id)


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
    if resp.status_code >= 400:
        logger.error("Keycloak token error %s: %s", resp.status_code, resp.text)
    resp.raise_for_status()
    return resp.json()