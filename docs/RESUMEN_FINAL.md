# Resumen del desarrollo final

---

## Lo que ya funciona (Primera entrega - COMPLETADO)

- Detectar objetos en fotos con YOLO
- Guardar imagenes y resultados en la nube (SeaweedFS + PostgreSQL)
- Buscar fotogramas por ubicacion, clase, camara
- Registrar personas
- Reconocimiento facial con DeepFace

---

## Lo que hay que corregir (Fase 0)

### 1. Reconocimiento facial falla con fotos distintas de la misma persona

**Problema:** Si tenes una foto de frente de Messi y despues subis una de perfil, no lo reconoce.

**Solucion:** Subir VARIAS fotos de la misma persona (frente, perfil, distintos angulos). El sistema va a guardar varios embeddings y al buscar va a tener mas chances de encontrar match.

**Tareas:**
- Cambiar el comando `faces embed` para que acepte una carpeta llena de fotos, no solo una foto
- Probar: subir 5 fotos de Messi → reconocer una sexta foto de Messi

---

### 2. La API debe poder hacer inferencia por si sola

**Problema:** Hoy el proceso es: vos sacas la foto → tu PC la procesa con YOLO → recien ahi la manda a la nube. Un frontend web no puede hacer eso.

**Solucion:** La API en la nube tambien debe aceptar imagenes sin procesar, enviarlas al YOLO (docker local) y devolver el resultado.

**Tareas:**
- Modificar `POST /api/detections` para que funcione con imagen sola (sin detecciones pre-calculadas)
- Conectar la API con el inference-server internamente

---

### 3. Correcciones menores

| Que | Por que |
|---|---|
| Agregar indice a pgvector | Para que las busquedas faciales no se lentifiquen con mas datos |
| Limpiar Dockerfile | Tiene librerias que ya no usamos |
| Mejorar mensajes de error | Cuando falta un modelo, muestra un traceback feo en vez de un mensaje claro |
| Actualizar ayuda del script | El ejemplo de `persons create` esta desactualizado |

---

## Lo nuevo para la segunda entrega (Fase 1)

### 4. Login con Keycloak

Cada endpoint va a requerir un token de acceso. Habra 3 roles:
- **admin** - puede todo
- **operator** - puede subir imagenes y consultar
- **viewer** - solo consulta

**Tareas:**
- Agregar Keycloak al docker-compose
- Configurar usuarios y roles
- Agregar validacion de token en la API

---

### 5. Frontend web

Una pagina web donde se pueda:
- Iniciar sesion (con Keycloak)
- Subir una foto para detectar objetos
- Ver los resultados con los cuadros dibujados
- Buscar fotogramas por filtros
- Administrar personas
- Subir fotos para reconocimiento facial
- Reconocer un rostro

**Tecnologia:** React o Vue. Comunicacion via REST con la API existente.

---

### 6. Monitoreo con Grafana

Paneles para ver en tiempo real:
- Cuantas requests por minuto recibe la API
- Tiempo promedio de inferencia
- Cuantos reconocimientos faciales son exitosos vs fallidos
- Uso de CPU/memoria

**Tecnologia:** Telegraf (recolecta metricas) + InfluxDB (almacena) + Grafana (visualiza)

---

### 7. Autenticacion biométrica (opcional)

Poder iniciar sesion con la cara: subis una foto, el sistema te reconoce y te genera un token, sin necesidad de escribir usuario y contraseña.

---

## Quien hace que

| Persona | Que hace |
|---|---|
| **Miembro A** | Mejorar reconocimiento facial (multiples fotos por persona). Auth biometrica si sobra tiempo. |
| **Miembro B** | Frontend web (React/Vue). Indice pgvector. Limpiar Dockerfile. |
| **Miembro C** | Keycloak (login). Monitoreo (Grafana). |
| **Miembro D** | API orquestador (que acepte imagenes sin procesar). Mejorar errores del CLI. Coordinar integracion. |

---

## Tiempo estimado

| Semana | Que pasa |
|---|---|
| **Semana 1** | Cada uno hace su tarea en paralelo |
| **Semana 2** | Unir todo, conectar frontend con API real, probar |
| **Semana 3** | Pruebas finales, deploy, preparar presentacion |
