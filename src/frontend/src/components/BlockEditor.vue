<script setup lang="ts">
/**
 * One block of the note, written where it is read.
 *
 * It opens on the Markdown of that block alone and gives it back when the
 * focus leaves — Esc gives back nothing instead, and the block returns to what
 * it was. What the whole-note editor offers is offered here too: the `[[`
 * autocompletion, the highlight palette a right-click opens, and the two
 * things that are easier clicked than typed — a table and an image.
 *
 * Everything the tools do keeps the focus in the field: a button that took it
 * would be a block leaving as it is being written.
 */
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import {
  TABLE_SKELETON,
  highlighted,
  useEditor,
  type HighlightColour,
} from '@/composables/useEditor'
import { useWikiLinks, type LinkSuggestion } from '@/composables/useWikiLinks'

import HighlightMenu from './HighlightMenu.vue'
import LinkAutocomplete from './LinkAutocomplete.vue'

const props = defineProps<{
  /** The Markdown the block is written in, which is what opens for editing. */
  source: string
  /** What to show while the block is empty. */
  placeholder?: string
}>()

const emit = defineEmits<{
  /** The block was left, carrying what it now says. */
  (event: 'commit', text: string): void
  /** The block was abandoned, and what was written in it is dropped. */
  (event: 'cancel'): void
}>()

const editor = useEditor()
const links = useWikiLinks()

const draft = ref(props.source)
const handed = ref(false)
const field = ref<HTMLTextAreaElement | null>(null)
const picker = ref<HTMLInputElement | null>(null)
const picking = ref(false)
const highlightAt = ref<{ top: number; left: number } | null>(null)

/** Keep the field exactly as tall as what is written in it. */
function fit(): void {
  const area = field.value
  if (!area) return
  area.style.height = 'auto'
  area.style.height = `${area.scrollHeight}px`
}

watch(draft, () => void nextTick(fit))

onMounted(() => {
  const area = field.value
  if (!area) return
  fit()
  area.focus()
  area.setSelectionRange(draft.value.length, draft.value.length)
})

/** Hand the block back as it now reads, once and once only. */
function commit(): void {
  if (handed.value) return
  handed.value = true
  links.close()
  emit('commit', draft.value)
}

/** Leaving the field hands the block back, unless it left for the file dialog. */
function onBlur(): void {
  if (picking.value) return
  commit()
}

/** Give the block back untouched — the blur that follows must not undo that. */
function abandon(): void {
  if (handed.value) return
  handed.value = true
  links.close()
  emit('cancel')
}

/** Let the autocompletion look at the block after anything that moved the caret. */
function onInput(): void {
  if (field.value) links.refresh(field.value)
}

/** Keep the list in step when the caret moves without typing. */
function onCaretMoved(): void {
  if (links.open.value) onInput()
}

/**
 * Give the autocompletion first refusal on the keys it owns, then the block.
 *
 * Esc drops what was written, Ctrl/Cmd + Enter keeps it, and Ctrl/Cmd + S
 * keeps it and saves the note — the block has to land in the buffer before the
 * save reads it, which is why the shortcut is answered here and stopped from
 * reaching the window.
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
    event.stopPropagation()
    commit()
    void editor.save()
    return
  }

  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
    event.preventDefault()
    return commit()
  }

  if (event.key === 'Escape') {
    event.preventDefault()
    return abandon()
  }

  if (event.key === 'Tab') {
    event.preventDefault()
    insert('  ')
  }
}

/** Replace what is selected in the block, keeping the caret usable. */
function insert(text: string): void {
  const area = field.value
  if (!area) return
  const start = area.selectionStart
  const end = area.selectionEnd
  draft.value = `${draft.value.slice(0, start)}${text}${draft.value.slice(end)}`
  void nextTick(() => {
    area.focus()
    area.setSelectionRange(start + text.length, start + text.length)
  })
}

