/**
 * The native feature toggles.
 *
 * One instance is shared by the whole app: `load` is called once from
 * `App.vue`, and any component can read `isEnabled` to gate its own UI.
 */

import { ref } from 'vue'

import { ApiError } from '@/api/http'
import { settingsApi, type Feature } from '@/api/settings'

const features = ref<Feature[]>([])
const error = ref<string>('')

/** The shared feature-toggle state, and the operations that change it. */
export function useSettings() {
  /** Load every feature from the server. */
  async function load(): Promise<void> {
    error.value = ''
    try {
      features.value = await settingsApi.getSettings()
    } catch (raised) {
      error.value = raised instanceof ApiError ? raised.message : 'Unexpected error'
    }
  }

  /** Turn a feature on or off, applied at once and rolled back on failure. */
  async function setFeature(id: string, enabled: boolean): Promise<void> {
    const before = features.value
    features.value = before.map((feature) => (feature.id === id ? { ...feature, enabled } : feature))
    error.value = ''
    try {
      features.value = await settingsApi.setFeature(id, enabled)
    } catch (raised) {
      features.value = before
      error.value = raised instanceof ApiError ? raised.message : 'Unexpected error'
    }
  }

  /** Whether a feature is currently on. */
  function isEnabled(id: string): boolean {
    return features.value.find((feature) => feature.id === id)?.enabled ?? false
  }

  return { features, error, load, setFeature, isEnabled }
}
