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
import SettingsPanel from '@/components/SettingsPanel.vue'
import Sidebar from '@/components/Sidebar.vue'
import TutorView from '@/components/TutorView.vue'
import { useAppView } from '@/composables/useAppView'
import { useEditor } from '@/composables/useEditor'
import { useSettings } from '@/composables/useSettings'
import { useSidebar } from '@/composables/useSidebar'
import { useHollow } from '@/composables/useHollow'

const hollow = useHollow()
const editor = useEditor()
const settings = useSettings()
const { collapsed } = useSidebar()
const { view } = useAppView()

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
  void settings.load()
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
      <TutorView v-show="view === 'tutor'" />

      <template v-if="view === 'notes'">
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
      </template>
    </main>

    <ContextMenu />
    <ConfirmDialog />
    <PromptDialog />
    <SettingsPanel />
  </div>
</template>
