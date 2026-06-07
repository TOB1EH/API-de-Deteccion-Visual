#!/usr/bin/env python3
"""Script de instalacion automatica del nodo de inferencia local.
Descarga modelos, levanta el contenedor Docker y genera un script de prueba.
"""
import os
import sys
import json
import urllib.request
import subprocess
import platform
import shutil

# ==============================================================================
# CONFIGURACION
# ==============================================================================
# URL base de la API central (cambiar si se despliega en otro dominio)
API_BASE = os.environ.get("API_BASE", "https://bfts2026.mooo.com")
# Directorio local donde se guardaran los modelos
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modelos")
# Contenedor del profesor (o la version mejorada del grupo)
DOCKER_IMAGE = "magm3333/simple-yolo-inference-server:latest"
CONTAINER_NAME = "yolo-inference-local"

# ==============================================================================
# COLORES
# ==============================================================================
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_step(msg):
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}[*] {msg}{Colors.ENDC}")


def print_ok(msg):
    print(f"{Colors.OKGREEN}  -> {msg}{Colors.ENDC}")


def print_warn(msg):
    print(f"{Colors.WARNING}  -> {msg}{Colors.ENDC}")


def print_error(msg):
    print(f"{Colors.FAIL}  -> {msg}{Colors.ENDC}")


# ==============================================================================
# FUNCIONES
# ==============================================================================
def check_docker():
    """Verifica que Docker este instalado y corriendo."""
    print_step("Verificando Docker...")
    try:
        subprocess.run(
            ["docker", "--version"],
            capture_output=True, check=True, timeout=10
        )
        print_ok("Docker detectado.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error(
            "Docker no encontrado. Instalalo desde https://docs.docker.com/get-docker/"
        )
        return False


def check_container_running():
    """Verifica si el contenedor de inferencia ya esta corriendo."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={CONTAINER_NAME}",
             "--filter", "status=running", "--format", "{{.Names}}"],
            capture_output=True, text=True, check=True, timeout=10
        )
        if CONTAINER_NAME in result.stdout:
            print_ok(f"Contenedor '{CONTAINER_NAME}' ya esta corriendo.")
            return True
    except subprocess.SubprocessError:
        pass
    return False


def pull_docker_image():
    """Descarga la imagen Docker de inferencia."""
    print_step(f"Descargando imagen Docker: {DOCKER_IMAGE}...")
    try:
        subprocess.run(
            ["docker", "pull", DOCKER_IMAGE],
            check=True, timeout=300
        )
        print_ok("Imagen descargada correctamente.")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Error descargando imagen: {e}")
        return False


def fetch_model_list():
    """Obtiene la lista de modelos disponibles desde la API remota."""
    print_step("Consultando modelos disponibles en la nube...")
    try:
        req = urllib.request.Request(f"{API_BASE}/api/models")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        models = data.get("models", [])
        if models:
            print_ok(f"{len(models)} modelo(s) disponible(s):")
            for m in models:
                size_mb = m["size"] / (1024 * 1024)
                print(f"     - {m['name']} ({size_mb:.1f} MB)")
        else:
            print_warn("No se encontraron modelos en la nube.")
        return models
    except Exception as e:
        print_error(f"Error consultando modelos: {e}")
        return []


def download_model(model_name, models_dir):
    """Descarga un modelo especifico desde la API remota."""
    model_path = os.path.join(models_dir, model_name)
    if os.path.exists(model_path):
        size_mb = os.path.getsize(model_path) / (1024 * 1024)
        print_ok(f"Modelo '{model_name}' ya existe localmente ({size_mb:.1f} MB).")
        return True

    url = f"{API_BASE}/api/models/{model_name}/download"
    print_step(f"Descargando modelo '{model_name}'...")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=120) as resp:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 8192
            os.makedirs(models_dir, exist_ok=True)
            with open(model_path, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        pct = int(downloaded * 100 / total_size)
                        bar = "#" * (pct // 5) + "." * (20 - pct // 5)
                        sys.stdout.write(
                            f"\r     [{bar}] {pct}% ({downloaded//1024} KB)"
                        )
                        sys.stdout.flush()
            print()
        print_ok(f"Modelo '{model_name}' descargado.")
        return True
    except Exception as e:
        print_error(f"Error descargando modelo: {e}")
        return False


def start_container(models_dir):
    """Inicia el contenedor Docker con los modelos montados."""
    print_step("Iniciando contenedor de inferencia...")

    # Detener contenedor previo si existe (sin importar estado)
    subprocess.run(
        ["docker", "rm", "-f", CONTAINER_NAME],
        capture_output=True, timeout=10
    )

    abs_models_dir = os.path.abspath(models_dir)
    try:
        subprocess.run(
            [
                "docker", "run", "-d",
                "--name", CONTAINER_NAME,
                "-p", "8001:8000",
                "-v", f"{abs_models_dir}:/app/models",
                DOCKER_IMAGE
            ],
            check=True, timeout=60
        )
        print_ok(
            f"Contenedor '{CONTAINER_NAME}' corriendo en http://localhost:8001"
        )
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Error iniciando contenedor: {e}")
        return False


def create_test_script():
    """Crea un script de prueba para verificar la inferencia local."""
    script_content = '''#!/usr/bin/env python3
"""
Script de prueba: Toma una imagen, la procesa con YOLO local y
sube los resultados al backend remoto.

USO:
    python3 test_inferencia.py ruta/a/mi/imagen.jpg
