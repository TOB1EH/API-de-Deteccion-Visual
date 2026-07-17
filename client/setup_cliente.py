#!/usr/bin/env python3
"""
CLI cliente para API Detection Visual.
Procesa imagenes localmente con YOLO y persiste en el backend.

Subcomandos:
  install    Descarga modelos y levanta contenedor de inferencia local
  models     Lista modelos disponibles en el backend
  infer      Infiere imagen localmente y sube resultados al backend
  process    Envia imagen a la API para que ella haga la inferencia (orquestador)
  frames     Consulta y descarga fotogramas (list, get, annotate)
  persons    Gestiona personas registradas (list, create, get)

Uso:
  export API_BASE=http://localhost  # backend local (default: remoto)
  python3 setup_cliente.py faces login
  python3 setup_cliente.py install
  python3 setup_cliente.py infer foto.jpg --model yolo11n.pt
  python3 setup_cliente.py frames list --clases person
  python3 setup_cliente.py frames annotate <frame_id>
  python3 setup_cliente.py persons create "Juan Perez"
"""

import os
import sys
import json
import base64
import io
import glob
import time
import argparse
import urllib.request
import urllib.error
import urllib.parse
import subprocess

# ==============================================================================
# CONFIGURACION
# ==============================================================================
API_BASE = os.environ.get("API_BASE", "https://bfts2026.mooo.com")
INFER_URL = os.environ.get("INFER_URL", "http://localhost:8001/infer")
INFER_DOWNLOAD_URL = os.environ.get("INFER_DOWNLOAD_URL", "http://localhost:8001/infer/download")
MODELS_DIR = os.environ.get("MODELS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "modelos"))
DOCKER_IMAGE = "tfunes/inference-server:latest"
CONTAINER_NAME = "yolo-inference-local"

# Face recognition (DeepFace local via inference-server)
FACE_INFER_URL = os.environ.get("FACE_INFER_URL", API_BASE)
API_URL = os.environ.get("API_URL", "https://bfts2026.mooo.com")
DOCKER_NETWORK = "api_de_deteccion_visual_api-detection-net-local"

# Keycloak authentication
TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".api_detection_token.json")
KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", API_BASE)
KEYCLOAK_REALM = "api-detection"
KEYCLOAK_CLIENT_ID = "api-backend"


def load_token():
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE) as f:
                data = json.load(f)
            expires_at = data.get("expires_at", 0)
            if time.time() < expires_at - 60:
                return data.get("access_token")
        except (json.JSONDecodeError, KeyError, OSError):
            pass
    return None


def save_token(access_token, expires_in):
    data = {
        "access_token": access_token,
        "expires_at": time.time() + expires_in,
    }
    os.makedirs(os.path.dirname(TOKEN_FILE) or ".", exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f)
    os.chmod(TOKEN_FILE, 0o600)


def _auth_headers():
    token = load_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

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
# HELPERS HTTP
# ==============================================================================
def _exit_unauthorized():
    print_error("Acceso no autorizado. Tu sesion expiro o no iniciaste sesion.")
    print_error("Ejecuta: python3 setup_cliente.py faces login")
    sys.exit(1)


def api_get(path):
    req = urllib.request.Request(f"{API_BASE}/api/{path}", headers=_auth_headers())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            _exit_unauthorized()
        raise


def api_get_raw(path):
    req = urllib.request.Request(f"{API_BASE}/api/{path}", headers=_auth_headers())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 401:
            _exit_unauthorized()
        raise


