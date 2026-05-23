# Fase 1: Infraestructura - Guía Completa

## Estado: COMPLETADA ✓

Infraestructura base funcionando en local y remota con HTTPS, proxy reverso, y acceso remoto a todos los servicios.

---

## Servicios Levantados

| Servicio | Imagen | Puertos | Red | Estado |
|---|---|---|---|---|
| PostgreSQL | pgvector/pgvector:pg16 | 5432 | api-detection-net | ✓ Healthy |
| SeaweedFS Master | chrislusf/seaweedfs:latest | 9333 | api-detection-net | ✓ Running |
| SeaweedFS Volume | chrislusf/seaweedfs:latest | 8080 | api-detection-net | ✓ Running |
| Nginx | nginx:1.31.1 | 80, 443 | api-detection-net | ✓ Running |
| pgAdmin | dpage/pgadmin4:latest | 80 (interno) | api-detection-net | ✓ Running |

---

## Local

### Levantar servicios
```bash
docker compose up -d
```

### Validar servicios
```bash
./validate_local.sh
```

### Conectarse a PostgreSQL
```bash
PGPASSWORD=secure_pwd_local psql -h localhost -U detections_user -d detections_db
```

### Ver logs de un servicio
```bash
docker compose logs -f [db|seaweed-master|seaweed-volume|nginx|pgadmin]
```

### Detener servicios
```bash
docker compose down
```

### Eliminar volúmenes (reiniciar desde cero)
```bash
docker compose down -v
```

### Puertos locales
- PostgreSQL: `localhost:5432`
- SeaweedFS Master: `localhost:9333`
- SeaweedFS Volume: `localhost:8080`
- Nginx: `localhost:80`
- pgAdmin: `localhost/pgadmin/`

### Credenciales (LOCAL)
```
DB User: detections_user
DB Password: secure_pwd_local
DB Name: detections_db
```

---

## Remota (VM: bfts2026.mooo.com)

### Levantar servicios
```bash
ssh user@bfts2026.mooo.com
cd /root/api-detections
docker compose up -d
```

### Verificar servicios
```bash
docker compose ps
```

### Conectarse a PostgreSQL
```bash
PGPASSWORD=bfts2026. psql -h bfts2026.mooo.com -U detections_user -d detections_db
```

### Ver logs
```bash
docker compose logs -f [servicio]
```

### Credenciales (REMOTA)
```
DB User: detections_user
DB Password: bfts2026.
DB Name: detections_db
pgAdmin Email: admin@bfts2026.mooo.com
pgAdmin Password: bfts2026.
```

---

## Acceso Remoto a través de HTTPS

### URLs públicas (desde cualquier máquina)

#### Health Check
```
https://bfts2026.mooo.com/
```
Respuesta: `API Detection Service OK`

#### pgAdmin - Gestión PostgreSQL
```
https://bfts2026.mooo.com/pgadmin/
```
- Email: `admin@bfts2026.mooo.com`
- Contraseña: `bfts2026.`

#### SeaweedFS Volume - Acceso a objetos
```
https://bfts2026.mooo.com/seaweed/
```
Almacenamiento de archivos (imágenes, modelos, etc.)

#### SeaweedFS Master - Estado del master
```
https://bfts2026.mooo.com/seaweed-master/
```
Información de estado y volúmenes disponibles

#### API REST (Fase 2 en adelante)
```
https://bfts2026.mooo.com/api/
```
Endpoints REST de la API de detección visual

---

## Certificados SSL

**Ubicación en remota:**
```
/etc/letsencrypt/live/bfts2026.mooo.com/
├── fullchain.pem
├── privkey.pem
├── chain.pem
└── cert.pem
```

**Montaje en Nginx (docker-compose.yml):**
```yaml
volumes:
  - /etc/letsencrypt/live/bfts2026.mooo.com/fullchain.pem:...
  - /etc/letsencrypt/live/bfts2026.mooo.com/privkey.pem:...
```

**Verificar certificado:**
```bash
openssl x509 -in /etc/letsencrypt/live/bfts2026.mooo.com/fullchain.pem -text -noout
```

---

## Auto-renovación con Certbot

### Instalar Certbot (si no está)
```bash
sudo apt install certbot -y
```

### Crear cron job para renovación automática
```bash
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet") | crontab -
```

### Validar que funciona
```bash
sudo certbot renew --dry-run
```

**Nota:** Los certificados se renuevan automáticamente 30 días antes de su expiración.

---

## Firewall (UFW) en Remota

### Estado actual
```bash
sudo ufw status numbered
```

### Puertos abiertos
- SSH (22/tcp)
- HTTP (80/tcp)
- HTTPS (443/tcp)
- PostgreSQL (5432/tcp)
- SeaweedFS Master (9333/tcp)
- SeaweedFS Volume (8080/tcp)

---

## Validación de Persistencia

Se verificó que los datos persisten tras reiniciar servicios:
- Base de datos PostgreSQL: ✓ OK
- SeaweedFS Master: ✓ OK (volumen persistente)
- SeaweedFS Volume: ✓ OK (almacenamiento persistente)

**Prueba ejecutada:**
```sql
CREATE TABLE test_persistence (id SERIAL PRIMARY KEY, message TEXT);
INSERT INTO test_persistence (message) VALUES ('Persistencia OK - Fase 1');
```

Tras `docker compose down && docker compose up -d`, los datos persisten.

---

## Estructura de archivos

```
/root/api-detections/  (en remota)
├── docker-compose.yml          # Definición de servicios
├── docker/
│   └── nginx.conf              # Configuración Nginx (proxy reverso + HTTPS)
├── config/
│   └── .env                    # Variables de entorno (no en git)
├── volumes/                    # Volúmenes persistentes (no en git)
│   ├── pg_data/
│   ├── seaweed_master/
│   └── seaweed_volume/
└── validate_local.sh           # Script de validación
```

---

## Próximas Fases

- **Fase 2:** Endpoint S1 (GET `/models`) - Listar modelos
- **Fase 3:** Endpoint S2 (POST `/detections`) - Ejecución de detecciones
- **Fase 4:** Endpoints S3-S4 (GET `/frames/`) - Consultas y filtrado
- **Fase 5:** Endpoints S5 (personas y reconocimiento facial)

---

## Troubleshooting

### "Connection refused" a PostgreSQL
```bash
# Verificar que el contenedor está running
docker compose ps | grep db

# Ver logs
docker compose logs db
```

### Nginx devuelve 502 Bad Gateway
```bash
# Verificar que los upstreams están configurados
docker compose ps

# Ver logs de Nginx
docker compose logs nginx
```

### Certificados no encontrados
```bash
# Verificar que existen en remota
ls -la /etc/letsencrypt/live/bfts2026.mooo.com/

# Si no existen, crear con Certbot
sudo certbot certonly --standalone -d bfts2026.mooo.com
```

---

## Referencias

- Docker Compose: https://docs.docker.com/compose/
- pgVector: https://github.com/pgvector/pgvector
- SeaweedFS: https://github.com/seaweedfs/seaweedfs
- pgAdmin: https://www.pgadmin.org/
- Let's Encrypt: https://letsencrypt.org/
- Nginx Proxy: https://nginx.org/en/docs/http/ngx_http_proxy_module.html
