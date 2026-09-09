<script setup lang="ts">
/** The bar above the note: where it is, which pane is showing, and what can be done. */
import { ref } from 'vue'

import { useEditor } from '@/composables/useEditor'
import { useHollow } from '@/composables/useHollow'

const hollow = useHollow()
const editor = useEditor()

const picker = ref<HTMLInputElement | null>(null)

/** Send the chosen file to the upload, then clear the input for the next one. */
async function onImageChosen(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) await editor.insertImage(file)
  input.value = ''
}
</script>

<template>
  <header class="note-toolbar">
    <div class="note-identity">
      <span class="note-path" :title="hollow.currentNote.value?.path">
        {{ hollow.currentNote.value?.path }}
      </span>
      <span v-if="editor.dirty.value" class="note-dirty" title="Unsaved changes">●</span>
    </div>

    <div class="note-modes">
      <button
        type="button"
        class="button button-small"
        :class="{ 'is-active': editor.mode.value === 'preview' }"
        @click="editor.setMode('preview')"
      >
        Preview
      </button>
      <button
        type="button"
        class="button button-small"
        :class="{ 'is-active': editor.mode.value === 'edit' }"
        @click="editor.setMode('edit')"
      >
        Edit
      </button>
    </div>

    <div class="note-actions">
      <template v-if="editor.mode.value === 'edit'">
        <button
          type="button"
          class="button button-small"
          title="Insert a table"
          @click="editor.insertTable()"
        >
          ▦ Table
        </button>
        <button
          type="button"
          class="button button-small"
          title="Upload an image"
          @click="picker?.click()"
        >
          🖼️ Image
        </button>
      </template>
      <button
        type="button"
        class="button button-small button-primary"
        :disabled="editor.saving.value || !editor.dirty.value"
        title="Ctrl/Cmd + S"
        @click="editor.save()"
      >
        {{ editor.saving.value ? 'Saving…' : 'Save' }}
      </button>
    </div>

    <input
      ref="picker"
      class="hidden-input"
      type="file"
      accept="image/*"
      @change="onImageChosen"
    />
  </header>
</template>
