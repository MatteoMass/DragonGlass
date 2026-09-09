/** Which of the app's top-level views the workspace shows. */

import { ref } from 'vue'

export type AppView = 'notes' | 'tutor'

const view = ref<AppView>('notes')

/** The active view, and the two gestures that switch it. */
export function useAppView() {
  return {
    view,
    showNotes: () => {
      view.value = 'notes'
    },
    showTutor: () => {
      view.value = 'tutor'
    },
  }
}
