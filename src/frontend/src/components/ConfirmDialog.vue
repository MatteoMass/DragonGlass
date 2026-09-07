<script setup lang="ts">
/**
 * The confirmation dialog, driven by `useConfirm`.
 *
 * It is a native `<dialog>`, so the browser gives it the top layer, the focus
 * trap and Escape without any of it being re-implemented here.
 */
import { nextTick, ref, watch } from 'vue'

import { useConfirm } from '@/composables/useConfirm'

const { question, answer } = useConfirm()

const dialog = ref<HTMLDialogElement | null>(null)
const agree = ref<HTMLButtonElement | null>(null)

/** Open and close the element as the question comes and goes. */
watch(question, async (asked) => {
  await nextTick()
  const element = dialog.value
  if (!element) return
  if (asked && !element.open) {
    element.showModal()
    agree.value?.focus()
  } else if (!asked && element.open) {
    element.close()
  }
})
</script>

<template>
  <dialog
    ref="dialog"
    class="dialog"
    role="alertdialog"
    @close="answer(false)"
    @click.self="answer(false)"
  >
    <template v-if="question">
      <h2 class="dialog-title">{{ question.title }}</h2>
      <p class="dialog-message">{{ question.message }}</p>
      <div class="dialog-actions">
        <button type="button" class="button" @click="answer(false)">Cancel</button>
        <button
          ref="agree"
          type="button"
          class="button"
          :class="question.danger ? 'button-danger' : 'button-primary'"
          @click="answer(true)"
        >
          {{ question.confirmLabel }}
        </button>
      </div>
    </template>
  </dialog>
</template>
