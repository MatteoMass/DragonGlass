<script setup lang="ts">
/** The right-click menu, drawn wherever it was opened and closed on any click. */
import { computed, onBeforeUnmount, onMounted } from 'vue'

import { useContextMenu } from '@/composables/useContextMenu'

const { menu, close } = useContextMenu()

/** Keep the menu inside the window, whichever corner it was opened in. */
const style = computed(() => {
  if (!menu.value) return {}
  const width = 220
  const height = menu.value.items.length * 34 + 12
  return {
    left: `${Math.min(menu.value.x, window.innerWidth - width - 8)}px`,
    top: `${Math.min(menu.value.y, window.innerHeight - height - 8)}px`,
  }
})

/** Close on Escape, as every transient surface in the app does. */
function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') close()
}

onMounted(() => {
  window.addEventListener('click', close)
  window.addEventListener('resize', close)
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('click', close)
  window.removeEventListener('resize', close)
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <Teleport to="body">
    <ul v-if="menu" class="context-menu" :style="style" @click.stop>
      <li
        v-for="(item, index) in menu.items"
        :key="index"
        class="context-menu-item"
        :class="{ 'is-danger': item.danger, 'is-separated': item.separated }"
        @click="
          () => {
            close()
            item.action()
          }
        "
      >
        <span v-if="item.icon" class="context-menu-icon">{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </li>
    </ul>
  </Teleport>
</template>
