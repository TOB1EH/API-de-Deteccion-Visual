<template>
  <svg
    class="detection-overlay"
    :viewBox="`0 0 ${width} ${height}`"
    xmlns="http://www.w3.org/2000/svg"
    style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;"
  >
    <g
      v-for="det in detections"
      :key="det.detection_id || det.class_name + det.confidence"
      style="pointer-events: auto; cursor: pointer;"
    >
      <title>{{ det.class_name }} ({{ (det.confidence * 100).toFixed(0) }}%)</title>
      <rect
        :x="det.bbox.x_min"
        :y="det.bbox.y_min"
        :width="det.bbox.x_max - det.bbox.x_min"
        :height="det.bbox.y_max - det.bbox.y_min"
        :fill="colorWithOpacity(det.class_name, 0.15)"
        :stroke="getColor(det.class_name)"
        stroke-width="2.5"
        rx="4"
        class="bbox-rect"
      />
      <rect
        :x="det.bbox.x_min"
        :y="det.bbox.y_min - 22"
        :width="labelWidth(det)"
        :height="20"
        :fill="getColor(det.class_name)"
        rx="3"
        v-if="det.bbox.y_min > 26"
      />
      <text
        :x="det.bbox.x_min + 4"
        :y="det.bbox.y_min - 7"
        fill="white"
        font-size="11"
        font-weight="bold"
        v-if="det.bbox.y_min > 26"
      >
        {{ det.class_name }} {{ (det.confidence * 100).toFixed(0) }}%
      </text>
    </g>
  </svg>
</template>

<script setup>
const CLASS_COLORS = {
  person: '#EF4444',
  car: '#3B82F6',
  dog: '#F97316',
  bicycle: '#22C55E',
  cat: '#A855F7',
  default: '#6B7280'
}

const props = defineProps({
  detections: { type: Array, required: true },
  width: { type: Number, default: 800 },
  height: { type: Number, default: 600 }
})

function getColor(className) {
  return CLASS_COLORS[className?.toLowerCase()] || CLASS_COLORS.default
}

function colorWithOpacity(className, opacity) {
  const hex = getColor(className)
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r},${g},${b},${opacity})`
}

function labelWidth(det) {
  const text = `${det.class_name} ${(det.confidence * 100).toFixed(0)}%`
  return text.length * 7 + 8
}
</script>

<style scoped>
.detection-overlay {
  border-radius: inherit;
}
.bbox-rect {
  transition: stroke-width 0.15s ease;
}
.bbox-rect:hover {
  stroke-width: 4;
}
</style>
