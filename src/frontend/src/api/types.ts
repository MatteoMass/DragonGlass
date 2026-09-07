/** The payloads the backend takes and gives back. */

/** What a node of the hollow tree is. */
export type EntryKind = 'folder' | 'note' | 'image'

/** One node of the hollow tree. */
export interface TreeNode {
  /** Whether the node is a folder, a note or an image. */
  kind: EntryKind
  /** The name on disk, extension included. */
  name: string
  /** The hollow-relative path of the node. */
  path: string
  /** The nodes below a folder; absent for notes and images. */
  children?: TreeNode[] | null
}

/** One block of a note: its Markdown, where it sits in the source, and its HTML. */
export interface NoteBlock {
  /** The offset the block starts at in the Markdown source. */
  start: number
  /** The offset just past its last character, so an edit can be written back by offsets. */
  end: number
  /** The Markdown the block is written in. */
  source: string
  /** That block rendered on its own. */
  html: string
}

/** A note, with the HTML already rendered by the server. */
export interface Note {
  /** The hollow-relative path the note lives at. */
  path: string
  /** The Markdown source, exactly as stored. */
  raw: string
  /** The rendered HTML, links resolved and images pointed home. */
  html: string
  /** The same note cut into the blocks the preview edits one at a time. */
  blocks: NoteBlock[]
}

/** Where an entry ended up after a rename or a move. */
export interface Entry {
  /** The hollow-relative path of the entry. */
  path: string
  /** Its name, extension included. */
  name: string
}

/** An uploaded image, ready to be written into the Markdown. */
export interface UploadedImage {
  /** The name the file was given, sanitised and de-duplicated. */
  name: string
  /** The hollow-relative path of the file. */
  path: string
}

/** What an import produced. */
export interface ImportResult {
  /** The hollow-relative paths that were written. */
  created: string[]
  /** Entries of a .zip that were neither a note nor an image, and so were left out. */
  skipped: number
}

/** An error the backend answered with, carrying its reason. */
export class ApiError extends Error {
  constructor(
    message: string,
    /** The HTTP status the backend answered with. */
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}
