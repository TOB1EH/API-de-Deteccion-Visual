#!/usr/bin/env python3
"""
Script para cargar imágenes faciales al sistema:
1. Sube cada imagen a SeaweedFS
2. Crea una persona por cada imagen
3. Genera embedding facial con DeepFace (S5.2)

Uso:
    python3 scripts/upload_facial_images.py [--dry-run]

Requiere:
    - Servicios Docker levantados (api, face-api, seaweed, db, nginx)
    - Imágenes en /home/masterxdual/Escritorio/famous_photos/
"""

import os
import sys
import json
import base64
import argparse
import requests
from pathlib import Path

BASE_URL = "http://localhost"
FACES_DIR = Path(os.path.expanduser("~/Escritorio/famous_photos"))

API_URL = f"{BASE_URL}/api"
DETECTIONS_URL = f"{API_URL}/detections"
PERSONS_URL = f"{API_URL}/persons"

COLORS = {
    "HEADER": "\033[95m",
    "OKBLUE": "\033[94m",
    "OKGREEN": "\033[92m",
    "WARNING": "\033[93m",
    "FAIL": "\033[91m",
    "ENDC": "\033[0m",
    "BOLD": "\033[1m",
}


def print_step(msg):
    print(f"\n{COLORS['OKBLUE']}{COLORS['BOLD']}[*] {msg}{COLORS['ENDC']}")

def print_ok(msg):
    print(f"{COLORS['OKGREEN']}  ✓ {msg}{COLORS['ENDC']}")

def print_warn(msg):
    print(f"{COLORS['WARNING']}  ⚠ {msg}{COLORS['ENDC']}")

def print_fail(msg):
    print(f"{COLORS['FAIL']}  ✗ {msg}{COLORS['ENDC']}")


def image_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_image_name(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").title()


def upload_to_seaweed(image_path: Path, dry_run: bool = False) -> str:
    if dry_run:
        return f"http://localhost/seaweed/{image_path.name}"

    with open(image_path, "rb") as f:
        files = {"file": (image_path.name, f, "image/jpeg")}
        try:
            resp = requests.post(
                "http://localhost:9333/submit",
                files=files,
                timeout=30
            )
            if resp.status_code in (200, 201):
                file_id = resp.json().get("fid", "")
                return f"http://localhost/seaweed/{file_id}.jpg"
            else:
                print_fail(f"Error subiendo a Seaweed: {resp.status_code} - {resp.text}")
                return ""
        except Exception as e:
            print_fail(f"Error de conexión a Seaweed: {e}")
            return ""


def create_person(name: str, image_url: str, dry_run: bool = False) -> str:
    if dry_run:
        return "dry-run-uuid"

    payload = {
        "name": name,
        "metadata": {"source_image": image_url}
    }
    try:
        resp = requests.post(PERSONS_URL, json=payload, timeout=10)
        if resp.status_code == 201:
            data = resp.json()
            print_ok(f"Persona creada: {data['person_id']}")
            return data["person_id"]
        else:
            print_fail(f"Error creando persona: {resp.status_code} - {resp.text}")
            return ""
    except Exception as e:
        print_fail(f"Error de conexión: {e}")
        return ""


def generate_embedding(person_id: str, image_url: str, dry_run: bool = False) -> bool:
    if dry_run:
        return True

    url = f"{API_URL}/persons/{person_id}/embeddings"
    payload = {"image_url": image_url}
    try:
        resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            print_ok(f"Embedding generado: {data['embedding_id']} (confianza: {data['confidence']:.4f})")
            return True
        else:
            print_fail(f"Error generando embedding: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print_fail(f"Error de conexión: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Cargar imágenes faciales al sistema")
    parser.add_argument("--dry-run", action="store_true", help="Simular sin ejecutar cambios")
    args = parser.parse_args()

    if args.dry_run:
        print_warn("MODO DRY RUN - No se ejecutarán cambios reales\n")

    if not FACES_DIR.exists():
        print_fail(f"Directorio no encontrado: {FACES_DIR}")
        print(f"Creá el directorio y poné las imágenes allí: mkdir -p {FACES_DIR}")
        sys.exit(1)

    images = sorted(FACES_DIR.glob("*.jpg")) + sorted(FACES_DIR.glob("*.jpeg")) + sorted(FACES_DIR.glob("*.png"))
    if not images:
        print_fail(f"No se encontraron imágenes JPG/PNG en {FACES_DIR}")
        sys.exit(1)

    print_step(f"Se encontraron {len(images)} imágenes para procesar\n")

    results = []

    for i, img_path in enumerate(images, 1):
        name = get_image_name(img_path)
        print_step(f"[{i}/{len(images)}] Procesando: {img_path.name} → {name}")

        image_url = upload_to_seaweed(img_path, args.dry_run)
        if not image_url:
            print_fail("  → Abortando esta imagen")
            continue
        print_ok(f"Imagen subida: {image_url}")

        person_id = create_person(name, image_url, args.dry_run)
        if not person_id:
            print_fail("  → Abortando esta imagen")
            continue

        success = generate_embedding(person_id, image_url, args.dry_run)

        results.append({
            "image": img_path.name,
            "name": name,
            "person_id": person_id,
            "image_url": image_url,
            "embedding_generated": success
        })

    print_step("RESUMEN FINAL")
    print(f"Total imágenes: {len(images)}")
    print(f"Procesadas exitosamente: {sum(1 for r in results if r['embedding_generated'])}")
    print(f"Fallidas: {sum(1 for r in results if not r['embedding_generated'])}")

    for r in results:
        status = "✓" if r["embedding_generated"] else "✗"
        print(f"  [{status}] {r['name']:20s} → {r['person_id']}")

    with open("scripts/upload_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResultados guardados en scripts/upload_results.json")


if __name__ == "__main__":
    main()
