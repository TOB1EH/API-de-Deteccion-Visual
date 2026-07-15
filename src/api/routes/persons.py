import logging
from fastapi import APIRouter, HTTPException, Depends
from uuid import uuid4
from datetime import datetime, timezone
from ..schemas.person import PersonCreate, PersonUpdate, PersonResponse, PersonListResponse
from ..services.db_service import db_service
from ..services.auth import require_role

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/persons",
    tags=["persons"],
    responses={404: {"description": "Not found"}},
)


@router.post("", response_model=PersonResponse, status_code=201,
             dependencies=[Depends(require_role(["admin"]))])
async def create_person(request: PersonCreate):
    try:
        person_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        name = f"{request.nombre} {request.apellido}"

        saved = db_service.create_person(
            person_id=person_id,
            name=name,
            email=request.email,
            metadata=request.metadata
        )

        if not saved:
            raise HTTPException(
                status_code=500,
                detail="Error al crear la persona en la base de datos"
            )

        return PersonResponse(
            person_id=person_id,
            nombre=request.nombre,
            apellido=request.apellido,
            email=request.email,
            metadata=request.metadata or {},
            created_at=timestamp,
            updated_at=timestamp
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
            metadata=request.metadata
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
