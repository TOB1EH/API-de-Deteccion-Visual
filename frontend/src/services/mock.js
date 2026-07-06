export const MOCK_MODELS = {
  total: 2,
  models: [
    { name: "yolo11n.pt", size: 4712345, type: "yolo", path: "models/local/yolo11n.pt" },
    { name: "yolo11s.pt", size: 18123456, type: "yolo", path: "models/local/yolo11s.pt" }
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

export const MOCK_SEARCH_RESULTS = {
  total: 25,
  frames: [
    {
      frame_id: "uuid-1",
      model_id: "yolo11n.pt",
      latitude: -34.6037,
      longitude: -58.3816,
      image_url: "https://via.placeholder.com/400x300?text=Frame+1",
      metadata: { camera_id: "cam-001", source: "web" },
      detections_count: 3,
      created_at: "2026-06-28T12:00:00Z",
      detections: [
        { detection_id: "det-1", class_name: "person", class_id: 0, confidence: 0.95, bbox: { x_min: 100, y_min: 200, x_max: 300, y_max: 400 } },
        { detection_id: "det-2", class_name: "car", class_id: 2, confidence: 0.87, bbox: { x_min: 50, y_min: 150, x_max: 200, y_max: 300 } }
      ]
    },
    {
      frame_id: "uuid-2",
      model_id: "yolo11s.pt",
      latitude: -34.6137,
      longitude: -58.3716,
      image_url: "https://via.placeholder.com/400x300?text=Frame+2",
      metadata: { camera_id: "cam-002", source: "mobile" },
      detections_count: 1,
      created_at: "2026-06-28T13:00:00Z",
      detections: [
        { detection_id: "det-3", class_name: "dog", class_id: 16, confidence: 0.92, bbox: { x_min: 200, y_min: 100, x_max: 400, y_max: 350 } }
      ]
    }
  ]
}

export const MOCK_PERSONS = {
  total: 3,
  persons: [
    { person_id: "p-1", nombre: "Juan", apellido: "Perez", email: "juan@mail.com", created_at: "2026-06-01", updated_at: "2026-06-01" },
    { person_id: "p-2", nombre: "Maria", apellido: "Garcia", email: "maria@mail.com", created_at: "2026-06-02", updated_at: "2026-06-02" },
    { person_id: "p-3", nombre: "Carlos", apellido: "Lopez", email: "carlos@mail.com", created_at: "2026-06-03", updated_at: "2026-06-03" }
  ]
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

export const MOCK_RECOGNITION = {
  person_id: "p-1",
  nombre: "Juan",
  apellido: "Perez",
  confidence: 0.87
}

export const MOCK_RECOGNITION_FAIL = {
  person_id: null,
  confidence: 0.45
}
