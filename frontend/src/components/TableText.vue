<template>
  <a-tooltip :title="tooltipText" :mouse-enter-delay="0.25">
    <span class="table-text-ellipsis" :style="textStyle">{{ displayText }}</span>
  </a-tooltip>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  value?: unknown
  maxWidth?: number | string
}>(), {
  maxWidth: 360
})

const displayText = computed(() => {
  if (props.value === null || props.value === undefined || props.value === '') return '-'
  return String(props.value)
})

const tooltipText = computed(() => (displayText.value === '-' ? '' : displayText.value))

const textStyle = computed(() => {
  const maxWidth = typeof props.maxWidth === 'number' ? `${props.maxWidth}px` : props.maxWidth
  return { maxWidth }
})
</script>
