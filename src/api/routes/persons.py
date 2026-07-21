import logging
from fastapi import APIRouter, HTTPException, Depends
from uuid import uuid4
from datetime import datetime, timezone
from ..schemas.person import PersonCreate, PersonUpdate, PersonResponse, PersonListResponse
from ..services.db_service import db_service
from ..services.auth import require_role, verify_token
from ..services.keycloak_admin import (
    create_keycloak_user, delete_keycloak_user, assign_realm_role_to_user,
    update_keycloak_user, get_user_realm_roles, list_keycloak_users,
)
from ..services.email_service import send_email

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
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        name = f"{request.nombre} {request.apellido}"

        try:
            new_keycloak_id, temp_password = create_keycloak_user(
                username=request.email,
                email=request.email,
                send_email=True,
                first_name=request.nombre,
                last_name=request.apellido,
            )
            try:
                assign_realm_role_to_user(new_keycloak_id, "operator")
            except Exception as e:
                logger.warning("No se pudo asignar rol operator al usuario %s: %s", request.email, e)
            keycloak_user_id = new_keycloak_id

            if temp_password:
                send_email(
                    to=request.email,
                    subject="Credenciales de acceso - API Deteccion Visual",
                    body=(
                        f"Estimado/a {request.nombre} {request.apellido},\n\n"
                        "Su cuenta ha sido creada en el sistema API Deteccion Visual.\n\n"
                        "Sus credenciales de acceso son:\n"
                        f"  Usuario: {request.email}\n"
                        f"  Contrasena: {temp_password}\n\n"
                        "Puede iniciar sesion en: https://bfts2026.mooo.com/\n\n"
                        "Se recomienda cambiar la contrasena despues del primer inicio de sesion.\n\n"
                        "Saludos,\nEquipo API Deteccion Visual"
                    ),
                )
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

        saved = db_service.create_person(
            person_id=person_id,
            name=name,
            email=request.email,
            metadata=request.metadata,
            keycloak_user_id=keycloak_user_id,
        )

        if not saved:
            try:
                delete_keycloak_user(keycloak_user_id)
            except Exception:
                logger.exception("Error haciendo rollback de Keycloak user %s", keycloak_user_id)
            raise HTTPException(
                status_code=500,
                detail="Error al crear la persona en la base de datos"
            )

        person_data = {
            "person_id": person_id,
            "nombre": request.nombre,
            "apellido": request.apellido,
            "email": request.email,
            "keycloak_user_id": keycloak_user_id,
            "metadata": request.metadata or {},
            "created_at": timestamp,
            "updated_at": timestamp,
            "profile_image_url": "",
        }
        return PersonResponse(**_enrich_person_with_roles(person_data))

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

        keycloak_user_id = existing.get("keycloak_user_id")
        if keycloak_user_id:
            try:
                update_keycloak_user(
                    keycloak_user_id,
                    first_name=request.nombre,
                    last_name=request.apellido,
                    email=request.email or "",
                )
            except Exception as e:
                logger.warning("No se pudo actualizar usuario Keycloak %s: %s", keycloak_user_id, e)

        person_data = {
            "person_id": person_id,
            "nombre": request.nombre,
            "apellido": request.apellido,
            "email": request.email,
            "keycloak_user_id": keycloak_user_id,
            "has_faces": existing.get("has_faces", False),
            "profile_image_url": request.profile_image_url or existing.get("profile_image_url", ""),
            "metadata": request.metadata or {},
            "created_at": existing["created_at"],
            "updated_at": timestamp,
        }
        return PersonResponse(**_enrich_person_with_roles(person_data))

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
        existing = db_service.get_person(person_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Persona {person_id} no encontrada"
            )

        keycloak_user_id = existing.get("keycloak_user_id")
        if keycloak_user_id:
            try:
                delete_keycloak_user(keycloak_user_id)
            except Exception as e:
                logger.warning("No se pudo eliminar usuario Keycloak %s: %s", keycloak_user_id, e)

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


def _enrich_person_with_roles(person: dict) -> dict:
    kcid = person.get("keycloak_user_id")
    if kcid:
        person["keycloak_roles"] = get_user_realm_roles(kcid)
    return person


