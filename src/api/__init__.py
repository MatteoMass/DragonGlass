"""The endpoints and their payloads, one module per resource."""

from . import entries, folders, frontend, images, imports, notes, tree

ROUTERS = (tree.router, notes.router, folders.router, entries.router, images.router, imports.router)

__all__ = ["ROUTERS", "entries", "folders", "frontend", "images", "imports", "notes", "tree"]
