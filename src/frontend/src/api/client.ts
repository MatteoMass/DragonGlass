/**
 * The hollow's own HTTP calls: notes, folders, entries, images, imports.
 *
 * The settings and tutor plugins keep their own API modules, `settings.ts`
 * and `tutor.ts`, built on the same `http.ts` plumbing -- so this module
 * never grows to know about a plugin that gets added or removed.
 */

import { ApiError, encodePath, json, request } from './http'
import type { Entry, ImportResult, Note, NoteBlock, TreeNode, UploadedImage } from './types'

export const api = {
  /** The whole hollow tree in one response. */
  tree(): Promise<TreeNode[]> {
    return request<TreeNode[]>('/tree')
  },

  /** Read one note, with its HTML already rendered. */
  readNote(path: string): Promise<Note> {
    return request<Note>(`/notes/${encodePath(path)}`)
  },

  /**
   * Save a note.
   *
   * The answer carries the **new** path when the note's title renamed the file,
   * which is why the caller replaces what it holds with what came back.
   */
  saveNote(path: string, content: string): Promise<Note> {
    return request<Note>(`/notes/${encodePath(path)}`, json('PUT', { content }))
  },

  /**
   * Render Markdown as the note at `path`, without saving anything.
   *
   * The answer has the same shape a read gives, blocks included: it is what
   * the preview asks for after a block was edited in place, while the file on
   * disk is still the one it was.
   */
  renderNote(path: string, content: string): Promise<Note> {
    return request<Note>(`/notes/${encodePath(path)}/render`, json('POST', { content }))
  },

  /** Create a note, born with its own title as a first-level heading. */
  createNote(parent: string, name: string): Promise<Note> {
    return request<Note>('/notes', json('POST', { parent, name }))
  },

  /** Create a folder. */
  createFolder(parent: string, name: string): Promise<Entry> {
    return request<Entry>('/folders', json('POST', { parent, name }))
  },

  /** Rename a note or a folder in place. */
  renameEntry(path: string, name: string): Promise<Entry> {
    return request<Entry>(`/entries/${encodePath(path)}`, json('PATCH', { name }))
  },

  /** Move a note or a folder into another folder. An empty parent is the root. */
  moveEntry(path: string, parent: string): Promise<Entry> {
    return request<Entry>(`/entries/${encodePath(path)}/move`, json('POST', { parent }))
  },

  /** Delete a note, or a folder and everything under it. */
  deleteEntry(path: string): Promise<void> {
    return request<void>(`/entries/${encodePath(path)}`, { method: 'DELETE' })
  },

  /** Upload an image into a note's sidecar folder. */
  uploadImage(notePath: string, file: File): Promise<UploadedImage> {
    const form = new FormData()
    form.append('image', file)
    return request<UploadedImage>(`/images/${encodePath(notePath)}`, {
      method: 'POST',
      body: form,
    })
  },

  /**
   * Import a `.md` note, or unpack a `.zip`, into a folder.
   *
   * A zip keeps only the notes and images it holds; everything else in it is
   * discarded rather than written to the hollow.
   */
  importUpload(parent: string, file: File): Promise<ImportResult> {
    const form = new FormData()
    form.append('parent', parent)
    form.append('file', file)
    return request<ImportResult>('/imports', { method: 'POST', body: form })
  },
}

export { ApiError }
export type { Entry, ImportResult, Note, NoteBlock, TreeNode, UploadedImage }
