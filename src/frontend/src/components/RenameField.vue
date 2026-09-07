<script setup lang="ts">
/** The inline field a tree entry turns into while it is being renamed. */
import { nextTick, onMounted, ref } from 'vue'

const props = defineProps<{
  /** The name the entry has now, which the field opens on. */
  modelValue: string
  /** Whether the extension is kept out of the initial selection. */
  keepExtension?: boolean
}>()

const emit = defineEmits<{
  /** The new name was confirmed. */
  (event: 'confirm', name: string): void
  /** The rename was abandoned. */
  (event: 'cancel'): void
}>()

const field = ref<HTMLInputElement | null>(null)
const draft = ref(props.modelValue)

onMounted(async () => {
  await nextTick()
  const input = field.value
  if (!input) return
  input.focus()
  const dot = props.keepExtension ? draft.value.lastIndexOf('.') : -1
  input.setSelectionRange(0, dot > 0 ? dot : draft.value.length)
})

/** Confirm the name, unless nothing was written or nothing changed. */
function confirm(): void {
  const name = draft.value.trim()
  if (!name || name === props.modelValue) emit('cancel')
  else emit('confirm', name)
}
</script>

<template>
  <input
    ref="field"
    v-model="draft"
    class="rename-field"
    type="text"
    spellcheck="false"
    @click.stop
    @keydown.stop
    @keyup.enter="confirm"
    @keyup.esc="emit('cancel')"
    @blur="confirm"
  />
</template>
