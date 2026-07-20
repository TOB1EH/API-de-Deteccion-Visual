import logging
import secrets
from fastapi import APIRouter, HTTPException, Depends
from uuid import uuid4
from datetime import datetime, timezone
from ..schemas.person import PersonCreate, PersonUpdate, PersonResponse, PersonListResponse
from ..services.db_service import db_service
from ..services.auth import require_role, verify_token
from ..services.keycloak_admin import create_keycloak_user, delete_keycloak_user, assign_realm_role_to_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/persons",
    tags=["persons"],
    responses={404: {"description": "Not found"}},
)


@router.post("", response_model=PersonResponse, status_code=201,
             dependencies=[Depends(require_role(["admin"]))])
async def create_person(request: PersonCreate, auth_data: dict = Depends(verify_token)):
    try:
        person_id = str(uuid4())
        keycloak_user_id = auth_data.get("sub")
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        name = f"{request.nombre} {request.apellido}"
        auth_password = None

        if request.email:
            password = request.password or secrets.token_urlsafe(12)
            try:
                new_keycloak_id = create_keycloak_user(
                    username=request.email,
                    email=request.email,
                    password=password,
                )
                try:
                    assign_realm_role_to_user(new_keycloak_id, "viewer")
                except Exception as e:
                    logger.warning("No se pudo asignar rol viewer al usuario %s: %s", request.email, e)

                keycloak_user_id = new_keycloak_id
                auth_password = password
            except ValueError as e:
                raise HTTPException(status_code=409, detail=str(e))

        saved = db_service.create_person(
            person_id=person_id,
            name=name,
            email=request.email,
            metadata=request.metadata,
            keycloak_user_id=keycloak_user_id,
            auth_password=auth_password,
        )

        if not saved:
            if auth_password:
                try:
                    delete_keycloak_user(keycloak_user_id)
                except Exception:
                    logger.exception("Error haciendo rollback de Keycloak user %s", keycloak_user_id)
            raise HTTPException(
                status_code=500,
                detail="Error al crear la persona en la base de datos"
            )

        return PersonResponse(
            person_id=person_id,
            nombre=request.nombre,
            apellido=request.apellido,
            email=request.email,
            keycloak_user_id=keycloak_user_id,
            metadata=request.metadata or {},
            created_at=timestamp,
            updated_at=timestamp,
            profile_image_url="",
            temporary_password=auth_password,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creando persona")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )


@router.put("/{person_id}", response_model=PersonResponse,
            dependencies=[Depends(require_role(["admin"]))])
async def update_person(person_id: str, request: PersonUpdate):
    """
    Actualiza los datos de una persona existente.

    PUT /api/persons/{person_id}

    Args:
        person_id: ID de la persona a actualizar
        request: Datos actualizados (nombre, apellido, email, metadata)

    Retorna:
        PersonResponse con los datos actualizados
        404 si la persona no existe
        500 si hay error de base de datos
    """
    try:
        # Verificar que la persona existe
        existing = db_service.get_person(person_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Persona {person_id} no encontrada"
            )

        name = f"{request.nombre} {request.apellido}"
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

        updated = db_service.update_person(
            person_id=person_id,
            name=name,
            email=request.email,
            metadata=request.metadata,
            profile_image_url=request.profile_image_url,
        )

        if not updated:
            raise HTTPException(
                status_code=500,
                detail="Error al actualizar la persona en la base de datos"
            )

        return PersonResponse(
            person_id=person_id,
            nombre=request.nombre,
            apellido=request.apellido,
            email=request.email,
            keycloak_user_id=existing.get("keycloak_user_id"),
            has_faces=existing.get("has_faces", False),
            profile_image_url=request.profile_image_url or existing.get("profile_image_url", ""),
            metadata=request.metadata or {},
            created_at=existing["created_at"],
            updated_at=timestamp
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error actualizando persona")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )


@router.delete("/{person_id}", status_code=204,
               dependencies=[Depends(require_role(["admin"]))])
async def delete_person(person_id: str):
    """
    Elimina una persona y sus embeddings asociados.

    DELETE /api/persons/{person_id}

    Args:
        person_id: ID de la persona a eliminar

    Retorna:
        204 No Content si se elimino correctamente
        404 si la persona no existe
        500 si hay error de base de datos
    """
    try:
        # Verificar que la persona existe
        existing = db_service.get_person(person_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Persona {person_id} no encontrada"
            )

        deleted = db_service.delete_person(person_id)

        if not deleted:
            raise HTTPException(
                status_code=500,
                detail="Error al eliminar la persona de la base de datos"
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error eliminando persona")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )


@router.get("/me", response_model=PersonResponse,
            dependencies=[Depends(require_role(["admin", "operator"]))])
async def get_my_person(auth_data: dict = Depends(verify_token)):
    """
    Retorna la persona vinculada al usuario autenticado (segun keycloak_user_id).
    GET /api/persons/me

    Requiere que la persona haya sido creada con sesion iniciada para que
    el keycloak_user_id quede registrado. Si no hay vinculacion, retorna 404.
    """
    keycloak_user_id = auth_data.get("sub")
    if not keycloak_user_id:
        raise HTTPException(status_code=400, detail="Token invalido: sin sub")

    person = db_service.get_person_by_keycloak_id(keycloak_user_id)
    if not person:
        raise HTTPException(
            status_code=404,
            detail="No hay persona vinculada a este usuario. Cree una persona primero."
        )
    return PersonResponse(**person)


@router.get("/{person_id}", response_model=PersonResponse,
            dependencies=[Depends(require_role(["admin", "operator"]))])
async def get_person(person_id: str):
    try:
        person = db_service.get_person(person_id)
        if not person:
            raise HTTPException(
                status_code=404,
                detail=f"Persona {person_id} no encontrada"
            )
        return PersonResponse(**person)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error obteniendo persona")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )


@router.get("", response_model=PersonListResponse,
            dependencies=[Depends(require_role(["admin", "operator"]))])
async def list_persons():
    try:
        persons = db_service.list_persons()
        return PersonListResponse(
            total=len(persons),
            persons=[PersonResponse(**p) for p in persons]
        )
    except Exception as e:
        logger.exception("Error listando personas")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )
