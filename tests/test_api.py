#!/usr/bin/env python3
"""
=============================================================================
Script de Pruebas Automatizadas: API de Detección Visual (Fase 2)
=============================================================================
Este script valida el funcionamiento de los endpoints S1 y S2 en local o remota.

Flujo:
1. Verifica que los servicios estén vivos (Health check)
2. Lista modelos disponibles (GET /api/models)
3. Descarga una imagen de prueba (cataas.com)
4. Codifica imagen a base64
5. Ejecuta detección simulada (POST /api/detections)
6. Valida que los datos se persistieron en PostgreSQL
7. Valida que la imagen se guardó en SeaweedFS
8. Genera reporte JSON con resultados
=============================================================================
"""

import os
import sys
import json
import time
import base64
import argparse
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# ============================================================================
# CONFIGURACIÓN Y CONSTANTES
# ============================================================================
TEST_IMAGE_URL = "https://cataas.com/cat"
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
RESULTS_FILE = os.path.join(os.path.dirname(__file__), "test_results.json")

# Ubicación de prueba: Obelisco de Buenos Aires
TEST_LATITUDE = -34.6037
TEST_LONGITUDE = -58.3816

# Colores para salida en terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================
def print_step(msg):
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}[*] {msg}{Colors.ENDC}")

def print_success(msg):
    print(f"{Colors.OKGREEN}  ✓ {msg}{Colors.ENDC}")

def print_error(msg):
    print(f"{Colors.FAIL}  ✗ {msg}{Colors.ENDC}")

def download_test_image():
    """Descarga una imagen aleatoria para usar en la prueba"""
    os.makedirs(FIXTURES_DIR, exist_ok=True)
    img_path = os.path.join(FIXTURES_DIR, "test_image.jpg")
    
    print_step("Descargando imagen de prueba...")
    try:
        response = requests.get(TEST_IMAGE_URL, timeout=10)
        response.raise_for_status()
        
        with open(img_path, 'wb') as f:
            f.write(response.content)
            
        print_success(f"Imagen descargada ({len(response.content)} bytes)")
        
        # Convertir a base64
        base64_data = base64.b64encode(response.content).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_data}"
        
    except Exception as e:
        print_error(f"Error descargando imagen: {str(e)}")
        sys.exit(1)

# ============================================================================
# CLASE PRINCIPAL DE TESTING
# ============================================================================
class ApiTester:
    def __init__(self, env="local", host=None):
        self.env = env
        self.results = {"timestamp": datetime.now().isoformat(), "tests": [], "summary": {}}
        
        # Configurar URLs según entorno
        if env == "local":
            self.api_url = "http://localhost/api"
            self.base_url = "http://localhost"
            
            # Credenciales de localhost (definidas en .env)
            self.db_host = "localhost"
            self.db_port = 5433
            self.db_user = "detections_user"
            self.db_pass = "secure_pwd_local"
            self.db_name = "detections_db"
            
        else:
            host = host or "bfts2026.mooo.com"
            self.api_url = f"https://{host}/api"
            self.base_url = f"https://{host}"
            
            # Credenciales remotas
            self.db_host = host
            self.db_port = 5432
            self.db_user = "detections_user"
            self.db_pass = "bfts2026."
            self.db_name = "detections_db"

    def record_result(self, name, status, details=None):
        self.results["tests"].append({
            "name": name,
            "status": status,
            "details": details
        })
        if status:
            print_success(name)
        else:
            print_error(f"{name} - {details}")

    # --- TESTS ---

    def test_health_check(self):
        print_step(f"Verificando conexión a {self.base_url}...")
        try:
            res = requests.get(f"{self.base_url}/", timeout=5)
            if res.status_code == 200:
                self.record_result("Health Check", True, res.text)
                return True
        except Exception as e:
            self.record_result("Health Check", False, str(e))
        return False

    def test_get_models(self):
        print_step("Probando GET /models...")
        try:
            res = requests.get(f"{self.api_url}/models", timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data.get("total", 0) > 0:
                    self.record_result("GET /models", True, f"Encontrados {data['total']} modelos")
                    return True
                else:
                    self.record_result("GET /models", False, "No se encontraron modelos")
            else:
                self.record_result("GET /models", False, f"Status {res.status_code}")
        except Exception as e:
            self.record_result("GET /models", False, str(e))
        return False

    def test_post_detections(self, image_base64):
        print_step("Probando POST /detections (núcleo S2)...")
        payload = {
            "image_base64": image_base64,
            "model_id": "yolo11n.pt",
            "latitude": TEST_LATITUDE,
            "longitude": TEST_LONGITUDE,
            "detections": [
                # Detecciones simuladas (COCO dataset realism)
                {
                    "class_name": "cat", "class_id": 16, "confidence": 0.98,
                    "bbox": {"x_min": 50, "y_min": 60, "x_max": 400, "y_max": 450}
                },
                {
                    "class_name": "person", "class_id": 0, "confidence": 0.85,
                    "bbox": {"x_min": 10, "y_min": 20, "x_max": 200, "y_max": 600}
                },
                {
                    "class_name": "car", "class_id": 2, "confidence": 0.76,
                    "bbox": {"x_min": 300, "y_min": 150, "x_max": 550, "y_max": 300}
                }
            ],
            "metadata": {"camera_id": "test-cam-01", "source": "automation-script"}
        }

        try:
            start_time = time.time()
            res = requests.post(f"{self.api_url}/detections", json=payload, timeout=15)
            elapsed = time.time() - start_time
            
            if res.status_code == 200:
                data = res.json()
                frame_id = data.get("frame_id")
                
                if frame_id:
                    self.record_result("POST /detections", True, f"Frame ID: {frame_id} ({elapsed:.2f}s)")
                    return frame_id, data.get("image_url")
                else:
                    self.record_result("POST /detections", False, "No devolvió frame_id")
            else:
                self.record_result("POST /detections", False, f"Status {res.status_code}: {res.text}")
        except Exception as e:
            self.record_result("POST /detections", False, str(e))
        
        return None, None

    def test_database_persistence(self, frame_id):
        print_step(f"Verificando persistencia en PostgreSQL (frame_id: {frame_id})...")
        try:
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                dbname=self.db_name,
                user=self.db_user,
                password=self.db_pass,
                connect_timeout=5
            )
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Verificar frame
            cursor.execute("SELECT * FROM frames WHERE frame_id = %s", (frame_id,))
            frame = cursor.fetchone()
            
            if not frame:
                self.record_result("BD: Frame guardado", False, "Frame no encontrado")
                return False
                
            self.record_result("BD: Frame guardado", True, f"1 frame validado")
            
            # Verificar detecciones
            cursor.execute("SELECT * FROM detections WHERE frame_id = %s", (frame_id,))
            detections = cursor.fetchall()
            
            if len(detections) == 3:
                self.record_result("BD: Detecciones guardadas", True, f"3 detecciones validadas")
            else:
                self.record_result("BD: Detecciones guardadas", False, f"Se esperaban 3, hay {len(detections)}")
                
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            self.record_result("BD: Persistencia", False, f"Error DB: {str(e)}")
            return False

    def test_seaweedfs_persistence(self, image_url):
        print_step("Verificando persistencia de imagen en SeaweedFS...")
        try:
            # Reemplazar localhost interno con localhost externo si estamos probando en local
            if self.env == "local" and "localhost/seaweed" in image_url:
                test_url = image_url
            else:
                test_url = image_url
                
            res = requests.get(test_url, timeout=5)
            if res.status_code == 200 and 'image/' in res.headers.get('Content-Type', ''):
                self.record_result("SeaweedFS: Imagen accesible", True, f"Imagen descargada ({len(res.content)} bytes)")
                return True
            else:
                self.record_result("SeaweedFS: Imagen accesible", False, f"Status {res.status_code}")
        except Exception as e:
            self.record_result("SeaweedFS: Imagen accesible", False, str(e))
        return False

    def generate_report(self):
        total = len(self.results["tests"])
        passed = sum(1 for t in self.results["tests"] if t["status"])
        
        self.results["summary"] = {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": f"{(passed/total)*100:.1f}%" if total > 0 else "0%"
        }
        
        with open(RESULTS_FILE, 'w') as f:
            json.dump(self.results, f, indent=2)
            
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== RESUMEN DE PRUEBAS ==={Colors.ENDC}")
        print(f"Total:  {total}")
        print(f"Pasados: {Colors.OKGREEN}{passed}{Colors.ENDC}")
        print(f"Fallados: {Colors.FAIL if total-passed > 0 else Colors.OKGREEN}{total-passed}{Colors.ENDC}")
        print(f"Reporte: {RESULTS_FILE}")

# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="Test API Detección Visual")
    parser.add_argument("--env", choices=["local", "remote"], default="local", help="Entorno de prueba")
    parser.add_argument("--host", default=None, help="Host remoto (ej: bfts2026.mooo.com)")
    args = parser.parse_args()
    
    print(f"{Colors.HEADER}{Colors.BOLD}Iniciando validación Fase 2 (Entorno: {args.env}){Colors.ENDC}")
    
    tester = ApiTester(env=args.env, host=args.host)
    
    # 1. Health check
    if not tester.test_health_check():
        print_error("Servicios no disponibles. Abortando pruebas.")
        tester.generate_report()
        sys.exit(1)
        
    # 2. Get Models
    tester.test_get_models()
    
    # 3. Preparar imagen
    image_b64 = download_test_image()
    
    # 4. POST Detections
    frame_id, image_url = tester.test_post_detections(image_b64)
    
    # 5. Validaciones persistencia (solo si el POST funcionó)
    if frame_id and image_url:
        tester.test_database_persistence(frame_id)
        tester.test_seaweedfs_persistence(image_url)
        
    # 6. Reporte final
    tester.generate_report()

if __name__ == "__main__":
    main()
