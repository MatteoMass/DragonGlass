
# Dragon Glass

[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.14+-3776AB?style=flat-square&logo=python&logoColor=white)](pyproject.toml)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Vue 3](https://img.shields.io/badge/Vue_3-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)](Dockerfile)


<p align="center">
  <img src="assets/dragon_glass.png" alt="Dragon Glass">
</p>



**Dragon Glass gives a folder of Markdown files a browser to be read in.**

Dragon Glass exists because **Obsidian is heavier than a folder of Markdown
files needs to be**; an editor, a whole vault format, a plugin ecosystem, and a desktop app to carry it all, when what was wanted was the tree, the links, the editor and the preview, and nothing underneath them. SilverBullet was tried
as the lighter alternative, but its interface never felt as intuitive or as
current as Obsidian's. **Dragon Glass is the middle point**: an interface as
modern and as easy to pick up as Obsidian's, on a system as light as
SilverBullet's — served instead of installed, a tree on the left, an editor
and a preview beside it, links between notes that behave like links, and
everything it writes is still a plain file when it is done.

It runs as **one process on your own machine**: a FastAPI service that reads and
writes the directory, and a Vue app the same service serves. **There is no
database, no account and no export step.** You can `git init` inside the hollow, point Syncthing at it, or open the same folder with another editor tomorrow.

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

Only `.md` files count as notes. The images belonging to a note `X.md` live in `X_images/`, in the same folder as the note, and follow it: renaming, moving or deleting the note takes the sidecar folder with it. The tree shows folders, notes and images (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`, `.bmp`); anything else on disk is ignored rather than hidden — it is simply not the app's business, and it stays where it is.

Because it is only files, a hollow can be versioned with Git, synchronised with anything, or copied elsewhere while the server is running.

An empty hollow (a fresh checkout, or a fresh volume in a container that has
never held one) is seeded with exactly the note above, `Welcome in Dragon
Glass.md`, so the tree is never blank on the first visit. Delete it, or edit it into something else: it does not come back once the hollow holds a note of its own.

## What happens to a note

A save is not a write. `PUT /notes/{path}` does four things, in this order because each one needs the last:

1. **The title claims the filename.** The first-level `# Heading` is compared
   with the name of the file. If they disagree the file is renamed to match the title, the `_images/` folder is renamed with it, and the image references in the body are rewritten to point at the new folder. A note is named by editing it, not by a dialog. If the target name is taken or is not a usable filename the rename is skipped and the content is saved as it stands; saving never fails because of a title.
2. **The bytes land**, at the path the step above settled on.
3. **The index is refreshed**, the flat list of every note in the hollow, which is what a `[[wiki-link]]` is resolved against.
4. **The Markdown is rendered**, server side, with the wiki-links resolved and the relative image paths rewritten towards `/hollow/...`.

The response carries the note back whole: `{path, raw, html, blocks}`, with the **new** path when step 1 moved it. The client replaces what it holds with what came back rather than guessing what the server did, which is why a rename that happens during a save never desynchronises the tree.

Rendering is server side on purpose. The client receives finished HTML and does no Markdown work at all, so the two panes — editor and preview — can never disagree about what a note means.

## Editing where you are reading

The whole note in a textarea is the right tool for rewriting a note, and the
wrong one for fixing a word. So the preview is editable in place: a click on a paragraph, a heading, a list or a code block opens that block — and only that block — as the Markdown it is written in, and leaving it renders it again.
<kbd>Esc</kbd> gives it back untouched. Under the block being written are the two things that are easier clicked than typed: ▦ writes a table skeleton on lines of its own, 🖼️ uploads an image into the note's `_images/` folder and writes the reference at the caret. Neither takes the focus away from what is being written.

That works because every note answer carries `blocks` beside `html`: the same note cut into the blocks it is written in, each with its own HTML and with the offsets it occupies in the source. Writing an edited block back is putting those characters between those two offsets — the blank lines around it, and every other block, are not touched. A block written empty is a block deleted; the empty space under the note adds one.

Nothing there saves anything. An edited block changes the buffer exactly as typing in the editor would, the dot in the toolbar lights, and the file hears about it on <kbd>Ctrl</kbd>/<kbd>Cmd</kbd> + <kbd>S</kbd>.

## Notes that point at each other

A folder of files is a filing cabinet; what makes it a hollow is that a note can name another one and mean it.

**Wiki-links** are written `[[Note name]]`, or `[[Note name|the text to show]]`. The name is resolved against the index of every note in the hollow, and a note of the same name **in the same folder** as the one being read wins — so a `Roadmap` linked from inside `Progetti/` is that project's roadmap, not the one three folders away.

Typing `[[` opens **autocompletion**: <kbd>↑</kbd>/<kbd>↓</kbd> to move, <kbd>Enter</kbd> or <kbd>Tab</kbd> to accept, <kbd>Esc</kbd> to dismiss.

A link that resolves to nothing is rendered as unresolved rather than dropped. Clicking it offers to create the missing note in the current folder and opens it immediately — which is the honest behaviour for a link to something you have not written yet.

**Images** are uploaded from the toolbar in edit mode: the file goes into the note's `_images/` folder and the `![name](path)` Markdown is inserted at the cursor. Names are sanitised and de-duplicated on the way in — `foto.png`,
`foto-1.png`, and so on — so an upload never overwrites what is already there.

**Highlighting** is a right-click on a selection: yellow, blue, green, or
remove. The selection is wrapped in `<mark class="hl-...">`; a different colour replaces the existing one and "transparent" unwraps it. It survives in the file, because it is just Markdown with a tag in it.

## Bringing notes in

**Import**, in the sidebar, takes a `.md` file or a `.zip` archive into the folder you are in. A `.md` is added as one note. A `.zip` is unpacked in place — folder structure and all, `*_images/` sidecars included — but only what is already a note or an image by the hollow's own conventions survives: everything else the archive holds is discarded rather than written to disk. Nothing already in the hollow is ever overwritten; a name that is taken gets `-1`, `-2`, and so on, the same as an image upload does.

The largest upload accepted is `server.max_import_bytes` (see [Configuration](#configuration)); a `.zip` unpacking past 200 MiB or 10,000 files is refused outright, the two limits guarding against an archive built to exhaust the server rather than to hold notes.

## Plugins

Dragon Glass ships with the hollow always on, and a small set of optional plugins that are off until switched on. The ⚙️ gear in the sidebar opens the settings panel, which lists every registered plugin with its own toggle;  turning one on or off takes effect immediately, for every tab open on the server, without a restart — the switch is read fresh on every request, not cached at startup.

A plugin that is off is not merely hidden: its API answers `404` for every one of its routes, the same as if they did not exist, so there is no way to reach a disabled plugin's data by calling its endpoints directly.

### DragonGlass Tutor

Turns a spreadsheet of exam-style questions into a quiz you take against the hollow, with each question optionally pointing back at the note it came from.

1. **Import** a `.csv` or `.xlsx` from the plugin's own view. The file is parsed and held in memory — nothing is written yet.
2. **Map its columns**: which one is the question, which ones are the answers (at least two), which one names the correct answer, and, optionally, which one is a reference. The correct-answer column is read leniently: the answer's own text, a letter (`A`, `B`, …) or a 1-based position name one answer; several of those together (`"C, D"`, `"B/D"`, or run together as `"CDE"`) name a multi-answer question.
3. A reference cell is resolved against the hollow's note index the same way a `[[wiki-link]]` is (by name, regardless of which folder holds it) so the spreadsheet only has to name a note, never its path. When a cell can name **more than one** source, ticking "a cell may name more than one reference" and giving the separator it is written with (`;` by default) splits it before each part is resolved on its own; a part that matches nothing is simply left out rather than failing the whole reference. If the shollow holds more than one note of the same name, a quiz's detail page can re-scope the search to one folder, subfolders included.
4. **Taking a quiz** offers three modes — sequential, shuffled, or a manual pick of exactly which questions — capped at however many of them you ask for. Every attempt is recorded (question count, correct count, when), so a quiz's detail page shows how many attempts it has had and the best and the last score.

Quiz sets and their attempts are persisted in `data/tutor.json` (`paths.tutor_file`); nothing about a quiz lives in the hollow itself.



## Requirements

- Python ≥ 3.14 and [Poetry](https://python-poetry.org/)
- Node.js ≥ 20 and npm — only to build the frontend

Docker needs neither: the image brings its own.

There is no API key and no `.env`. Dragon Glass has no secrets to keep, so everything configurable lives in [`dragonglass.yml`](dragonglass.yml), where every key is optional and every key is commented, see [Configuration](#configuration).

## Run

### Locally

```bash
./build_and_run.sh
```

That builds the frontend and then serves it together with the API on <http://127.0.0.1:8017> — the built app is mounted at `/`, so one process answers both. The interactive API documentation is at `/docs`, and `/redoc` beside it.

The script installs what is missing before it starts: the npm dependencies when `node_modules` is absent or older than the lock file, and the Poetry environment when the project has never been installed.

| Option          | What it does                                             |
| --------------- | -------------------------------------------------------- |
| `--no-build`    | Skip the frontend build and serve the current `dist/`.    |
| `--reload`      | Restart the backend when the Python sources change.       |
| `--port <n>`    | Serve on another port. Default `8017`.                    |
| `--host <addr>` | Bind elsewhere — `0.0.0.0` to accept from the network.     |
| `--help`        | Print the same, from the script itself.                   |

The address comes from `server.host` and `server.port` in `dragonglass.yml`, or from `DRAGONGLASS_HOST` and `DRAGONGLASS_PORT`; the flags win over both.

Without a build the service still starts and answers the API only, so `./build_and_run.sh --no-build` on a fresh checkout is an API-only server, not an error.

The hollow is `./data/root`, created on first start if it is not there.

### With Docker

```bash
docker compose up --build
```

Same thing on <http://localhost:8017>, with nothing installed on the host. [`Dockerfile`](Dockerfile) is the same two steps in two stages: node builds the frontend, python serves it, and nothing of node survives into the image that ships.

[`docker-compose.yml`](docker-compose.yml) mounts a named volume at `/app/data/root` so the notes outlive the container, and mounts `./dragonglass.yml` read-only so a setting can be changed with a restart instead of a rebuild. The container sets `DRAGONGLASS_HOLLOW_ROOT` itself, and a variable always wins over the file — so there is no mode to switch and nothing to edit before building.

To keep the hollow in a folder of the host instead of a named volume:

```bash
docker run -d -p 8017:8017 -v "$PWD/data/root:/app/data/root" dragon-glass
```

The frontend build is also available on its own, writing into the checkout so a local run can serve it:

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

Vite proxies `/tree`, `/notes`, `/folders`, `/entries`, `/images` and `/hollow` to `http://127.0.0.1:8000`, so the app uses the same relative URLs it does when the backend serves it. Point the proxy elsewhere with `DRAGONGLASS_API_URL`. A frontend that calls the API directly instead of through the proxy needs its origin in `server.cors_origins`; through the proxy it needs nothing.

## Configuration

Three layers decide every setting, and they win in this order:

1. the defaults in [`src/config.py`](src/config.py), which is what a checkout with nothing configured runs on;
2. [`dragonglass.yml`](dragonglass.yml) at the root of the project — or wherever `DRAGONGLASS_CONFIG_FILE` says — which is where an installation writes down what it wants differently;
3. the environment, which overrules both, so a container passing its own values keeps them whatever the file says.

The file is read once, when the server starts, and a missing file is not an error. A file that is there and unparseable is: the service refuses to start rather than run on settings nobody asked for. A single value that cannot be read is reported and the layer below answers instead.

| Section    | What you can change                                                                                                                                            |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `paths`    | Where the hollow is (`hollow_root`, created if absent), where the built frontend is looked for (`frontend_dist`), and where the plugins' own state is persisted (`settings_file`, `tutor_file`). |
| `server`   | Host and port, the origins allowed to call the API from a browser, the largest image and import accepted.                                                          |
| `logging`  | Level of the root logger.                                                                                                                                          |
| `hollow`    | Which extension is a note, the suffix of the sidecar image folders, which image extensions appear in the tree, whether a save is allowed to rename the file after its title. |
| `markdown` | Which Markdown extensions are enabled, and whether wiki-links, image-path rewriting and task lists are installed at all.                                             |

Every key in `dragonglass.yml` is documented in place, with its default and the
environment variable that overrules it — `DRAGONGLASS_HOLLOW_ROOT`,
`DRAGONGLASS_PORT`, `DRAGONGLASS_SYNC_TITLE`, and so on for all of them.

Relative paths are read against the directory the server was started in, which
`build_and_run.sh` makes the root of the project.

## What it does not do

Dragon Glass is meant for one person on a local network. Before putting it
anywhere else:

- **There is no authentication.** Whoever reaches the port can read, edit and delete every note. Put it behind a reverse proxy that authenticates if it has to be reachable from outside.
- **There is no concurrency control.** The last save wins. Two people editing the same note is not a case the app has an answer for.
- **There is no bin.** `DELETE` removes files from disk, folders included and recursively. Version the hollow with Git, or keep backups.
- **Inline HTML is allowed.** Markdown is rendered without sanitisation — which is what makes `<mark>` highlighting possible, and also means a note's content runs as HTML. Do not open a hollow you did not write.
- **Path traversal is blocked**, in one place: `hollow_connector/paths.py`. Every path is resolved and checked against the hollow root before anything is touched.

## License

[MIT](LICENSE).
