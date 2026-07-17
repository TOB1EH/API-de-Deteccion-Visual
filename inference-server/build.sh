#!/bin/bash
# Script para construir y subir la imagen Docker a Docker Hub

# Detener el script si ocurre algún error
set -e

IMAGE_NAME="tfunes/inference-server"
TAG="latest"

echo "=== 1. Construyendo la imagen Docker: ${IMAGE_NAME}:${TAG} ==="
docker build -t "${IMAGE_NAME}:${TAG}" .

echo "=== 2. Subiendo la imagen a Docker Hub ==="
docker push "${IMAGE_NAME}:${TAG}"

echo "=== ¡Proceso completado con éxito! ==="
