<script setup lang="ts">
/**
 * The two panes: the file tree on the left, the selected note on the right.
 *
 * The note shows in one of its two modes, Preview or Edit, and nothing
 * shows at all until one is opened.
 */
import { onBeforeUnmount, onMounted } from 'vue'

import ConfirmDialog from '@/components/ConfirmDialog.vue'
import ContextMenu from '@/components/ContextMenu.vue'
import NoteEditor from '@/components/NoteEditor.vue'
import NotePreview from '@/components/NotePreview.vue'
import NoteToolbar from '@/components/NoteToolbar.vue'
import PromptDialog from '@/components/PromptDialog.vue'
import Sidebar from '@/components/Sidebar.vue'
import { useEditor } from '@/composables/useEditor'
import { useSidebar } from '@/composables/useSidebar'
import { useHollow } from '@/composables/useHollow'

const hollow = useHollow()
const editor = useEditor()
const { collapsed } = useSidebar()

/** Ctrl/Cmd + S saves from anywhere in the app, not only from the textarea. */
function onKeydown(event: KeyboardEvent): void {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
    event.preventDefault()
    void editor.save()
  }
}

/** Warn before the tab closes on a note with unsaved changes. */
function onBeforeLeaving(event: BeforeUnloadEvent): void {
  if (editor.dirty.value) event.preventDefault()
}

onMounted(() => {
  void hollow.refreshTree()
  window.addEventListener('keydown', onKeydown)
  window.addEventListener('beforeunload', onBeforeLeaving)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('beforeunload', onBeforeLeaving)
})
</script>

<template>
  <div class="app" :class="{ 'is-collapsed': collapsed }">
    <Sidebar />

    <main class="workspace">
      <template v-if="hollow.currentNote.value">
        <NoteToolbar />
        <p v-if="editor.saveError.value" class="workspace-error">{{ editor.saveError.value }}</p>
        <NotePreview v-if="editor.mode.value === 'preview'" />
        <NoteEditor v-else />
      </template>

      <div v-else class="workspace-empty">
        <h2>Dragon Glass</h2>
        <p>Pick a note from the tree, or create a new one.</p>
      </div>
    </main>

    <ContextMenu />
    <ConfirmDialog />
    <PromptDialog />
  </div>
</template>
