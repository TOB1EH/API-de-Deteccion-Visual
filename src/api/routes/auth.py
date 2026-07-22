"""
Rutas para autenticacion biométrica facial.

Flujos:

1. Registro facial (POST /api/auth/register):
   - Usuario completa formulario (nombre, apellido, email, password)
   - Backend crea usuario en Keycloak y persona en BD
   - Las fotos se envian posteriormente al inference-server LOCAL del cliente
     via /face/embed, que las reenvia a /persons/{person_id}/embeddings

2. Login facial (POST /api/auth/login/facial):
   - Usuario se toma una foto (webcam o archivo)
   - Frontend envia al inference-server LOCAL /face/recognize
   - Inference-server reenvia a /api/face-recognition, devuelve person_id
   - Frontend envia person_id a /api/auth/login/facial para obtener token JWT

3. Verificacion facial como segundo factor (POST /api/auth/verify-face):
   - Usuario ya autenticado con Keycloak, verifica su rostro como 2FA
"""

import os
import base64
import io
import logging
import secrets
import requests
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from ..services.db_service import db_service
from ..services.auth import verify_token, create_facial_token
from ..services.image_utils import validate_image, get_format_and_mime
from ..services.keycloak_admin import create_keycloak_user, delete_keycloak_user, assign_realm_role_to_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)


class FaceVerifyRequest(BaseModel):
    image_base64: str = Field(..., description="Imagen facial en base64 (con o sin prefijo data:)")
    threshold: float = Field(0.8, ge=0.0, le=1.0, description="Umbral minimo de confianza (0.0 - 1.0)")


class FaceVerifyResponse(BaseModel):
    verified: bool = Field(..., description="True si el rostro coincide con la persona vinculada al token")
    confidence: float = Field(0.0, description="Confianza de la coincidencia (0.0 - 1.0)")
    person_id: Optional[str] = Field(None, description="ID de la persona verificada")
    nombre: Optional[str] = Field(None, description="Nombre de la persona verificada")
    apellido: Optional[str] = Field(None, description="Apellido de la persona verificada")


class RegisterFaceRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    apellido: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6, max_length=255)


class RegisterFaceResponse(BaseModel):
    person_id: str
    nombre: str
    apellido: str
    email: str
    message: str
    access_token: str = ""
    token_type: str = "bearer"


class FacialLoginRequest(BaseModel):
    person_id: str = Field(..., description="ID de la persona identificada por reconocimiento facial")


class FacialLoginResponse(BaseModel):
    access_token: str = ""
    token_type: str = "bearer"
    expires_in: int = 0
    scope: str = ""
    person_id: Optional[str] = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None


@router.post("/verify-face", response_model=FaceVerifyResponse)
async def verify_face(request: FaceVerifyRequest, auth_data: dict = Depends(verify_token)):
    """
    Verifica que la imagen facial pertenece a la persona vinculada al token.

    POST /api/auth/verify-face

    Args:
        request: Imagen facial + threshold de confianza
        auth_data: Token JWT (extrae keycloak_user_id para buscar la persona)

    Retorna:
        FaceVerifyResponse con verified=True/False, confianza y datos de la persona

    Proceso:
        1. Busca la persona vinculada al keycloak_user_id del token
        2. Envia la imagen al inference-server para generar embedding
        3. Compara el embedding generado contra los almacenados de esa persona
        4. Si la distancia es menor al threshold, la verificacion es exitosa
    """
    # 1. Obtener la persona vinculada al token
    keycloak_user_id = auth_data.get("sub")
    if not keycloak_user_id:
        raise HTTPException(status_code=400, detail="Token invalido: sin sub")

    person = db_service.get_person_by_keycloak_id(keycloak_user_id)
    if not person:
        raise HTTPException(
            status_code=404,
            detail="No hay persona vinculada a este usuario. Registrese primero."
        )

    # 2. Verificar que la persona tenga embeddings faciales almacenados
    if not person.get("has_faces", False):
        return FaceVerifyResponse(
            verified=False,
            confidence=0.0,
            person_id=person.get("person_id"),
            nombre=person.get("nombre"),
            apellido=person.get("apellido"),
        )

    # 3. Enviar la imagen al inference-server para generar embedding
    inference_url = os.getenv("INFERENCE_SERVER_URL", "http://localhost:8001")
    image_bytes = base64.b64decode(request.image_base64.split(",")[-1])

    # Validar que sea una imagen valida antes de enviar a DeepFace
    if not validate_image(image_bytes):
        raise HTTPException(
            status_code=400,
            detail="La imagen enviada no es un archivo de imagen valido (JPEG, PNG, WebP, BMP, GIF)."
        )

    # Detectar formato real para declarar Content-Type correcto al inference-server
    _, mime_type = get_format_and_mime(image_bytes)

    try:
        import requests as http_requests

        resp = http_requests.post(
            f"{inference_url}/face/embed",
            files={"image": ("face." + mime_type.split("/")[-1], io.BytesIO(image_bytes), mime_type)},
            timeout=120
        )
        result = resp.json()
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo conectar con el inference-server para generar el embedding: {str(e)}"
        )

    if result.get("error") or resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail="No se detecto un rostro en la imagen o hubo un error en DeepFace"
        )

    # 4. Comparar el embedding generado contra los almacenados de la persona
    # El inference-server devuelve el embedding en result["embedding"]
    new_embedding = result.get("embedding", result.get("embeddings", [None])[0])
    if not new_embedding:
        raise HTTPException(
            status_code=502,
            detail="El inference-server no devolvio un embedding valido"
        )

    # Buscar el embedding mas cercano usando distancia coseno via pgvector
    person_id = person["person_id"]
    conn = db_service.get_connection()
    try:
        from psycopg2.extras import RealDictCursor
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Convertir embedding a formato vector para pgvector
        embedding_str = "[" + ",".join(str(v) for v in new_embedding) + "]"

        cursor.execute(
            """
            SELECT fe.embedding_id::TEXT,
                   fe.embedding <=> %s::vector AS distance
            FROM face_embeddings fe
            WHERE fe.person_id = %s
            ORDER BY distance ASC
            LIMIT 1
            """,
            (embedding_str, person_id),
        )
        row = cursor.fetchone()
        cursor.close()
    finally:
        conn.close()

    if not row:
        # La persona tiene has_faces=true pero no se encontraron embeddings (inconsistencia)
        return FaceVerifyResponse(
            verified=False,
            confidence=0.0,
            person_id=person_id,
            nombre=person.get("nombre"),
            apellido=person.get("apellido"),
        )

    # Calcular confianza: a menor distancia coseno, mayor confianza
    distance = row["distance"]
    confidence = max(0.0, 1.0 - distance)

    if confidence >= request.threshold:
        return FaceVerifyResponse(
            verified=True,
            confidence=round(confidence, 4),
            person_id=person_id,
            nombre=person.get("nombre"),
            apellido=person.get("apellido"),
        )
    else:
        return FaceVerifyResponse(
            verified=False,
            confidence=round(confidence, 4),
            person_id=person_id,
            nombre=person.get("nombre"),
            apellido=person.get("apellido"),
        )


