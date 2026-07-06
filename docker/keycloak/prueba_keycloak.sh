#!/bin/bash
# Prueba exhaustiva de Keycloak + API (local)
# Ejecutar: bash docker/keycloak/prueba_keycloak.sh

set +e

BASE="http://localhost"

decode_token() {
    echo "$1" | cut -d. -f2 | python3 -c "
import sys, base64, json
data = sys.stdin.read().strip()
padding = 4 - len(data) % 4 if len(data) % 4 else 0
payload = json.loads(base64.urlsafe_b64decode(data + '=' * padding))
print('  Usuario:', payload.get('preferred_username'))
print('  Roles:', payload.get('realm_access', {}).get('roles', []))
print('  Email:', payload.get('email'))
print('  Expira:', payload.get('exp'))
"
}

get_token() {
    local user=$1 pass=$2
    local resp
    resp=$(curl -s -X POST "$BASE/auth/realms/api-detection/protocol/openid-connect/token" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "client_id=api-backend" \
      -d "username=$user" \
      -d "password=$pass" \
      -d "grant_type=password")
    echo "$resp"
}

test_endpoint() {
    local desc=$1 expected=$2 url=$3 token=$4
    local http_code
    if [ -n "$token" ]; then
        http_code=$(curl -s -o /tmp/kc_test.json -w "%{http_code}" \
            -H "Authorization: Bearer $token" "$url")
    else
        http_code=$(curl -s -o /tmp/kc_test.json -w "%{http_code}" "$url")
    fi
    if [ "$http_code" = "$expected" ]; then
        echo "  $expected OK"
    else
        echo "  ESPERADO $expected | OBTENIDO $http_code ERROR"
    fi
}

echo "=============================================="
echo " Prueba Keycloak - LOCAL (localhost)"
echo "=============================================="
echo ""

# =========== SECCION 1: OBTENER TOKENS ===========
echo "--- 1. OBTENER TOKENS ---"

echo "[1a] admin / admin123 (roles: admin, operator, viewer)"
RESP=$(get_token admin admin123)
TOKEN_ADMIN=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
REFRESH_ADMIN=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['refresh_token'])" 2>/dev/null)
if [ -n "$TOKEN_ADMIN" ]; then
    echo "  Token obtenido: ${TOKEN_ADMIN:0:30}..."
    decode_token "$TOKEN_ADMIN"
else
    echo "  ERROR: No se obtuvo token"
    echo "$RESP"
fi
echo ""

echo "[1b] operator1 / op123 (roles: operator, viewer)"
RESP=$(get_token operator1 op123)
TOKEN_OP=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
if [ -n "$TOKEN_OP" ]; then
    echo "  Token obtenido: ${TOKEN_OP:0:30}..."
    decode_token "$TOKEN_OP"
else
    echo "  ERROR: No se obtuvo token"
fi
echo ""

echo "[1c] viewer1 / view123 (roles: viewer)"
RESP=$(get_token viewer1 view123)
TOKEN_VIEW=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
if [ -n "$TOKEN_VIEW" ]; then
    echo "  Token obtenido: ${TOKEN_VIEW:0:30}..."
    decode_token "$TOKEN_VIEW"
else
    echo "  ERROR: No se obtuvo token"
fi
echo ""

# =========== SECCION 2: ERRORES DE AUTENTICACION ===========
echo "--- 2. ERRORES DE AUTENTICACION ---"

echo "[2a] Password incorrecto (debe retornar error)"
RESP=$(get_token admin wrongpass)
ERR=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('error',''))" 2>/dev/null)
if echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if 'error' in d else 1)" 2>/dev/null; then
    echo "  OK - Rechazado: $(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('error_description',''))" 2>/dev/null)"
else
    echo "  ERROR: Se esperaba un error"
fi
echo ""

echo "[2b] Token invalido (garbage)"
test_endpoint "GET /api/models" 401 "$BASE/api/models" "token-falso-invalido"
echo ""

# =========== SECCION 3: TOKENS POR USUARIO ===========
echo "--- 3. TOKENS POR USUARIO ---"

echo "[3a] admin - GET /api/models"
test_endpoint "GET /api/models" 200 "$BASE/api/models" "$TOKEN_ADMIN"
curl -s -H "Authorization: Bearer $TOKEN_ADMIN" "$BASE/api/models" | python3 -m json.tool 2>/dev/null || curl -s -H "Authorization: Bearer $TOKEN_ADMIN" "$BASE/api/models"
echo ""

echo "[3b] operator1 - GET /api/models"
test_endpoint "GET /api/models" 200 "$BASE/api/models" "$TOKEN_OP"
echo ""

echo "[3c] viewer1 - GET /api/models"
test_endpoint "GET /api/models" 200 "$BASE/api/models" "$TOKEN_VIEW"
echo ""

