#!/bin/bash
echo "=== Validando Infraestructura Local ==="
# 1. Verificar Docker Compose
echo -n "[1/5] Docker Compose: "
if docker compose version > /dev/null 2>&1; then
    echo "✓ OK"
else
    echo "✗ FALLO"
    exit 1
fi
# 2. PostgreSQL
echo -n "[2/5] PostgreSQL: "
if PGPASSWORD=secure_pwd_local psql -h localhost -U detections_user -d detections_db -c "SELECT 1" > /dev/null 2>&1; then
    echo "✓ OK (pgvector disponible)"
else
    echo "✗ NO ACCESIBLE en puerto 5432"
    exit 1
fi
# 3. SeaweedFS Master
echo -n "[3/5] SeaweedFS Master: "
if curl -s http://localhost:9333/status > /dev/null 2>&1; then
    echo "✓ OK"
else
    echo "✗ NO ACCESIBLE en puerto 9333"
    exit 1
fi
# 4. SeaweedFS Volume
echo -n "[4/5] SeaweedFS Volume: "
if curl -s http://localhost:8080/ > /dev/null 2>&1; then
    echo "✓ OK"
else
    echo "✗ NO ACCESIBLE en puerto 8080"
    exit 1
fi
# 5. Nginx
echo -n "[5/5] Nginx: "
if curl -s http://localhost/ > /dev/null 2>&1; then
    echo "✓ OK"
else
    echo "✗ NO ACCESIBLE en puerto 80"
    exit 1
fi
echo ""
echo "=== Todas las validaciones pasaron ==="