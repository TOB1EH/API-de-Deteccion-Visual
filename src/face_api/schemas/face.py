"""
Modelos Pydantic para S5.2 y S5.3: generación de embeddings y reconocimiento facial.
"""

from pydantic import BaseModel, Field
from typing import Optional


class EmbeddingRequest(BaseModel):
    image_url: str
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class EmbeddingResponse(BaseModel):
    person_id: str
    embedding_id: str
    confidence: float
    image_url: str
    status: str
    message: str


class RecognitionRequest(BaseModel):
    image_url: str
    threshold: float = Field(default=0.8, ge=0.0, le=1.0)


class RecognitionMatch(BaseModel):
    person_id: str
    name: str
    distance: float
    confidence: float


class RecognitionResponse(BaseModel):
    recognized: bool
    matches: list[RecognitionMatch]
    threshold: float
    image_url: str
    facial_area: Optional[dict] = None
