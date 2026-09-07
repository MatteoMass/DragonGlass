/**
 * The `[[` autocompletion.
 *
 * Typing `[[` opens the list of every note in the hollow, filtered as the name
 * is written: ↑/↓ to move, Enter or Tab to accept, Esc to dismiss. What is
 * accepted is written into the buffer between the brackets that opened it.
 */

import { computed, ref } from 'vue'

import type { TreeNode } from '@/api/client'

import { useHollow } from './useHollow'

/** One note offered by the autocompletion. */
export interface LinkSuggestion {
  /** The name to write between the brackets. */
  name: string
  /** The hollow-relative folder holding it, shown to tell namesakes apart. */
  folder: string
}

/** Where the caret is, so the list can be drawn beside it. */
export interface CaretPosition {
  top: number
  left: number
}

const HOW_MANY = 12

const open = ref(false)
const query = ref('')
const highlighted = ref(0)
const position = ref<CaretPosition>({ top: 0, left: 0 })
const openedAt = ref(-1)

/** Collect every note of the tree into a flat list of suggestions. */
function collect(nodes: TreeNode[], into: LinkSuggestion[] = []): LinkSuggestion[] {
  for (const node of nodes) {
    if (node.kind === 'note') {
      const cut = node.path.lastIndexOf('/')
      into.push({
        name: node.name.replace(/\.md$/i, ''),
        folder: cut === -1 ? '' : node.path.slice(0, cut),
      })
    } else if (node.children) {
      collect(node.children, into)
    }
  }
  return into
}

/** Where the caret is inside a textarea, in pixels relative to the page. */
function caretPosition(field: HTMLTextAreaElement): CaretPosition {
  const mirror = document.createElement('div')
  const style = window.getComputedStyle(field)
  for (const property of style) {
    mirror.style.setProperty(property, style.getPropertyValue(property))
  }
  mirror.style.position = 'absolute'
  mirror.style.visibility = 'hidden'
  mirror.style.whiteSpace = 'pre-wrap'
  mirror.style.overflow = 'hidden'
  mirror.style.height = 'auto'

  mirror.textContent = field.value.slice(0, field.selectionStart)
  const marker = document.createElement('span')
  marker.textContent = '​'
  mirror.appendChild(marker)
  document.body.appendChild(mirror)

  const box = field.getBoundingClientRect()
  const top = box.top + marker.offsetTop - field.scrollTop + marker.offsetHeight
  const left = box.left + marker.offsetLeft - field.scrollLeft
  document.body.removeChild(mirror)

  return { top, left }
}

/** The autocompletion, from both sides: the textarea's and the list's. */
export function useWikiLinks() {
  const hollow = useHollow()

  /** Every note of the hollow, as the list would offer it unfiltered. */
  const allNotes = computed(() => collect(hollow.tree.value))

  /** The notes matching what has been typed since the brackets opened. */
  const suggestions = computed<LinkSuggestion[]>(() => {
    const wanted = query.value.trim().toLowerCase()
    const notes = allNotes.value
    if (!wanted) return notes.slice(0, HOW_MANY)
    return notes
      .filter((note) => note.name.toLowerCase().includes(wanted))
      .sort((a, b) => {
        const byStart =
          Number(b.name.toLowerCase().startsWith(wanted)) -
          Number(a.name.toLowerCase().startsWith(wanted))
        return byStart || a.name.localeCompare(b.name, undefined, { sensitivity: 'base' })
      })
      .slice(0, HOW_MANY)
  })

  /** The suggestion Enter would accept. */
  const selected = computed(() => suggestions.value[highlighted.value] ?? null)

  /**
   * Look at the buffer after a keystroke and open, refine or close the list.
   *
   * The list opens on the `[[` nearest behind the caret, and closes as soon as
   * that pair is gone, is closed by `]]`, or the name being typed runs over a
   * line break.
   */
  function refresh(field: HTMLTextAreaElement): void {
    const caret = field.selectionStart
    const before = field.value.slice(0, caret)
    const brackets = before.lastIndexOf('[[')

    if (brackets === -1) return close()
    const typed = before.slice(brackets + 2)
    if (typed.includes(']') || typed.includes('\n') || typed.includes('[')) return close()

    if (!open.value || openedAt.value !== brackets) {
      highlighted.value = 0
      position.value = caretPosition(field)
      openedAt.value = brackets
    }
    query.value = typed
    open.value = true
  }

  /** Move the highlight down (1) or up (-1), wrapping around the ends. */
  function move(step: number): void {
    const count = suggestions.value.length
    if (count === 0) return
    highlighted.value = (highlighted.value + step + count) % count
  }

  /** Point the highlight at one suggestion, as hovering does. */
  function highlight(index: number): void {
    highlighted.value = index
  }

  /**
   * Write a suggestion into the buffer, closing the brackets it opened.
   *
   * Returns the new buffer and where the caret should land, so the caller can
   * apply both at once.
   */
  function accept(
    value: string,
    caret: number,
    suggestion: LinkSuggestion | null = selected.value,
  ): { value: string; caret: number } | null {
    if (!open.value || !suggestion || openedAt.value === -1) return null
    const after = value.slice(caret)
    const closing = after.startsWith(']]') ? 2 : 0
    const written = `${value.slice(0, openedAt.value)}[[${suggestion.name}]]`
    close()
    return { value: `${written}${after.slice(closing)}`, caret: written.length }
  }

  /** Dismiss the list. */
  function close(): void {
    open.value = false
    query.value = ''
    highlighted.value = 0
    openedAt.value = -1
  }

  return { open, position, query, suggestions, highlighted, selected, accept, close, highlight, move, refresh }
}
