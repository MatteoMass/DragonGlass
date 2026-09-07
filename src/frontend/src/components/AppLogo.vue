<script setup lang="ts">
/**
 * The mark of the app: the same image used as the tab's favicon.
 */
withDefaults(defineProps<{ /** The side of the square, in pixels. */ size?: number }>(), {
  size: 18,
})
</script>

<template>
  <img
    class="app-logo"
    src="/favicon.png"
    :width="size"
    :height="size"
    alt="Dragon Glass"
  />
</template>
