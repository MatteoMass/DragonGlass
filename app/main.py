from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import load_storage_config
from .storage import (
    EntryAlreadyExistsError,
    EntryNotFoundError,
    InvalidNameError,
    MarkdownStorage,
    PathOutsideRootError,
)

storage_config = load_storage_config()
storage = MarkdownStorage(storage_config.root)

app = FastAPI(title="Dragon Glass")

STATIC_DIR = Path(__file__).resolve().parent / "static"


class FileContent(BaseModel):
    content: str


class CreateEntryRequest(BaseModel):
    parent: str = ""
    name: str


class RenameEntryRequest(BaseModel):
    name: str


class MoveEntryRequest(BaseModel):
    path: str
    parent: str = ""


def _build_path(parent: str, name: str) -> str:
    parent = parent.strip().strip("/")
    return f"{parent}/{name}" if parent else name


def _dirname(file_path: str) -> str:
    parent, _, _ = file_path.rpartition("/")
    return parent


@app.get("/api/tree")
def get_tree():
    return storage.list_tree()


@app.get("/api/file/{file_path:path}")
def get_file(file_path: str):
    try:
        raw = storage.read(file_path)
    except PathOutsideRootError:
        raise HTTPException(status_code=400, detail="Percorso non valido")
    except EntryNotFoundError:
        raise HTTPException(status_code=404, detail="File non trovato")
    return {"path": file_path, "raw": raw, "html": storage.render_html(raw, _dirname(file_path))}


@app.put("/api/file/{file_path:path}")
def save_file(file_path: str, body: FileContent):
    if not file_path.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="Sono supportati solo file .md")
    try:
        new_path, new_content = storage.sync_title(file_path, body.content)
        storage.write(new_path, new_content)
    except PathOutsideRootError:
        raise HTTPException(status_code=400, detail="Percorso non valido")
    return {
        "path": new_path,
        "raw": new_content,
        "html": storage.render_html(new_content, _dirname(new_path)),
    }


@app.post("/api/images/{file_path:path}")
async def upload_image(file_path: str, image: UploadFile = File(...)):
    if not file_path.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="Percorso file non valido")

    data = await image.read()
    try:
        relative_image_path = storage.save_image(file_path, image.filename or "image", data)
    except PathOutsideRootError:
        raise HTTPException(status_code=400, detail="Percorso non valido")
    return {"name": image.filename or "image", "path": relative_image_path}


@app.post("/api/files")
def create_file(body: CreateEntryRequest):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Il nome del file non puo' essere vuoto")
    if not name.lower().endswith(".md"):
        name = f"{name}.md"

    relative_path = _build_path(body.parent, name)
    title = name[: -len(".md")]
    try:
        storage.create_file(relative_path, content=f"# {title}\n\n")
    except PathOutsideRootError:
        raise HTTPException(status_code=400, detail="Percorso non valido")
    except EntryAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Esiste gia' un file con questo nome")
    return {"type": "file", "name": name, "path": relative_path}


@app.post("/api/folders")
def create_folder(body: CreateEntryRequest):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Il nome della cartella non puo' essere vuoto")

    relative_path = _build_path(body.parent, name)
    try:
        storage.create_folder(relative_path)
    except PathOutsideRootError:
        raise HTTPException(status_code=400, detail="Percorso non valido")
    except EntryAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Esiste gia' una cartella con questo nome")
    return {"type": "folder", "name": name, "path": relative_path, "children": []}


@app.patch("/api/entries/{entry_path:path}")
def rename_entry(entry_path: str, body: RenameEntryRequest):
    try:
        new_path = storage.rename(entry_path, body.name.strip())
    except PathOutsideRootError:
        raise HTTPException(status_code=400, detail="Percorso non valido")
    except InvalidNameError:
        raise HTTPException(status_code=400, detail="Nome non valido")
    except EntryNotFoundError:
        raise HTTPException(status_code=404, detail="Elemento non trovato")
    except EntryAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Esiste gia' un elemento con questo nome")
    return {"path": new_path, "name": new_path.rsplit("/", 1)[-1]}


@app.post("/api/move")
def move_entry(body: MoveEntryRequest):
    try:
        new_path = storage.move(body.path, body.parent)
    except PathOutsideRootError:
        raise HTTPException(status_code=400, detail="Percorso non valido")
    except InvalidNameError:
        raise HTTPException(status_code=400, detail="Spostamento non consentito")
    except EntryNotFoundError:
        raise HTTPException(status_code=404, detail="Elemento o destinazione non trovati")
    except EntryAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Esiste gia' un elemento con questo nome nella destinazione")
    return {"path": new_path, "name": new_path.rsplit("/", 1)[-1]}


@app.delete("/api/entries/{entry_path:path}")
def delete_entry(entry_path: str):
    try:
        storage.delete(entry_path)
    except PathOutsideRootError:
        raise HTTPException(status_code=400, detail="Percorso non valido")
    except InvalidNameError:
        raise HTTPException(status_code=400, detail="Operazione non consentita")
    except EntryNotFoundError:
        raise HTTPException(status_code=404, detail="Elemento non trovato")
    return {"status": "ok"}


app.mount("/vault", StaticFiles(directory=storage.root), name="vault")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