def api_post(path, data):
    headers = {"Content-Type": "application/json"}
    headers.update(_auth_headers())
    req = urllib.request.Request(
        f"{API_BASE}/api/{path}",
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            _exit_unauthorized()
        raise


# ==============================================================================
# FUNCIONES DE INSTALACION
# ==============================================================================
def check_docker():
    print_step("Verificando Docker...")
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True, timeout=10)
        print_ok("Docker detectado.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error("Docker no encontrado. Instalalo desde https://docs.docker.com/get-docker/")
        return False


def check_container_running():
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
    print_step(f"Descargando imagen Docker: {DOCKER_IMAGE}...")
    try:
        subprocess.run(["docker", "pull", DOCKER_IMAGE], check=True, timeout=300)
        print_ok("Imagen descargada correctamente.")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Error descargando imagen: {e}")
        return False


def fetch_model_list():
    print_step("Consultando modelos disponibles en la nube...")
    try:
        req = urllib.request.Request(f"{API_BASE}/api/models", headers=_auth_headers())
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
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print_warn("Autenticacion requerida para listar modelos. Ejecuta 'python3 setup_cliente.py faces login' primero.")
        else:
            print_error(f"Error consultando modelos: {e}")
        return []
    except Exception as e:
        print_error(f"Error consultando modelos: {e}")
        return []


def download_model(model_name, models_dir):
    model_path = os.path.join(models_dir, model_name)
    if os.path.exists(model_path):
        size_mb = os.path.getsize(model_path) / (1024 * 1024)
        print_ok(f"Modelo '{model_name}' ya existe localmente ({size_mb:.1f} MB).")
        return True

    url = f"{API_BASE}/api/models/{model_name}/download"
    print_step(f"Descargando modelo '{model_name}'...")
    try:
        req = urllib.request.Request(url, headers=_auth_headers())
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
                        sys.stdout.write(f"\r     [{bar}] {pct}% ({downloaded//1024} KB)")
                        sys.stdout.flush()
            print()
        print_ok(f"Modelo '{model_name}' descargado.")
        return True
    except Exception as e:
        print_error(f"Error descargando modelo: {e}")
        return False


def select_models(models):
    if not models:
        return []
    print()
    print(f"  {'N°':<4} {'Modelo':<20} {'Tamaño':<10}")
    print(f"  {'---':<4} {'------':<20} {'------':<10}")
    for i, m in enumerate(models, 1):
        size_mb = m["size"] / (1024 * 1024)
        print(f"  {i:<4} {m['name']:<20} {size_mb:.1f} MB")
    print()
    print("  Ingresa los numeros de los modelos a descargar")
    print("  (ej: 1,3  o  1-3  o  *  para todos, Enter solo el primero):")
    choice = input(f"  {Colors.OKCYAN}> {Colors.ENDC}").strip()

    selected = []
    if not choice:
        selected = [models[0]]
    elif choice == "*":
        selected = models
    else:
        parts = choice.replace(" ", "").split(",")
        for p in parts:
            if "-" in p:
                a, b = p.split("-")
                for idx in range(int(a) - 1, int(b)):
                    if 0 <= idx < len(models):
                        selected.append(models[idx])
            else:
                try:
                    idx = int(p) - 1
                    if 0 <= idx < len(models):
                        selected.append(models[idx])
                except ValueError:
                    pass
    print_ok(f"{len(selected)} modelo(s) seleccionado(s).")
    return selected


def start_container(models_dir):
    print_step("Iniciando contenedor de inferencia...")
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True, timeout=10)
    abs_models_dir = os.path.abspath(models_dir)
    face_weights_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_weights")
    cmd = [
        "docker", "run", "-d",
        "--name", CONTAINER_NAME,
        "-p", "8001:8000",
        "-v", f"{abs_models_dir}:/app/models",
    ]
    os.makedirs(face_weights_dir, exist_ok=True)
    cmd.extend(["-v", f"{face_weights_dir}:/root/.deepface/weights"])
    is_local = any(x in API_URL for x in ["localhost", "127.0.0.1", "api_detection_api_local"])
    if is_local:
        cmd.extend(["--network", DOCKER_NETWORK])
        api_url_internal = API_URL.replace("localhost:8000", "api:8000") \
                                 .replace("127.0.0.1:8000", "api:8000")
        cmd.extend(["-e", f"API_URL={api_url_internal}"])
    else:
        cmd.extend(["-e", f"API_URL={API_URL}"])
    deepface_backend = os.environ.get("DEEPFACE_BACKEND", "Facenet")
    cmd.extend(["-e", f"DEEPFACE_BACKEND={deepface_backend}"])
    cors_origins = os.environ.get("CORS_ORIGINS", "https://bfts2026.mooo.com")
    cmd.extend(["-e", f"CORS_ORIGINS={cors_origins}"])
    cmd.append(DOCKER_IMAGE)
    try:
        subprocess.run(cmd, check=True, timeout=60)
        print_ok(f"Contenedor '{CONTAINER_NAME}' corriendo en http://localhost:8001")
        print_ok(f"Reconocimiento facial habilitado (DeepFace + API en {API_URL})")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Error iniciando contenedor: {e}")
        return False


# ==============================================================================
# COMANDO: install
# ==============================================================================
def cmd_install():
    print(f"{Colors.HEADER}{Colors.BOLD}")
    print("=" * 60)
    print("  INSTALADOR DEL NODO DE INFERENCIA LOCAL")
    print("  API Detection Visual - Trabajo Integrador SOA")
    print("=" * 60)
    print(f"{Colors.ENDC}")

    if not check_docker():
        sys.exit(1)

    if not pull_docker_image():
        sys.exit(1)

    models_dir = MODELS_DIR
    os.makedirs(models_dir, exist_ok=True)
    models = fetch_model_list()
    if not models:
        print_warn("No se descargaran modelos (no hay disponibles en la nube).")

    models_to_download = select_models(models) if models else []
    downloaded_model = None
    for m in models_to_download:
        if download_model(m["name"], models_dir):
            downloaded_model = downloaded_model or m["name"]

    if not start_container(models_dir):
        sys.exit(1)

    print(f"\n{Colors.OKGREEN}{Colors.BOLD}")
    print("=" * 60)
    print("  INSTALACION COMPLETADA")
    print("=" * 60)
    print(f"{Colors.ENDC}")
    print(f"  Nodo de inferencia: http://localhost:8001")
    print(f"  Documentacion local: http://localhost:8001/docs")
    print(f"  Modelos descargados: {models_dir}")
    print()
    print(f"  Para procesar una imagen, ejecuta:")
    print(f"    {Colors.OKCYAN}python3 setup_cliente.py infer ruta/imagen.jpg --model {downloaded_model or 'yolo11n.pt'}{Colors.ENDC}")
    print()
    print(f"  Reconocimiento facial habilitado:")
    print(f"    {Colors.OKCYAN}python3 setup_cliente.py faces embed <person_id> ruta/foto.jpg{Colors.ENDC}")
    print(f"    {Colors.OKCYAN}python3 setup_cliente.py faces embed <person_id> ruta/directorio/{Colors.ENDC}")
    print(f"    {Colors.OKCYAN}python3 setup_cliente.py faces recognize foto.jpg --threshold 0.5{Colors.ENDC}")
    print()


