export const MOCK_MODELS = {
  total: 7,
  models: [
    { name: "yolo11n.pt", size: 4712345, type: "yolo", path: "models/local/yolo11n.pt" },
    { name: "celular.pt", size: 4123456, type: "yolo", path: "models/local/celular.pt" },
    { name: "dados.pt", size: 3987654, type: "yolo", path: "models/local/dados.pt" },
    { name: "mouse.pt", size: 4234567, type: "yolo", path: "models/local/mouse.pt" },
    { name: "pelotas.pt", size: 4345678, type: "yolo", path: "models/local/pelotas.pt" },
    { name: "ropa.pt", size: 4456789, type: "yolo", path: "models/local/ropa.pt" }
  ]
}

export const MOCK_DETECTIONS = [
  { class_name: "person", class_id: 0, confidence: 0.95, bbox: { x_min: 100, y_min: 200, x_max: 300, y_max: 400 } },
  { class_name: "car", class_id: 2, confidence: 0.87, bbox: { x_min: 50, y_min: 150, x_max: 200, y_max: 300 } }
]

export const MOCK_FRAME_RESULT = {
  frame_id: "a1b2c3d4-e5f6-7890-aaaa-bbbbccccdddd",
  image_url: "https://via.placeholder.com/800x600",
  detections_count: 2,
  status: "processed",
  message: "Se procesaron 2 detecciones",
  timestamp: new Date().toISOString()
}

function generateMockFrames() {
  const clases = ['person', 'car', 'dog', 'bicycle', 'cat', 'truck', 'bus', 'motorcycle']
  const cameras = ['cam-001', 'cam-002', 'cam-003', 'cam-004']
  const framess = []

  for (let i = 1; i <= 25; i++) {
    const detCount = Math.floor(Math.random() * 4) + 1
    const detections = []
    for (let d = 1; d <= detCount; d++) {
      const cls = clases[Math.floor(Math.random() * clases.length)]
      detections.push({
        detection_id: `det-frame-${i}-${d}`,
        class_name: cls,
        class_id: Math.floor(Math.random() * 80),
        confidence: 0.5 + Math.random() * 0.5,
        bbox: {
          x_min: Math.floor(Math.random() * 400),
          y_min: Math.floor(Math.random() * 200),
          x_max: 200 + Math.floor(Math.random() * 400),
          y_max: 100 + Math.floor(Math.random() * 400)
        }
      })
    }

    framess.push({
      frame_id: `uuid-mock-${String(i).padStart(3, '0')}`,
      model_id: i % 2 === 0 ? 'yolo11s.pt' : 'yolo11n.pt',
      latitude: -34.6 - Math.random() * 0.1,
      longitude: -58.4 - Math.random() * 0.1,
      image_url: `https://picsum.photos/seed/frame${i}/400/300`,
      metadata: { camera_id: cameras[Math.floor(Math.random() * cameras.length)], source: 'web' },
      detections_count: detections.length,
      created_at: new Date(2026, 5, 28 + Math.floor(i / 5), 12 + (i % 12), 0, 0).toISOString(),
      detections
    })
  }

  return framess
}

export const MOCK_SEARCH_RESULTS = {
  total: 25,
  frames: generateMockFrames()
}

export const MOCK_PERSONS = {
  total: 3,
  persons: [
    { person_id: "p-1", nombre: "Juan", apellido: "Perez", email: "juan@mail.com", created_at: "2026-06-01", updated_at: "2026-06-01" },
    { person_id: "p-2", nombre: "Maria", apellido: "Garcia", email: "maria@mail.com", created_at: "2026-06-02", updated_at: "2026-06-02" },
    { person_id: "p-3", nombre: "Carlos", apellido: "Lopez", email: "carlos@mail.com", created_at: "2026-06-03", updated_at: "2026-06-03" }
  ]
}

// Mock de reconocimiento facial exitoso
export const MOCK_RECOGNITION = {
  person_id: "p-1",
  nombre: "Juan",
  apellido: "Perez",
  confidence: 0.87,
  image_url: "https://picsum.photos/200/200?random=face1"
}

// Mock de reconocimiento facial fallido
export const MOCK_RECOGNITION_FAIL = {
  person_id: null,
  nombre: null,
  apellido: null,
  confidence: 0.45,
  image_url: null
}

export const MOCK_FRAME_DETAIL = {
  frame_id: "a1b2c3d4-e5f6-7890-aaaa-bbbbccccdddd",
  model_id: "yolo11n.pt",
  latitude: -34.6037,
  longitude: -58.3816,
  image_url: "https://picsum.photos/800/600?random=1",
  metadata: { camera_id: "cam-001", source: "web" },
  detections_count: 2,
  status: "processed",
  created_at: "2026-06-28T12:00:00Z",
  detections: [
    { detection_id: "det-1", class_name: "person", class_id: 0, confidence: 0.95, bbox: { x_min: 150, y_min: 100, x_max: 450, y_max: 500 } },
    { detection_id: "det-2", class_name: "car", class_id: 2, confidence: 0.87, bbox: { x_min: 50, y_min: 300, x_max: 350, y_max: 550 } }
  ]
}

