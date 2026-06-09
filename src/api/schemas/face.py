from pydantic import BaseModel, Field
from typing import Optional


class FaceEmbedRequest(BaseModel):
    person_id: str
    image_base64: str
    embedding: list[float]
    confidence: float = Field(..., ge=0.0, le=1.0)


class FaceEmbedResponse(BaseModel):
    embedding_id: str
    person_id: str
    name: str
    confidence: float
    image_url: str
    status: str


class FaceRecognizeRequest(BaseModel):
    embedding: list[float]
    threshold: float = Field(0.8, ge=0.0, le=1.0)


class FaceMatchResult(BaseModel):
    person_id: str
    name: str
    distance: float
    confidence: float


class FaceRecognizeResponse(BaseModel):
    recognized: bool
    matches: list[FaceMatchResult]
    threshold: float
