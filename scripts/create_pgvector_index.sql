-- Tarea 0.2: Crear indice IVFFLAT en face_embeddings para busqueda vectorial rapida
-- Ejecutar via pgAdmin (https://bfts2026.mooo.com/pgadmin/) o psql remoto
-- 
-- pgAdmin: Servidor -> db:5432, DB: detections_db, abrir Query Tool y pegar esto
-- psql:   PGPASSWORD=<pass> psql -h bfts2026.mooo.com -U detections_user -d detections_db -f scripts/create_pgvector_index.sql

CREATE INDEX IF NOT EXISTS idx_face_embeddings_vector
ON face_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Verificar que el indice se creo correctamente
SELECT
    relname AS index_name,
    amname AS index_type,
    pg_size_pretty(pg_relation_size(oid)) AS size
FROM pg_class c
JOIN pg_am a ON c.relam = a.oid
WHERE c.relname = 'idx_face_embeddings_vector';
