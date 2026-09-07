
# Dragon Glass

[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.14+-3776AB?style=flat-square&logo=python&logoColor=white)](pyproject.toml)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Vue 3](https://img.shields.io/badge/Vue_3-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)](Dockerfile)


<p align="center">
  <img src="src/frontend/public/favicon.png" width="96" height="96" alt="Dragon Glass">
</p>



Dragon Glass gives a folder of Markdown files a browser to be read in.

Notes outlive the tools that hold them. An app with a database owns them until
the day it stops being maintained, and getting them out again is a project of
its own. Dragon Glass never takes possession: it points at a directory of `.md`
files on your disk and serves it — a tree on the left, an editor and a preview
beside it, links between notes that behave like links — and everything it
writes is still a plain file when it is done.

It runs as one process on your own machine: a FastAPI service that reads and
writes the directory, and a Vue app the same service serves. There is no
database, no account and no export step. You can `git init` inside the hollow,
point Syncthing at it, or open the same folder with another editor tomorrow.
Nothing leaves the machine, ever — there is nothing in Dragon Glass that talks
to a network.

## What an Hollow is

A hollow is an ordinary directory. Dragon Glass adds conventions to it, not
structure:

```
data/root/
├── Welcome in Dragon Glass.md
├── Project/
│   ├── Roadmap.md
│   └── Roadmap_images/
│       └── diagram.png
└── Test.md
```

Only `.md` files count as notes. The images belonging to a note `X.md` live in
`X_images/`, in the same folder as the note, and follow it: renaming, moving or
deleting the note takes the sidecar folder with it. The tree shows folders,
notes and images (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`, `.bmp`);
anything else on disk is ignored rather than hidden — it is simply not the
app's business, and it stays where it is.

Because it is only files, a hollow can be versioned with Git, synchronised with
anything, or copied elsewhere while the server is running.

An empty hollow — a fresh checkout, or a fresh volume in a container that has
never held one — is seeded with exactly the note above, `Welcome in Dragon
Glass.md`, so the tree is never blank on the first visit. Delete it, or edit it
into something else: it does not come back once the hollow holds a note of its
own.

## What happens to a note

A save is not a write. `PUT /notes/{path}` does four things, in this order
because each one needs the last:

1. **The title claims the filename.** The first-level `# Heading` is compared
   with the name of the file. If they disagree the file is renamed to match the
   title, the `_images/` folder is renamed with it, and the image references in
   the body are rewritten to point at the new folder. A note is named by
   editing it, not by a dialog. If the target name is taken or is not a usable
   filename the rename is skipped and the content is saved as it stands —
   saving never fails because of a title.
2. **The bytes land**, at the path the step above settled on.
3. **The index is refreshed** — the flat list of every note in the hollow, which
   is what a `[[wiki-link]]` is resolved against.
4. **The Markdown is rendered**, server side, with the wiki-links resolved and
   the relative image paths rewritten towards `/hollow/...`.

The response carries the note back whole: `{path, raw, html, blocks}`, with the
**new** path when step 1 moved it. The client replaces what it holds with what
came back rather than guessing what the server did, which is why a rename that
happens during a save never desynchronises the tree.

Rendering is server side on purpose. The client receives finished HTML and does
no Markdown work at all, so the two panes — editor and preview — can never
disagree about what a note means.

## Editing where you are reading

The whole note in a textarea is the right tool for rewriting a note, and the
wrong one for fixing a word. So the preview is editable in place: a click on a
paragraph, a heading, a list or a code block opens that block — and only that
block — as the Markdown it is written in, and leaving it renders it again.
<kbd>Esc</kbd> gives it back untouched. Under the block being written are the
two things that are easier clicked than typed: ▦ writes a table skeleton on
lines of its own, 🖼️ uploads an image into the note's `_images/` folder and
writes the reference at the caret. Neither takes the focus away from what is
being written.

That works because every note answer carries `blocks` beside `html`: the same
note cut into the blocks it is written in, each with its own HTML and with the
offsets it occupies in the source. Writing an edited block back is putting
those characters between those two offsets — the blank lines around it, and
every other block, are not touched. A block written empty is a block deleted;
the empty space under the note adds one.

Nothing there saves anything. An edited block changes the buffer exactly as
typing in the editor would, the dot in the toolbar lights, and the file hears
about it on <kbd>Ctrl</kbd>/<kbd>Cmd</kbd> + <kbd>S</kbd>.

## Notes that point at each other

A folder of files is a filing cabinet; what makes it a hollow is that a note can
name another one and mean it.

**Wiki-links** are written `[[Note name]]`, or `[[Note name|the text to show]]`.
The name is resolved against the index of every note in the hollow, and a note
of the same name **in the same folder** as the one being read wins — so a
`Roadmap` linked from inside `Progetti/` is that project's roadmap, not the one
three folders away.

Typing `[[` opens **autocompletion**: <kbd>↑</kbd>/<kbd>↓</kbd> to move,
<kbd>Enter</kbd> or <kbd>Tab</kbd> to accept, <kbd>Esc</kbd> to dismiss.

A link that resolves to nothing is rendered as unresolved rather than dropped.
Clicking it offers to create the missing note in the current folder and opens
it immediately — which is the honest behaviour for a link to something you have
not written yet.

**Images** are uploaded from the toolbar in edit mode: the file goes into the
note's `_images/` folder and the `![name](path)` Markdown is inserted at the
cursor. Names are sanitised and de-duplicated on the way in — `foto.png`,
`foto-1.png`, and so on — so an upload never overwrites what is already there.

**Highlighting** is a right-click on a selection: yellow, blue, green, or
remove. The selection is wrapped in `<mark class="hl-...">`; a different colour
replaces the existing one and "transparent" unwraps it. It survives in the
file, because it is just Markdown with a tag in it.

## Bringing notes in

**Import**, in the sidebar, takes a `.md` file or a `.zip` archive into the
folder you are in. A `.md` is added as one note. A `.zip` is unpacked in
place — folder structure and all, `*_images/` sidecars included — but only
what is already a note or an image by the hollow's own conventions survives:
everything else the archive holds (a `.DS_Store`, a `README`, whatever else a
real export drags along) is discarded rather than written to disk. Nothing
already in the hollow is ever overwritten; a name that is taken gets `-1`,
`-2`, and so on, the same as an image upload does.

The largest upload accepted is `server.max_import_bytes` (see
[Configuration](#configuration)); a `.zip` unpacking past 200 MiB or 10,000
files is refused outright, the two limits guarding against an archive built to
exhaust the server rather than to hold notes.

## Requirements

- Python ≥ 3.14 and [Poetry](https://python-poetry.org/)
- Node.js ≥ 20 and npm — only to build the frontend

Docker needs neither: the image brings its own.

There is no API key and no `.env`. Dragon Glass has no secrets to keep, so
everything configurable lives in [`dragonglass.yml`](dragonglass.yml), where
every key is optional and every key is commented — see
[Configuration](#configuration).

## Run

### Locally

```bash
./build_and_run.sh
```

That builds the frontend and then serves it together with the API on
<http://127.0.0.1:8017> — the built app is mounted at `/`, so one process
answers both. The interactive API documentation is at `/docs`, and `/redoc`
beside it.

The script installs what is missing before it starts: the npm dependencies when
`node_modules` is absent or older than the lock file, and the Poetry
environment when the project has never been installed.

| Option          | What it does                                             |
| --------------- | -------------------------------------------------------- |
| `--no-build`    | Skip the frontend build and serve the current `dist/`.    |
| `--reload`      | Restart the backend when the Python sources change.       |
| `--port <n>`    | Serve on another port. Default `8017`.                    |
| `--host <addr>` | Bind elsewhere — `0.0.0.0` to accept from the network.     |
| `--help`        | Print the same, from the script itself.                   |

The address comes from `server.host` and `server.port` in `dragonglass.yml`, or
from `DRAGONGLASS_HOST` and `DRAGONGLASS_PORT`; the flags win over both.

Without a build the service still starts and answers the API only, so
`./build_and_run.sh --no-build` on a fresh checkout is an API-only server, not
an error.

The hollow is `./data/root`, created on first start if it is not there.

### With Docker

```bash
docker compose up --build
```

Same thing on <http://localhost:8017>, with nothing installed on the host.
[`Dockerfile`](Dockerfile) is the same two steps in two stages: node builds the
frontend, python serves it, and nothing of node survives into the image that
ships.

[`docker-compose.yml`](docker-compose.yml) mounts a named volume at
`/app/data/root` so the notes outlive the container, and mounts
`./dragonglass.yml` read-only so a setting can be changed with a restart
instead of a rebuild. The container sets `DRAGONGLASS_HOLLOW_ROOT` itself, and a
variable always wins over the file — so there is no mode to switch and nothing
to edit before building.

To keep the hollow in a folder of the host instead of a named volume:

```bash
docker run -d -p 8017:8017 -v "$PWD/data/root:/app/data/root" dragon-glass
```

The frontend build is also available on its own, writing into the checkout so a
local run can serve it:

```bash
docker compose --profile build run --rm frontend-build   # → src/frontend/dist
./build_and_run.sh --no-build
```

### By hand

The script does nothing that cannot be done in four commands:

```bash
npm --prefix src/frontend ci
npm --prefix src/frontend run build
poetry install
poetry run uvicorn backend:app --app-dir src --port 8017
```

## Development

With the frontend changing, run Vite next to the API instead of rebuilding:

```bash
./build_and_run.sh --no-build --reload --port 8000   # the API, restarting
npm --prefix src/frontend run dev                    # http://localhost:5173
```

Vite proxies `/tree`, `/notes`, `/folders`, `/entries`, `/images` and `/hollow`
to `http://127.0.0.1:8000`, so the app uses the same relative URLs it does when
the backend serves it. Point the proxy elsewhere with `DRAGONGLASS_API_URL`. A
frontend that calls the API directly instead of through the proxy needs its
origin in `server.cors_origins`; through the proxy it needs nothing.

## How it is put together

Four layers, from the outside in.

### Connectors — `src/connectors/`

Everything that talks to something outside the process, behind an interface
that hides which something it is. Here that is exactly one thing: the disk.

**`hollow_connector/`** is the only code in the project that touches the
filesystem, and the only thing that knows a hollow is a directory at all.
`HollowConnector` is the whole surface; the pieces behind it are:

| Module           | What it owns                                                                                              |
| ---------------- | --------------------------------------------------------------------------------------------------------- |
| `connector.py`   | `HollowConnector`: the façade the rest of the code holds, opened once for the life of the process.           |
| `paths.py`       | The security boundary. Every path arriving from outside is resolved and checked against the hollow root before anything is opened; one that would escape raises `InvalidPath` and never reaches the disk. |
| `tree.py`        | Walking the hollow into `Entry` nodes — folders, notes, images — with the ignore rules and the sort order.   |
| `notes.py`       | Reading and writing a note, creating one with its `# title`, renaming, moving, deleting.                    |
| `images.py`      | The `<note>_images/` sidecars: upload, name sanitising, de-duplication, and following the note they belong to on every rename, move and delete. |
| `imports.py`     | Bringing a `.md` note or a `.zip` archive in from an upload, keeping only what is already a note or an image and discarding the rest. |
| `index.py`       | The flat index of every note in the hollow — name, folder, path — which is what wiki-links resolve against.  |
| `types.py`       | `Entry`, `EntryKind`, `Note`, `NoteIndex`, and the errors: `EntryNotFound`, `EntryAlreadyExists`, `InvalidName`, `InvalidPath`, `InvalidMove`, `NotANote`, `HollowError`. |

Errors are named for what is missing rather than suffixed `…Error`, and they
are the vocabulary the API translates into status codes.

### Core — `src/core/`

The business logic: from a note on disk to what a reader sees. It knows nothing
of HTTP and nothing of where the bytes came from.

`MarkdownRenderer` is the whole of it seen from outside, and the only thing an
entrypoint needs to know. Inside:

| Module                    | What it does                                                                                      |
| ------------------------- | ------------------------------------------------------------------------------------------------- |
| `renderer.py`             | `MarkdownRenderer`: builds the `markdown.Markdown` instance once and renders a note against an index — whole, and block by block. Enabled extensions: `fenced_code`, `tables`, `toc`, `sane_lists`, plus the three below. |
| `blocks.py`               | Where one block of a note ends and the next begins: a blank line, unless it is inside a fenced code block. Each block remembers the offsets it occupies, which is what lets one of them be rewritten in place. |
| `extensions/wikilinks.py` | The `[[…]]` inline pattern: resolution against the index, same-folder preference, and the unresolved class the frontend styles differently. |
| `extensions/images.py`    | Rewrites relative image paths towards the `/hollow/...` route. Absolute URLs, explicit protocols and `data:` URIs are left exactly as written. |
| `extensions/tasklists.py` | Turns `- [x]` and `- [ ]` list items into checkboxes. Markdown has no task lists of its own, so without this the brackets stay in the text. The boxes are rendered disabled: a note is edited as Markdown, not by ticking its preview. |
| `titles.py`               | The title↔filename sync, and the rewriting of image references that a rename implies. Returns the path the note ended up at. |
| `types.py`                | `RenderedNote`, `RenderedBlock`, `SourceBlock`, `LinkTarget`, and what crosses the layer boundary.  |

### Backend — `src/backend.py`, `src/api/`, `src/config.py`

`backend.py` only assembles: it opens the hollow connector and the renderer for
the life of the process, registers the routers, installs CORS when it is
configured, and translates connector errors into status codes — so no endpoint
has to.

| Raised                                  | Answered            |
| --------------------------------------- | ------------------- |
| `EntryNotFound`, `NotANote`             | `404`                |
| `EntryAlreadyExists`                    | `409`                |
| `InvalidName`, `InvalidPath`, `InvalidMove` | `400`            |
| any other `HollowError`                  | `500`                |

The reason is always in `detail`.

The endpoints themselves are in `api/`, one module per resource. Every `{path}`
is relative to the hollow root and URL-encoded per segment.

| Router                     | What it is for                                                                                                                  |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `GET /tree`                | The whole tree in one response: `{kind: folder\|note\|image, name, path, children?}`. Folders are few and human-made, so nesting them client side costs less than one request per level. |
| `GET /notes/{path}`        | A note: `{path, raw, html, blocks}`, the HTML already rendered and the note also cut into its blocks.                              |
| `PUT /notes/{path}`        | Save it (`{content}`). Runs the four steps of [What happens to a note](#what-happens-to-a-note) and answers with the **new** path.   |
| `POST /notes`              | Create one (`{parent, name}`) — `.md` is appended if missing and the file is born with `# <title>`.                                 |
| `POST /notes/{path}/render`| Render Markdown that was never saved (`{content}`), as the note at `{path}`. Same answer as a read; nothing is written. It is what the preview asks for after a block was edited in place. |
| `POST /folders`            | Create a folder (`{parent, name}`).                                                                                                |
| `PATCH /entries/{path}`    | Rename a note or a folder (`{name}`).                                                                                              |
| `POST /entries/{path}/move`| Move it (`{parent}`); an empty `parent` is the root. A folder into itself or into one of its own descendants is a `400`.            |
| `DELETE /entries/{path}`   | Delete a note, or a folder and everything under it, together with the matching `*_images/`.                                        |
| `POST /images/{path}`      | Upload an image for a note (`multipart/form-data`, field `image`); answers `{name, path}` ready to be written into the Markdown.    |
| `POST /imports`            | Import a `.md` note, or unpack a `.zip` (`multipart/form-data`, fields `parent` and `file`), keeping only the notes and images inside it; answers `{created, skipped}`. |
| `GET /hollow/{...}`         | The hollow's static files — the images the notes reference. Mounted read-only.                                                      |
| `GET /`                    | The built frontend.                                                                                                                |

`api/dependencies.py` is what every router asks for, and the only place the
application state is reached:

```python
Hollow = Annotated[HollowConnector, Depends(get_hollow)]
Renderer = Annotated[MarkdownRenderer, Depends(get_renderer)]
```

`api/schemas.py` holds the payloads — `NoteOut`, `NoteUpdate`, `NoteCreate`,
`FolderCreate`, `EntryOut`, `EntryRename`, `EntryMove`, `ImageOut`, `TreeNode` —
and nothing else. `api/frontend.py` mounts `dist/` at `/` when there is one, and
that mount goes last, after every router, because a mount at `/` catches
whatever the routes above it did not.

`config.py` assembles the settings once, when it is imported, out of the three
layers described below.

### Frontend — `src/frontend/`

Vue 3, Vite and TypeScript. Two panes: the file tree on the left, the selected
note on the right — a toolbar, and the note itself in one of its two modes,
**Preview** or **Edit**. It has its own [README](src/frontend/README.md).

| Path                  | What lives there                                                                                                            |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `src/api/`            | The only place that talks HTTP — `client.ts` and the payload types.                                                            |
| `src/composables/`    | The shared state: `useHollow` (tree, selection, CRUD), `useEditor` (buffer, dirty flag, save, the unsaved-changes guard), `useBlocks` (the blocks of the preview and the one being written in place), `useWikiLinks` (the `[[` autocomplete), `useContextMenu`, `useConfirm`, `useTheme`. |
| `src/components/`     | `Sidebar.vue`, `FileTree.vue` and the recursive `TreeNode.vue`, `NoteToolbar.vue`, `NoteEditor.vue`, `NotePreview.vue`, `BlockEditor.vue`, `ContextMenu.vue`, `HighlightMenu.vue`, `LinkAutocomplete.vue`, `RenameField.vue`, `ConfirmDialog.vue`. |
| `src/styles/main.css` | The tokens for both themes, the highlight colours, the components.                                                             |

The tree creates files and folders from the toolbar or the context menu,
renames, deletes (folders recursively), sorts by name (A-Z / Z-A) from the
context menu — which a right-click opens anywhere in the sidebar, not only over
an entry — and moves by drag & drop: dropping on the empty sidebar returns an
entry to the root, and dragging a folder into itself or into one of its
descendants is refused before the request is made.

Every question the app asks is a native `<dialog>` of its own — naming a new
note, confirming a deletion — so nothing reaches for `window.prompt` or
`window.confirm`.

The editor saves with the button or <kbd>Ctrl</kbd>/<kbd>Cmd</kbd> +
<kbd>S</kbd>, inserts a ready-made table skeleton at the cursor, and asks for
confirmation before leaving a note with unsaved changes. The theme toggle is in
the sidebar; the choice is kept in `localStorage` and, on a first visit,
follows `prefers-color-scheme`.

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

The build lands in `dist/`, which the API mounts at `/` when it is there — so a
checkout that has never run `npm run build` still starts, and answers the API
alone.

## Configuration

Three layers decide every setting, and they win in this order:

1. the defaults in [`src/config.py`](src/config.py), which is what a checkout
   with nothing configured runs on;
2. [`dragonglass.yml`](dragonglass.yml) at the root of the project — or
   wherever `DRAGONGLASS_CONFIG_FILE` says — which is where an installation
   writes down what it wants differently;
3. the environment, which overrules both, so a container passing its own values
   keeps them whatever the file says.

The file is read once, when the server starts, and a missing file is not an
error. A file that is there and unparseable is: the service refuses to start
rather than run on settings nobody asked for. A single value that cannot be
read is reported and the layer below answers instead.

| Section    | What you can change                                                                                                                                            |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `paths`    | Where the hollow is (`hollow_root`, created if absent) and where the built frontend is looked for (`frontend_dist`).                                                 |
| `server`   | Host and port, the origins allowed to call the API from a browser, the largest image and import accepted.                                                          |
| `logging`  | Level of the root logger.                                                                                                                                          |
| `hollow`    | Which extension is a note, the suffix of the sidecar image folders, which image extensions appear in the tree, whether a save is allowed to rename the file after its title. |
| `markdown` | Which Markdown extensions are enabled, and whether wiki-links, image-path rewriting and task lists are installed at all.                                             |

Every key in `dragonglass.yml` is documented in place, with its default and the
environment variable that overrules it — `DRAGONGLASS_HOLLOW_ROOT`,
`DRAGONGLASS_PORT`, `DRAGONGLASS_SYNC_TITLE`, and so on for all of them.

Relative paths are read against the directory the server was started in, which
`build_and_run.sh` makes the root of the project.

## Layout

| Path                       | What lives there                                                |
| -------------------------- | ---------------------------------------------------------------- |
| `src/backend.py`           | Assembles the app: routers, errors, lifespan.                     |
| `src/config.py`            | The settings, and the three layers behind them.                   |
| `src/api/`                 | The endpoints and their payloads.                                 |
| `src/connectors/`          | The hollow on disk, behind one interface.                          |
| `src/core/`                | Rendering, wiki-links, the title sync.                            |
| `src/frontend/`            | The Vue app — see its own [README](src/frontend/README.md).       |
| `dragonglass.yml`          | Every setting, commented, with its environment variable.          |
| `build_and_run.sh`         | Build the frontend, then serve everything.                        |
| `Dockerfile`               | The same, in two stages.                                          |
| `docker-compose.yml`       | The image, its volume and its config mount.                       |
| `data/root/`               | The default hollow. Not in git.                                    |

## Where the previous version's code went

The first Dragon Glass was three modules and a folder of static files. Nothing
of what it did is gone; it is spread across the layers that now separate
filesystem from meaning from transport.

| Was                        | Is now                                                                                                          |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `app/storage.py` — I/O     | `src/connectors/hollow_connector/` — tree, notes, images, index, and the path check that guards all of them.        |
| `app/storage.py` — Markdown| `src/core/` — the renderer and the two extensions, with no filesystem underneath them.                             |
| `app/storage.py` — title sync | `src/core/titles.py`, called by the `/notes` router between the write and the render.                          |
| `app/main.py`              | `src/backend.py` (assembly and error translation) + `src/api/*.py` (one module per resource).                      |
| `app/config.py` + `config.yaml` `storage.mode` | `src/config.py` + `dragonglass.yml`. The mode switch is gone: Docker sets `DRAGONGLASS_HOLLOW_ROOT` and the environment wins over the file. |
| `app/static/app.js`        | `src/frontend/src/composables/` (state) and `src/components/` (the views).                                         |
| `app/static/style.css`     | `src/frontend/src/styles/main.css`.                                                                                |
| `/api/file/...`, `/api/…`  | `/notes/...`, `/tree`, `/folders`, `/entries`, `/images` — resource routers, no `/api` prefix.                     |

## What it does not do

Dragon Glass is meant for one person on a local network. Before putting it
anywhere else:

- **There is no authentication.** Whoever reaches the port can read, edit and
  delete every note. Put it behind a reverse proxy that authenticates if it has
  to be reachable from outside.
- **There is no concurrency control.** The last save wins. Two people editing
  the same note is not a case the app has an answer for.
- **There is no bin.** `DELETE` removes files from disk, folders included and
  recursively. Version the hollow with Git, or keep backups.
- **Inline HTML is allowed.** Markdown is rendered without sanitisation — which
  is what makes `<mark>` highlighting possible, and also means a note's content
  runs as HTML. Do not open a hollow you did not write.
- **Path traversal is blocked**, in one place: `hollow_connector/paths.py`. Every
  path is resolved and checked against the hollow root before anything is
  touched.

## License

[MIT](LICENSE).
