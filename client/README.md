# Cliente de Inferencia Local

CLI para procesar imagenes con YOLO en tu PC y almacenar resultados en el backend central.

## Requisitos

- Python 3.8+
- Docker
- Pillow (para `frames annotate` y `frames get --thumbnail`): `pip install Pillow`

## Instalacion

```bash
python3 setup_cliente.py install
```

Descarga modelos, inicia el contenedor YOLO y deja todo listo para inferir.

## Uso basico

### Inferir una imagen

```bash
python3 setup_cliente.py infer ruta/imagen.jpg --model yolo11n.pt
```

Esto:
1. Procesa la imagen con YOLO local (puerto 8001)
2. Sube detecciones + imagen al backend
3. Descarga la imagen anotada (con bounding boxes)

Parametros opcionales:
- `--model`: modelo YOLO (default: yolo11n.pt)
- `--confidence`: umbral de confianza (default: 0.25)
- `--lat` / `--lon`: coordenadas (default: -34.6037, -58.3816)
- `--camera-id`: identificador de camara (default: local-cam)

### Consultar modelos disponibles

```bash
# Listar todos los modelos
python3 setup_cliente.py models list

# Informacion detallada de un modelo especifico
python3 setup_cliente.py models info yolo11n.pt
```

### Buscar fotogramas (S4)

```bash
python3 setup_cliente.py frames list --clases person --limit 10
```

Muestra por cada fotograma: frame_id, modelo, coordenadas, URL de imagen, metadatos, clases detectadas y detalle de cada deteccion (confidence, bbox, detection_id).

Filtros:
- `--clases`: filtrar por clase separada por comas (person,car,cat)
- `--lat-min` / `--lat-max`: rango de latitud (ambos obligatorios si se usa uno)
- `--lon-min` / `--lon-max`: rango de longitud (ambos obligatorios si se usa uno)
- `--limit`: maximo resultados (default: 10, max: 200)
- `--offset`: desplazamiento para paginacion

Nota: Los filtros de latitud y longitud requieren el par completo (min + max). Si solo se pasa uno, el script muestra un error y se detiene.

### Descargar imagen de un fotograma (S3)

```bash
# Descargar imagen original
python3 setup_cliente.py frames get <frame_id>

# Descargar thumbnail (300px, mas rapido)
python3 setup_cliente.py frames get <frame_id> --thumbnail
```

Opciones:
- `--output` / `-o`: ruta de salida personalizada
- `--thumbnail` / `-t`: descarga miniatura de 300px redimensionada localmente con Pillow

### Descargar imagen con detecciones marcadas

```bash
python3 setup_cliente.py frames annotate <frame_id>
```

Descarga la imagen original y dibuja los bounding boxes con las clases detectadas. Requiere Pillow.

### Gestionar personas

```bash
# Listar todas
python3 setup_cliente.py persons list

# Crear una
python3 setup_cliente.py persons create "Juan Perez" --email juan@mail.com

# Obtener por ID
python3 setup_cliente.py persons get <person_id>
```

### Reconocimiento facial

```bash
# Generar embedding facial para una persona (S5.2)
python3 setup_cliente.py faces embed <person_id> ~/foto.jpg

# Reconocer rostro en una imagen (S5.3)
python3 setup_cliente.py faces recognize ~/foto_test.jpg --threshold 0.5
```

**Flujo completo para reconocer un famoso:**

```bash
# 1. Crear la persona
python3 setup_cliente.py persons create "Franco Colapinto"

# 2. Copiar el person_id del resultado
# 3. Subir una foto de referencia y generar el embedding
python3 setup_cliente.py faces embed <person_id> ~/famosos/colapinto.jpg

# 4. Reconocer una foto diferente
python3 setup_cliente.py faces recognize ~/famosos/colapinto_otra.jpg --threshold 0.5
# -> RECONOCIDO: Franco Colapinto (confianza: 0.85)
```

## Backend local vs remoto

Por defecto apunta al servidor remoto (`https://bfts2026.mooo.com`).

Para usar un backend local:

```bash
export API_BASE=http://localhost
python3 setup_cliente.py models
python3 setup_cliente.py infer foto.jpg
```

Tambien se puede pasar la variable en cada comando:

```bash
API_BASE=http://localhost python3 setup_cliente.py frames list
```

## Variables de entorno

| Variable | Default | Descripcion |
|---|---|---|
| `API_BASE` | `https://bfts2026.mooo.com` | URL del backend |
| `MODELS_DIR` | `./modelos` | Directorio de modelos YOLO |
| `INFER_URL` | `http://localhost:8001/infer` | URL del servidor de inferencia |

## Referencia rapida de subcomandos

| Comando | Subcomando | Descripcion |
|---|---|---|
| `install` | - | Descarga modelos e inicia contenedor YOLO local |
| `models` | `list` | Lista modelos disponibles en el backend |
| `models` | `info <nombre>` | Detalle de un modelo (tamaño, tipo, ruta) |
| `infer` | `<imagen>` | Infiere localmente y sube al backend |
| `frames` | `list` | Busca fotogramas con filtros (S4) |
| `frames` | `get <id>` | Descarga imagen de un fotograma (S3) |
| `frames` | `annotate <id>` | Descarga imagen con bounding boxes dibujados |
| `persons` | `list` | Lista personas registradas |
| `persons` | `create <nombre>` | Crea una nueva persona |
| `persons` | `get <id>` | Obtiene detalle de una persona |

## Solucion de problemas

**Error: Conexion rechazada en localhost:8001**
El contenedor YOLO no esta corriendo. Ejecuta `python3 setup_cliente.py install`.

**Error: Pillow no esta instalado**
Ejecuta `pip install Pillow` para el comando `frames annotate`.

**Error: 404 en los comandos**
Verifica que `API_BASE` este correcto. Para pruebas locales debe ser `http://localhost`.

**Error: Debes especificar ambos: --lat-min Y --lat-max (o ninguno)**
Los filtros geograficos requieren el par completo de minimo y maximo. Corrige el comando agregando ambos valores.