@router.get("/me", response_model=PersonResponse)
async def get_my_person(auth_data: dict = Depends(verify_token)):
    keycloak_user_id = auth_data.get("sub")
    if not keycloak_user_id:
        raise HTTPException(status_code=400, detail="Token invalido: sin sub")

    person = db_service.get_person_by_keycloak_id(keycloak_user_id)
    if not person:
        raise HTTPException(
            status_code=404,
            detail="No hay persona vinculada a este usuario"
        )
    return PersonResponse(**_enrich_person_with_roles(person))


@router.post("/me", response_model=PersonResponse, status_code=201)
async def create_my_person(request: PersonCreate, auth_data: dict = Depends(verify_token)):
    """
    Crea una persona vinculada al usuario autenticado.
    POST /api/persons/me
    Accesible por cualquier usuario autenticado.
    Si ya existe una persona vinculada, retorna 409 Conflict.
    """
    keycloak_user_id = auth_data.get("sub")
    if not keycloak_user_id:
        raise HTTPException(status_code=400, detail="Token invalido: sin sub")

    existing = db_service.get_person_by_keycloak_id(keycloak_user_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Ya existe una persona vinculada a este usuario"
        )

    try:
        person_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        name = f"{request.nombre} {request.apellido}"

        try:
            update_keycloak_user(
                keycloak_user_id,
                first_name=request.nombre,
                last_name=request.apellido,
                email=request.email or "",
            )
        except Exception as e:
            logger.warning("No se pudo actualizar nombre en Keycloak: %s", e)

        saved = db_service.create_person(
            person_id=person_id,
            name=name,
            email=request.email,
            metadata=request.metadata,
            keycloak_user_id=keycloak_user_id
        )

        if not saved:
            raise HTTPException(
                status_code=500,
                detail="Error al crear la persona en la base de datos"
            )

        person_data = {
            "person_id": person_id,
            "nombre": request.nombre,
            "apellido": request.apellido,
            "email": request.email,
            "keycloak_user_id": keycloak_user_id,
            "metadata": request.metadata or {},
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        return PersonResponse(**_enrich_person_with_roles(person_data))

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creando persona propia")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )


@router.post("/sync-keycloak", response_model=PersonListResponse,
             dependencies=[Depends(require_role(["admin"]))])
async def sync_keycloak_users():
    try:
        kc_users = list_keycloak_users()
        existing_persons = db_service.list_persons()
        existing_kc_ids = {p.get("keycloak_user_id") for p in existing_persons if p.get("keycloak_user_id")}

        created = []
        for kc_user in kc_users:
            kcid = kc_user.get("id")
            if kcid in existing_kc_ids:
                continue
            email = kc_user.get("email") or f"{kc_user['username']}@placeholder.local"
            person_id = str(uuid4())
            timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            first = kc_user.get("firstName") or kc_user["username"]
            last = kc_user.get("lastName") or ""
            name = f"{first} {last}"

            saved = db_service.create_person(
                person_id=person_id,
                name=name,
                email=email,
                keycloak_user_id=kcid,
            )
            if saved:
                created.append(person_id)

        persons = db_service.list_persons()
        return PersonListResponse(
            total=len(persons),
            persons=[PersonResponse(**_enrich_person_with_roles(p)) for p in persons]
        )
    except Exception as e:
        logger.exception("Error sincronizando usuarios Keycloak")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/{person_id}", response_model=PersonResponse,
            dependencies=[Depends(require_role(["admin", "operator", "viewer"]))])
async def get_person(person_id: str):
    try:
        person = db_service.get_person(person_id)
        if not person:
            raise HTTPException(
                status_code=404,
                detail=f"Persona {person_id} no encontrada"
            )
        return PersonResponse(**_enrich_person_with_roles(person))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error obteniendo persona")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )


@router.get("", response_model=PersonListResponse,
            dependencies=[Depends(require_role(["admin", "operator", "viewer"]))])
async def list_persons():
    try:
        persons = db_service.list_persons()
        return PersonListResponse(
            total=len(persons),
            persons=[PersonResponse(**_enrich_person_with_roles(p)) for p in persons]
        )
    except Exception as e:
        logger.exception("Error listando personas")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )
