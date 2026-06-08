"""
Script de siembra (seed) para generar datos de prueba en la API de Deteccion Visual.

Genera:
- 5 imagenes sinteticas con colores, formas y texto usando Pillow
- Sube cada imagen a SeaweedFS
- Inserta 5 frames en PostgreSQL con coordenadas geograficas de Argentina
- Inserta 2-4 detecciones por frame (person, car, dog, cat, bicycle)
- Inserta 3 personas de prueba

Uso:
    python scripts/seed.py                    # Usa defaults locales
    python scripts/seed.py --env remote       # Usa configuracion remota
    python scripts/seed.py --db-url postgresql://user:pass@host:port/db
"""

import argparse
import base64
import io
import json
import logging
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

COORDINATES = [
    {"city": "Buenos Aires", "lat": -34.6037, "lon": -58.3816},
    {"city": "Cordoba", "lat": -31.4201, "lon": -64.1888},
    {"city": "Rosario", "lat": -32.9468, "lon": -60.6393},
    {"city": "Mendoza", "lat": -32.8895, "lon": -68.8458},
    {"city": "Bariloche", "lat": -41.1335, "lon": -71.3103},
]

DETECTION_TEMPLATES = [
    {"class_name": "person", "class_id": 0, "bbox": {"x_min": 50, "y_min": 30, "x_max": 200, "y_max": 480}},
    {"class_name": "car", "class_id": 2, "bbox": {"x_min": 180, "y_min": 200, "x_max": 420, "y_max": 340}},
    {"class_name": "dog", "class_id": 16, "bbox": {"x_min": 60, "y_min": 350, "x_max": 180, "y_max": 460}},
    {"class_name": "cat", "class_id": 15, "bbox": {"x_min": 300, "y_min": 100, "x_max": 380, "y_max": 220}},
    {"class_name": "bicycle", "class_id": 1, "bbox": {"x_min": 220, "y_min": 280, "x_max": 350, "y_max": 420}},
]

PERSONS = [
    {"nombre": "Juan", "apellido": "Perez", "email": "juan.perez@example.com", "extra": {"telefono": "+54 11 5555-0101", "edad": 30}},
    {"nombre": "Maria", "apellido": "Garcia", "email": "maria.garcia@example.com", "extra": {"telefono": "+54 351 5555-0202", "edad": 28}},
    {"nombre": "Carlos", "apellido": "Lopez", "email": "carlos.lopez@example.com", "extra": {"rol": "admin", "activo": True}},
]


def generate_synthetic_image(width=640, height=480, color=(100, 149, 237), text="Test"):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.error("Pillow no instalado. Ejecute: pip install Pillow")
        sys.exit(1)

    img = Image.new("RGB", (width, height), color)
    draw = ImageDraw.Draw(img)

    for _ in range(5):
        import random
        x1 = random.randint(0, width - 50)
        y1 = random.randint(0, height - 50)
        x2 = x1 + random.randint(20, 100)
        y2 = y1 + random.randint(20, 100)
        r, g, b = random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
        draw.rectangle([x1, y1, x2, y2], outline=(r, g, b), width=3)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except (IOError, OSError):
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tx = (width - (bbox[2] - bbox[0])) // 2
    ty = (height - (bbox[3] - bbox[1])) // 2
    draw.text((tx, ty), text, fill=(255, 255, 255), font=font)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def get_db_connection(db_url):
    import psycopg2
    from psycopg2.extras import RealDictCursor

    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    return conn


def upload_to_seaweedfs(image_bytes, frame_id, seaweed_url, seaweed_master_url):
    import requests

    files = {"file": (f"{frame_id}.jpg", io.BytesIO(image_bytes), "image/jpeg")}
    try:
        resp = requests.post(f"{seaweed_master_url}/submit", files=files, timeout=30)
        if resp.status_code in (200, 201):
            data = resp.json()
            fid = data.get("fid")
            logger.info("Imagen subida a SeaweedFS: fid=%s", fid)
            return fid
        else:
            logger.error("Error SeaweedFS: %s %s", resp.status_code, resp.text)
            return None
    except Exception as e:
        logger.error("Error subiendo a SeaweedFS: %s", e)
        return None