@router.post("/register", response_model=RegisterFaceResponse)
async def register_face(request: RegisterFaceRequest):
    """
    Registra un nuevo usuario con autenticacion facial.

    POST /api/auth/register

    Crea el usuario en Keycloak y la persona en la BD.
    Las fotos faciales se envian posteriormente al inference-server local
    del cliente, que las reenvia a /persons/{person_id}/embeddings.
    """
    name = f"{request.nombre} {request.apellido}"
    person_id = str(uuid4())
    keycloak_password = request.password

    try:
        keycloak_user_id, _ = create_keycloak_user(
            username=request.email,
            email=request.email,
            password=keycloak_password,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail="El email ya esta registrado. Inicia sesion o usa otro email.")
    except Exception as e:
        logger.exception("Error creando usuario en Keycloak")
        raise HTTPException(status_code=502, detail=f"Error creando usuario en Keycloak: {str(e)}")

    try:
        try:
            assign_realm_role_to_user(keycloak_user_id, "admin")
        except Exception as e:
            logger.warning("No se pudo asignar rol viewer: %s", e)

        saved = db_service.create_person(
            person_id=person_id,
            name=name,
            email=request.email,
            metadata={},
            keycloak_user_id=keycloak_user_id,
            auth_password=keycloak_password,
        )
        if not saved:
            raise Exception("Error al crear persona en BD")
    except Exception as e:
        logger.exception("Error en registro, realizando rollback de Keycloak user")
        delete_keycloak_user(keycloak_user_id)
        raise HTTPException(status_code=500, detail=str(e))

    token = ""
    try:
        token_data = get_user_token(request.email, keycloak_password)
        token = token_data.get("access_token", "")
    except Exception as e:
        logger.warning("No se pudo obtener token JWT para el registro: %s", e)

    return RegisterFaceResponse(
        person_id=person_id,
        nombre=request.nombre,
        apellido=request.apellido,
        email=request.email,
        message="Registro exitoso. Enviando fotos faciales al inference-server local.",
        access_token=token,
        token_type="bearer",
    )


@router.post("/login/facial", response_model=FacialLoginResponse)
async def login_facial(request: FacialLoginRequest):
    """
    Inicia sesion mediante reconocimiento facial.

    POST /api/auth/login/facial

    Recibe el person_id de la persona identificada por el
    inference-server local del cliente, y genera un token JWT de Keycloak.
    """
    person_id = request.person_id

    conn = db_service.get_connection()
    try:
        from psycopg2.extras import RealDictCursor
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT person_id::TEXT, name, email FROM persons WHERE person_id = %s",
            (person_id,),
        )
        person = cursor.fetchone()
        cursor.close()
    finally:
        conn.close()

    if not person:
        raise HTTPException(status_code=401, detail="Persona no encontrada")

    email = person.get("email", "")
    name_parts = person["name"].split(" ", 1)
    nombre = name_parts[0]
    apellido = name_parts[1] if len(name_parts) > 1 else ""

    conn = db_service.get_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT keycloak_user_id FROM persons WHERE person_id = %s",
            (person_id,),
        )
        person_row = cursor.fetchone()
        cursor.close()
    finally:
        conn.close()

    keycloak_user_id = person_row["keycloak_user_id"] if person_row else None

    roles = ["viewer"]
    if keycloak_user_id:
        try:
            from ..services.keycloak_admin import _get_admin_token
            kc_url = os.getenv("KEYCLOAK_INTERNAL_URL", "http://keycloak:8080")
            kc_realm = os.getenv("KEYCLOAK_REALM", "api-detection")
            headers = {"Authorization": f"Bearer {_get_admin_token()}"}
            resp = requests.get(
                f"{kc_url}/auth/admin/realms/{kc_realm}/users/{keycloak_user_id}/role-mappings/realm",
                headers=headers,
                timeout=10,
            )
            if resp.ok:
                assigned_roles = resp.json()
                roles = [r["name"] for r in assigned_roles]
        except Exception as e:
            logger.warning("Error obteniendo roles de Keycloak: %s", e)

    access_token = create_facial_token(
        person_id=person_id,
        email=email,
        roles=roles,
        keycloak_user_id=keycloak_user_id,
    )

    return FacialLoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=3600,
        scope="openid profile email",
        person_id=person_id,
        nombre=nombre,
        apellido=apellido,
    )
