/**
 * The light/dark choice.
 *
 * The choice is kept in localStorage and, on a first visit, follows the
 * operating system's `prefers-color-scheme`.
 */

import { ref, watchEffect } from 'vue'

/** The two themes the stylesheet defines. */
export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'dragonglass.theme'

/** Read the stored choice, falling back to what the system prefers. */
function initialTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') return stored
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

const theme = ref<Theme>(initialTheme())

watchEffect(() => {
  document.documentElement.dataset.theme = theme.value
  localStorage.setItem(STORAGE_KEY, theme.value)
})

/** The theme, and the one gesture that changes it. */
export function useTheme() {
  /** Swap light for dark and back. */
  function toggle(): void {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }

  return { theme, toggle }
}
