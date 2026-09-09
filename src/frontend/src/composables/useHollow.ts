/**
 * The tree, the selection, and everything that changes the hollow's shape.
 *
 * One instance is shared by the whole app: the sidebar reads the tree from
 * here, and every creation, rename, move and deletion goes through here so the
 * tree is refreshed from the server rather than patched by hand.
 */

import { computed, ref } from 'vue'

import { ApiError, api, type ImportResult, type Note, type TreeNode } from '@/api/client'

/** How the tree is ordered. */
export type SortOrder = 'asc' | 'desc'

const tree = ref<TreeNode[]>([])
const currentNote = ref<Note | null>(null)
const selectedPath = ref<string>('')
const expanded = ref<Set<string>>(new Set())
const sortOrder = ref<SortOrder>('asc')
const loading = ref(false)
const error = ref<string>('')

/** Sort a tree recursively, folders first and then files by name. */
function sorted(nodes: TreeNode[], order: SortOrder): TreeNode[] {
  const direction = order === 'asc' ? 1 : -1
  return [...nodes]
    .map((node) =>
      node.children ? { ...node, children: sorted(node.children, order) } : node,
    )
    .sort((a, b) => {
      if (a.kind === 'folder' && b.kind !== 'folder') return -1
      if (a.kind !== 'folder' && b.kind === 'folder') return 1
      return direction * a.name.localeCompare(b.name, undefined, { sensitivity: 'base' })
    })
}

/** The folder holding a hollow-relative path, empty at the root. */
export function parentOf(path: string): string {
  const cut = path.lastIndexOf('/')
  return cut === -1 ? '' : path.slice(0, cut)
}

/** Whether `path` is `folder` itself or something inside it. */
export function isInside(path: string, folder: string): boolean {
  if (!folder) return true
  return path === folder || path.startsWith(`${folder}/`)
}

