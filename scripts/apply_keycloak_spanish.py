import os
import sys
import time
import requests

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8081")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "api-detection")
ADMIN_USER = os.getenv("KEYCLOAK_ADMIN", "admin")
ADMIN_PASS = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin123")


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


def apply_spanish_locale(admin_token):
    r = requests.get(
        f"{KEYCLOAK_URL}/auth/admin/realms/{KEYCLOAK_REALM}",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=10,
    )
    r.raise_for_status()
    realm = r.json()

    realm["internationalizationEnabled"] = True
    realm["supportedLocales"] = ["es", "en"]
    realm["defaultLocale"] = "es"

    r = requests.put(
        f"{KEYCLOAK_URL}/auth/admin/realms/{KEYCLOAK_REALM}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=realm,
        timeout=10,
    )
    r.raise_for_status()
    print("Locale espanol aplicado correctamente")
    return True


def main():
    if not wait_for_keycloak():
        sys.exit(1)

    admin_token = get_admin_token()
    apply_spanish_locale(admin_token)


if __name__ == "__main__":
    main()