# ==============================================================================
# COMANDO: models
# ==============================================================================
def cmd_models():
    data = api_get("models")
    print(f"\n{Colors.BOLD}Modelos disponibles ({data['total']}):{Colors.ENDC}\n")
    for m in data["models"]:
        size_mb = m["size"] / (1024 * 1024)
        print(f"  {m['name']:<25} {size_mb:.1f} MB    {m.get('type', 'yolo')}")


def cmd_models_info(model_name):
    try:
        data = api_get(f"models/{model_name}")
    except urllib.error.HTTPError as e:
        print_error(f"Error {e.code}: Modelo '{model_name}' no encontrado")
        sys.exit(1)

    size_mb = data["size"] / (1024 * 1024)
    print(f"\n{Colors.BOLD}Informacion del modelo:{Colors.ENDC}\n")
    print(f"  Nombre: {data['name']}")
    print(f"  Tamaño: {size_mb:.1f} MB")
    print(f"  Tipo:   {data['type']}")
    print(f"  Ruta:   {data['path']}")
    print()


# ==============================================================================
# COMANDO: infer
# ==============================================================================
def cmd_infer(args):
    image_path = args.image
    if not os.path.exists(image_path):
        print_error(f"Imagen no encontrada: {image_path}")
        sys.exit(1)

    model_name = args.model
    confidence = args.confidence
    lat = args.lat
    lon = args.lon
    camera_id = args.camera_id

    with open(image_path, "rb") as f:
        img_data = f.read()

    print_step(f"Inferencia local con modelo '{model_name}'...")
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="image.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode() + img_data + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="model_name"\r\n\r\n'
        f"{model_name}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="confidence"\r\n\r\n'
        f"{confidence}\r\n"
        f"--{boundary}--\r\n"
    ).encode()

    req = urllib.request.Request(
        INFER_URL, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            infer_result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print_error(f"Modelo '{model_name}' no encontrado en el contenedor local.")
            print_error("Asegurate de haberlo descargado con: python3 setup_cliente.py install")
            print_error("Tambien podes probar con el comando 'process' que usa la API en la nube.")
            sys.exit(1)
        else:
            print_error(f"Error {e.code} del inference-server: {e.reason}")
            sys.exit(1)
    except urllib.error.URLError as e:
        print_error(f"No se puede conectar al inference-server en {INFER_URL}.")
        print_error("Asegurate de haber ejecutado: python3 setup_cliente.py install")
        sys.exit(1)

    if infer_result["info"]["error"]:
        print_error(f"Error en inferencia: {infer_result['info']['errormsg']}")
        sys.exit(1)

    detections = infer_result["results"]
    print_ok(f"Detectados {len(detections)} objeto(s).")

    print_step("Subiendo resultados al backend...")
    image_b64 = base64.b64encode(img_data).decode("utf-8")
    payload = {
        "image_base64": f"data:image/jpeg;base64,{image_b64}",
        "model_id": model_name,
        "latitude": lat,
        "longitude": lon,
        "detections": [
            {
                "class_name": d["classname"],
                "class_id": d["classnumber"],
                "confidence": round(d["conf"] / 100.0, 4),
                "bbox": {
                    "x_min": int(d["bbox_object"]["x_min"]),
                    "y_min": int(d["bbox_object"]["y_min"]),
                    "x_max": int(d["bbox_object"]["x_max"]),
                    "y_max": int(d["bbox_object"]["y_max"]),
                },
            }
            for d in detections
        ],
        "metadata": {
            "camera_id": camera_id,
            "source": "setup-cliente",
        },
    }

    result = api_post("detections", payload)
    frame_id = result["frame_id"]
    print_ok(f"Frame ID: {frame_id}")
    print_ok(f"Estado: {result['status']}")
    print_ok(f"Imagen URL: {result['image_url']}")

    print_step("Descargando imagen anotada...")
    annotated_id = infer_result["annotated_image_url"].split("/")[-1]
    annotated_url = f"{INFER_DOWNLOAD_URL}/{annotated_id}"
    output_dir = os.path.dirname(os.path.abspath(image_path))
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    annotated_path = os.path.join(output_dir, f"{base_name}_anotada.jpg")
    with urllib.request.urlopen(annotated_url) as resp:
        with open(annotated_path, "wb") as f:
            f.write(resp.read())
    print_ok(f"Imagen anotada guardada: {annotated_path}")
    print()
    print(f"  Para consultar este frame despues:")
    print(f"    {Colors.OKCYAN}python3 setup_cliente.py frames get {frame_id}{Colors.ENDC}")
    print(f"    {Colors.OKCYAN}python3 setup_cliente.py frames annotate {frame_id}{Colors.ENDC}")
    print()


# ==============================================================================
# COMANDO: process
# ==============================================================================
def cmd_process(args):
    """
    Envia una imagen directamente a la API para que ella misma ejecute la
    inferencia (via inference-server interno) y persista los resultados.

    A diferencia de 'infer', este comando NO requiere tener el inference-server
    corriendo localmente. La API en la nube orquesta todo el proceso.

    Requiere que el servidor tenga configurada INFERENCE_SERVER_URL y que
    el contenedor inference-server este corriendo en la misma red Docker.
    """
    image_path = args.image
    if not os.path.exists(image_path):
        print_error(f"Imagen no encontrada: {image_path}")
        sys.exit(1)

    with open(image_path, "rb") as f:
        img_data = f.read()

    model_name = args.model
    confidence = args.confidence
    lat = args.lat
    lon = args.lon
    camera_id = args.camera_id

    print_step(f"Enviando imagen a {API_BASE}/api/detections para inferencia remota...")
    print_step(f"Modelo: {model_name} | Confianza: {confidence} | Coordenadas: {lat}, {lon}")

    image_b64 = base64.b64encode(img_data).decode("utf-8")
    payload = {
        "image_base64": f"data:image/jpeg;base64,{image_b64}",
        "model_id": model_name,
        "latitude": lat,
        "longitude": lon,
        "confidence": confidence,
        "metadata": {
            "camera_id": camera_id,
            "source": "setup-cliente-process",
        },
    }

    try:
        result = api_post("detections", payload)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print_error(f"Error {e.code}: {error_body}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error de conexion con {API_BASE}: {e}")
        sys.exit(1)

    frame_id = result["frame_id"]
    print_ok(f"Procesado exitosamente!")
    print(f"  Frame ID:      {frame_id}")
    print(f"  Detecciones:   {result['detections_count']}")
    print(f"  Estado:        {result['status']}")
    print(f"  Mensaje:       {result['message']}")
    print(f"  Imagen URL:    {result['image_url']}")
    print()

    print(f"  Para consultar este frame despues:")
    print(f"    {Colors.OKCYAN}python3 setup_cliente.py frames get {frame_id}{Colors.ENDC}")
    print(f"    {Colors.OKCYAN}python3 setup_cliente.py frames annotate {frame_id}{Colors.ENDC}")
    print()


# ==============================================================================
# COMANDO: frames
# ==============================================================================
def cmd_frames_list(args):
    if (args.lat_min is None) != (args.lat_max is None):
        print_error("Debes especificar ambos: --lat-min Y --lat-max (o ninguno)")
        sys.exit(1)
    if (args.lon_min is None) != (args.lon_max is None):
        print_error("Debes especificar ambos: --lon-min Y --lon-max (o ninguno)")
        sys.exit(1)

    params = []
    if args.clases:
        params.append(f"clases={args.clases}")
    if args.lat_min is not None:
        params.extend([f"lat_min={args.lat_min}", f"lat_max={args.lat_max}"])
    if args.lon_min is not None:
        params.extend([f"lon_min={args.lon_min}", f"lon_max={args.lon_max}"])
    if args.camera_id:
        params.append(f"camera_id={args.camera_id}")
    if args.source:
        params.append(f"source={args.source}")
    params.append(f"limit={args.limit}")
    params.append(f"offset={args.offset}")

    query = "?" + "&".join(params) if params else ""
    data = api_get(f"frames/search{query}")

    total = data["total"]
    showing = min(args.limit, total - args.offset) if args.offset < total else 0
    print(f"\n{Colors.BOLD}Frames encontrados: {total} (mostrando {showing}){Colors.ENDC}\n")
    for f in data["frames"]:
        dets = f["detections"]
        clases = ", ".join(set(d["class_name"] for d in dets)) if dets else "sin detecciones"
        print(f"  {Colors.OKCYAN}{f['frame_id']}{Colors.ENDC}")
        print(f"    modelo: {f['model_id']}  |  detecciones: {f['detections_count']}")
        print(f"    coordenadas: {f['latitude']}, {f['longitude']}")
        print(f"    imagen: {f['image_url']}")
        if f.get("metadata"):
            print(f"    metadata: {json.dumps(f['metadata'], ensure_ascii=False)}")
        print(f"    clases: {clases}")
        print(f"    creado: {f['created_at']}")
        if dets:
            print(f"    detecciones:")
            for d in dets:
                bbox = d["bbox"]
                print(f"      [{d['class_name']}]  "
                      f"id={d['detection_id'][:8]}  "
                      f"conf={d['confidence']:.2f}  "
                      f"bbox=({bbox['x_min']},{bbox['y_min']},{bbox['x_max']},{bbox['y_max']})")
        print()


def cmd_frames_get(args):
    print_step(f"Descargando imagen del frame {args.frame_id}...")
    try:
        image_bytes = api_get_raw(f"frames/{args.frame_id}")
    except urllib.error.HTTPError as e:
        print_error(f"Error {e.code}: Frame no encontrado")
        sys.exit(1)

    if args.thumbnail:
        try:
            from PIL import Image
            from io import BytesIO
        except ImportError:
            print_error("Pillow no esta instalado. Ejecuta: pip install Pillow")
            sys.exit(1)
        img = Image.open(BytesIO(image_bytes))
        img.thumbnail((300, 300))
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        image_bytes = buffer.getvalue()

    extension = ".jpg"
    if args.output:
        output_path = args.output
    else:
        suffix = "_thumb" if args.thumbnail else ""
        output_path = f"{args.frame_id}{suffix}{extension}"

    with open(output_path, "wb") as f:
        f.write(image_bytes)
    print_ok(f"Imagen guardada: {output_path} ({len(image_bytes)} bytes)")


def cmd_frames_annotate(args):
    frame_id = args.frame_id

    print_step(f"Obteniendo detecciones del frame {frame_id}...")
    try:
        detections_data = api_get(f"detections/{frame_id}")
    except urllib.error.HTTPError as e:
        print_error(f"Error {e.code}: Frame no encontrado")
        sys.exit(1)

    dets = detections_data.get("detections", [])
    if not dets:
        print_warn("El frame no tiene detecciones. Se descargara la imagen original.")
        cmd_frames_get(args)
        return

    print_step("Descargando imagen original...")
    try:
        image_bytes = api_get_raw(f"frames/{frame_id}")
    except urllib.error.HTTPError as e:
        print_error(f"Error {e.code}: Frame no encontrado")
        sys.exit(1)

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print_error("Pillow no esta instalado. Ejecuta: pip install Pillow")
        sys.exit(1)

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)

    colores = [
        "#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF",
        "#00FFFF", "#FF8800", "#8800FF", "#00FF88", "#FF0088",
    ]

    print_step(f"Dibujando {len(dets)} detecciones...")
    for i, d in enumerate(dets):
        if "bbox" in d:
            x1, y1, x2, y2 = d["bbox"]["x_min"], d["bbox"]["y_min"], d["bbox"]["x_max"], d["bbox"]["y_max"]
        else:
            x1, y1, x2, y2 = d["bbox_x_min"], d["bbox_y_min"], d["bbox_x_max"], d["bbox_y_max"]
        color = colores[i % len(colores)]
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
        label = f"{d['class_name']} {d['confidence']:.2f}"
        draw.text((x1 + 5, y1 + 5), label, fill=color)

    extension = ".jpg"
    if args.output:
        output_path = args.output
    else:
        output_path = f"{frame_id}_anotada{extension}"

    img.save(output_path, "JPEG", quality=95)
    print_ok(f"Imagen anotada guardada: {output_path}")
    if img.width > 0:
        print_ok(f"Dimensiones: {img.width}x{img.height}")


