# Dragon Glass — frontend

Vue 3, Vite and TypeScript. Two panes: the file tree on the left, the selected
note on the right — a toolbar, and the note itself in one of its two modes,
**Preview** or **Edit**.

The app does no Markdown work at all. The backend renders every note and sends
finished HTML, so the editor and the preview can never disagree about what a
note means, and a save answers with the note whole — including the **new** path
when its title renamed the file.

The preview is not read-only. Every note answer carries `blocks` beside `html`
— the note cut into the blocks it is written in, each with its own HTML and its
offsets in the source — so a click on a paragraph opens that block alone as
Markdown, and leaving it puts those characters back between those offsets and
renders it again. It changes the buffer, not the file: saving is still explicit.

## Run it

Against a backend already running on `:8000`:

```bash
npm install
npm run dev                                   # http://localhost:5173
```

Vite proxies `/tree`, `/notes`, `/folders`, `/entries`, `/images` and `/hollow`
to `http://127.0.0.1:8000`, so the app uses the same relative URLs it does when
the backend serves it. Point the proxy elsewhere with `DRAGONGLASS_API_URL`. A
frontend that calls the API directly instead of through the proxy needs its
origin in `server.cors_origins`; through the proxy it needs nothing.

| Command              | What it does                                  |
| -------------------- | --------------------------------------------- |
| `npm run dev`        | Vite, with the API proxied.                   |
| `npm run build`      | The production build, into `dist/`.           |
| `npm run preview`    | Serve the build to look at it.                |
| `npm run type-check` | `vue-tsc`, which the build does not run.      |

The build lands in `dist/`, which the API mounts at `/` when it is there — so a
checkout that has never run `npm run build` still starts, and answers the API
alone.

## How it is put together

| Path                  | What lives there                                                |
| --------------------- | ---------------------------------------------------------------- |
| `src/api/`            | The only place that talks HTTP — `client.ts` and the payload types. |
| `src/composables/`    | The shared state.                                                |
| `src/components/`     | The views.                                                       |
| `src/styles/main.css` | The tokens for both themes, the highlight colours, the components. |

### The composables

State is shared by module scope rather than by an injected store: each
composable holds its refs outside the function it exports, so every component
calling `useHollow()` reads the same tree.

| Composable      | What it owns                                                                                            |
| --------------- | --------------------------------------------------------------------------------------------------------- |
| `useHollow`      | The tree, the selection, which folders are open, the sort order, and every creation, rename, move and deletion. Each of them refreshes the tree from the server rather than patching it. |
| `useEditor`     | The buffer, the dirty flag, the save, the unsaved-changes guard, the table skeleton, the image upload and the highlighting. |
| `useBlocks`     | The blocks the preview is drawn from, which one is being written in place, and putting an edited one back into the buffer by its offsets. |
| `useWikiLinks`  | The `[[` autocompletion: what has been typed, what matches, where the caret is, and what accepting writes. |
| `useContextMenu`| Where the right-click menu is and what it holds — the tree, the sidebar itself and the editor each open it with their own items. |
| `useConfirm`    | The one confirmation dialog, as a promise a caller can await.                                             |
| `usePrompt`     | The one text-input dialog, likewise — nothing in the app reaches for `window.prompt`.                      |
| `useTheme`      | The light/dark choice, kept in `localStorage` and following `prefers-color-scheme` on a first visit.       |

### The components

`App.vue` is the two-column layout and the global shortcuts. `Sidebar.vue`
holds the toolbar, the theme toggle and `FileTree.vue`, which owns every gesture
the tree offers and draws itself out of the recursive `TreeNode.vue`.
`NoteToolbar.vue`, `NotePreview.vue` and `NoteEditor.vue` are the right pane,
with `BlockEditor.vue` as the one block a click on the preview opens — the
field, its table and image tools, and the two surfaces they share with the
whole-note editor;
`ContextMenu.vue`, `HighlightMenu.vue`, `LinkAutocomplete.vue`,
`RenameField.vue`, `ConfirmDialog.vue` and `PromptDialog.vue` are the surfaces
the rest of them open. The two dialogs are native `<dialog>` elements, so the
browser gives them the top layer, the focus trap and Escape.

## What you can do

| To do this                                | Do that                                                                    |
| ----------------------------------------- | --------------------------------------------------------------------------- |
| Save the note                             | <kbd>Ctrl</kbd>/<kbd>Cmd</kbd> + <kbd>S</kbd>, or *Save*                     |
| Act on a file or folder                   | Right-click it in the tree                                                   |
| Create or sort from nowhere in particular | Right-click anywhere in the sidebar                                          |
| Edit one block where it is                | Click it in the preview; leave it, or <kbd>Ctrl</kbd>/<kbd>Cmd</kbd> + <kbd>Enter</kbd> |
| Give a block back untouched               | <kbd>Esc</kbd>                                                               |
| Write a new block                         | Click the empty space under the note                                         |
| Add a table or an image                   | The ▦ / 🖼️ buttons under the block being written, or the toolbar in *Edit*   |
| Highlight text                            | Select in either editor, right-click, pick a colour                          |
| Move an entry                             | Drag & drop in the tree — the empty sidebar is the root                      |
| Complete a wiki-link                      | Type `[[` → <kbd>↑</kbd>/<kbd>↓</kbd> → <kbd>Enter</kbd> / <kbd>Tab</kbd>    |
| Switch theme                              | 🌙 / ☀️ in the sidebar                                                        |

A wiki-link that resolves to nothing is rendered as unresolved rather than
dropped; clicking it offers to create the missing note in the current folder and
opens it immediately.