/**
 * Insert a piece of Markdown as a block of its own, however the draft reads.
 *
 * A table is only a table when nothing shares its lines, so what was around
 * the caret is pushed above and below it — which on commit is what cuts the
 * block in three.
 */
function insertOnItsOwn(markdown: string): void {
  const area = field.value
  if (!area) return
  const before = draft.value.slice(0, area.selectionStart).replace(/\s+$/, '')
  const after = draft.value.slice(area.selectionEnd).replace(/^\s+/, '')
  const written = `${before ? `${before}\n\n` : ''}${markdown}`
  draft.value = `${written}${after ? `\n\n${after}` : ''}`
  void nextTick(() => {
    area.focus()
    area.setSelectionRange(written.length, written.length)
  })
}

/** Write a table skeleton into the block, on lines of its own. */
function addTable(): void {
  insertOnItsOwn(TABLE_SKELETON.trim())
}

/**
 * Ask for a file, remembering that the field is only losing the focus to it.
 *
 * A dialog dismissed without choosing anything says so with `cancel`, which
 * not every browser sends; the window getting the focus back is the same news
 * from a source all of them have.
 */
function chooseImage(): void {
  picking.value = true
  window.addEventListener('focus', returned, { once: true })
  picker.value?.click()
}

/** Upload the chosen image and write its Markdown at the caret. */
async function onImageChosen(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  returned()
  if (!file) return
  const markdown = await editor.uploadImage(file)
  if (markdown !== null) insert(markdown)
}

/** The file dialog is done with, one way or the other. */
function returned(): void {
  picking.value = false
  field.value?.focus()
}

onBeforeUnmount(() => window.removeEventListener('focus', returned))

/** Write the highlighted suggestion into the block and put the caret after it. */
function pick(suggestion: LinkSuggestion | null = null): void {
  const area = field.value
  if (!area) return
  const written = links.accept(draft.value, area.selectionStart, suggestion ?? undefined)
  if (!written) return
  draft.value = written.value
  void nextTick(() => {
    area.focus()
    area.setSelectionRange(written.caret, written.caret)
  })
}

/** Open the highlight palette, but only over an actual selection. */
function onContextMenu(event: MouseEvent): void {
  const area = field.value
  if (!area || area.selectionStart === area.selectionEnd) return
  event.preventDefault()
  highlightAt.value = { top: event.clientY, left: event.clientX }
}

/** Apply the chosen colour to the selection and close the palette. */
function onHighlight(colour: HighlightColour): void {
  const area = field.value
  highlightAt.value = null
  if (!area) return
  const start = area.selectionStart
  const end = area.selectionEnd
  const written = highlighted(draft.value.slice(start, end), colour)
  if (written === null) return
  draft.value = `${draft.value.slice(0, start)}${written}${draft.value.slice(end)}`
  void nextTick(() => {
    area.focus()
    area.setSelectionRange(start, start + written.length)
  })
}
</script>

<template>
  <div class="block-editor">
    <textarea
      ref="field"
      v-model="draft"
      class="block-textarea"
      spellcheck="false"
      :placeholder="props.placeholder ?? 'Write in Markdown. Type [[ to link another note.'"
      @input="onInput"
      @keydown="onKeydown"
      @keyup="onCaretMoved"
      @click="onCaretMoved"
      @blur="onBlur"
      @contextmenu="onContextMenu"
    />

    <div class="block-tools">
      <button
        type="button"
        class="button button-small"
        title="Insert a table"
        @mousedown.prevent
        @click="addTable"
      >
        ▦ Table
      </button>
      <button
        type="button"
        class="button button-small"
        title="Upload an image"
        @mousedown.prevent
        @click="chooseImage"
      >
        🖼️ Image
      </button>
      <input
        ref="picker"
        class="hidden-input"
        type="file"
        accept="image/*"
        @change="onImageChosen"
        @cancel="returned"
      />
    </div>

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