# ==============================================================================
# COMANDO: persons
# ==============================================================================
def cmd_persons_list():
    data = api_get("persons")
    print(f"\n{Colors.BOLD}Personas registradas: {data['total']}{Colors.ENDC}\n")
    for p in data["persons"]:
        print(f"  {Colors.OKCYAN}{p['person_id']}{Colors.ENDC}")
        print(f"    nombre: {p['nombre']} {p['apellido']}")
        if p.get("email"):
            print(f"    email: {p['email']}")
        print(f"    creado: {p['created_at']}")
        print()


def cmd_persons_create(args):
    payload = {"nombre": args.nombre, "apellido": args.apellido}
    if args.email:
        payload["email"] = args.email
    if args.metadata:
        try:
            payload["metadata"] = json.loads(args.metadata)
        except json.JSONDecodeError:
            print_error("metadata debe ser un JSON valido, ej: '{\"key\":\"value\"}'")
            sys.exit(1)

    result = api_post("persons", payload)
    print_ok(f"Persona creada:")
    print(f"  ID:   {result['person_id']}")
    print(f"  Nombre: {result['nombre']} {result['apellido']}")
    print(f"  Email: {result.get('email', '-')}")


def cmd_persons_get(args):
    try:
        person = api_get(f"persons/{args.person_id}")
    except urllib.error.HTTPError as e:
        print_error(f"Error {e.code}: Persona no encontrada")
        sys.exit(1)

    print(f"\n  ID:   {Colors.OKCYAN}{person['person_id']}{Colors.ENDC}")
    print(f"  Nombre: {person['nombre']} {person['apellido']}")
    print(f"  Email: {person.get('email', '-')}")
    print(f"  Metadata: {person.get('metadata', {})}")
    print(f"  Creado: {person['created_at']}")
    print()


