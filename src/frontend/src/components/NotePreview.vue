<script setup lang="ts">
/**
 * The rendered note, one block at a time.
 *
 * The HTML comes finished from the server, so this pane does no Markdown work
 * at all; what it does own is what a click means. A click on a wiki-link opens
 * the note it points at, or offers to create the one it does not. A click
 * anywhere else opens that block for writing, in the place it is read, and
 * leaving it renders it again — the whole-note editor is for when the whole
 * note is what needs changing, not for fixing a word.
 */
import { onMounted } from 'vue'

import { APPEND, useBlocks } from '@/composables/useBlocks'
import { useConfirm } from '@/composables/useConfirm'
import { useEditor } from '@/composables/useEditor'
import { parentOf, useHollow } from '@/composables/useHollow'

import BlockEditor from './BlockEditor.vue'

const hollow = useHollow()
const editor = useEditor()
const blocks = useBlocks()
const { ask } = useConfirm()

/** The buffer may have moved on in the other pane while this one was away. */
onMounted(() => void blocks.sync())

/**
 * Intercept a click on a wiki-link.
 *
 * A resolved link opens its note; an unresolved one offers to create the
 * missing note in the folder of the note being read, and opens it immediately —
 * which is the honest behaviour for a link to something not written yet.
 */
async function onClick(event: MouseEvent): Promise<void> {
  const link = (event.target as HTMLElement).closest<HTMLAnchorElement>('a.wikilink')
  if (!link) return
  event.preventDefault()

  const path = link.dataset.path
  if (path) {
    if (path === hollow.currentNote.value?.path) return
    if (!(await editor.confirmLeaving())) return
    await hollow.openNote(path)
    return
  }

  const name = link.dataset.wikilink
  if (!name) return
  const agreed = await ask(
    'Missing note',
    `“${name}” does not exist yet. Create it in the current folder?`,
    { confirmLabel: 'Create and open' },
  )
  if (!agreed) return
  if (!(await editor.confirmLeaving())) return
  await hollow.createNote(parentOf(hollow.currentNote.value?.path ?? ''), name)
}

/**
 * Open the block that was clicked.
 *
 * A link is followed rather than edited, and a click that ends a selection is
 * the end of a selection: text is read and copied out of the preview far more
 * often than it is rewritten.
 */
function onBlockClick(index: number, event: MouseEvent): void {
  if ((event.target as HTMLElement).closest('a')) return
  if (window.getSelection()?.isCollapsed === false) return
  blocks.begin(index)
}
</script>

<template>
  <article class="note-preview markdown-body" @click="onClick">
    <p v-if="blocks.error.value" class="note-block-error">{{ blocks.error.value }}</p>

    <template v-for="(block, index) in blocks.blocks.value" :key="index">
      <BlockEditor
        v-if="blocks.editing.value === index"
        :source="block.source"
        @commit="(text) => blocks.commit(index, text)"
        @cancel="blocks.cancel()"
      />
      <div
        v-else
        class="note-block"
        v-html="block.html"
        @click="onBlockClick(index, $event)"
      />
    </template>

    <BlockEditor
      v-if="blocks.editing.value === APPEND"
      source=""
      placeholder="A new block. Markdown, [[ to link another note."
      @commit="(text) => blocks.commit(APPEND, text)"
      @cancel="blocks.cancel()"
    />
    <div v-else class="note-append" @click="blocks.begin(APPEND)">
      <span v-if="!blocks.blocks.value.length" class="note-append-hint">
        Click here to start writing.
      </span>
    </div>
  </article>
</template>
