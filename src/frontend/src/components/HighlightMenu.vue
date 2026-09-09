<script setup lang="ts">
/**
 * The right-click palette over a selection in the editor.
 *
 * A colour wraps the selection in `<mark class="hl-...">`, a different colour
 * replaces the one already there, and «rimuovi» unwraps it.
 */
import type { HighlightColour } from '@/composables/useEditor'

defineProps<{
  /** Where the menu was opened, in page coordinates. */
  position: { top: number; left: number }
}>()

const emit = defineEmits<{
  /** A colour was chosen. */
  (event: 'pick', colour: HighlightColour): void
  /** The palette was dismissed. */
  (event: 'close'): void
}>()

/** The palette, in the order it is drawn. */
const COLOURS: { value: HighlightColour; label: string }[] = [
  { value: 'yellow', label: 'Yellow' },
  { value: 'blue', label: 'Blue' },
  { value: 'green', label: 'Green' },
  { value: 'transparent', label: 'Remove' },
]
</script>

<template>
  <Teleport to="body">
    <div
      class="highlight-backdrop"
      @mousedown.prevent
      @click="emit('close')"
      @contextmenu.prevent="emit('close')"
    >
      <div
        class="highlight-menu"
        :style="{ top: `${position.top}px`, left: `${position.left}px` }"
        @click.stop
      >
        <button
          v-for="colour in COLOURS"
          :key="colour.value"
          type="button"
          class="highlight-swatch"
          :class="`hl-${colour.value}`"
          :title="colour.label"
          @click="emit('pick', colour.value)"
        >
          {{ colour.value === 'transparent' ? '✕' : '' }}
        </button>
      </div>
    </div>
  </Teleport>
</template>
