"""
<<<<<<< HEAD
Gestión de la Identidad para Reconocimiento Facial.

Actividad S5.1: Implementa los endpoints REST para la creación y consulta de 
registros de personas. Garantiza la persistencia en la base de datos y la 
generación de identificadores únicos (personId) requeridos para la trazabilidad.
"""
=======
Rutas para S5.1: Gestión de personas (CRUD básico).
"""

>>>>>>> e5276770437f19548c61beda4aaa118bc8ce4485
import logging
from fastapi import APIRouter, HTTPException
from uuid import uuid4
from datetime import datetime, timezone
<<<<<<< HEAD
from typing import Optional
=======
>>>>>>> e5276770437f19548c61beda4aaa118bc8ce4485
from ..schemas.person import PersonCreate, PersonResponse, PersonListResponse
from ..services.db_service import db_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/persons",
    tags=["persons"],
<<<<<<< HEAD
    responses={404: {"description": "Person not found"}},
)

@router.post("", response_model=PersonResponse, status_code=201)
async def create_person(person: PersonCreate):
    try:
        person_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        result = db_service.create_person(
            person_id=person_id,
            nombre=person.nombre,
            apellido=person.apellido,
            email=person.email,
            extra=person.extra,
        )

        if not result:
            raise HTTPException(status_code=400, detail="No se pudo crear la persona (email posiblemente duplicado)")

        return PersonResponse(
            person_id=person_id,
            nombre=person.nombre,
            apellido=person.apellido,
            email=person.email,
            extra=person.extra,
            created_at=timestamp,
            updated_at=timestamp,
=======
    responses={404: {"description": "Not found"}},
)


@router.post("", response_model=PersonResponse, status_code=201)
async def create_person(request: PersonCreate):
    """
    Crea una nueva persona.

    POST /api/persons

    Args:
        request: PersonCreate (name, email opcional, metadata opcional)

    Retorna:
        PersonResponse con person_id, name, email, metadata, timestamps
    """
    try:
        person_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

        saved = db_service.create_person(
            person_id=person_id,
            name=request.name,
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
            name=request.name,
            email=request.email,
            metadata=request.metadata or {},
            created_at=timestamp,
            updated_at=timestamp
>>>>>>> e5276770437f19548c61beda4aaa118bc8ce4485
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creando persona")
<<<<<<< HEAD
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(person_id: str):
    try:
        person = db_service.get_person_by_id(person_id)
        if not person:
            raise HTTPException(status_code=404, detail=f"Persona {person_id} no encontrada")

        return PersonResponse(
            person_id=person["person_id"],
            nombre=person["nombre"],
            apellido=person["apellido"],
            email=person["email"],
            extra=person.get("extra"),
            created_at=person["created_at"].isoformat() if hasattr(person["created_at"], "isoformat") else str(person["created_at"]),
            updated_at=person["updated_at"].isoformat() if hasattr(person["updated_at"], "isoformat") else str(person["updated_at"]),
        )

=======
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )


@router.get("", response_model=PersonListResponse)
async def list_persons():
    """
    Lista todas las personas registradas.

    GET /api/persons
    """
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


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(person_id: str):
    """
    Obtiene una persona por su ID.

    GET /api/persons/{person_id}
    """
    try:
        person = db_service.get_person(person_id)
        if not person:
            raise HTTPException(
                status_code=404,
                detail=f"Persona {person_id} no encontrada"
            )
        return PersonResponse(**person)
>>>>>>> e5276770437f19548c61beda4aaa118bc8ce4485
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error obteniendo persona")
<<<<<<< HEAD
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("", response_model=PersonListResponse)
async def list_persons(limit: int = 50, offset: int = 0):
    try:
        persons = db_service.list_persons(limit=limit, offset=offset)
        total = db_service.count_persons()

        return PersonListResponse(
            total=total,
            persons=[
                PersonResponse(
                    person_id=p["person_id"],
                    nombre=p["nombre"],
                    apellido=p["apellido"],
                    email=p["email"],
                    extra=p.get("extra"),
                    created_at=p["created_at"].isoformat() if hasattr(p["created_at"], "isoformat") else str(p["created_at"]),
                    updated_at=p["updated_at"].isoformat() if hasattr(p["updated_at"], "isoformat") else str(p["updated_at"]),
                ) for p in persons
            ]
        )

    except Exception as e:
        logger.exception("Error listando personas")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
=======
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )
>>>>>>> e5276770437f19548c61beda4aaa118bc8ce4485