"""
import os
import sys
import json
import base64
import urllib.request

API_BASE = os.environ.get("API_BASE", "{api_base}")
INFER_URL = "http://localhost:8001/infer"
DETECTIONS_URL = f"{{API_BASE}}/api/detections"
MODEL_NAME = "{model_name}"


def main(image_path):
    if not os.path.exists(image_path):
        print(f"ERROR: Imagen no encontrada: {{image_path}}")
        sys.exit(1)

    print(f"Procesando: {{image_path}}...")

    # 1. Inferencia LOCAL con YOLO
    with open(image_path, "rb") as f:
        img_data = f.read()

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{{boundary}}\\r\\n"
        f'Content-Disposition: form-data; name="image"; filename="test.jpg"\\r\\n'
        f"Content-Type: image/jpeg\\r\\n\\r\\n"
    ).encode() + img_data + (
        f"\\r\\n--{{boundary}}\\r\\n"
        f'Content-Disposition: form-data; name="model_name"\\r\\n\\r\\n'
        f"{{MODEL_NAME}}\\r\\n"
        f"--{{boundary}}\\r\\n"
        f'Content-Disposition: form-data; name="confidence"\\r\\n\\r\\n'
        f"0.25\\r\\n"
        f"--{{boundary}}--\\r\\n"
    ).encode()

    req = urllib.request.Request(
        INFER_URL, data=body,
        headers={{"Content-Type": "multipart/form-data; boundary={{boundary}}"}}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        infer_result = json.loads(resp.read().decode())

    if infer_result["info"]["error"]:
        print(f"ERROR en inferencia: {{infer_result['info']['errormsg']}}")
        sys.exit(1)

    detections = infer_result["results"]
    print(f"  Detectados {{len(detections)}} objeto(s).")

    # 2. Subir al backend remoto
    image_b64 = base64.b64encode(img_data).decode("utf-8")
    payload = {{
        "image_base64": f"data:image/jpeg;base64,{{image_b64}}",
        "model_id": MODEL_NAME,
        "latitude": -34.6037,
        "longitude": -58.3816,
        "detections": [
            {{
                "class_name": d["classname"],
                "class_id": d["classnumber"],
                "confidence": round(d["conf"] / 100.0, 4),
                "bbox": {{
                    "x_min": d["bbox"][0],
                    "y_min": d["bbox"][1],
                    "x_max": d["bbox"][2],
                    "y_max": d["bbox"][3]
                }}
            }}
            for d in detections
        ],
        "metadata": {{
            "camera_id": "local-test",
            "source": "setup-cliente"
        }}
    }}

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        DETECTIONS_URL, data=data,
        headers={{"Content-Type": "application/json"}}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode())

    print(f"  Frame ID: {{result['frame_id']}}")
    print(f"  Estado: {{result['status']}}")
    print(f"  Imagen URL: {{result['image_url']}}")
    print("PROCESO COMPLETO.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 test_inferencia.py <ruta/imagen.jpg>")
        sys.exit(1)
    main(sys.argv[1])
'''
    script_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "test_inferencia.py"
    )
    with open(script_path, "w") as f:
        f.write(script_content)
    os.chmod(script_path, 0o755)
    print_ok(f"Script de prueba creado: {script_path}")
    return script_path


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    print(f"{Colors.HEADER}{Colors.BOLD}")
    print("=" * 60)
    print("  INSTALADOR DEL NODO DE INFERENCIA LOCAL")
    print("  API Detection Visual - Trabajo Integrador SOA")
    print("=" * 60)
    print(f"{Colors.ENDC}")

    # 1. Verificar Docker
    if not check_docker():
        sys.exit(1)

    # 2. Verificar si el contenedor ya esta corriendo
    if check_container_running():
        # Solo sincronizar modelos
        models_dir = MODELS_DIR
        os.makedirs(models_dir, exist_ok=True)
        models = fetch_model_list()
        if models:
            for m in models:
                download_model(m["name"], models_dir)
        print_ok("Todo listo. El nodo de inferencia local esta operativo.")
        return

    # 3. Descargar imagen Docker
    if not pull_docker_image():
        sys.exit(1)

    # 4. Consultar modelos remotos
    models_dir = MODELS_DIR
    os.makedirs(models_dir, exist_ok=True)
    models = fetch_model_list()
    if not models:
        print_warn("No se descargaran modelos (no hay disponibles en la nube).")

    # 5. Descargar modelos
    downloaded_model = None
    for m in models:
        if download_model(m["name"], models_dir):
            downloaded_model = m["name"]

    # 6. Iniciar contenedor
    if not start_container(models_dir):
        sys.exit(1)

    # 7. Crear script de prueba
    test_script = create_test_script()
    test_script = test_script.replace("{api_base}", API_BASE)
    test_script = test_script.replace("{model_name}", downloaded_model or "yolo11n.pt")

    # 8. Resumen final
    print(f"\n{Colors.OKGREEN}{Colors.BOLD}")
    print("=" * 60)
    print("  INSTALACION COMPLETADA")
    print("=" * 60)
    print(f"{Colors.ENDC}")
    print(f"  Nodo de inferencia: http://localhost:8001")
    print(f"  Documentacion local: http://localhost:8001/docs")
    print(f"  Modelos descargados: {models_dir}")
    print(f"  Script de prueba:    python3 {test_script}")
    print()
    print(f"  Para procesar una imagen, ejecuta:")
    print(f"    {Colors.OKCYAN}python3 {test_script} ruta/a/tu/imagen.jpg{Colors.ENDC}")
    print()


if __name__ == "__main__":
    main()
