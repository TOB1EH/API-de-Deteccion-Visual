#!/usr/bin/env python3
"""
Reconocimiento facial desde una imagen local.
Sube la imagen a SeaweedFS y la reconoce contra la BD.

Uso:
    python3 scripts/face_recognition_local.py ruta/a/mi/foto.jpg [threshold]

Ejemplo:
    python3 scripts/face_recognition_local.py ~/Escritorio/foto_prueba.jpg 0.5

Requiere:
    - Servicios Docker levantados
    - pip install requests
"""

import sys
import os
import requests

SEAWEED_SUBMIT = "http://localhost:9333/submit"
FACE_API_URL = "http://localhost/api/face-recognition"


def upload_to_seaweed(image_path: str) -> str:
    with open(image_path, "rb") as f:
        files = {"file": (os.path.basename(image_path), f, "image/jpeg")}
        resp = requests.post(SEAWEED_SUBMIT, files=files, timeout=30)
        if resp.status_code in (200, 201):
            file_id = resp.json().get("fid", "")
            return f"http://localhost/seaweed/{file_id}.jpg"
        else:
            print(f"Error subiendo a Seaweed: {resp.status_code} - {resp.text}")
            sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 scripts/face_recognition_local.py <imagen> [threshold]")
        sys.exit(1)

    image_path = sys.argv[1]
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5

    if not os.path.exists(image_path):
        print(f"Error: archivo no encontrado: {image_path}")
        sys.exit(1)

    print(f"Subiendo {image_path} a SeaweedFS...")
    image_url = upload_to_seaweed(image_path)
    print(f"  URL: {image_url}")

    print("Reconociendo rostro...")
    resp = requests.post(
        FACE_API_URL,
        json={"image_url": image_url, "threshold": threshold},
        timeout=60
    )

    if resp.status_code != 200:
        print(f"Error: {resp.status_code} - {resp.text}")
        sys.exit(1)

    result = resp.json()

    if result.get("recognized"):
        for match in result["matches"]:
            print(f"\n  RECONOCIDO: {match['name']}")
            print(f"  Confianza: {match['confidence']:.4f}")
            print(f"  Distancia: {match['distance']:.4f}")
    else:
        print("\n  No reconocido (no hay coincidencias sobre el threshold)")


if __name__ == "__main__":
    main()
