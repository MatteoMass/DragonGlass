/**
 * The one confirmation dialog the app has.
 *
 * `ask` returns a promise that settles when the user answers, so a caller can
 * `await` a question the way it would await anything else.
 */

import { ref } from 'vue'

/** What the dialog is currently asking. */
interface Question {
  /** The heading of the dialog. */
  title: string
  /** The sentence below it. */
  message: string
  /** The label of the button that agrees. */
  confirmLabel: string
  /** Whether that button is styled as a destructive action. */
  danger: boolean
}

const question = ref<Question | null>(null)
let settle: ((agreed: boolean) => void) | null = null

/** The confirmation dialog, from both sides: asking it and answering it. */
export function useConfirm() {
  /**
   * Ask the user something and wait for the answer.
   *
   * A question asked while another is open replaces it, and the one it replaced
   * settles as declined.
   */
  function ask(
    title: string,
    message: string,
    options: { confirmLabel?: string; danger?: boolean } = {},
  ): Promise<boolean> {
    settle?.(false)
    question.value = {
      title,
      message,
      confirmLabel: options.confirmLabel ?? 'Confirm',
      danger: options.danger ?? false,
    }
    return new Promise<boolean>((resolve) => {
      settle = resolve
    })
  }

  /** Answer the open question and close the dialog. */
  function answer(agreed: boolean): void {
    question.value = null
    settle?.(agreed)
    settle = null
  }

  return { question, ask, answer }
}