# ==============================================================================
# COMANDO: faces
# ==============================================================================
def _embed_one_image(person_id, image_path):
    with open(image_path, "rb") as f:
        img_data = f.read()
    b64 = base64.b64encode(img_data).decode("utf-8")
    return api_post(f"persons/{person_id}/face-embed", {"image_base64": b64, "confidence": 0.8})


def cmd_faces_login(args):
    username = args.username
    password = args.password

    if not username:
        username = input("Usuario: ")
    if not password:
        import getpass
        password = getpass.getpass("Contrasena: ")

    token_url = f"{KEYCLOAK_URL}/auth/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
    data = urllib.parse.urlencode({
        "client_id": KEYCLOAK_CLIENT_ID,
        "username": username,
        "password": password,
        "grant_type": "password",
    }).encode()

    req = urllib.request.Request(
        token_url, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        try:
            err_detail = json.loads(error_body).get("error_description", error_body)
        except json.JSONDecodeError:
            err_detail = error_body
        print_error(f"Error de autenticacion: {err_detail}")
        sys.exit(1)

    access_token = result["access_token"]
    expires_in = result.get("expires_in", 3600)
    save_token(access_token, expires_in)
    print_ok(f"Sesion iniciada correctamente ({expires_in // 60} min de validez)")


def cmd_faces_embed(args):
    person_id = args.person_id
    path_arg = args.path

    if not os.path.exists(path_arg):
        print_error(f"Ruta no encontrada: {path_arg}")
        sys.exit(1)

    if os.path.isdir(path_arg):
        images = []
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"):
            images.extend(glob.glob(os.path.join(path_arg, ext)))
        images.sort()
        if not images:
            print_error(f"No se encontraron imagenes (jpg/png) en: {path_arg}")
            sys.exit(1)
        print_step(f"Procesando {len(images)} imagenes desde: {path_arg}")
    else:
        images = [path_arg]

    total = len(images)
    success = 0
    errors = 0
    print(f"  Conectando a: {API_BASE}/api/persons/{person_id}/face-embed")

    for i, image_path in enumerate(images, 1):
        print(f"\n[{i}/{total}] {os.path.basename(image_path)}")
        try:
            result = _embed_one_image(person_id, image_path)
            print_ok(f"Embedding ID: {result.get('embedding_id', 'N/A')}")
            print(f"  Persona ID: {result['person_id']}")
            print(f"  Imagen URL: {result.get('image_url', 'N/A')}")
            print(f"  Validas: {result.get('valid_embeddings', 0)}")
            success += 1
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            print_error(f"Error {e.code}: {error_body}")
            errors += 1
        except Exception as e:
            print_error(f"Error de conexion: {e}")
            errors += 1

    print(f"\n{'='*50}")
    print(f"  Resumen: {total} procesadas, {success} exitos, {errors} errores")
    if errors:
        print_warn(f"  {errors} imagen(es) fallaron, revisa las rutas y conexiones")
    print(f"{'='*50}")


def cmd_faces_recognize(args):
    image_path = args.image

    if not os.path.exists(image_path):
        print_error(f"Imagen no encontrada: {image_path}")
        sys.exit(1)

    with open(image_path, "rb") as f:
        img_data = f.read()

    threshold = args.threshold
    print_step(f"Enviando imagen a inference-server para reconocimiento (threshold={threshold})...")
    url = FACE_INFER_URL.rstrip("/") + "/face/recognize"
    print(f"  Conectando a: {url}")
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="image.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode() + img_data + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="threshold"\r\n\r\n'
        f"{threshold}\r\n"
        f"--{boundary}--\r\n"
    ).encode()

    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print_error(f"Error {e.code}: {error_body}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error de conexion: {e}")
        sys.exit(1)

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print_error("Pillow no esta instalado. Ejecuta: pip install Pillow")
        sys.exit(1)

    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    output_dir = os.path.dirname(os.path.abspath(image_path))
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    annotated_path = os.path.join(output_dir, f"{base_name}_anotada.jpg")

    facial_area = result.get("facial_area", {})

    if facial_area and "x" in facial_area:
        x = facial_area["x"]
        y = facial_area["y"]
        w = facial_area["w"]
        h = facial_area["h"]

        if result.get("person_id"):
            nombre = result.get("nombre", "")
            apellido = result.get("apellido", "")
            full_name = f"{nombre} {apellido}".strip()
            confianza = result.get("confidence", 0.0)
            label = f"{full_name} ({confianza:.2f})"

            draw.rectangle([x, y, x + w, y + h], outline="#00FF00", width=4)
            tw = draw.textlength(label, font=font)
            draw.rectangle([x - 2, y - 14, x + tw + 2, y], fill="#00FF00")
            draw.text((x, y - 14), label, fill="#000000", font=font)
        else:
            label = "Unknown"

            draw.rectangle([x, y, x + w, y + h], outline="#FF0000", width=4)
            tw = draw.textlength(label, font=font)
            draw.rectangle([x - 2, y - 14, x + tw + 2, y], fill="#FF0000")
            draw.text((x, y - 14), label, fill="#FFFFFF", font=font)

    img.save(annotated_path, "JPEG", quality=95)
    print_ok(f"Imagen anotada guardada: {annotated_path}")

    if result.get("person_id"):
        nombre = result.get("nombre", "")
        apellido = result.get("apellido", "")
        full_name = f"{nombre} {apellido}".strip()
        print()
        print(f"  {Colors.OKGREEN}RECONOCIDO:{Colors.ENDC} {full_name}")
        print(f"  Persona ID: {result['person_id']}")
        print(f"  Confianza: {result['confidence']:.4f}")
        print()
    else:
        print(f"\n  {Colors.WARNING}No reconocido{Colors.ENDC} (ninguna coincidencia supera threshold={threshold})")


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="CLI cliente para API Detection Visual",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python3 setup_cliente.py faces login
  python3 setup_cliente.py faces login --username admin --password admin123
  python3 setup_cliente.py install
  python3 setup_cliente.py models list
  python3 setup_cliente.py models info yolo11n.pt
  python3 setup_cliente.py infer foto.jpg --model yolo11n.pt
  python3 setup_cliente.py process foto.jpg --model yolo11n.pt
  python3 setup_cliente.py frames list --clases person
  python3 setup_cliente.py frames get <frame_id>
  python3 setup_cliente.py frames annotate <frame_id>
  python3 setup_cliente.py persons list
  python3 setup_cliente.py persons create "Juan" "Perez"
  python3 setup_cliente.py faces embed <person_id> ruta/foto.jpg
  python3 setup_cliente.py faces embed <person_id> ruta/directorio/
  python3 setup_cliente.py faces recognize foto.jpg --threshold 0.5

