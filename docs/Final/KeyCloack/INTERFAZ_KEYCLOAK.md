# Interfaz de Administracion de Keycloak

## Acceso

Keycloak incluye una interfaz web de administracion que se sirve a traves del mismo Nginx que el resto del proyecto.

### Local
```
URL:      http://localhost/auth/admin/
Usuario:  admin
Password: admin123
```

### Remoto
```
URL:      https://bfts2026.mooo.com/auth/admin/
Usuario:  admin
Password: admin123
```

No requiere instalacion adicional -- Keycloak trae la interfaz incorporada.

## Para Que Sirve la Interfaz

La consola de administracion permite gestionar todos los aspectos de Keycloak sin tocar archivos JSON ni reiniciar contenedores. Es util para:

### 1. Gestion de Usuarios

Desde `Users` podes:
- **Crear usuarios nuevos**: `Users` > `Add user` > completar datos > `Save`
- **Asignar password**: entrar al usuario > `Credentials` > `Set password` > desmarcar `Temporary`
- **Asignar roles**: entrar al usuario > `Role mapping` > `Assign role` > seleccionar `admin`, `operator` o `viewer`
- **Ver sesiones activas**: entrar al usuario > `Sessions` > ver desde que IP y cuando se logueo
- **Deshabilitar usuario**: entrar al usuario > `Actions` > desmarcar `Enabled`
- **Ver eventos del usuario**: entrar al usuario > `User events`

### 2. Gestion de Roles

Desde `Realm roles` podes:
- **Ver roles existentes**: `admin`, `operator`, `viewer`
- **Crear nuevos roles** (ej: `supervisor`, `analyst`)
- **Eliminar roles** que no se usen
- **Ver que usuarios tienen cada rol**

### 3. Configuracion de Tokens

Desde `Realm settings` > `Tokens` podes:
- **Cambiar tiempo de expiracion**: `Access Token Lifespan` (default: 1 hora)
- **Cambiar tiempo de refresh**: `Refresh Token Lifespan` (default: 30 minutos)
- **Configurar politicas de sesion**: session idle timeout, max sessions, etc.

### 4. Gestion del Cliente

Desde `Clients` > `api-backend` podes:
- **Ver configuracion del cliente**: URLs de redirect, grant types habilitados
- **Ver scopes**: que informacion incluye el token (profile, email, roles)
- **Ver mapeo de atributos**: que claims se incluyen en el JWT
- **Descargar configuracion**: JSON de config para integrar en otros lenguajes

### 5. Monitoreo y Seguridad

Desde `Realm settings` > `General` podes:
- **Ver el estado del realm**: habilitado/deshabilitado
- **Ver eventos de seguridad**: login fallidos, tokens emitidos
- **Configurar politicas de password**: longitud, caracteres especiales, expiracion
- **Configurar CORS**: origenes permitidos

## Capturas de las Secciones Principales

### Login
```
http://localhost/auth/admin/
```
Ingresar con `admin` / `admin123`. Se ve la pagina principal del realm `api-detection` con informacion general: cantidad de usuarios, clientes, roles.

### Panel de Usuarios
`Users` muestra tabla con:
- Username
- Email
- Email verified (si/no)
- Enabled (si/no)
- Created

Al hacer clic en un usuario se ven pestanas:
- **Details**: nombre, apellido, email, atributos
- **Credentials**: password y tipo de autenticacion
- **Role mapping**: roles asignados (realm-level y client-level)
- **Groups**: grupos del usuario
- **Sessions**: sesiones activas
- **Consents**: permisos otorgados a clientes

### Panel de Roles
`Realm roles` muestra los 3 roles. Al hacer clic en uno:
- **Details**: nombre y descripcion
- **Users in role**: lista de usuarios que tienen este rol
- **Associated roles**: roles compuestos (si un rol incluye otro)

### Panel del Cliente
`Clients` > `api-backend` muestra:
- **Settings**: client ID, name, description, enabled
- **Client scopes**: scopes asignados por defecto
- **Advanced**: access token lifespan override, logout URLs
- **Roles**: roles especificos del cliente (si los hay)

## Como Probar que la Interfaz Funciona

### Paso 1: Verificar que la consola carga
Abrir en el navegador:
```
http://localhost/auth/admin/
```
Se debe ver la pantalla de login de Keycloak.

### Paso 2: Iniciar sesion
Usuario: `admin`
Password: `admin123`

### Paso 3: Verificar el realm
En la pagina principal debe aparecer `api-detection` como el realm activo.

### Paso 4: Ver los usuarios
Ir a `Users` y verificar que aparecen `admin`, `operator1` y `viewer1`.

### Paso 5: Ver los roles
Ir a `Realm roles` y verificar que aparecen `admin`, `operator` y `viewer`.

### Paso 6: Ver el cliente
Ir a `Clients` y verificar que aparece `api-backend`.

### Paso 7: Probar la integracion
1. Ir a un usuario (ej: `admin`)
2. Ir a `Role mapping`
3. Verificar que tiene los roles `admin`, `operator` y `viewer` asignados
4. Esto confirma que el realm se importo correctamente

## Para Que Sirve el Realm Export

Los cambios hechos desde la interfaz se pueden exportar a `docker/keycloak/realm-export.json` para persistirlos:

```
Realm settings > Actions > Download adapter config > Keycloak JSON
```

Para exportar el realm completo:
```
Realm settings > Export > Export groups and roles > Export users
```

Esto descarga un JSON que se puede usar para recrear el realm en otro entorno.

## Notas

- La interfaz esta en ingles, no tiene traduccion al espanol
- Las credenciales de administrador (`admin`/`admin123`) son las del contenedor Keycloak, NO las de pgAdmin
- Cualquier cambio hecho desde la interfaz es persistente en la base de datos PostgreSQL
- Si se elimina el contenedor Keycloak (`docker compose down` + `up`), los cambios hechos desde la interfaz se mantienen porque la BD es persistente (volumen Docker)
- Si se quiere resetear a la configuracion inicial, hay que eliminar la BD y recrear con `--import-realm`
