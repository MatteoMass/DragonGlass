<script setup lang="ts">
/**
 * The tree of the hollow.
 *
 * Every gesture the tree offers — opening, the context menu, renaming in place
 * and moving by drag & drop — is decided here and carried out by `useHollow`.
 */
import { ref } from 'vue'

import type { TreeNode as Node } from '@/api/client'
import { useAppView } from '@/composables/useAppView'
import { useConfirm } from '@/composables/useConfirm'
import { useContextMenu } from '@/composables/useContextMenu'
import { useEditor } from '@/composables/useEditor'
import { usePrompt } from '@/composables/usePrompt'
import { parentOf, useHollow } from '@/composables/useHollow'

import TreeNode from './TreeNode.vue'

const hollow = useHollow()
const editor = useEditor()
const { ask } = useConfirm()
const { ask: askName } = usePrompt()
const { open: openMenu } = useContextMenu()
const { showNotes } = useAppView()

const renaming = ref('')

/** Open a note, or fold and unfold a folder — always back in the notes view. */
async function onOpen(node: Node): Promise<void> {
  showNotes()
  if (node.kind === 'folder') {
    hollow.select(node.path)
    hollow.toggleFolder(node.path)
    return
  }
  if (node.kind === 'image') {
    hollow.select(node.path)
    return
  }
  if (node.path === hollow.currentNote.value?.path) return
  if (!(await editor.confirmLeaving())) return
  await hollow.openNote(node.path)
}

/** Everything that can be done to one entry of the tree. */
function onMenu({ event, node }: { event: MouseEvent; node: Node }): void {
  hollow.select(node.path)
  const folder = node.kind === 'folder' ? node.path : parentOf(node.path)

  openMenu(event, [
    { label: 'New note', icon: '📄', action: () => createNote(folder) },
    { label: 'New folder', icon: '📁', action: () => createFolder(folder) },
    { label: 'Rename', icon: '✏️', action: () => (renaming.value = node.path), separated: true },
    { label: 'Delete', icon: '🗑️', danger: true, action: () => remove(node) },
  ])
}

/** Ask for a name and create a note in a folder. */
async function createNote(parent: string): Promise<void> {
  const name = await askName('New note', {
    label: 'Name of the note',
    placeholder: 'My note',
  })
  if (!name) return
  if (!(await editor.confirmLeaving())) return
  await hollow.createNote(parent, name)
}

/** Ask for a name and create a folder. */
async function createFolder(parent: string): Promise<void> {
  const name = await askName('New folder', {
    label: 'Name of the folder',
    placeholder: 'Projects',
  })
  if (!name) return
  await hollow.createFolder(parent, name)
}

/** Confirm and delete an entry — a folder goes with everything under it. */
async function remove(node: Node): Promise<void> {
  const isFolder = node.kind === 'folder'
  const agreed = await ask(
    isFolder ? 'Delete the folder' : 'Delete',
    isFolder
      ? `“${node.name}” and everything under it will be removed from disk. This cannot be undone.`
      : `“${node.name}” will be removed from disk, together with its images. This cannot be undone.`,
    { confirmLabel: 'Delete', danger: true },
  )
  if (agreed) await hollow.deleteEntry(node.path)
}

/** Confirm a rename typed in place. */
async function onRename({ node, name }: { node: Node; name: string }): Promise<void> {
  renaming.value = ''
  await hollow.renameEntry(node.path, name)
}

/** Move a dropped entry into the folder it was dropped on. */
async function onDrop({ source, target }: { source: string; target: Node }): Promise<void> {
  if (source === target.path) return
  await hollow.moveEntry(source, target.path)
}
</script>

<template>
  <div class="file-tree">
    <p v-if="hollow.loading.value && !hollow.tree.value.length" class="tree-empty">Loading…</p>
    <p v-else-if="!hollow.tree.value.length" class="tree-empty">
      The hollow is empty. Create the first note from the bar above.
    </p>
    <ul v-else class="tree-root">
      <TreeNode
        v-for="node in hollow.tree.value"
        :key="node.path"
        :node="node"
        :depth="0"
        :renaming="renaming"
        @open="onOpen"
        @menu="onMenu"
        @rename="onRename"
        @cancel-rename="renaming = ''"
        @drop-entry="onDrop"
      />
    </ul>
  </div>
</template>
