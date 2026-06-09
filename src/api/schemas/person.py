from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class PersonCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    apellido: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    metadata: Optional[dict[str, Any]] = None


class PersonResponse(BaseModel):
    person_id: str
    nombre: str
    apellido: str
    email: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: str
    updated_at: str


class PersonListResponse(BaseModel):
    total: int
    persons: list[PersonResponse]
