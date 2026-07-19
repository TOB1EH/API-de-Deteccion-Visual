"""
Rutas para autenticacion biométrica facial.

Flujos:

1. Registro facial (POST /api/auth/register):
   - Usuario completa formulario (nombre, apellido, email, password) + 4+ fotos
   - Backend crea usuario en Keycloak, crea persona, genera embeddings faciales
   - Retorna exito con datos de la persona

2. Login facial (POST /api/auth/login/facial):
   - Usuario se toma una foto (webcam o archivo)
   - Backend genera embedding, compara contra la BD
   - Si hay coincidencia, obtiene un token JWT de Keycloak y lo retorna

3. Verificacion facial como segundo factor (POST /api/auth/verify-face):
   - Usuario ya autenticado con Keycloak, verifica su rostro como 2FA
"""

import os
import base64
import io
import logging
import secrets
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from ..services.db_service import db_service
from ..services.auth import verify_token
from ..services.image_utils import validate_image, get_format_and_mime
from ..services.keycloak_admin import create_keycloak_user, delete_keycloak_user, assign_realm_role_to_user, get_user_token

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
    images: list[str] = Field(..., min_length=4, max_length=10, description="Lista de 4-10 fotos en base64")


class RegisterFaceResponse(BaseModel):
    person_id: str
    nombre: str
    apellido: str
    email: str
    message: str


class FacialLoginRequest(BaseModel):
    image_base64: str = Field(..., description="Foto del rostro en base64")
    threshold: float = Field(0.8, ge=0.0, le=1.0)


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


def _generate_embedding(image_base64: str) -> list[float]:
    inference_url = os.getenv("INFERENCE_SERVER_URL", "http://localhost:8001")
    image_bytes = base64.b64decode(image_base64.split(",")[-1])
    if not validate_image(image_bytes):
        raise HTTPException(status_code=400, detail="La imagen no es valida")
    _, mime_type = get_format_and_mime(image_bytes)
    import requests as http_requests
    resp = http_requests.post(
        f"{inference_url}/face/embed",
        files={"image": ("face." + mime_type.split("/")[-1], io.BytesIO(image_bytes), mime_type)},
        timeout=120
    )
    result = resp.json()
    if result.get("error") or resp.status_code >= 400:
        raise HTTPException(status_code=502, detail="No se detecto un rostro en la imagen")
    embedding = result.get("embedding", result.get("embeddings", [None])[0])
    if not embedding:
        raise HTTPException(status_code=502, detail="El inference-server no devolvio un embedding valido")
    return embedding


def _embedding_to_str(embedding: list[float]) -> str:
    return "[" + ",".join(str(v) for v in embedding) + "]"


