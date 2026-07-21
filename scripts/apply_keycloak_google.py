import os
import sys
import time
import requests

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8081")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "api-detection")
ADMIN_USER = os.getenv("KEYCLOAK_ADMIN", "admin")
ADMIN_PASS = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin123")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

GOOGLE_IDP_PAYLOAD = {
    "alias": "google",
    "displayName": "Google",
    "providerId": "google",
    "enabled": True,
    "updateProfileFirstLoginMode": "on",
    "trustEmail": True,
    "storeToken": False,
    "addReadTokenRoleOnCreate": False,
    "authenticateByDefault": False,
    "linkOnly": False,
    "firstBrokerLoginFlowAlias": "first broker login",
    "config": {
        "clientId": GOOGLE_CLIENT_ID,
        "clientSecret": GOOGLE_CLIENT_SECRET,
        "syncMode": "IMPORT",
        "defaultScope": "openid profile email",
        "acceptScopes": "openid profile email",
        "useJwksUrl": "true",
    },
}


def wait_for_keycloak(max_retries=30, delay=5):
    for i in range(max_retries):
        try:
            r = requests.get(f"{KEYCLOAK_URL}/auth/realms/master", timeout=5)
            if r.status_code == 200:
                print("Keycloak ready")
                return True
        except requests.RequestException:
            pass
        print(f"Waiting for Keycloak ({i+1}/{max_retries})...")
        time.sleep(delay)
    print("Keycloak not ready after max retries")
    return False


def get_admin_token():
    r = requests.post(
        f"{KEYCLOAK_URL}/auth/realms/master/protocol/openid-connect/token",
        data={
            "client_id": "admin-cli",
            "username": ADMIN_USER,
            "password": ADMIN_PASS,
            "grant_type": "password",
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def apply_google_idp(admin_token):
    url = f"{KEYCLOAK_URL}/auth/admin/realms/{KEYCLOAK_REALM}/identity-provider/instances/google"
    r = requests.get(url, headers={"Authorization": f"Bearer {admin_token}"}, timeout=10)

    if r.status_code == 200:
        print("Google IdP already exists, updating...")
        r = requests.put(
            url,
            headers={"Authorization": f"Bearer {admin_token}"},
            json=GOOGLE_IDP_PAYLOAD,
            timeout=10,
        )
        r.raise_for_status()
        print("Google IdP updated successfully")
    elif r.status_code == 404:
        print("Google IdP not found, creating...")
        r = requests.post(
            f"{KEYCLOAK_URL}/auth/admin/realms/{KEYCLOAK_REALM}/identity-provider/instances",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=GOOGLE_IDP_PAYLOAD,
            timeout=10,
        )
        r.raise_for_status()
        print("Google IdP created successfully")
    else:
        print(f"Unexpected response: {r.status_code} {r.text}")
        sys.exit(1)


def main():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("ERROR: GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET deben estar configuradas")
        sys.exit(1)

    if not wait_for_keycloak():
        sys.exit(1)

    admin_token = get_admin_token()
    apply_google_idp(admin_token)


if __name__ == "__main__":
    main()
