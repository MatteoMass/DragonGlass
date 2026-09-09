<script setup lang="ts">
/** The list `[[` opens: every note of the hollow, filtered as the name is typed. */
import type { LinkSuggestion } from '@/composables/useWikiLinks'

defineProps<{
  /** The notes to offer, already filtered and ordered. */
  suggestions: LinkSuggestion[]
  /** Which of them Enter would accept. */
  highlighted: number
  /** Where the caret is, so the list is drawn beside it. */
  position: { top: number; left: number }
}>()

const emit = defineEmits<{
  /** One suggestion was chosen. */
  (event: 'pick', suggestion: LinkSuggestion): void
  /** The pointer moved onto one of them. */
  (event: 'highlight', index: number): void
}>()
</script>

<template>
  <Teleport to="body">
    <ul
      v-if="suggestions.length"
      class="link-autocomplete"
      :style="{ top: `${position.top}px`, left: `${position.left}px` }"
      @mousedown.prevent
    >
      <li
        v-for="(suggestion, index) in suggestions"
        :key="`${suggestion.folder}/${suggestion.name}`"
        class="link-suggestion"
        :class="{ 'is-highlighted': index === highlighted }"
        @mouseenter="emit('highlight', index)"
        @click="emit('pick', suggestion)"
      >
        <span class="link-suggestion-name">{{ suggestion.name }}</span>
        <span v-if="suggestion.folder" class="link-suggestion-folder">{{ suggestion.folder }}</span>
      </li>
    </ul>
  </Teleport>
</template>
