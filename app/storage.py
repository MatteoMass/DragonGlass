from __future__ import annotations

import re
import shutil
import xml.etree.ElementTree as etree
from pathlib import Path
from typing import Any
from urllib.parse import quote

import markdown as md_lib
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from markdown.treeprocessors import Treeprocessor

MARKDOWN_EXTENSIONS = ["fenced_code", "tables", "toc", "sane_lists"]
IMAGE_DIR_SUFFIX = "_images"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
EXTERNAL_SRC_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*:)?//|^/|^data:")
INVALID_FILENAME_CHARS_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
H1_TITLE_RE = re.compile(r"(?m)^#[ \t]+(.+?)[ \t]*$")


def _note_dir_and_stem(relative_path: str) -> tuple[str, str]:
    posix_path = relative_path.replace("\\", "/")
    parent, _, filename = posix_path.rpartition("/")
    stem = filename[: -len(".md")] if filename.lower().endswith(".md") else filename
    return parent, stem


def extract_h1_title(content: str) -> str | None:
    match = H1_TITLE_RE.search(content)
    if not match:
        return None
    title = INVALID_FILENAME_CHARS_RE.sub(" ", match.group(1))
    title = re.sub(r"\s+", " ", title).strip().rstrip(". ")
    return title or None


def _image_dir_path(parent: str, stem: str) -> str:
    name = f"{stem}{IMAGE_DIR_SUFFIX}"
    return f"{parent}/{name}" if parent else name


class _ImagePathTreeprocessor(Treeprocessor):
    def __init__(self, md, base_dir: str):
        super().__init__(md)
        self.base_dir = base_dir

    def run(self, root):
        for img in root.iter("img"):
            src = img.get("src", "")
            if not src or EXTERNAL_SRC_RE.match(src):
                continue
            prefix = f"/vault/{quote(self.base_dir, safe='/')}/" if self.base_dir else "/vault/"
            img.set("src", prefix + quote(src, safe="/"))


class _ImagePathExtension(Extension):
    def __init__(self, base_dir: str = ""):
        self.base_dir = base_dir

    def extendMarkdown(self, md):
        md.treeprocessors.register(_ImagePathTreeprocessor(md, self.base_dir), "image_path", 5)


WIKILINK_RE = r"\[\[([^\[\]|]+?)(?:\|([^\[\]]+?))?\]\]"


class _WikiLinkInlineProcessor(InlineProcessor):
    def __init__(self, pattern: str, index: dict[str, list[str]], base_dir: str):
        super().__init__(pattern)
        self.index = index
        self.base_dir = base_dir

    def _resolve(self, target: str) -> str | None:
        matches = self.index.get(target.strip().lower())
        if not matches:
            return None
        same_folder = [m for m in matches if _note_dir_and_stem(m)[0] == self.base_dir]
        return sorted(same_folder or matches)[0]

    def handleMatch(self, m, data):
        target = m.group(1).strip()
        if not target:
            return None, None, None
        display = (m.group(2) or target).strip()

        resolved = self._resolve(target)
        a = etree.Element("a")
        a.text = display
        a.set("href", "#")
        if resolved:
            a.set("class", "wiki-link")
            a.set("data-path", resolved)
        else:
            a.set("class", "wiki-link-broken")
            a.set("data-path", target)
        return a, m.start(0), m.end(0)


class _WikiLinkExtension(Extension):
    def __init__(self, root: Path, base_dir: str = ""):
        self.root = root
        self.base_dir = base_dir

    def extendMarkdown(self, md):
        index: dict[str, list[str]] = {}
        for path in self.root.rglob("*.md"):
            index.setdefault(path.stem.lower(), []).append(path.relative_to(self.root).as_posix())
        md.inlinePatterns.register(
            _WikiLinkInlineProcessor(WIKILINK_RE, index, self.base_dir), "wiki_link", 75
        )


class PathOutsideRootError(Exception):
    pass


class EntryNotFoundError(Exception):
    pass


class EntryAlreadyExistsError(Exception):
    pass


class InvalidNameError(Exception):
    pass


