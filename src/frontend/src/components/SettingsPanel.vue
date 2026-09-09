<script setup lang="ts">
/**
 * The settings panel: one row per feature the backend registry returns.
 *
 * It renders whatever `useSettings` holds, so adding a feature to the
 * registry never touches this component.
 */
import { nextTick, ref, watch } from 'vue'

import { useSettings } from '@/composables/useSettings'
import { useSettingsPanel } from '@/composables/useSettingsPanel'

const { features, error, setFeature } = useSettings()
const { open, hide } = useSettingsPanel()

const dialog = ref<HTMLDialogElement | null>(null)

/** Open and close the element as the panel is shown and hidden. */
watch(open, async (shown) => {
  await nextTick()
  const element = dialog.value
  if (!element) return
  if (shown && !element.open) element.showModal()
  else if (!shown && element.open) element.close()
})
</script>

<template>
  <dialog ref="dialog" class="dialog" @close="hide()" @click.self="hide()">
    <h2 class="dialog-title">Settings</h2>

    <ul class="settings-list">
      <li v-for="feature in features" :key="feature.id" class="settings-row">
        <div class="settings-row-text">
          <span class="settings-row-label">{{ feature.label }}</span>
          <span class="settings-row-description">{{ feature.description }}</span>
        </div>
        <button
          type="button"
          class="switch"
          role="switch"
          :aria-checked="feature.enabled"
          :class="{ 'is-on': feature.enabled }"
          @click="setFeature(feature.id, !feature.enabled)"
        >
          <span class="switch-knob" />
        </button>
      </li>
    </ul>

    <p v-if="error" class="field-error">{{ error }}</p>

    <div class="dialog-actions">
      <button type="button" class="button button-primary" @click="hide()">Close</button>
    </div>
  </dialog>
</template>

<style scoped>
.settings-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 0 0 8px;
  padding: 0;
  list-style: none;
}

.settings-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}

.settings-row:last-child {
  border-bottom: none;
}

.settings-row-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.settings-row-label {
  color: var(--text);
  font-size: 13.5px;
}

.settings-row-description {
  color: var(--text-muted);
  font-size: 12px;
}

.switch {
  position: relative;
  flex-shrink: 0;
  width: 36px;
  height: 20px;
  padding: 0;
  background: var(--bg-sunken);
  border: 1px solid var(--border);
  border-radius: 999px;
  cursor: pointer;
}

.switch.is-on {
  background: var(--accent);
  border-color: var(--accent);
}

.switch-knob {
  position: absolute;
  top: 1px;
  left: 1px;
  width: 16px;
  height: 16px;
  background: var(--bg-panel);
  border-radius: 50%;
  transition: transform 0.12s ease;
}

.switch.is-on .switch-knob {
  transform: translateX(16px);
}
</style>
