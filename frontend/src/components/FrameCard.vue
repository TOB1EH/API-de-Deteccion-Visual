<template>
  <v-card
    class="frame-card rounded-lg"
    :to="`/frame/${frame.frame_id}`"
    variant="outlined"
    hover
  >
    <v-img
      :src="frame.image_url"
      height="180"
      cover
      class="bg-grey-lighten-3"
    >
      <template v-slot:placeholder>
        <v-row class="fill-height ma-0" align="center" justify="center">
          <v-progress-circular indeterminate size="24" color="primary" />
        </v-row>
      </template>

      <div class="d-flex ga-1 pa-2" style="position: absolute; top: 0; right: 0;">
        <v-chip size="x-small" color="primary" text-color="white" class="font-weight-medium">
          {{ frame.detections_count }} det
        </v-chip>
      </div>
    </v-img>

    <v-card-text class="pa-3">
      <div class="d-flex align-center mb-2">
        <v-icon size="14" color="medium-emphasis" class="mr-1">mdi-map-marker</v-icon>
        <span class="text-caption text-medium-emphasis font-family-monospace">
          {{ frame.latitude?.toFixed(4) }}, {{ frame.longitude?.toFixed(4) }}
        </span>
      </div>
      <div class="d-flex align-center">
        <v-icon size="14" color="medium-emphasis" class="mr-1">mdi-calendar</v-icon>
        <span class="text-caption text-medium-emphasis">
          {{ new Date(frame.created_at).toLocaleDateString() }}
        </span>
      </div>
      <div class="d-flex align-center mt-1">
        <v-icon size="14" color="medium-emphasis" class="mr-1">mdi-identifier</v-icon>
        <span class="text-caption text-medium-emphasis font-family-monospace" style="font-size: 11px;">
          {{ frame.frame_id?.substring(0, 12) }}...
        </span>
      </div>
    </v-card-text>

    <v-divider />

    <div class="pa-2 d-flex flex-wrap ga-1">
      <v-chip
        v-for="det in frame.detections?.slice(0, 3)"
        :key="det.detection_id"
        size="x-small"
        :color="getColor(det.class_name)"
        variant="tonal"
        class="font-weight-medium"
      >
        {{ det.class_name }}
      </v-chip>
      <v-chip
        v-if="(frame.detections?.length || 0) > 3"
        size="x-small"
        variant="text"
        class="font-weight-medium"
      >
        +{{ frame.detections.length - 3 }}
      </v-chip>
    </div>
  </v-card>
</template>

<script setup>
const CLASS_COLORS = {
  person: 'red',
  car: 'blue',
  dog: 'orange',
  bicycle: 'green',
  cat: 'purple',
  default: 'grey'
}

defineProps({
  frame: { type: Object, required: true }
})

function getColor(className) {
  return CLASS_COLORS[className?.toLowerCase()] || CLASS_COLORS.default
}
</script>

<style scoped>
.frame-card {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.frame-card:hover {
  transform: translateY(-3px);
}
</style>
