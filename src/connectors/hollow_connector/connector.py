"""The façade the rest of the project holds.

``HollowConnector`` is opened once for the life of the process and is the only
thing outside this package that knows a hollow exists at all. Nothing above it
knows the hollow is a directory.
"""

from __future__ import annotations

import logging
from pathlib import Path

from . import images, imports, index, notes, tree
from .paths import PathResolver
from .types import Entry, ImportResult, Note, NoteIndex, UploadedImage, HollowConfig

logger = logging.getLogger(__name__)


class HollowConnector:
    """Read and write access to one hollow on disk.

    Every method takes hollow-relative POSIX paths and returns them, so no caller
    ever holds an absolute path or learns where the hollow lives.
    """

    def __init__(self, root: Path, config: HollowConfig | None = None) -> None:
        """Open the connector on a hollow, creating the directory when absent.

        Args:
            root: The directory holding the hollow.
            config: The conventions to apply. Defaults to the standard ones.

        Raises:
            InvalidPath: The root exists and is not a directory.
        """
        self._config = config or HollowConfig()
        self._paths = PathResolver(root)
        logger.info("Hollow opened at %s", self._paths.root)
        if not any(self._paths.root.iterdir()):
            notes.seed_welcome(self._paths, self._config)

    @property
    def root(self) -> Path:
        """The absolute path of the hollow root."""
        return self._paths.root

    @property
    def config(self) -> HollowConfig:
        """The conventions this hollow is read with."""
        return self._config

    def tree(self, path: str = "") -> tuple[Entry, ...]:
        """The nodes below a folder, folders first and then files by name.

        Args:
            path: The hollow-relative folder to walk. Empty is the root.

        Returns:
            The whole subtree, with folders carrying their own children.
        """
        return tree.walk(self._paths, self._config, path)

    def index(self) -> NoteIndex:
        """The flat index of every note in the hollow, freshly built."""
        return index.build(self._paths, self._config)

    def read_note(self, path: str) -> Note:
        """Read one note. See ``notes.read``."""
        return notes.read(self._paths, self._config, path)

    def write_note(self, path: str, content: str) -> Note:
        """Write one note. See ``notes.write``."""
        return notes.write(self._paths, self._config, path, content)

    def create_note(self, parent: str, name: str) -> Note:
        """Create one note, born with its title. See ``notes.create``."""
        return notes.create(self._paths, self._config, parent, name)

    def create_folder(self, parent: str, name: str) -> str:
        """Create one folder. See ``notes.create_folder``."""
        return notes.create_folder(self._paths, parent, name)

    def rename_entry(self, path: str, name: str) -> str:
        """Rename a note or a folder in place. See ``notes.rename``."""
        return notes.rename(self._paths, self._config, path, name)

    def move_entry(self, path: str, parent: str) -> str:
        """Move a note or a folder elsewhere. See ``notes.move``."""
        return notes.move(self._paths, self._config, path, parent)

    def delete_entry(self, path: str) -> None:
        """Delete a note, or a folder and all it holds. See ``notes.delete``."""
        notes.delete(self._paths, self._config, path)

    def store_image(self, note_path: str, filename: str, content: bytes) -> UploadedImage:
        """Put an image in a note's sidecar folder. See ``images.store``."""
        return images.store(self._paths, self._config, note_path, filename, content)

    def import_upload(self, parent: str, filename: str, content: bytes) -> ImportResult:
        """Import a note, or unpack a ``.zip`` of notes and images. See ``imports.run``."""
        return imports.run(self._paths, self._config, parent, filename, content)

    def images_folder(self, note_path: str) -> str:
        """The hollow-relative sidecar folder of a note, whether or not it exists."""
        return images.relative_folder_for(self._paths, self._config, note_path)

    def exists(self, path: str) -> bool:
        """Whether anything is at a hollow-relative path."""
        from .types import InvalidPath

        try:
            return self._paths.resolve(path).exists()
        except InvalidPath:
            return False
