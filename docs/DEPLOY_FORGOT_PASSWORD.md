# Deploy: Recordar Contrasena (Forgot Password)

## Pre-requisitos

- Keycloak corriendo en remoto
- Acceso SSH a la VM (`bfts2026.mooo.com`)
- Gmail App Password generada (ver mas abajo)

## Pasos

### 1. Agregar `SMTP_PASSWORD` al `.env` en la VM

```bash
ssh <user>@bfts2026.mooo.com
cd /ruta/al/proyecto
echo 'SMTP_PASSWORD=zdld tbba xinh mzzb' >> .env
```

### 2. Sincronizar cambios del branch

```bash
git fetch origin
git checkout feature/forgot_pass  # o main si ya se mergeo
git pull
```

### 3. Recrear contenedores (si hay cambios de codigo)

```bash
docker compose up -d --build
```

### 4. Ejecutar script de configuracion SMTP

Una sola vez, despues de que Keycloak este ready:

```bash
python3 scripts/apply_keycloak_smtp.py
```

Esto habilita `resetPasswordAllowed: true` y configura el servidor SMTP (Gmail) con la password del `.env`.

Verificar en logs que no haya errores de SMTP:

```bash
docker compose logs keycloak | grep -i smtp
```

### 5. Probar

- Ir a `https://bfts2026.mooo.com/auth/realms/api-detection/account/`
- Hacer clic en "Sign In" -> "Forgot Password?"
- Ingresar el email del usuario registrado en Keycloak
- Revisar la bandeja de entrada (SPAM tambien)

## Notas

| Aspecto | Detalle |
|---------|---------|
| **SMTP** | Gmail App Password. `from` usa `abrambilla804@alumnos.iua.edu.ar`. |
| **Destinatarios** | Funciona para Gmail/Hotmail. NO para correos @unc.edu.ar (rebota por SPF/DMARC). |
| **Script** | `scripts/apply_keycloak_smtp.py` se conecta a la admin API de Keycloak con las credenciales `KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD` del `.env`. |
| **Token** | Si Keycloak da `401` al ejecutar el script, verificar que `KEYCLOAK_ADMIN_PASSWORD` en `.env` coincida con la del contenedor Keycloak. |

## Si falla: depuracion manual

```bash
# Ver config actual del realm via API
curl -s -X POST "https://bfts2026.mooo.com/auth/realms/master/protocol/openid-connect/token" \
  -d "client_id=admin-cli" \
  -d "username=admin" \
  -d "password=$ADMIN_PASS" \
  -d "grant_type=password" | jq -r '.access_token'
```
(Usar el token en `Authorization: Bearer` para GET/PUT en `/auth/admin/realms/api-detection`)
