<script setup lang="ts">
/**
 * The text-input dialog, driven by `usePrompt`.
 *
 * It is a native `<dialog>`, so the browser gives it the top layer, the focus
 * trap and Escape without any of it being re-implemented here.
 */
import { nextTick, ref, watch } from 'vue'

import { usePrompt } from '@/composables/usePrompt'

const { request, answer } = usePrompt()

const dialog = ref<HTMLDialogElement | null>(null)
const field = ref<HTMLInputElement | null>(null)
const draft = ref('')

/** Open and close the element as the request comes and goes. */
watch(request, async (asked) => {
  draft.value = asked?.initial ?? ''
  await nextTick()
  const element = dialog.value
  if (!element) return
  if (asked && !element.open) {
    element.showModal()
    field.value?.focus()
    field.value?.select()
  } else if (!asked && element.open) {
    element.close()
  }
})
</script>

<template>
  <dialog ref="dialog" class="dialog" @close="answer(null)" @click.self="answer(null)">
    <form v-if="request" class="dialog-form" @submit.prevent="answer(draft)">
      <h2 class="dialog-title">{{ request.title }}</h2>
      <label class="dialog-label" for="prompt-field">{{ request.label }}</label>
      <input
        id="prompt-field"
        ref="field"
        v-model="draft"
        class="dialog-field"
        type="text"
        spellcheck="false"
        autocomplete="off"
        :placeholder="request.placeholder"
      />
      <div class="dialog-actions">
        <button type="button" class="button" @click="answer(null)">Cancel</button>
        <button type="submit" class="button button-primary" :disabled="!draft.trim()">
          {{ request.confirmLabel }}
        </button>
      </div>
    </form>
  </dialog>
</template>
