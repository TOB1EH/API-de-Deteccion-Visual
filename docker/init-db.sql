-- ============================================================================
-- Script de Inicialización: Schema PostgreSQL para Detección Visual (Fase 2)
-- ============================================================================
-- Propósito: Crear estructura base de datos (tablas, índices, constraints)
-- Ejecutado automáticamente por PostgreSQL al iniciar el contenedor
-- Compatible con: docker-compose.local.yml + docker-compose.yml
-- ============================================================================

-- Habilitar extensión pgvector para búsqueda vectorial (futuro uso en S5)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================================
-- TABLA: frames (fotogramas detectados)
-- Propósito: Persistir metadatos de cada fotograma procesado por S2
-- ============================================================================
CREATE TABLE IF NOT EXISTS frames (
    -- Identificador único: UUID generado automáticamente
    frame_id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    
    -- Referencias a modelo YOLO usado
    model_id VARCHAR(255) NOT NULL,
    
    -- Geolocalización obligatoria (S2 requiere lat/lon)
    latitude FLOAT8 NOT NULL,
    longitude FLOAT8 NOT NULL,
    
    -- URL pública para acceder a imagen en SeaweedFS (generada por S2)
    image_url TEXT NOT NULL,
    
    -- Cantidad de detecciones para este fotograma (desnormalizado para queries rápidas)
    detections_count INT DEFAULT 0 CHECK (detections_count >= 0),
    
    -- Metadatos adicionales (cámara origen, fuente, etc.)
    camera_id VARCHAR(255),
    source VARCHAR(255),
    
    -- Auditoría: timestamps automáticos
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Comentario de tabla (documentación en BD)
COMMENT ON TABLE frames IS 'Metadatos de fotogramas procesados. Cada frame vinculado a 1+ detecciones.';

-- ============================================================================
-- TABLA: detections (objetos detectados dentro de fotogramas)
-- Propósito: Persistir cada objeto detectado por YOLO (person, dog, car, etc.)
-- Relación: N detections → 1 frame (FK frame_id)
-- ============================================================================
CREATE TABLE IF NOT EXISTS detections (
    -- Identificador único: UUID generado automáticamente
    detection_id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    
    -- Referencia a fotograma padre (CASCADE: eliminar frame → elimina detecciones)
    frame_id VARCHAR(36) NOT NULL,
    CONSTRAINT fk_detections_frame_id 
        FOREIGN KEY (frame_id) REFERENCES frames(frame_id) ON DELETE CASCADE,
    
    -- Clase detectada (person, dog, car, etc. - nomenclatura COCO)
    class_name VARCHAR(255) NOT NULL,
    
    -- ID numérico de clase COCO (0=person, 1=bicycle, ..., 17=dog, ...)
    class_id INT NOT NULL,
    
    -- Confianza de la detección: 0.0 a 1.0 (YOLO output)
    confidence FLOAT8 NOT NULL,
    CONSTRAINT check_confidence_range CHECK (confidence >= 0.0 AND confidence <= 1.0),
    
    -- Bounding box: coordenadas píxel (x_min, y_min) a (x_max, y_max)
    -- Tipo INT: dimensiones imagen típicamente < 2^31-1 píxeles
    bbox_x_min INT NOT NULL CHECK (bbox_x_min >= 0),
    bbox_y_min INT NOT NULL CHECK (bbox_y_min >= 0),
    bbox_x_max INT NOT NULL CHECK (bbox_x_max >= 0),
    bbox_y_max INT NOT NULL CHECK (bbox_y_max >= 0),
    
    -- Auditoría: timestamp de creación
    created_at TIMESTAMP DEFAULT NOW()
);

-- Comentario de tabla (documentación en BD)
COMMENT ON TABLE detections IS 'Objetos detectados dentro de fotogramas. Vinculados a frame_id con cascada.';

-- ============================================================================
-- ÍNDICES: Optimización de búsquedas frecuentes
-- ============================================================================

-- Índice en frames.model_id (filtrar por modelo)
CREATE INDEX IF NOT EXISTS idx_frames_model_id 
    ON frames(model_id);
COMMENT ON INDEX idx_frames_model_id IS 'Búsqueda rápida por modelo YOLO usado.';

-- Índice en frames.created_at DESC (listar fotogramas recientes)
CREATE INDEX IF NOT EXISTS idx_frames_created_at_desc 
    ON frames(created_at DESC);
COMMENT ON INDEX idx_frames_created_at_desc IS 'Ordenar fotogramas por fecha (descending).';

-- Índice en frames.latitude + longitude (búsqueda geoespacial futura)
CREATE INDEX IF NOT EXISTS idx_frames_geo 
    ON frames(latitude, longitude);
COMMENT ON INDEX idx_frames_geo IS 'Búsqueda rápida por coordenadas geográficas.';

-- Índice en detections.frame_id (obtener detecciones de frame)
CREATE INDEX IF NOT EXISTS idx_detections_frame_id 
    ON detections(frame_id);
COMMENT ON INDEX idx_detections_frame_id IS 'Obtener todas las detecciones de un fotograma.';

-- Índice en detections.class_id (filtrar por tipo de objeto)
CREATE INDEX IF NOT EXISTS idx_detections_class_id 
    ON detections(class_id);
COMMENT ON INDEX idx_detections_class_id IS 'Filtrar detecciones por clase (ej: todas las personas).';

-- Índice en detections.confidence (filtrar por confianza)
CREATE INDEX IF NOT EXISTS idx_detections_confidence 
    ON detections(confidence DESC);
COMMENT ON INDEX idx_detections_confidence IS 'Filtrar detecciones por nivel de confianza.';

-- ============================================================================
-- CONSTRAINT ADICIONAL: Asegurar que bbox sea válido (x_min < x_max, y_min < y_max)
-- ============================================================================
ALTER TABLE detections 
    ADD CONSTRAINT check_bbox_valid 
    CHECK (bbox_x_min < bbox_x_max AND bbox_y_min < bbox_y_max);

-- ============================================================================
-- TABLA: persons (personas registradas para reconocimiento facial)
-- Propósito: Almacenar datos de personas para S5.1, S5.2 y S5.3
-- ============================================================================
CREATE TABLE IF NOT EXISTS persons (
    person_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    keycloak_user_id VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE persons IS 'Personas registradas para reconocimiento facial.';

-- ============================================================================
-- TABLA: face_embeddings (vectores faciales de personas)
-- Propósito: Almacenar embeddings faciales generados por DeepFace (S5.2)
-- Relación: N face_embeddings → 1 person (FK person_id)
-- ============================================================================
CREATE TABLE IF NOT EXISTS face_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,
    CONSTRAINT fk_face_embeddings_person_id
        FOREIGN KEY (person_id) REFERENCES persons(person_id) ON DELETE CASCADE,
    embedding vector(128) NOT NULL,
    confidence FLOAT,
    CONSTRAINT check_embedding_confidence CHECK (confidence >= 0.0 AND confidence <= 1.0),
    image_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE face_embeddings IS 'Embeddings faciales generados por DeepFace. Vinculados a person_id con cascada.';

-- ============================================================================
-- ÍNDICES para persons y face_embeddings
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_face_embeddings_person_id
    ON face_embeddings(person_id);
COMMENT ON INDEX idx_face_embeddings_person_id IS 'Obtener todos los embeddings de una persona.';

-- Índice IVFFLAT para búsqueda vectorial aproximada (S5.3)
CREATE INDEX IF NOT EXISTS idx_face_embeddings_ivfflat
    ON face_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
COMMENT ON INDEX idx_face_embeddings_ivfflat IS 'Búsqueda aproximada de rostros similares (distancia cosine).';

-- ============================================================================
-- MIGRACION: Agregar columna keycloak_user_id a tabla persons existentes
-- Usa DO bloque para evitar error si la columna ya existe
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'persons' AND column_name = 'keycloak_user_id'
    ) THEN
        ALTER TABLE persons ADD COLUMN keycloak_user_id VARCHAR(255);
        COMMENT ON COLUMN persons.keycloak_user_id IS 'ID del usuario de Keycloak vinculado a esta persona (sub del token JWT)';
    END IF;
END $$;

-- ============================================================================
-- RESULTADO FINAL
-- ============================================================================
-- ✓ Tabla frames: almacena fotogramas con geolocalización + metadatos
-- ✓ Tabla detections: almacena objetos detectados con bbox + confianza
-- ✓ Tabla persons: almacena personas registradas (S5.1)
-- ✓ Tabla face_embeddings: almacena vectores faciales 128D (S5.2/S5.3)
-- ✓ Relación: frame_id FK con CASCADE (integridad referencial)
-- ✓ Relación: person_id FK con CASCADE (integridad referencial)
-- ✓ Índices: optimizados para queries S2, S3, S4, S5
-- ✓ Índice IVFFLAT: búsqueda facial aproximada (S5.3)
-- ✓ Constraints: validación de datos (confidence 0-1, bbox válido, etc.)
-- ============================================================================