@router.post("/register", response_model=RegisterFaceResponse)
async def register_face(request: RegisterFaceRequest):
    """
    Registra un nuevo usuario con autenticacion facial.

    POST /api/auth/register

    Crea el usuario en Keycloak, la persona en la BD,
    y genera embeddings faciales para cada foto.
    Requiere al menos 4 fotos desde distintos angulos.
    """
    name = f"{request.nombre} {request.apellido}"
    person_id = str(uuid4())
    keycloak_password = request.password

    # 1. Validar que TODAS las imagenes tengan rostros detectables ANTES de crear Keycloak user
    valid_embeddings = []
    for idx, image_b64 in enumerate(request.images):
        try:
            embedding = _generate_embedding(image_b64)
            valid_embeddings.append(embedding)
        except HTTPException as e:
            if e.status_code == 502:
                raise HTTPException(
                    status_code=400,
                    detail=f"Foto {idx + 1}: no se detecto un rostro. Asegurate de que todas las fotos muestren tu rostro claramente."
                )
            raise
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Foto {idx + 1}: error al procesar la imagen: {str(e)}"
            )

    if len(valid_embeddings) < 4:
        raise HTTPException(status_code=400, detail="Se requieren al menos 4 fotos con rostros detectables")

    # 2. Crear usuario en Keycloak
    try:
        keycloak_user_id = create_keycloak_user(
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
        # 3. Asignar rol viewer por defecto
        try:
            assign_realm_role_to_user(keycloak_user_id, "viewer")
        except Exception as e:
            logger.warning("No se pudo asignar rol viewer: %s", e)

        # 4. Crear persona en BD
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

        # 5. Generar embeddings para cada foto
        success_count = 0
        conn = db_service.get_connection()
        try:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            for idx, image_b64 in enumerate(request.images):
                try:
                    embedding = valid_embeddings[idx]
                    image_url = ""
                    try:
                        from ..services.seaweedfs_client import seaweedfs_client
                        _, img_mime = get_format_and_mime(base64.b64decode(image_b64.split(",")[-1]))
                        image_url = seaweedfs_client.upload_image(
                            image_b64, f"face_{person_id}_{uuid4()}", mime_type=img_mime
                        )
                    except Exception:
                        pass
                    embedding_id = str(uuid4())
                    cursor.execute(
                        """
                        INSERT INTO face_embeddings (embedding_id, person_id, embedding, confidence, image_url)
                        VALUES (%s, %s, %s::vector, %s, %s)
                        """,
                        (embedding_id, person_id, _embedding_to_str(embedding), 0.9, image_url),
                    )
                    if idx == 0 and image_url:
                        cursor.execute(
                            "UPDATE persons SET profile_image_url = %s, updated_at = NOW() WHERE person_id = %s",
                            (image_url, person_id),
                        )
                    success_count += 1
                except Exception as e:
                    logger.warning("Error guardando embedding %d: %s", idx, e)
                    continue
            conn.commit()
            cursor.close()
        finally:
            conn.close()

        if success_count == 0:
            raise Exception("Ningun embedding pudo ser guardado")
    except Exception as e:
        logger.exception("Error en registro, realizando rollback de Keycloak user")
        delete_keycloak_user(keycloak_user_id)
        raise HTTPException(status_code=500, detail=str(e))

    return RegisterFaceResponse(
        person_id=person_id,
        nombre=request.nombre,
        apellido=request.apellido,
        email=request.email,
        message=f"Registro exitoso. {success_count} rostro(s) procesado(s) correctamente.",
    )


@router.post("/login/facial", response_model=FacialLoginResponse)
async def login_facial(request: FacialLoginRequest):
    """
    Inicia sesion mediante reconocimiento facial.

    POST /api/auth/login/facial

    Recibe una foto, la procesa con el inference-server,
    busca la persona mas cercana en la BD, y si coincide,
    genera un token JWT de Keycloak para esa persona.
    """
    # 1. Generar embedding de la foto
    try:
        embedding = _generate_embedding(request.image_base64)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error procesando imagen: {str(e)}")

    # 2. Buscar la persona mas cercana en la BD
    embedding_str = _embedding_to_str(embedding)
    conn = db_service.get_connection()
    try:
        from psycopg2.extras import RealDictCursor
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT fe.embedding_id::TEXT,
                   p.person_id::TEXT,
                   p.name,
                   p.email,
                   fe.confidence,
                   fe.embedding <=> %s::vector AS distance
            FROM face_embeddings fe
            JOIN persons p ON p.person_id = fe.person_id
            WHERE fe.embedding <=> %s::vector < %s
            ORDER BY distance ASC
            LIMIT 1
            """,
            (embedding_str, embedding_str, 2.0 - request.threshold),
        )
        row = cursor.fetchone()
        cursor.close()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Rostro no reconocido")

    distance = row["distance"]
    confidence = max(0.0, 1.0 - distance)
    if confidence < request.threshold:
        raise HTTPException(status_code=401, detail="Rostro no reconocido con suficiente confianza")

    # 3. Obtener la password almacenada para generar token Keycloak
    person_id = row["person_id"]
    auth_password = db_service.get_auth_password(person_id)
    if not auth_password:
        raise HTTPException(status_code=500, detail="Error interno: password de autenticacion no encontrada")

    email = row.get("email", "")
    try:
        token_data = get_user_token(email, auth_password)
    except Exception as e:
        logger.exception("Error obteniendo token de Keycloak")
        raise HTTPException(status_code=502, detail=f"Error obteniendo token de autenticacion: {str(e)}")

    name_parts = row["name"].split(" ", 1)
    nombre = name_parts[0]
    apellido = name_parts[1] if len(name_parts) > 1 else ""

    return FacialLoginResponse(
        access_token=token_data.get("access_token", ""),
        token_type=token_data.get("token_type", "bearer"),
        expires_in=token_data.get("expires_in", 0),
        scope=token_data.get("scope", ""),
        person_id=person_id,
        nombre=nombre,
        apellido=apellido,
    )
