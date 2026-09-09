<script setup lang="ts">
/**
 * The left pane: the hollow's name, what can be made in it, and the tree.
 *
 * A right-click anywhere in the pane that an entry of the tree has not already
 * claimed opens the same menu — creating at the root, and ordering the tree.
 *
 * The mark in its corner folds the pane down to itself, and opens it again.
 */
import { ref } from 'vue'

import { useAppView } from '@/composables/useAppView'
import { useContextMenu } from '@/composables/useContextMenu'
import { useEditor } from '@/composables/useEditor'
import { usePrompt } from '@/composables/usePrompt'
import { useSettings } from '@/composables/useSettings'
import { useSettingsPanel } from '@/composables/useSettingsPanel'
import { useSidebar } from '@/composables/useSidebar'
import { useTheme } from '@/composables/useTheme'
import { useHollow } from '@/composables/useHollow'

import AppLogo from './AppLogo.vue'
import FileTree from './FileTree.vue'

const hollow = useHollow()
const editor = useEditor()
const { theme, toggle } = useTheme()
const { collapsed, toggle: toggleSidebar } = useSidebar()
const { open: openMenu } = useContextMenu()
const { ask } = usePrompt()
const { show: showSettings } = useSettingsPanel()
const { isEnabled } = useSettings()
const { view, showTutor } = useAppView()

const importInput = ref<HTMLInputElement | null>(null)

/** Ask for a name and create a note in a folder. */
async function newNote(parent: string): Promise<void> {
  const name = await ask('New note', {
    label: 'Name of the note',
    placeholder: 'My note',
  })
  if (!name) return
  if (!(await editor.confirmLeaving())) return
  await hollow.createNote(parent, name)
}

/** Ask for a name and create a folder. */
async function newFolder(parent: string): Promise<void> {
  const name = await ask('New folder', {
    label: 'Name of the folder',
    placeholder: 'Projects',
  })
  if (!name) return
  await hollow.createFolder(parent, name)
}

/**
 * The menu of the pane itself: create at the root, and sort the whole tree.
 *
 * An entry of the tree stops the event before it gets here, so a right-click on
 * a note or a folder still opens that entry's own menu.
 */
function onBackgroundMenu(event: MouseEvent): void {
  openMenu(event, [
    { label: 'New note', icon: '📄', action: () => newNote('') },
    { label: 'New folder', icon: '📁', action: () => newFolder('') },
    { label: 'Import…', icon: '📥', action: () => importInput?.value?.click() },
    {
      label: 'Sort A-Z',
      icon: '⬇️',
      separated: true,
      action: () => hollow.setSortOrder('asc'),
    },
    { label: 'Sort Z-A', icon: '⬆️', action: () => hollow.setSortOrder('desc') },
    { label: 'Reload the tree', icon: '↻', separated: true, action: () => hollow.refreshTree() },
  ])
}

/** Dropping on the empty sidebar returns an entry to the root, a file imports it. */
async function onDrop(event: DragEvent): Promise<void> {
  event.preventDefault()
  const files = event.dataTransfer?.files
  if (files?.length) {
    await importFiles(files, hollow.currentFolder.value)
    return
  }
  const source = event.dataTransfer?.getData('text/plain')
  if (source) await hollow.moveEntry(source, '')
}

/** Import every `.md` or `.zip` file dropped or picked, into one folder. */
async function importFiles(files: FileList | File[], parent: string): Promise<void> {
  for (const file of Array.from(files)) {
    await hollow.importUpload(parent, file)
  }
}

/** Send the files chosen through the picker to the import, then clear it. */
async function onImportChosen(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  if (input.files?.length) await importFiles(input.files, hollow.currentFolder.value)
  input.value = ''
}
</script>

<template>
  <aside
    class="sidebar"
    :class="{ 'is-collapsed': collapsed }"
    @contextmenu="onBackgroundMenu"
    @dragover.prevent
    @drop="onDrop"
  >
    <header class="sidebar-header">
      <button
        type="button"
        class="icon-button sidebar-logo"
        :title="collapsed ? 'Open the sidebar' : 'Collapse the sidebar'"
        @click.stop="toggleSidebar"
      >
        <AppLogo />
      </button>

      <template v-if="!collapsed">
        <h1 class="sidebar-title">Dragon Glass</h1>
        <button type="button" class="icon-button" title="Settings" @click="showSettings">
          ⚙️
        </button>
        <button
          type="button"
          class="icon-button"
          :title="theme === 'dark' ? 'Switch to the light theme' : 'Switch to the dark theme'"
          @click="toggle"
        >
          {{ theme === 'dark' ? '☀️' : '🌙' }}
        </button>
      </template>
    </header>

    <template v-if="!collapsed">
      <div class="sidebar-toolbar">
        <div class="sidebar-toolbar-group">
          <button
            type="button"
            class="icon-button"
            title="New note"
            @click="newNote(hollow.currentFolder.value)"
          >
            📄
          </button>
          <button
            type="button"
            class="icon-button"
            title="New folder"
            @click="newFolder(hollow.currentFolder.value)"
          >
            📁
          </button>
          <button
            type="button"
            class="icon-button"
            title="Import a .md note or a .zip archive"
            @click="importInput?.click()"
          >
            📥
          </button>
        </div>

        <div class="sidebar-toolbar-group">
          <button
            v-if="isEnabled('tutor')"
            type="button"
            class="icon-button"
            :class="{ 'is-active': view === 'tutor' }"
            title="DragonGlass Tutor"
            @click="showTutor()"
          >
            🎓
          </button>
          <button
            type="button"
            class="icon-button"
            title="Reload the tree"
            @click="hollow.refreshTree()"
          >
            ↻
          </button>
        </div>
      </div>

      <div class="sidebar-tree">
        <FileTree />
      </div>

      <p v-if="hollow.error.value" class="sidebar-error" @click="hollow.clearError()">
        {{ hollow.error.value }}
      </p>
    </template>

    <input
      ref="importInput"
      class="hidden-input"
      type="file"
      accept=".md,.zip"
      multiple
      @change="onImportChosen"
    />
  </aside>
</template>
