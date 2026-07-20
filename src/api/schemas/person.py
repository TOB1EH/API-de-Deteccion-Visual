from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class PersonCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    apellido: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = Field(None, min_length=6, max_length=255,
                                    description="Contrasena para Keycloak. Si no se provee con email, se auto-genera una.")
    metadata: Optional[dict[str, Any]] = None


class PersonResponse(BaseModel):
    person_id: str
    nombre: str
    apellido: str
    email: Optional[str] = None
    keycloak_user_id: Optional[str] = None
    has_faces: bool = False
    profile_image_url: str = ""
    temporary_password: Optional[str] = Field(None,
                                              description="Contrasena temporal generada. Solo se devuelve al crear la persona.")
    metadata: Optional[dict[str, Any]] = None
    created_at: str
    updated_at: str


class PersonUpdate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    apellido: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    profile_image_url: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class PersonListResponse(BaseModel):
    total: int
    persons: list[PersonResponse]
