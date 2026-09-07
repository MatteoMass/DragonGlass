/**
 * The right-click menu, wherever it is opened from.
 *
 * The menu holds its items rather than knowing them, so the tree, the sidebar
 * background and the editor each open the same component with their own.
 */

import { ref } from 'vue'

/** One line of the menu. */
export interface MenuItem {
  /** What the line says. */
  label: string
  /** What it does when it is chosen. */
  action: () => void
  /** An optional glyph shown before the label. */
  icon?: string
  /** Whether the line is styled as a destructive action. */
  danger?: boolean
  /** Whether a separator is drawn above the line. */
  separated?: boolean
}

/** Where the menu is, and what it holds. */
interface MenuState {
  x: number
  y: number
  items: MenuItem[]
}

const menu = ref<MenuState | null>(null)

/** The context menu, from both sides: opening it and closing it. */
export function useContextMenu() {
  /**
   * Open the menu at the position of a mouse event.
   *
   * The event's default menu is suppressed, and an empty list opens nothing.
   */
  function open(event: MouseEvent, items: MenuItem[]): void {
    event.preventDefault()
    event.stopPropagation()
    if (items.length === 0) {
      menu.value = null
      return
    }
    menu.value = { x: event.clientX, y: event.clientY, items }
  }

  /** Close the menu. */
  function close(): void {
    menu.value = null
  }

  return { menu, open, close }
}
