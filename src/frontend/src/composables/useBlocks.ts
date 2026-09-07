/**
 * The preview, block by block.
 *
 * The server sends a note cut into the blocks it is written in, each with the
 * offsets it occupies in the source. That is all the preview needs to let one
 * block be written in place: what a click opens is the Markdown of that block
 * alone, and what leaving it does is put those characters back between the
 * offsets they came from — the rest of the file is not touched.
 *
 * Nothing here saves anything. An edited block changes the buffer, exactly as
 * typing in the whole-note editor would, and the note on disk hears about it
 * when the note is saved.
 */

import { ref, watch } from 'vue'

import { ApiError, api, type Note, type NoteBlock } from '@/api/client'

import { useEditor } from './useEditor'
import { useHollow } from './useHollow'

/** The block that does not exist yet: the empty space under the note. */
export const APPEND = -1

const blocks = ref<NoteBlock[]>([])
const cutFrom = ref<string | null>(null)
const editing = ref<number | null>(null)
const rendering = ref(false)
const error = ref('')

/** The blocks of the open note, and the one being written. */
export function useBlocks() {
  const hollow = useHollow()
  const editor = useEditor()

  /** Take the blocks from a note, which is what a read or a save just rendered. */
  function adopt(note: Note | null): void {
    editing.value = null
    error.value = ''
    blocks.value = note?.blocks ?? []
    cutFrom.value = note?.raw ?? null
  }

  /** A different note replaces the blocks with its own. */
  watch(() => hollow.currentNote.value, adopt)

  /**
   * Ask the server to cut the buffer into blocks again.
   *
   * The loop is for the edit that lands while a render is in flight: the
   * blocks are only right once they describe the buffer as it is now.
   */
  async function refresh(): Promise<void> {
    const note = hollow.currentNote.value
    if (!note || rendering.value) return
    rendering.value = true
    error.value = ''
    try {
      while (cutFrom.value !== editor.buffer.value) {
        const content = editor.buffer.value
        const rendered = await api.renderNote(note.path, content)
        if (hollow.currentNote.value !== note) return
        blocks.value = rendered.blocks
        cutFrom.value = content
      }
    } catch (raised) {
      error.value = raised instanceof ApiError ? raised.message : 'The preview could not be drawn'
    } finally {
      rendering.value = false
    }
  }

  /**
   * Make sure the blocks describe the buffer, and not what it used to be.
   *
   * A buffer still equal to what the server confirmed needs no request: the
   * note came with its blocks already.
   */
  async function sync(): Promise<void> {
    const note = hollow.currentNote.value
    if (!note) return adopt(null)
    if (cutFrom.value === editor.buffer.value) return
    if (editor.buffer.value === note.raw) return adopt(note)
    await refresh()
  }

  /**
   * Open one block for writing.
   *
   * Blocks whose offsets no longer describe the buffer are not opened at all —
   * they are re-cut first, and the click is spent on that.
   */
  function begin(index: number): void {
    if (index !== APPEND && cutFrom.value !== editor.buffer.value) {
      void sync()
      return
    }
    editing.value = index
  }

  /** Leave a block without keeping what was written in it. */
  function cancel(): void {
    editing.value = null
  }

  /**
   * Put an edited block back into the buffer and draw the note again.
   *
   * A block written empty leaves nothing between the blank lines that
   * surrounded it, which is how a block is deleted; `APPEND` writes a new one
   * under the note instead of replacing any.
   */
  async function commit(index: number, text: string): Promise<void> {
    editing.value = null
    const buffer = editor.buffer.value

    if (index === APPEND) {
      if (!text.trim()) return
      const body = buffer.replace(/\s+$/, '')
      editor.buffer.value = body ? `${body}\n\n${text}\n` : `${text}\n`
    } else {
      const block = blocks.value[index]
      if (!block || text === block.source) return
      if (cutFrom.value !== buffer) return
      editor.buffer.value = `${buffer.slice(0, block.start)}${text}${buffer.slice(block.end)}`
    }

    await refresh()
  }

  return { blocks, editing, error, rendering, begin, cancel, commit, sync }
}
