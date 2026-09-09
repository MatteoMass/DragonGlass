/**
 * Whether the left pane is open or folded down to its icon.
 *
 * The choice is kept in localStorage, so a hollow opened folded stays folded
 * across reloads.
 */

import { ref, watchEffect } from 'vue'

const STORAGE_KEY = 'dragonglass.sidebar-collapsed'

const collapsed = ref<boolean>(localStorage.getItem(STORAGE_KEY) === 'true')

watchEffect(() => {
  localStorage.setItem(STORAGE_KEY, String(collapsed.value))
})

/** The state of the pane, and the one gesture that changes it. */
export function useSidebar() {
  /** Fold the pane down to its icon, or open it back up. */
  function toggle(): void {
    collapsed.value = !collapsed.value
  }

  return { collapsed, toggle }
}
