<script setup lang="ts">
/**
 * The Markdown pane.
 *
 * The textarea is the whole of it; what surrounds it is the two things typing
 * in it can summon — the `[[` autocompletion, and the highlight palette a
 * right-click opens over a selection.
 */
import { nextTick, ref } from 'vue'

import { useEditor, type HighlightColour } from '@/composables/useEditor'
import { useWikiLinks, type LinkSuggestion } from '@/composables/useWikiLinks'

import HighlightMenu from './HighlightMenu.vue'
import LinkAutocomplete from './LinkAutocomplete.vue'

const editor = useEditor()
const links = useWikiLinks()

const highlightAt = ref<{ top: number; left: number } | null>(null)

/** Let the autocompletion look at the buffer after anything that moved the caret. */
function onInput(): void {
  const field = editor.textarea.value
  if (field) links.refresh(field)
}

/** Keep the list in step when the caret moves without typing. */
function onCaretMoved(): void {
  if (links.open.value) onInput()
}

/**
 * Give the autocompletion first refusal on the keys it owns, then the editor.
 *
 * Ctrl/Cmd + S saves from anywhere in the pane; Tab inserts a real tab rather
 * than leaving the field.
 */
function onKeydown(event: KeyboardEvent): void {
  if (links.open.value) {
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault()
        return links.move(1)
      case 'ArrowUp':
        event.preventDefault()
        return links.move(-1)
      case 'Enter':
      case 'Tab':
        event.preventDefault()
        return pick()
      case 'Escape':
        event.preventDefault()
        return links.close()
    }
  }

  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
    event.preventDefault()
    void editor.save()
    return
  }

  if (event.key === 'Tab') {
    event.preventDefault()
    editor.insert('  ')
  }
}

/** Write the highlighted suggestion into the buffer and put the caret after it. */
function pick(suggestion: LinkSuggestion | null = null): void {
  const field = editor.textarea.value
  if (!field) return
  const written = links.accept(editor.buffer.value, field.selectionStart, suggestion ?? undefined)
  if (!written) return
  editor.buffer.value = written.value
  void nextTick(() => {
    field.focus()
    field.setSelectionRange(written.caret, written.caret)
  })
}

/** Open the highlight palette, but only over an actual selection. */
function onContextMenu(event: MouseEvent): void {
  const field = editor.textarea.value
  if (!field || field.selectionStart === field.selectionEnd) return
  event.preventDefault()
  highlightAt.value = { top: event.clientY, left: event.clientX }
}

/** Apply the chosen colour and close the palette. */
function onHighlight(colour: HighlightColour): void {
  editor.highlight(colour)
  highlightAt.value = null
}
</script>

<template>
  <div class="note-editor">
    <textarea
      :ref="(element) => (editor.textarea.value = element as HTMLTextAreaElement | null)"
      v-model="editor.buffer.value"
      class="note-textarea"
      spellcheck="false"
      placeholder="Write in Markdown. Type [[ to link another note."
      @input="onInput"
      @keydown="onKeydown"
      @keyup="onCaretMoved"
      @click="onCaretMoved"
      @blur="links.close()"
      @contextmenu="onContextMenu"
    />

    <LinkAutocomplete
      v-if="links.open.value"
      :suggestions="links.suggestions.value"
      :highlighted="links.highlighted.value"
      :position="links.position.value"
      @pick="pick"
      @highlight="links.highlight"
    />

    <HighlightMenu
      v-if="highlightAt"
      :position="highlightAt"
      @pick="onHighlight"
      @close="highlightAt = null"
    />
  </div>
</template>
