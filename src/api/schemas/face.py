from pydantic import BaseModel, Field
from typing import Optional


class FaceEmbedRequest(BaseModel):
    image_base64: str
    embedding: list[float]
    confidence: float = Field(..., ge=0.0, le=1.0)


class FaceEmbedResponse(BaseModel):
    person_id: str
    processed_images: int
    valid_embeddings: int
    rejected_images: int
    embedding_id: str
    image_url: str


class FaceRecognizeFromImageRequest(BaseModel):
    image_base64: str
    threshold: float = Field(0.8, ge=0.0, le=1.0)


class FaceRecognizeRequest(BaseModel):
    embedding: list[float]
    threshold: float = Field(0.8, ge=0.0, le=1.0)


class FaceRecognizeResponse(BaseModel):
    person_id: Optional[str] = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    confidence: float = 0.0


class FaceEmbedUploadRequest(BaseModel):
    image_base64: str
    confidence: float = Field(0.8, ge=0.0, le=1.0)


class FaceEmbedUploadResponse(BaseModel):
    person_id: str
    valid_embeddings: int
    embedding_id: str
    image_url: str
