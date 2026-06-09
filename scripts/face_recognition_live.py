#!/usr/bin/env python3
"""
################### PARA FINAL #####################
Script para reconocimiento facial en vivo con camara web.
Presiona ESPACIO para capturar y reconocer, ESC para salir.

Uso:
    pip install opencv-python requests
    python3 scripts/face_recognition_live.py

Requiere:
    - Servicios Docker levantados (api, face-api, seaweed, db, nginx)
"""

import cv2
import requests
import tempfile
import os
import sys
from pathlib import Path

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
            print(f"  Error subiendo a Seaweed: {resp.status_code} - {resp.text}")
            return ""


def recognize_face(image_path: str, threshold: float = 0.5):
    image_url = upload_to_seaweed(image_path)
    if not image_url:
        return None

    resp = requests.post(
        FACE_API_URL,
        json={"image_url": image_url, "threshold": threshold},
        timeout=60
    )

    if resp.status_code != 200:
        print(f"  Error en face-recognition: {resp.status_code} - {resp.text}")
        return None

    return resp.json()


def main():
    print("Iniciando camara...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: No se pudo abrir la camara (0). Probando con 1...")
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            print("Error: No se pudo abrir la camara.")
            sys.exit(1)

    print("Presiona ESPACIO para capturar y reconocer, ESC para salir")
    window_name = "Reconocimiento Facial - [ESPACIO] capturar  [ESC] salir"
    last_result = ""
    show_until = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error al leer frame de la camara")
            break

        if show_until > cv2.getTickCount():
            display = frame.copy()
            cv2.putText(display, last_result, (20, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
            cv2.imshow(window_name, display)
        else:
            cv2.imshow(window_name, frame)

        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            break
        elif key == 32:
            print("\nCapturando frame...")
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                tmp_path = f.name
                cv2.imwrite(tmp_path, frame)

            print("  Subiendo a SeaweedFS y reconociendo...")
            result = recognize_face(tmp_path)
            os.unlink(tmp_path)

            if result is None:
                last_result = "Error en reconocimiento"
            elif result.get("recognized"):
                match = result["matches"][0]
                name = match["name"]
                conf = match["confidence"]
                last_result = f"{name} ({conf:.2f})"
                print(f"  RECONOCIDO: {name} (confianza: {conf:.2f})")
            else:
                last_result = "No reconocido"
                print("  No reconocido")

            show_until = cv2.getTickCount() + int(cv2.getTickFrequency() * 3)

    cap.release()
    cv2.destroyAllWindows()
    print("\nCamara cerrada.")


if __name__ == "__main__":
    main()
