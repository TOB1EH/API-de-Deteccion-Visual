# Componentes

Componentes reutilizables ubicados en `src/components/`.

---

## FrameCard.vue

Tarjeta de presentacion de un fotograma, usada en la grilla de resultados de busqueda.

### Props
| Prop | Tipo | Requerido | Descripcion |
|---|---|---|---|
| `frame` | Object | Si | Datos del fotograma |

### Estructura del objeto `frame`
```js
{
  frame_id: "uuid-1",
  image_url: "https://...",
  latitude: -34.6037,
  longitude: -58.3816,
  detections_count: 3,
  created_at: "2026-06-28T12:00:00Z",
  detections: [
    { detection_id: "det-1", class_name: "person", confidence: 0.95, bbox: {...} }
  ]
}
```

### Visual
- Imagen thumbnail (180px altura, `cover`)
- Chip con cantidad de detecciones superpuesto
- Ubicacion (lat/lon a 4 decimales)
- Fecha de creacion
- Frame ID truncado (12 caracteres)
- Chips de clases detectadas (max 3 visibles + "+N" si hay mas)

### Interaccion
- `v-card` con `hover` y enlace a `/frame/:id`
- Efecto hover: translateY(-3px)
- Placeholder: spinner mientras carga la imagen

### Colores de clases
| Clase | Color |
|---|---|
| person | red |
| car | blue |
| dog | orange |
| bicycle | green |
| cat | purple |
| default | grey |

---

## DetectionOverlay.vue

Overlay SVG que dibuja bounding boxes sobre la imagen del fotograma.

### Props
| Prop | Tipo | Requerido | Default | Descripcion |
|---|---|---|---|---|
| `detections` | Array | Si | - | Lista de detecciones con bbox |
| `width` | Number | No | 800 | Ancho natural de la imagen |
| `height` | Number | No | 600 | Alto natural de la imagen |

### Estructura de cada deteccion
```js
{
  detection_id: "det-1",
  class_name: "person",
  confidence: 0.95,
  bbox: { x_min: 150, y_min: 100, x_max: 450, y_max: 500 }
}
```

### Comportamiento
- Se posiciona absolutamente sobre la imagen (`position: absolute; top:0; left:0; width:100%; height:100%`)
- `viewBox` se escala a las dimensiones naturales de la imagen
- Cada deteccion renderiza:
  - `rect` semi-transparente con borde de color
  - Label con nombre y confianza (si hay espacio arriba del bbox)
- Tooltip HTML nativo (`<title>`) con nombre y porcentaje
- `pointer-events: none` en el SVG, `pointer-events: auto` en cada grupo para hover

### Colores
| Clase | Hex |
|---|---|
| person | #EF4444 |
| car | #3B82F6 |
| dog | #F97316 |
| bicycle | #22C55E |
| cat | #A855F7 |
| default | #6B7280 |

### Funciones internas
- `getColor(className)`: retorna el hex segun la clase
- `colorWithOpacity(className, opacity)`: convierte hex a rgba
- `labelWidth(det)`: calcula ancho aproximado del label segun el texto

---

## PersonForm.vue

Formulario para crear o editar una persona.

### Props
| Prop | Tipo | Requerido | Default | Descripcion |
|---|---|---|---|---|
| `person` | Object | No | null | Datos para edicion (null = crear nuevo) |

### Campos
| Campo | Tipo | Regla |
|---|---|---|
| Nombre | text | Requerido |
| Apellido | text | Requerido |
| Email | email | Opcional, validacion regex si se ingresa |

### Eventos emitidos
| Evento | Payload | Descripcion |
|---|---|---|
| `submit` | `{ nombre, apellido, email }` | Formulario valido enviado |
| `cancel` | - | Usuario cancelo |

### Comportamiento
- Si recibe `person` prop, precarga los valores para edicion
- Si no recibe `person`, inicia en blanco (modo crear)
- Validacion nativa de Vuetify en cada campo
- Boton "Guardar" tipo `submit`, boton "Cancelar" emite `cancel`
