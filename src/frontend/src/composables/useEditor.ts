/**
 * The editing buffer, the dirty flag, the save, and the unsaved-changes guard.
 *
 * The buffer is what the textarea binds to; the note the hollow holds is what
 * the server last confirmed. The two are compared to know whether anything is
 * unsaved.
 */

import { computed, ref, watch } from 'vue'

import { ApiError, api } from '@/api/client'

import { useConfirm } from './useConfirm'
import { useHollow } from './useHollow'

/** The colours a selection can be highlighted in, and the one that removes it. */
export type HighlightColour = 'yellow' | 'blue' | 'green' | 'transparent'

const HIGHLIGHT_TAG = /^\s*<mark class="hl-[a-z]+">([\s\S]*)<\/mark>\s*$/

/** Take an existing `<mark>` off a selection, if it is wrapped in one. */
function stripHighlight(selection: string): string {
  return HIGHLIGHT_TAG.exec(selection)?.[1] ?? selection
}

/**
 * What a selection becomes once a highlight colour is applied to it.
 *
 * A different colour replaces the one already there, and 'transparent' unwraps
 * the selection back to plain Markdown. Null means there was nothing to
 * highlight. Both editors -- the whole-note textarea and the one a block is
 * written in -- ask this the same question.
 */
export function highlighted(selection: string, colour: HighlightColour): string | null {
  const inner = stripHighlight(selection)
  if (!inner.trim()) return null
  return colour === 'transparent' ? inner : `<mark class="hl-${colour}">${inner}</mark>`
}

/** Which of the two panes is showing. */
export type EditorMode = 'preview' | 'edit'

/** The table a click on ▦ writes, ready to be typed over. */
export const TABLE_SKELETON =
  '\n| Column 1 | Column 2 |\n| -------- | -------- |\n|          |          |\n|          |          |\n\n'

const buffer = ref('')
const mode = ref<EditorMode>('preview')
const saving = ref(false)
const saveError = ref('')
const textarea = ref<HTMLTextAreaElement | null>(null)

/** The buffer and everything that acts on it. */
export function useEditor() {
  const hollow = useHollow()
  const { ask } = useConfirm()

  /** Whether the buffer differs from what the server last confirmed. */
  const dirty = computed(() => {
    const note = hollow.currentNote.value
    return note !== null && buffer.value !== note.raw
  })

  /** Reload the buffer whenever a different note is opened. */
  watch(
    () => hollow.currentNote.value,
    (note) => {
      buffer.value = note?.raw ?? ''
      saveError.value = ''
    },
    { immediate: true },
  )

  /**
   * Save the buffer.
   *
   * The answer carries the note back whole, with its new path when the title
   * renamed the file, and the client replaces what it holds with what came back
   * rather than guessing what the server did.
   */
  async function save(): Promise<boolean> {
    const note = hollow.currentNote.value
    if (!note || saving.value) return false

    saving.value = true
    saveError.value = ''
    try {
      const saved = await api.saveNote(note.path, buffer.value)
      const renamed = saved.path !== note.path
      hollow.adoptNote(saved)
      buffer.value = saved.raw
      if (renamed) await hollow.refreshTree()
      return true
    } catch (raised) {
      saveError.value = raised instanceof ApiError ? raised.message : 'Unexpected error'
      return false
    } finally {
      saving.value = false
    }
  }

  /**
   * Ask before leaving a note with unsaved changes.
   *
   * Returns whether the caller may go on. A clean buffer never asks.
   */
  async function confirmLeaving(): Promise<boolean> {
    if (!dirty.value) return true
    return ask(
      'Unsaved changes',
      'The open note has changes that have not been saved. Leave and lose them?',
      { confirmLabel: 'Leave without saving', danger: true },
    )
  }

  /** Show the preview or the editor. */
  function setMode(next: EditorMode): void {
    mode.value = next
  }

  /** Replace the selected text of the textarea, keeping the caret usable. */
  function replaceSelection(text: string, select = false): void {
    const field = textarea.value
    if (!field) {
      buffer.value += text
      return
    }
    const start = field.selectionStart
    const end = field.selectionEnd
    buffer.value = `${buffer.value.slice(0, start)}${text}${buffer.value.slice(end)}`
    requestAnimationFrame(() => {
      field.focus()
      field.setSelectionRange(select ? start : start + text.length, start + text.length)
    })
  }

  /** Insert text at the caret, replacing whatever was selected. */
  function insert(text: string): void {
    replaceSelection(text)
  }

  /** Insert a ready-made table skeleton at the caret. */
  function insertTable(): void {
    insert(TABLE_SKELETON)
  }

  /**
   * Upload an image into the note's sidecar folder.
   *
   * Returns the Markdown that points at it, or null when the upload failed —
   * whoever asked decides where those characters go, which is what lets a
   * block being written in place take an image as readily as the editor does.
   */
  async function uploadImage(file: File): Promise<string | null> {
    const note = hollow.currentNote.value
    if (!note) return null
    saveError.value = ''
    try {
      const uploaded = await api.uploadImage(note.path, file)
      const folder = uploaded.path.split('/').slice(-2).join('/')
      return `![${uploaded.name}](${folder})`
    } catch (raised) {
      saveError.value = raised instanceof ApiError ? raised.message : 'The upload failed'
      return null
    }
  }

  /** Upload an image and write its Markdown at the caret. */
  async function insertImage(file: File): Promise<boolean> {
    const markdown = await uploadImage(file)
    if (markdown === null) return false
    insert(markdown)
    return true
  }

  /**
   * Wrap the current selection in a highlight, or take one off.
   *
   * It survives in the file, because it is just Markdown with a tag in it.
   */
  function highlight(colour: HighlightColour): void {
    const field = textarea.value
    if (!field) return
    const start = field.selectionStart
    const end = field.selectionEnd
    if (start === end) return

    const written = highlighted(buffer.value.slice(start, end), colour)
    if (written === null) return
    replaceSelection(written, true)
  }

  return {
    buffer,
    dirty,
    highlight,
    mode,
    save,
    saveError,
    saving,
    textarea,
    confirmLeaving,
    insert,
    insertImage,
    insertTable,
    replaceSelection,
    setMode,
    uploadImage,
  }
}
