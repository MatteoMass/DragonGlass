<script setup lang="ts">
/**
 * One node of the file tree, recursive into its own children.
 *
 * A folder carries a caret that points down once it is open; the children it
 * holds are drawn against a faint line dropped from it.
 */
import type { TreeNode as Node } from '@/api/client'
import { useHollow } from '@/composables/useHollow'

import RenameField from './RenameField.vue'

const props = defineProps<{
  /** The node to draw. */
  node: Node
  /** How deep it sits, which is what indents it. */
  depth: number
  /** The path currently being renamed, if it is this one. */
  renaming: string
}>()

const emit = defineEmits<{
  /** The node was chosen. */
  (event: 'open', node: Node): void
  /** The node was right-clicked. */
  (event: 'menu', payload: { event: MouseEvent; node: Node }): void
  /** A rename was confirmed on the node. */
  (event: 'rename', payload: { node: Node; name: string }): void
  /** The rename was abandoned. */
  (event: 'cancel-rename'): void
  /** An entry was dropped onto this node. */
  (event: 'drop-entry', payload: { source: string; target: Node }): void
}>()

const hollow = useHollow()

/** The glyph standing for the kind of node, open folders included. */
function iconOf(node: Node): string {
  if (node.kind === 'folder') return hollow.isExpanded(node.path) ? '📂' : '📁'
  return node.kind === 'image' ? '🖼️' : '📄'
}

/** A note is shown without its extension; everything else as it is on disk. */
function labelOf(node: Node): string {
  return node.kind === 'note' ? node.name.replace(/\.md$/i, '') : node.name
}

/** Carry the dragged entry's path, which is all a drop needs to know. */
function onDragStart(event: DragEvent): void {
  event.dataTransfer?.setData('text/plain', props.node.path)
  if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
}

/**
 * Only a folder accepts a drop.
 *
 * A note or an image refuses it outright rather than letting the sidebar behind
 * it treat the drop as one on its empty area, which would return the entry to
 * the root instead of leaving it where it was.
 */
function onDragOver(event: DragEvent): void {
  event.stopPropagation()
  if (props.node.kind !== 'folder') return
  event.preventDefault()
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'
}

/** Hand the dropped path up; the hollow decides whether the move is legal. */
function onDrop(event: DragEvent): void {
  event.preventDefault()
  event.stopPropagation()
  if (props.node.kind !== 'folder') return
  const source = event.dataTransfer?.getData('text/plain')
  if (source) emit('drop-entry', { source, target: props.node })
}
</script>

<template>
  <li class="tree-node">
    <div
      class="tree-row"
      :class="{
        'is-selected': hollow.selectedPath.value === node.path,
        'is-folder': node.kind === 'folder',
      }"
      :style="{ paddingLeft: `${depth * 14 + 8}px` }"
      draggable="true"
      @click="emit('open', node)"
      @contextmenu="emit('menu', { event: $event, node })"
      @dragstart="onDragStart"
      @dragover="onDragOver"
      @drop="onDrop"
    >
      <span
        class="tree-twisty"
        :class="{ 'is-open': hollow.isExpanded(node.path) }"
        aria-hidden="true"
        >{{ node.kind === 'folder' ? '▸' : '' }}</span
      >
      <span class="tree-icon">{{ iconOf(node) }}</span>
      <RenameField
        v-if="renaming === node.path"
        :model-value="labelOf(node)"
        @confirm="(name) => emit('rename', { node, name })"
        @cancel="emit('cancel-rename')"
      />
      <span v-else class="tree-label" :title="node.path">{{ labelOf(node) }}</span>
    </div>

    <ul
      v-if="node.children && node.children.length && hollow.isExpanded(node.path)"
      class="tree-children"
      :style="{ '--guide-left': `${depth * 14 + 14}px` }"
    >
      <TreeNode
        v-for="child in node.children"
        :key="child.path"
        :node="child"
        :depth="depth + 1"
        :renaming="renaming"
        @open="(payload) => emit('open', payload)"
        @menu="(payload) => emit('menu', payload)"
        @rename="(payload) => emit('rename', payload)"
        @cancel-rename="emit('cancel-rename')"
        @drop-entry="(payload) => emit('drop-entry', payload)"
      />
    </ul>
  </li>
</template>
