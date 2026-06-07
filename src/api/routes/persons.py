"""
Gestión de la Identidad para Reconocimiento Facial.

Actividad S5.1: Implementa los endpoints REST para la creación y consulta de 
registros de personas. Garantiza la persistencia en la base de datos y la 
generación de identificadores únicos (personId) requeridos para la trazabilidad.
"""
import logging
from fastapi import APIRouter, HTTPException
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional
from ..schemas.person import PersonCreate, PersonResponse, PersonListResponse
from ..services.db_service import db_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/persons",
    tags=["persons"],
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
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creando persona")
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

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error obteniendo persona")
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
