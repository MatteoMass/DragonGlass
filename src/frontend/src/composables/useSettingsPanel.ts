/** Whether the settings panel is open, shared between the gear button and the dialog. */

import { ref } from 'vue'

const open = ref(false)

/** The settings panel, from both sides: opening it and closing it. */
export function useSettingsPanel() {
  return {
    open,
    show: () => {
      open.value = true
    },
    hide: () => {
      open.value = false
    },
  }
}