/** The shared hollow state, and the operations that change it. */
export function useHollow() {
  /** The tree as the sidebar shows it, in the chosen order. */
  const orderedTree = computed(() => sorted(tree.value, sortOrder.value))

  /** The folder a new entry lands in: the selection's folder, or the root. */
  const currentFolder = computed(() => {
    if (!selectedPath.value) return ''
    const node = findNode(selectedPath.value)
    return node?.kind === 'folder' ? node.path : parentOf(selectedPath.value)
  })

  /** Find one node of the tree by its path. */
  function findNode(path: string, nodes: TreeNode[] = tree.value): TreeNode | null {
    for (const node of nodes) {
      if (node.path === path) return node
      if (node.children) {
        const found = findNode(path, node.children)
        if (found) return found
      }
    }
    return null
  }

  /** Run an operation, reporting whatever the backend refused it with. */
  async function attempt<T>(operation: () => Promise<T>): Promise<T | null> {
    error.value = ''
    try {
      return await operation()
    } catch (raised) {
      error.value = raised instanceof ApiError ? raised.message : 'Unexpected error'
      return null
    }
  }

  /** Reload the whole tree from the server. */
  async function refreshTree(): Promise<void> {
    loading.value = true
    const fetched = await attempt(() => api.tree())
    if (fetched) tree.value = fetched
    loading.value = false
  }

  /** Open a note, replacing what the editor holds. */
  async function openNote(path: string): Promise<Note | null> {
    const note = await attempt(() => api.readNote(path))
    if (note) {
      currentNote.value = note
      selectedPath.value = note.path
      expandTo(note.path)
    }
    return note
  }

  /** Replace the open note with what a save gave back, at its possibly new path. */
  function adoptNote(note: Note): void {
    currentNote.value = note
    selectedPath.value = note.path
    expandTo(note.path)
  }

  /** Select an entry without opening it — a folder, or an image. */
  function select(path: string): void {
    selectedPath.value = path
  }

  /** Open every folder above a path so the entry is visible in the tree. */
  function expandTo(path: string): void {
    const segments = path.split('/')
    segments.pop()
    let walked = ''
    for (const segment of segments) {
      walked = walked ? `${walked}/${segment}` : segment
      expanded.value.add(walked)
    }
    expanded.value = new Set(expanded.value)
  }

  /** Open or close one folder of the tree. */
  function toggleFolder(path: string): void {
    const open = new Set(expanded.value)
    if (open.has(path)) open.delete(path)
    else open.add(path)
    expanded.value = open
  }

  /** Whether a folder is open in the tree. */
  function isExpanded(path: string): boolean {
    return expanded.value.has(path)
  }

  /** Create a note and open it. */
  async function createNote(parent: string, name: string): Promise<Note | null> {
    const note = await attempt(() => api.createNote(parent, name))
    if (note) {
      await refreshTree()
      adoptNote(note)
    }
    return note
  }

  /** Create a folder and reveal it. */
  async function createFolder(parent: string, name: string): Promise<boolean> {
    const created = await attempt(() => api.createFolder(parent, name))
    if (!created) return false
    await refreshTree()
    expandTo(created.path)
    expanded.value = new Set(expanded.value).add(created.path)
    selectedPath.value = created.path
    return true
  }

  /**
   * Import a `.md` note, or unpack a `.zip`, into a folder, and reveal what came of it.
   *
   * A zip keeps only the notes and images it holds; everything else in it is
   * discarded rather than written to the hollow.
   */
  async function importUpload(parent: string, file: File): Promise<ImportResult | null> {
    const result = await attempt(() => api.importUpload(parent, file))
    if (result) {
      await refreshTree()
      if (parent) {
        expandTo(parent)
        expanded.value = new Set(expanded.value).add(parent)
      }
    }
    return result
  }

  /** Rename an entry, following the open note if it was the one renamed. */
  async function renameEntry(path: string, name: string): Promise<boolean> {
    const renamed = await attempt(() => api.renameEntry(path, name))
    if (!renamed) return false
    await refreshTree()
    await followMovedEntry(path, renamed.path)
    return true
  }

  /** Move an entry into a folder, following the open note when it travelled. */
  async function moveEntry(path: string, parent: string): Promise<boolean> {
    if (parentOf(path) === parent) return true
    if (isInside(parent, path)) {
      error.value = 'A folder cannot be moved into itself'
      return false
    }
    const moved = await attempt(() => api.moveEntry(path, parent))
    if (!moved) return false
    await refreshTree()
    await followMovedEntry(path, moved.path)
    return true
  }

  /** Delete an entry, closing the open note when it was inside what went. */
  async function deleteEntry(path: string): Promise<boolean> {
    const done = await attempt(async () => {
      await api.deleteEntry(path)
      return true
    })
    if (!done) return false
    if (currentNote.value && isInside(currentNote.value.path, path)) {
      currentNote.value = null
      selectedPath.value = ''
    }
    await refreshTree()
    return true
  }

  /** Re-open the current note at its new path when its entry moved under it. */
  async function followMovedEntry(oldPath: string, newPath: string): Promise<void> {
    const open = currentNote.value?.path
    if (!open || !isInside(open, oldPath)) {
      selectedPath.value = newPath
      return
    }
    await openNote(open === oldPath ? newPath : `${newPath}${open.slice(oldPath.length)}`)
  }

  /** Change how the tree is ordered. */
  function setSortOrder(order: SortOrder): void {
    sortOrder.value = order
  }

  /** Clear the last reported error. */
  function clearError(): void {
    error.value = ''
  }

  return {
    tree: orderedTree,
    currentNote,
    selectedPath,
    currentFolder,
    sortOrder,
    loading,
    error,
    adoptNote,
    clearError,
    createFolder,
    createNote,
    deleteEntry,
    findNode,
    importUpload,
    isExpanded,
    moveEntry,
    openNote,
    refreshTree,
    renameEntry,
    select,
    setSortOrder,
    toggleFolder,
  }
}
