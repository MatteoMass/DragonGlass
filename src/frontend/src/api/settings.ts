/** The settings plugin's own types and HTTP calls: the native feature toggles. */

import { json, request } from './http'

/** A togglable native feature, with its current state. */
export interface Feature {
  /** The feature's stable identifier. */
  id: string
  /** The name shown in the settings panel. */
  label: string
  /** The sentence shown under the label. */
  description: string
  /** Whether it is currently on. */
  enabled: boolean
}

export const settingsApi = {
  /** Every native feature, with its current state. */
  getSettings(): Promise<Feature[]> {
    return request<Feature[]>('/settings')
  },

  /** Turn a feature on or off. */
  setFeature(id: string, enabled: boolean): Promise<Feature[]> {
    return request<Feature[]>(`/settings/${encodeURIComponent(id)}`, json('PATCH', { enabled }))
  },
}