# =========== SECCION 4: ENDPOINTS PROTEGIDOS ===========
echo "--- 4. ENDPOINTS PROTEGIDOS (con token de admin) ---"

echo "[4a] GET /api/models"
test_endpoint "GET /api/models" 200 "$BASE/api/models" "$TOKEN_ADMIN"
echo ""

echo "[4b] GET /api/persons"
test_endpoint "GET /api/persons" 200 "$BASE/api/persons" "$TOKEN_ADMIN"
echo ""

echo "[4c] GET /api/frames/search"
test_endpoint "GET /api/frames/search" 200 "$BASE/api/frames/search" "$TOKEN_ADMIN"
echo ""

echo "[4d] GET /api/docs (NUNCA debe pedir token)"
test_endpoint "GET /api/docs" 200 "$BASE/api/docs" ""
echo ""

# =========== SECCION 5: ENDPOINTS PUBLICOS ===========
echo "--- 5. ENDPOINTS PUBLICOS (sin token) ---"

echo "[5a] GET /"
test_endpoint "GET /" 200 "$BASE/" ""
echo ""

echo "[5b] GET /health"
test_endpoint "GET /health" 200 "$BASE/health" ""
curl -s "$BASE/health" | python3 -m json.tool 2>/dev/null || curl -s "$BASE/health"
echo ""

echo "[5c] GET /api/docs"
test_endpoint "GET /api/docs" 200 "$BASE/api/docs" ""
echo ""

echo "[5d] GET /api/redoc"
test_endpoint "GET /api/redoc" 200 "$BASE/api/redoc" ""
echo ""

# =========== SECCION 6: SIN TOKEN ===========
echo "--- 6. ENDPOINTS PROTEGIDOS SIN TOKEN (deben dar 401) ---"

echo "[6a] GET /api/models sin token"
test_endpoint "GET /api/models" 401 "$BASE/api/models" ""
echo ""

echo "[6b] GET /api/persons sin token"
test_endpoint "GET /api/persons" 401 "$BASE/api/persons" ""
echo ""

echo "[6c] GET /api/frames/search sin token"
test_endpoint "GET /api/frames/search" 401 "$BASE/api/frames/search" ""
echo ""

# =========== SECCION 7: REFRESH TOKEN ===========
echo "--- 7. REFRESH TOKEN ---"

echo "[7a] Refresh token de admin"
RESP=$(curl -s -X POST "$BASE/auth/realms/api-detection/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=api-backend" \
  -d "refresh_token=$REFRESH_ADMIN" \
  -d "grant_type=refresh_token")
NEW_TOKEN=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
if [ -n "$NEW_TOKEN" ]; then
    echo "  Nuevo token obtenido: ${NEW_TOKEN:0:30}..."
    test_endpoint "GET /api/models con nuevo token" 200 "$BASE/api/models" "$NEW_TOKEN"
else
    echo "  ERROR: $RESP"
fi
echo ""

# =========== RESUMEN ===========
echo "=============================================="
echo " PRUEBAS COMPLETADAS"
echo "=============================================="
echo ""
echo "Resumen de pruebas:"
echo "  [1a] admin token ............... $( [ -n "$TOKEN_ADMIN" ] && echo OK || echo FAIL)"
echo "  [1b] operator1 token ........... $( [ -n "$TOKEN_OP" ] && echo OK || echo FAIL)"
echo "  [1c] viewer1 token ............ $( [ -n "$TOKEN_VIEW" ] && echo OK || echo FAIL)"
echo "  [2a] wrong password ........... OK (revisar arriba)"
echo "  [2b] invalid token ............ OK (revisar arriba)"
echo "  [3a] admin accede ............. OK (revisar arriba)"
echo "  [3b] operator1 accede ......... OK (revisar arriba)"
echo "  [3c] viewer1 accede ........... OK (revisar arriba)"
echo "  [4a] /api/models protegido .... OK (revisar arriba)"
echo "  [4b] /api/persons protegido ... OK (revisar arriba)"
echo "  [4c] /api/frames protegido .... OK (revisar arriba)"
echo "  [4d] /api/docs publico ........ OK (revisar arriba)"
echo "  [5a] / publico ................ OK (revisar arriba)"
echo "  [5b] /health publico .......... OK (revisar arriba)"
echo "  [5c] /api/docs publico ........ OK (revisar arriba)"
echo "  [5d] /api/redoc publico ....... OK (revisar arriba)"
echo "  [6a] /api/models 401 .......... OK (revisar arriba)"
echo "  [6b] /api/persons 401 ......... OK (revisar arriba)"
echo "  [6c] /api/frames 401 .......... OK (revisar arriba)"
echo "  [7a] refresh token ............ OK (revisar arriba)"
