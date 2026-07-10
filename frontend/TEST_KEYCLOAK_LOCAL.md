# Prueba Local de Keycloak con el Frontend

## Requisitos

- Docker instalado (`docker --version`)
- Node.js 18+ instalado (`node --version`)
- Puerto 8081 libre (verificar con `ss -tlnp | grep 8081` o `lsof -ti :8081`)

---

## Paso 1: Levantar Keycloak con Docker

Ejecutar en la terminal **en cualquier directorio** (el comando usa la ruta absoluta):

```bash
docker run -d \
  --name api_detection_keycloak_local \
  -p 8081:8080 \
  -e KC_BOOTSTRAP_ADMIN_USERNAME=admin \
  -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin123 \
  -e KC_HOSTNAME=localhost \
  -e KC_HTTP_PORT=8080 \
  -e KC_HTTP_RELATIVE_PATH=/auth \
  -v /home/sofia/API-de-Deteccion-Visual/docker/keycloak/realm-export.json:/opt/keycloak/data/import/realm-export.json:ro \
  quay.io/keycloak/keycloak:26.6 \
  start-dev --import-realm
```

**Salida esperada:** un hash largo (ID del contenedor).

---

## Paso 2: Esperar que Keycloak termine de iniciar

```bash
docker logs -f api_detection_keycloak_local
```

Esperar hasta ver en la terminal algo como:

```
Realm 'api-detection' imported
...
Keycloak started in 30s
```

Una vez que veas eso, presiona **Ctrl+C** para salir del log.

> Si no ves el mensaje despues de 2 minutos, algo salio mal. Revisa los logs completos con `docker logs api_detection_keycloak_local`.

---

## Paso 3: Verificar que Keycloak responde

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/auth/realms/api-detection
```

**Salida esperada:** `200`

Si ves `000` o `Connection refused`, Keycloak no esta corriendo. Volve al Paso 1.

---

## Paso 4: Iniciar el frontend (Vite dev server)

Abre una **nueva terminal** (manteniendo la anterior abierta con Docker corriendo) y ejecuta:

```bash
cd ~/API-de-Deteccion-Visual/frontend
npm run dev
```

**Salida esperada:**

```
VITE v5.x  ready in XXX ms
  Local:   http://localhost:3000/
```

> Si ves `Port 3000 is in use, trying another one...`, primero mata el proceso anterior con `lsof -ti :3000 | xargs kill -9` y ejecuta `npm run dev` de nuevo.

---

## Paso 5: Probar el login desde el navegador

1. Abri `http://localhost:3000/` en el navegador
2. Hace clic en **"Iniciar sesion con Keycloak"**
3. El navegador te redirige al formulario de login de Keycloak en `http://localhost:8081/auth/...`
4. Inicia sesion con las credenciales de prueba:

   | Usuario | Contrasena | Roles |
   |---------|-----------|-------|
   | `admin` | `admin123` | admin, operator, viewer |
   | `operator1` | `op123` | operator, viewer |
   | `viewer1` | `view123` | viewer |

5. Keycloak te redirige de vuelta a `http://localhost:3000/cargar` autenticado
6. Deberias ver la barra de navegacion con tu nombre de usuario y el icono de logout

---

## Paso 6: Limpiar cuando termines

```bash
docker stop api_detection_keycloak_local
docker rm api_detection_keycloak_local
```

Para verificar que se detuvo:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/auth/realms/api-detection
```

**Salida esperada:** `000` (conexion rechazada, el contenedor ya no existe)

---

## Solucion de problemas

### Error: `Port 8081 is already in use`

Otro contenedor o proceso esta usando el puerto 8081. Liberalo con:

```bash
# Si es un contenedor Docker
docker stop api_detection_keycloak_local && docker rm api_detection_keycloak_local

# Si es otro proceso
lsof -ti :8081 | xargs kill -9
```

### Error: `Realm 'api-detection' imported` no aparece

El archivo `realm-export.json` no se esta montando correctamente. Verifica la ruta:

```bash
ls -la /home/sofia/API-de-Deteccion-Visual/docker/keycloak/realm-export.json
```

### Error: Al hacer clic en Keycloak login no pasa nada (aparece snackbar rojo)

1. Verifica que Keycloak este corriendo: `curl http://localhost:8081/auth/realms/api-detection`
2. Verifica que el frontend este en `http://localhost:3000`
3. Revisa la consola del navegador (F12) por errores de CORS o conexion

### Error: `"parametro no valido: redirect_uri"` en la pagina de Keycloak

El `realm-export.json` no tiene `http://localhost:3000/*` en `redirectUris`. Verifica el archivo:

```bash
grep redirectUris /home/sofia/API-de-Deteccion-Visual/docker/keycloak/realm-export.json
```

Debe mostrar: `"redirectUris": ["https://bfts2026.mooo.com/*", "http://localhost:3000/*"]`

### Modo Demo siempre funciona

Si Keycloak no esta disponible, podes usar el boton **"Ingresar en Modo Demo (Bypass)"** que no requiere Keycloak y funciona con datos mock.
