/**
 * The one text-input dialog the app has.
 *
 * `ask` returns a promise that settles with what was written, or with null when
 * the dialog was dismissed — so a caller can `await` a name the way it would
 * await anything else, and nothing in the app has to reach for `window.prompt`.
 */

import { ref } from 'vue'

/** What the dialog is currently asking for. */
interface Request {
  /** The heading of the dialog. */
  title: string
  /** The label above the field. */
  label: string
  /** The text the field opens on. */
  initial: string
  /** The greyed-out hint inside an empty field. */
  placeholder: string
  /** The label of the button that confirms. */
  confirmLabel: string
}

const request = ref<Request | null>(null)
let settle: ((value: string | null) => void) | null = null

/** The prompt dialog, from both sides: asking it and answering it. */
export function usePrompt() {
  /**
   * Ask the user for a line of text and wait for it.
   *
   * A request made while another is open replaces it, and the one it replaced
   * settles as dismissed.
   */
  function ask(
    title: string,
    options: {
      label?: string
      initial?: string
      placeholder?: string
      confirmLabel?: string
    } = {},
  ): Promise<string | null> {
    settle?.(null)
    request.value = {
      title,
      label: options.label ?? 'Name',
      initial: options.initial ?? '',
      placeholder: options.placeholder ?? '',
      confirmLabel: options.confirmLabel ?? 'Create',
    }
    return new Promise<string | null>((resolve) => {
      settle = resolve
    })
  }

  /**
   * Answer the open request and close the dialog.
   *
   * A value that is blank once trimmed is answered as a dismissal, because an
   * empty name is not a name.
   */
  function answer(value: string | null): void {
    const written = value?.trim()
    request.value = null
    settle?.(written ? written : null)
    settle = null
  }

  return { request, ask, answer }
}