class MarkdownStorage:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root.resolve())
        except ValueError:
            raise PathOutsideRootError(relative_path)
        return candidate

    def list_tree(self) -> list[dict[str, Any]]:
        return self._build_tree(self.root)

    def _build_tree(self, directory: Path) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for entry in sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if entry.is_dir():
                entries.append(
                    {
                        "type": "folder",
                        "name": entry.name,
                        "path": entry.relative_to(self.root).as_posix(),
                        "children": self._build_tree(entry),
                    }
                )
            elif entry.suffix.lower() == ".md":
                entries.append(
                    {
                        "type": "file",
                        "name": entry.name,
                        "path": entry.relative_to(self.root).as_posix(),
                    }
                )
            elif entry.suffix.lower() in IMAGE_EXTENSIONS:
                entries.append(
                    {
                        "type": "image",
                        "name": entry.name,
                        "path": entry.relative_to(self.root).as_posix(),
                    }
                )
        return entries

    def read(self, relative_path: str) -> str:
        file_path = self._resolve(relative_path)
        if not file_path.is_file():
            raise EntryNotFoundError(relative_path)
        return file_path.read_text(encoding="utf-8")

    def write(self, relative_path: str, content: str) -> None:
        file_path = self._resolve(relative_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    def create_file(self, relative_path: str, content: str = "") -> None:
        file_path = self._resolve(relative_path)
        if file_path.exists():
            raise EntryAlreadyExistsError(relative_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    def create_folder(self, relative_path: str) -> None:
        folder_path = self._resolve(relative_path)
        if folder_path.exists():
            raise EntryAlreadyExistsError(relative_path)
        folder_path.mkdir(parents=True)

    def rename(self, relative_path: str, new_name: str) -> str:
        if not new_name or "/" in new_name or "\\" in new_name or new_name in (".", ".."):
            raise InvalidNameError(new_name)

        source = self._resolve(relative_path)
        if source == self.root.resolve():
            raise InvalidNameError(new_name)
        if not source.exists():
            raise EntryNotFoundError(relative_path)

        is_markdown_file = source.is_file() and source.suffix.lower() == ".md"
        if is_markdown_file and not new_name.lower().endswith(".md"):
            new_name = f"{new_name}.md"

        target = source.parent / new_name
        if target.exists():
            raise EntryAlreadyExistsError(new_name)

        source.rename(target)

        if is_markdown_file:
            self._rename_image_dir(relative_path, new_name)

        return target.relative_to(self.root).as_posix()

    def _rename_image_dir(self, old_relative_path: str, new_name: str) -> None:
        parent, old_stem = _note_dir_and_stem(old_relative_path)
        old_image_dir = self._resolve(_image_dir_path(parent, old_stem))
        if not old_image_dir.is_dir():
            return

        new_stem = new_name[: -len(".md")] if new_name.lower().endswith(".md") else new_name
        new_image_dir = self._resolve(_image_dir_path(parent, new_stem))
        new_image_dir.parent.mkdir(parents=True, exist_ok=True)
        old_image_dir.rename(new_image_dir)

    def move(self, relative_path: str, new_parent: str) -> str:
        source = self._resolve(relative_path)
        if source == self.root.resolve():
            raise InvalidNameError(relative_path)
        if not source.exists():
            raise EntryNotFoundError(relative_path)

        new_parent = new_parent.strip().strip("/")
        dest_dir = self._resolve(new_parent) if new_parent else self.root
        if not dest_dir.is_dir():
            raise EntryNotFoundError(new_parent)

        if source.is_dir():
            try:
                dest_dir.relative_to(source)
                raise InvalidNameError(relative_path)
            except ValueError:
                pass

        target = dest_dir / source.name
        if target == source:
            return relative_path
        if target.exists():
            raise EntryAlreadyExistsError(source.name)

        is_markdown_file = source.is_file() and source.suffix.lower() == ".md"

        source.rename(target)

        if is_markdown_file:
            self._move_image_dir(relative_path, new_parent)

        return target.relative_to(self.root).as_posix()

    def _move_image_dir(self, old_relative_path: str, new_parent: str) -> None:
        old_parent, stem = _note_dir_and_stem(old_relative_path)
        old_image_dir = self._resolve(_image_dir_path(old_parent, stem))
        if not old_image_dir.is_dir():
            return

        new_image_dir = self._resolve(_image_dir_path(new_parent, stem))
        if new_image_dir.exists():
            return
        new_image_dir.parent.mkdir(parents=True, exist_ok=True)
        old_image_dir.rename(new_image_dir)

    def delete(self, relative_path: str) -> None:
        target = self._resolve(relative_path)
        if target == self.root.resolve():
            raise InvalidNameError(relative_path)
        if not target.exists():
            raise EntryNotFoundError(relative_path)

        is_markdown_file = target.is_file() and target.suffix.lower() == ".md"

        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()

        if is_markdown_file:
            parent, stem = _note_dir_and_stem(relative_path)
            image_dir = self._resolve(_image_dir_path(parent, stem))
            if image_dir.is_dir():
                shutil.rmtree(image_dir)

    def sync_title(self, relative_path: str, content: str) -> tuple[str, str]:
        if not relative_path.lower().endswith(".md"):
            return relative_path, content

        title = extract_h1_title(content)
        if not title:
            return relative_path, content

        _, current_stem = _note_dir_and_stem(relative_path)
        if title == current_stem:
            return relative_path, content

        try:
            new_path = self.rename(relative_path, title)
        except (EntryAlreadyExistsError, InvalidNameError):
            return relative_path, content

        _, new_stem = _note_dir_and_stem(new_path)
        old_prefix = f"{current_stem}{IMAGE_DIR_SUFFIX}/"
        new_prefix = f"{new_stem}{IMAGE_DIR_SUFFIX}/"
        if old_prefix != new_prefix:
            content = content.replace(old_prefix, new_prefix)

        return new_path, content

    def save_image(self, note_path: str, filename: str, data: bytes) -> str:
        parent, stem = _note_dir_and_stem(note_path)
        image_dir = self._resolve(_image_dir_path(parent, stem))
        image_dir.mkdir(parents=True, exist_ok=True)

        safe_name = self._sanitize_filename(filename)
        name_stem, suffix = Path(safe_name).stem, Path(safe_name).suffix
        candidate = safe_name
        counter = 1
        while (image_dir / candidate).exists():
            candidate = f"{name_stem}-{counter}{suffix}"
            counter += 1

        (image_dir / candidate).write_bytes(data)
        return f"{stem}{IMAGE_DIR_SUFFIX}/{candidate}"

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        name = Path(filename).name
        name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
        return name or "image"

    def render_html(self, raw_markdown: str, base_dir: str = "") -> str:
        extensions = [
            *MARKDOWN_EXTENSIONS,
            _ImagePathExtension(base_dir),
            _WikiLinkExtension(self.root, base_dir),
        ]
        return md_lib.markdown(raw_markdown, extensions=extensions)