Variables de entorno:
  API_BASE           Backend al que apuntar (default: https://bfts2026.mooo.com)
  MODELS_DIR         Directorio de modelos (default: ./modelos)
  INFER_URL          URL del servidor de inferencia local
  API_URL            URL de la API para persistencia facial (default: https://bfts2026.mooo.com)
  KEYCLOAK_URL       URL de Keycloak para autenticacion (default: mismo que API_BASE)
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="Comando a ejecutar")

    # install
    subparsers.add_parser("install", help="Descarga modelos y levanta contenedor YOLO")

    # models
    models_parser = subparsers.add_parser("models", help="Operaciones con modelos")
    models_sub = models_parser.add_subparsers(dest="models_subcommand", help="Subcomando")
    models_sub.add_parser("list", help="Lista modelos disponibles en el backend")
    models_info = models_sub.add_parser("info", help="Informacion detallada de un modelo")
    models_info.add_argument("model_name", help="Nombre del modelo (ej: yolo11n.pt)")

    # infer
    infer_parser = subparsers.add_parser("infer", help="Infere imagen localmente y sube al backend")
    infer_parser.add_argument("image", help="Ruta a la imagen a procesar")
    infer_parser.add_argument("--model", default="yolo11n.pt", help="Modelo YOLO a usar (default: yolo11n.pt)")
    infer_parser.add_argument("--confidence", type=float, default=0.25, help="Umbral de confianza (default: 0.25)")
    infer_parser.add_argument("--lat", type=float, default=-34.6037, help="Latitud (default: -34.6037)")
    infer_parser.add_argument("--lon", type=float, default=-58.3816, help="Longitud (default: -58.3816)")
    infer_parser.add_argument("--camera-id", default="local-cam", help="ID de camara (default: local-cam)")

    # process
    process_parser = subparsers.add_parser("process", help="Envia imagen a la API para inferencia remota (orquestador)")
    process_parser.add_argument("image", help="Ruta a la imagen a procesar")
    process_parser.add_argument("--model", default="yolo11n.pt", help="Modelo YOLO a usar (default: yolo11n.pt)")
    process_parser.add_argument("--confidence", type=float, default=0.25, help="Umbral de confianza (default: 0.25)")
    process_parser.add_argument("--lat", type=float, default=-34.6037, help="Latitud (default: -34.6037)")
    process_parser.add_argument("--lon", type=float, default=-58.3816, help="Longitud (default: -58.3816)")
    process_parser.add_argument("--camera-id", default="local-cam", help="ID de camara (default: local-cam)")

    # frames
    frames_parser = subparsers.add_parser("frames", help="Operaciones con fotogramas")
    frames_sub = frames_parser.add_subparsers(dest="frames_subcommand", help="Subcomando")

    frames_list = frames_sub.add_parser("list", help="Buscar fotogramas")
    frames_list.add_argument("--clases", help="Filtrar por clases (ej: person,car)")
    frames_list.add_argument("--lat-min", type=float, help="Latitud minima")
    frames_list.add_argument("--lat-max", type=float, help="Latitud maxima")
    frames_list.add_argument("--lon-min", type=float, help="Longitud minima")
    frames_list.add_argument("--lon-max", type=float, help="Longitud maxima")
    frames_list.add_argument("--camera-id", help="Filtrar por ID de camara")
    frames_list.add_argument("--source", help="Filtrar por fuente")
    frames_list.add_argument("--limit", type=int, default=10, help="Maximo resultados (default: 10)")
    frames_list.add_argument("--offset", type=int, default=0, help="Desplazamiento (default: 0)")

    frames_get = frames_sub.add_parser("get", help="Descargar imagen de un fotograma")
    frames_get.add_argument("frame_id", help="ID del fotograma")
    frames_get.add_argument("--thumbnail", "-t", action="store_true", help="Descargar thumbnail (300px, mas rapido)")
    frames_get.add_argument("--output", "-o", help="Ruta de salida (default: <frame_id>.jpg)")

    frames_annotate = frames_sub.add_parser("annotate", help="Descargar imagen con detecciones marcadas")
    frames_annotate.add_argument("frame_id", help="ID del fotograma")
    frames_annotate.add_argument("--output", "-o", help="Ruta de salida (default: <frame_id>_anotada.jpg)")

    # persons
    persons_parser = subparsers.add_parser("persons", help="Operaciones con personas")
    persons_sub = persons_parser.add_subparsers(dest="persons_subcommand", help="Subcomando")

    persons_sub.add_parser("list", help="Listar personas registradas")

    persons_create = persons_sub.add_parser("create", help="Crear una persona")
    persons_create.add_argument("nombre", help="Nombre de la persona")
    persons_create.add_argument("apellido", help="Apellido de la persona")
    persons_create.add_argument("--email", help="Email de la persona")
    persons_create.add_argument("--metadata", help="Metadatos adicionales (JSON)")

    persons_get = persons_sub.add_parser("get", help="Obtener una persona por ID")
    persons_get.add_argument("person_id", help="ID de la persona")

    # faces
    faces_parser = subparsers.add_parser("faces", help="Reconocimiento facial (S5.2 y S5.3)")
    faces_sub = faces_parser.add_subparsers(dest="faces_subcommand", help="Subcomando")

    faces_login = faces_sub.add_parser("login", help="Iniciar sesion en Keycloak")
    faces_login.add_argument("--username", help="Nombre de usuario")
    faces_login.add_argument("--password", help="Contrasena")

    faces_embed = faces_sub.add_parser("embed", help="Generar embedding facial para una persona")
    faces_embed.add_argument("person_id", help="ID de la persona")
    faces_embed.add_argument("path", help="Ruta a la imagen o directorio con fotos del rostro")
    faces_embed.add_argument("--confidence", type=float, help="Confianza manual (0-1)")

    faces_recognize = faces_sub.add_parser("recognize", help="Reconocer rostro en una imagen")
    faces_recognize.add_argument("image", help="Ruta a la imagen con el rostro a reconocer")
    faces_recognize.add_argument("--threshold", type=float, default=0.5, help="Umbral de confianza (default: 0.5)")

    args = parser.parse_args()

    if args.command == "install":
        cmd_install()
    elif args.command == "models":
        if args.models_subcommand == "list":
            cmd_models()
        elif args.models_subcommand == "info":
            cmd_models_info(args.model_name)
        else:
            models_parser.print_help()
    elif args.command == "infer":
        cmd_infer(args)
    elif args.command == "process":
        cmd_process(args)
    elif args.command == "frames":
        if args.frames_subcommand == "list":
            cmd_frames_list(args)
        elif args.frames_subcommand == "get":
            cmd_frames_get(args)
        elif args.frames_subcommand == "annotate":
            cmd_frames_annotate(args)
        else:
            frames_parser.print_help()
    elif args.command == "persons":
        if args.persons_subcommand == "list":
            cmd_persons_list()
        elif args.persons_subcommand == "create":
            cmd_persons_create(args)
        elif args.persons_subcommand == "get":
            cmd_persons_get(args)
        else:
            persons_parser.print_help()
    elif args.command == "faces":
        if args.faces_subcommand == "login":
            cmd_faces_login(args)
        elif args.faces_subcommand == "embed":
            cmd_faces_embed(args)
        elif args.faces_subcommand == "recognize":
            cmd_faces_recognize(args)
        else:
            faces_parser.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
