#!/usr/bin/env python3
"""
CLI cliente para API Detection Visual.
Procesa imagenes localmente con YOLO y persiste en el backend.

Subcomandos:
  install    Descarga modelos y levanta contenedor de inferencia local
  models     Lista modelos disponibles en el backend
  infer      Infiere imagen localmente y sube resultados al backend
  frames     Consulta y descarga fotogramas (list, get, annotate)
  persons    Gestiona personas registradas (list, create, get)

Uso:
  export API_BASE=http://localhost  # backend local (default: remoto)
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
import argparse
import urllib.request
import urllib.error
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
def api_get(path):
    req = urllib.request.Request(f"{API_BASE}/api/{path}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def api_get_raw(path):
    req = urllib.request.Request(f"{API_BASE}/api/{path}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def api_post(path, data):
    req = urllib.request.Request(
        f"{API_BASE}/api/{path}",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


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
    try:
        subprocess.run(
            [
                "docker", "run", "-d",
                "--name", CONTAINER_NAME,
                "-p", "8001:8000",
                "-v", f"{abs_models_dir}:/app/models",
                DOCKER_IMAGE,
            ],
            check=True, timeout=60
        )
        print_ok(f"Contenedor '{CONTAINER_NAME}' corriendo en http://localhost:8001")
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

    if check_container_running():
        models_dir = MODELS_DIR
        os.makedirs(models_dir, exist_ok=True)
        models = fetch_model_list()
        if models:
            selected = select_models(models)
            for m in selected:
                download_model(m["name"], models_dir)
        print_ok("Todo listo. El nodo de inferencia local esta operativo.")
        return

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
    with urllib.request.urlopen(req, timeout=120) as resp:
        infer_result = json.loads(resp.read().decode())

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
# COMANDO: frames
# ==============================================================================
def cmd_frames_list(args):
    params = []
    if args.clases:
        params.append(f"clases={args.clases}")
    if args.lat_min is not None:
        params.extend([f"lat_min={args.lat_min}", f"lat_max={args.lat_max}"])
    if args.lon_min is not None:
        params.extend([f"lon_min={args.lon_min}", f"lon_max={args.lon_max}"])
    params.append(f"limit={args.limit}")
    params.append(f"offset={args.offset}")

    query = "?" + "&".join(params) if params else ""
    data = api_get(f"frames/search{query}")

    print(f"\n{Colors.BOLD}Frames encontrados: {data['total']}{Colors.ENDC}\n")
    for f in data["frames"]:
        dets = f["detections"]
        clases = ", ".join(set(d["class_name"] for d in dets)) if dets else "sin detecciones"
        print(f"  {Colors.OKCYAN}{f['frame_id']}{Colors.ENDC}")
        print(f"    modelo: {f['model_id']}  |  detecciones: {f['detections_count']}")
        print(f"    clases: {clases}")
        print(f"    creado: {f['created_at']}")
        print()


def cmd_frames_get(args):
    print_step(f"Descargando imagen del frame {args.frame_id}...")
    try:
        image_bytes = api_get_raw(f"frames/{args.frame_id}")
    except urllib.error.HTTPError as e:
        print_error(f"Error {e.code}: Frame no encontrado")
        sys.exit(1)

    extension = ".jpg"
    if args.output:
        output_path = args.output
    else:
        output_path = f"{args.frame_id}{extension}"

    with open(output_path, "wb") as f:
        f.write(image_bytes)
    print_ok(f"Imagen guardada: {output_path}")


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

    img = Image.open(io.BytesIO(image_bytes))
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
        print(f"    nombre: {p['name']}")
        if p.get("email"):
            print(f"    email: {p['email']}")
        print(f"    creado: {p['created_at']}")
        print()


def cmd_persons_create(args):
    payload = {"name": args.name}
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
    print(f"  Nombre: {result['name']}")
    print(f"  Email: {result.get('email', '-')}")


def cmd_persons_get(args):
    try:
        person = api_get(f"persons/{args.person_id}")
    except urllib.error.HTTPError as e:
        print_error(f"Error {e.code}: Persona no encontrada")
        sys.exit(1)

    print(f"\n  ID:   {Colors.OKCYAN}{person['person_id']}{Colors.ENDC}")
    print(f"  Nombre: {person['name']}")
    print(f"  Email: {person.get('email', '-')}")
    print(f"  Metadata: {person.get('metadata', {})}")
    print(f"  Creado: {person['created_at']}")
    print()


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="CLI cliente para API Detection Visual",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python3 setup_cliente.py install
  python3 setup_cliente.py models list
  python3 setup_cliente.py models info yolo11n.pt
  python3 setup_cliente.py infer foto.jpg --model yolo11n.pt
  python3 setup_cliente.py frames list --clases person
  python3 setup_cliente.py frames get <frame_id>
  python3 setup_cliente.py frames annotate <frame_id>
  python3 setup_cliente.py persons list
  python3 setup_cliente.py persons create "Juan Perez"

Variables de entorno:
  API_BASE      Backend al que apuntar (default: https://bfts2026.mooo.com)
  MODELS_DIR    Directorio de modelos (default: ./modelos)
  INFER_URL     URL del servidor de inferencia local
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

    # frames
    frames_parser = subparsers.add_parser("frames", help="Operaciones con fotogramas")
    frames_sub = frames_parser.add_subparsers(dest="frames_subcommand", help="Subcomando")

    frames_list = frames_sub.add_parser("list", help="Buscar fotogramas")
    frames_list.add_argument("--clases", help="Filtrar por clases (ej: person,car)")
    frames_list.add_argument("--lat-min", type=float, help="Latitud minima")
    frames_list.add_argument("--lat-max", type=float, help="Latitud maxima")
    frames_list.add_argument("--lon-min", type=float, help="Longitud minima")
    frames_list.add_argument("--lon-max", type=float, help="Longitud maxima")
    frames_list.add_argument("--limit", type=int, default=10, help="Maximo resultados (default: 10)")
    frames_list.add_argument("--offset", type=int, default=0, help="Desplazamiento (default: 0)")

    frames_get = frames_sub.add_parser("get", help="Descargar imagen de un fotograma")
    frames_get.add_argument("frame_id", help="ID del fotograma")
    frames_get.add_argument("--output", "-o", help="Ruta de salida (default: <frame_id>.jpg)")

    frames_annotate = frames_sub.add_parser("annotate", help="Descargar imagen con detecciones marcadas")
    frames_annotate.add_argument("frame_id", help="ID del fotograma")
    frames_annotate.add_argument("--output", "-o", help="Ruta de salida (default: <frame_id>_anotada.jpg)")

    # persons
    persons_parser = subparsers.add_parser("persons", help="Operaciones con personas")
    persons_sub = persons_parser.add_subparsers(dest="persons_subcommand", help="Subcomando")

    persons_sub.add_parser("list", help="Listar personas registradas")

    persons_create = persons_sub.add_parser("create", help="Crear una persona")
    persons_create.add_argument("name", help="Nombre de la persona")
    persons_create.add_argument("--email", help="Email de la persona")
    persons_create.add_argument("--metadata", help="Metadatos adicionales (JSON)")

    persons_get = persons_sub.add_parser("get", help="Obtener una persona por ID")
    persons_get.add_argument("person_id", help="ID de la persona")

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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
