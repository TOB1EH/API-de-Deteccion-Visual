"""
Actividad S5.1: Modelo de datos de personas.
Define la estructura para el registro y respuesta de personas. 
Cumple con los requisitos de personId (UUID), campos básicos (nombre, apellido, email) 
y el campo flexible 'extra' (JSON) para extensibilidad de atributos adicionales.
"""
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime

class PersonCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    apellido: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., max_length=255)
    extra: Optional[Dict[str, Any]] = Field(default_factory=dict)

class PersonResponse(BaseModel):
    person_id: str
    nombre: str
    apellido: str
    email: str
    extra: Optional[Dict[str, Any]]
    created_at: str
    updated_at: str

class PersonListResponse(BaseModel):
    total: int
    persons: list[PersonResponse]