def seed_database(args):
    db_url = args.db_url
    seaweed_url = args.seaweed_url
    seaweed_master_url = args.seaweed_master_url
    seaweed_public_url = args.seaweed_public_url

    conn = get_db_connection(db_url)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM frames")
        existing = cursor.fetchone()[0]
        if existing > 0:
            logger.warning("Ya existen %d frames en la BD. Use --force para resetear.", existing)
            if not args.force:
                logger.info("Omitiendo siembra de frames. Use --force para forzar.")
                seed_persons(cursor, conn, args.force)
                conn.close()
                return

        if args.force:
            logger.warning("Forzando reseteo de datos existentes...")
            cursor.execute("DELETE FROM detections")
            cursor.execute("DELETE FROM frames")
            cursor.execute("DELETE FROM persons")
            cursor.execute("DELETE FROM embeddings")
            conn.commit()
            logger.info("Datos previos eliminados.")

        for i, coord in enumerate(COORDINATES):
            frame_id = str(uuid4())
            city = coord["city"]
            lat = coord["lat"]
            lon = coord["lon"]

            color_hex = hash(city) & 0xFFFFFF
            color = ((color_hex >> 16) & 0xFF, (color_hex >> 8) & 0xFF, color_hex & 0xFF)

            image_bytes = generate_synthetic_image(
                width=640, height=480, color=color, text=f"{city} - Frame {i+1}"
            )

            fid = upload_to_seaweedfs(image_bytes, frame_id, seaweed_url, seaweed_master_url)
            if not fid:
                logger.error("No se pudo subir imagen para %s, saltando...", city)
                continue

            image_url = f"{seaweed_public_url}/{fid}.jpg"

            num_detections = 2 + (i % 3)
            selected_detections = DETECTION_TEMPLATES[:num_detections]

            cursor.execute("""
                INSERT INTO frames (frame_id, model_id, latitude, longitude, image_url,
                                    detections_count, camera_id, source, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (
                frame_id, "yolo11n.pt", lat, lon, image_url,
                len(selected_detections), f"cam-{i+1:03d}", "seed-script"
            ))

            for det in selected_detections:
                detection_id = str(uuid4())
                confidence = 0.65 + (hash(det["class_name"]) % 30) / 100.0
                bbox = det["bbox"]
                cursor.execute("""
                    INSERT INTO detections (detection_id, frame_id, class_name, class_id,
                                            confidence, bbox_x_min, bbox_y_min,
                                            bbox_x_max, bbox_y_max, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    detection_id, frame_id, det["class_name"], det["class_id"],
                    confidence, bbox["x_min"], bbox["y_min"],
                    bbox["x_max"], bbox["y_max"]
                ))

            conn.commit()
            logger.info("Frame %d/%d: %s | %d detecciones | fid=%s",
                        i + 1, len(COORDINATES), city, len(selected_detections), fid)

        logger.info("Siembra de frames completada exitosamente.")
        seed_persons(cursor, conn, args.force)

    except Exception as e:
        conn.rollback()
        logger.exception("Error durante la siembra: %s", e)
        raise
    finally:
        cursor.close()
        conn.close()


def seed_persons(cursor, conn, force=False):
    try:
        cursor.execute("SELECT COUNT(*) FROM persons")
        existing = cursor.fetchone()[0]
        if existing > 0 and not force:
            logger.info("Ya existen %d personas en la BD. Omitiendo.", existing)
            return

        if force:
            cursor.execute("DELETE FROM persons")
            conn.commit()

        for p in PERSONS:
            person_id = str(uuid4())
            extra_json = json.dumps(p["extra"])
            cursor.execute("""
                INSERT INTO persons (person_id, nombre, apellido, email, extra, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (email) DO NOTHING
            """, (person_id, p["nombre"], p["apellido"], p["email"], extra_json))

        conn.commit()
        logger.info("Se insertaron %d personas de prueba.", len(PERSONS))
    except Exception as e:
        conn.rollback()
        logger.exception("Error insertando personas: %s", e)


def verify_data(args):
    import psycopg2
    from psycopg2.extras import RealDictCursor

    conn = psycopg2.connect(args.db_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("SELECT COUNT(*) as cnt FROM frames")
    frames_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM detections")
    detections_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM persons")
    persons_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT frame_id, latitude, longitude, detections_count FROM frames ORDER BY created_at")
    frames = cursor.fetchall()

    cursor.close()
    conn.close()

    print("\n=== VERIFICACION DE DATOS ===")
    print(f"Frames:     {frames_count}")
    print(f"Detections: {detections_count}")
    print(f"Persons:    {persons_count}")
    print()
    for f in frames:
        print(f"  Frame {f['frame_id'][:8]}... | lat={f['latitude']:.4f} lon={f['longitude']:.4f} dets={f['detections_count']}")

    return frames_count > 0


def main():
    parser = argparse.ArgumentParser(description="Seed data for API Deteccion Visual")
    parser.add_argument("--env", choices=["local", "remote"], default="local")
    parser.add_argument("--db-url", help="PostgreSQL connection URL")
    parser.add_argument("--seaweed-url", help="SeaweedFS volume URL")
    parser.add_argument("--seaweed-master-url", help="SeaweedFS master URL")
    parser.add_argument("--seaweed-public-url", help="SeaweedFS public URL base")
    parser.add_argument("--force", action="store_true", help="Resetear datos existentes")
    parser.add_argument("--verify", action="store_true", help="Solo verificar datos sin sembrar")

    args = parser.parse_args()

    if args.env == "local":
        args.db_url = args.db_url or "postgresql://detections_user:secure_pwd_local@localhost:5433/detections_db"
        args.seaweed_url = args.seaweed_url or "http://localhost:8090"
        args.seaweed_master_url = args.seaweed_master_url or "http://localhost:9333"
        args.seaweed_public_url = args.seaweed_public_url or "http://localhost/seaweed"
    else:
        args.db_url = args.db_url or "postgresql://detections_user:bfts2026.@bfts2026.mooo.com:5432/detections_db"
        args.seaweed_url = args.seaweed_url or "https://bfts2026.mooo.com/seaweed"
        args.seaweed_master_url = args.seaweed_master_url or "http://seaweed-master:9333"
        args.seaweed_public_url = args.seaweed_public_url or "https://bfts2026.mooo.com/seaweed"

    if args.verify:
        verify_data(args)
        return

    seed_database(args)
    verify_data(args)


if __name__ == "__main__":
    main()
