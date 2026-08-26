const treeEl = document.getElementById("tree");
const emptyState = document.getElementById("empty-state");
const editor = document.getElementById("editor");
const fileTitle = document.getElementById("file-title");
const previewPane = document.getElementById("preview-pane");
const editPane = document.getElementById("edit-pane");
const btnPreview = document.getElementById("btn-preview");
const btnEdit = document.getElementById("btn-edit");
const btnSave = document.getElementById("btn-save");
const btnNewFile = document.getElementById("btn-new-file");
const btnNewFolder = document.getElementById("btn-new-folder");
const contextMenu = document.getElementById("context-menu");
const highlightMenu = document.getElementById("highlight-menu");
const wikilinkAutocomplete = document.getElementById("wikilink-autocomplete");
const sidebarEl = document.getElementById("sidebar");
const toolbarInsert = document.getElementById("toolbar-insert");
const btnInsertTable = document.getElementById("btn-insert-table");
const btnInsertImage = document.getElementById("btn-insert-image");
const imageInput = document.getElementById("image-input");
const modalOverlay = document.getElementById("modal-overlay");
const modalTitle = document.getElementById("modal-title");
const modalInput = document.getElementById("modal-input");
const modalCancel = document.getElementById("modal-cancel");
const modalConfirm = document.getElementById("modal-confirm");
const btnThemeToggle = document.getElementById("btn-theme-toggle");

let currentPath = null;
let currentRaw = "";
let dirty = false;
let treeData = [];
let sortMode = "name-asc";
let dragSourcePath = null;
let dragSourceType = null;

function buildUrl(base, path) {
  if (!path) return base;
  return base + "/" + path.split("/").map(encodeURIComponent).join("/");
}

function apiFileUrl(path) {
  return buildUrl("/api/file", path);
}

function apiEntryUrl(path) {
  return buildUrl("/api/entries", path);
}

function dirnameOf(path) {
  const i = path.lastIndexOf("/");
  return i === -1 ? "" : path.slice(0, i);
}

function isSameOrDescendant(path, ancestor) {
  return path === ancestor || path.startsWith(ancestor + "/");
}

async function safeErrorMessage(res) {
  try {
    const data = await res.json();
    return data.detail;
  } catch {
    return null;
  }
}

async function loadTree() {
  const res = await fetch("/api/tree");
  treeData = await res.json();
  renderTreeRoot();
}

function renderTreeRoot() {
  treeEl.innerHTML = "";
  treeEl.appendChild(renderTree(sortNodes(treeData)));
}

function sortNodes(nodes) {
  const factor = sortMode === "name-desc" ? -1 : 1;
  const sorted = [...nodes].sort((a, b) => factor * a.name.localeCompare(b.name, "it", { sensitivity: "base" }));
  for (const node of sorted) {
    if (node.type === "folder") node.children = sortNodes(node.children);
  }
  return sorted;
}

function setSortMode(mode) {
  sortMode = mode;
  renderTreeRoot();
}

function renderTree(nodes) {
  const ul = document.createElement("ul");
  ul.className = "tree-list";

  for (const node of nodes) {
    const li = document.createElement("li");

    if (node.type === "folder") {
      li.className = "tree-folder";
      const label = document.createElement("div");
      label.className = "tree-label folder-label";
      label.textContent = "\u{1F4C1} " + node.name;
      label.addEventListener("click", () => li.classList.toggle("collapsed"));
      label.addEventListener("contextmenu", (e) => showContextMenu(e, node));
      makeDraggable(label, node);
      makeDropTarget(label, node);
      li.appendChild(label);
      li.appendChild(renderTree(node.children));
    } else if (node.type === "image") {
      li.className = "tree-file";
      const label = document.createElement("div");
      label.className = "tree-label file-label";
      label.textContent = "\u{1F5BC} " + node.name;
      label.dataset.path = node.path;
      label.addEventListener("click", () => window.open(buildUrl("/vault", node.path), "_blank"));
      label.addEventListener("contextmenu", (e) => showContextMenu(e, node));
      makeDraggable(label, node);
      makeDropTarget(label, node);
      li.appendChild(label);
    } else {
      li.className = "tree-file";
      const label = document.createElement("div");
      label.className = "tree-label file-label";
      label.textContent = "\u{1F4C4} " + node.name;
      label.dataset.path = node.path;
      if (node.path === currentPath) label.classList.add("active");
      label.addEventListener("click", () => openFile(node.path, label));
      label.addEventListener("contextmenu", (e) => showContextMenu(e, node));
      makeDraggable(label, node);
      makeDropTarget(label, node);
      li.appendChild(label);
    }

    ul.appendChild(li);
  }

  return ul;
}

// --- Drag & drop (spostamento file/cartelle) ---

function dropParentFor(node) {
  return node.type === "folder" ? node.path : dirnameOf(node.path);
}

function canDropOn(node) {
  if (!dragSourcePath || dragSourcePath === node.path) return false;
  const targetParent = dropParentFor(node);
  if (dragSourceType === "folder" && isSameOrDescendant(targetParent, dragSourcePath)) return false;
  return true;
}

function makeDraggable(label, node) {
  label.draggable = true;
  label.addEventListener("dragstart", (event) => {
    event.stopPropagation();
    dragSourcePath = node.path;
    dragSourceType = node.type;
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", node.path);
    label.classList.add("dragging");
  });
  label.addEventListener("dragend", () => {
    label.classList.remove("dragging");
    document.querySelectorAll(".drag-over").forEach((el) => el.classList.remove("drag-over"));
    dragSourcePath = null;
    dragSourceType = null;
  });
}

function makeDropTarget(label, node) {
  label.addEventListener("dragover", (event) => {
    if (!canDropOn(node)) return;
    event.preventDefault();
    event.stopPropagation();
    event.dataTransfer.dropEffect = "move";
    label.classList.add("drag-over");
  });
  label.addEventListener("dragleave", () => label.classList.remove("drag-over"));
  label.addEventListener("drop", async (event) => {
    if (!canDropOn(node)) return;
    event.preventDefault();
    event.stopPropagation();
    label.classList.remove("drag-over");
    await moveEntry(dragSourcePath, dragSourceType, dropParentFor(node));
  });
}

function remapOpenPath(oldPath, newPath, isFolder) {
  if (!currentPath) return;
  if (isFolder) {
    if (!isSameOrDescendant(currentPath, oldPath)) return;
    currentPath = newPath + currentPath.slice(oldPath.length);
  } else if (currentPath === oldPath) {
    currentPath = newPath;
  } else {
    return;
  }
  fileTitle.textContent = currentPath;
}

async function moveEntry(sourcePath, sourceType, targetParent) {
  const res = await fetch("/api/move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: sourcePath, parent: targetParent }),
  });

  if (!res.ok) {
    alert((await safeErrorMessage(res)) || "Impossibile spostare l'elemento");
    return;
  }

  const data = await res.json();
  remapOpenPath(sourcePath, data.path, sourceType === "folder");
  await loadTree();
}

async function openFile(path, labelEl) {
  if (dirty && !confirm("Ci sono modifiche non salvate. Continuare senza salvare?")) {
    return;
  }

  const res = await fetch(apiFileUrl(path));
  if (!res.ok) {
    alert((await safeErrorMessage(res)) || "Impossibile aprire il file");
    return;
  }
  const data = await res.json();

  currentPath = data.path;
  currentRaw = data.raw;
  dirty = false;

  document.querySelectorAll(".file-label.active").forEach((el) => el.classList.remove("active"));
  if (labelEl) labelEl.classList.add("active");

  fileTitle.textContent = currentPath;
  previewPane.innerHTML = data.html;
  editPane.value = data.raw;

  emptyState.classList.add("hidden");
  editor.classList.remove("hidden");
  showPreview();
}

function closeEditorIfOpen(path, isFolder) {
  if (!currentPath) return;
  const affected = isFolder ? currentPath === path || currentPath.startsWith(path + "/") : currentPath === path;
  if (!affected) return;
  currentPath = null;
  dirty = false;
  editor.classList.add("hidden");
  emptyState.classList.remove("hidden");
}

function showPreview() {
  previewPane.classList.remove("hidden");
  editPane.classList.add("hidden");
  btnPreview.classList.add("active");
  btnEdit.classList.remove("active");
  btnSave.classList.add("hidden");
  toolbarInsert.classList.add("hidden");
}

function showEdit() {
  previewPane.classList.add("hidden");
  editPane.classList.remove("hidden");
  btnEdit.classList.add("active");
  btnPreview.classList.remove("active");
  btnSave.classList.remove("hidden");
  toolbarInsert.classList.remove("hidden");
  editPane.focus();
}

btnPreview.addEventListener("click", showPreview);
btnEdit.addEventListener("click", showEdit);

editPane.addEventListener("input", () => {
  dirty = editPane.value !== currentRaw;
});

btnSave.addEventListener("click", async () => {
  if (!currentPath) return;

  const res = await fetch(apiFileUrl(currentPath), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content: editPane.value }),
  });

  if (!res.ok) {
    alert((await safeErrorMessage(res)) || "Salvataggio fallito");
    return;
  }

  const data = await res.json();
  const renamed = data.path !== currentPath;
  currentPath = data.path;
  currentRaw = data.raw;
  dirty = false;
  previewPane.innerHTML = data.html;
  editPane.value = data.raw;
  fileTitle.textContent = currentPath;

  if (renamed) await loadTree();
});

// --- Inserimento tabella / immagine ---

function insertAtCursor(text) {
  const start = editPane.selectionStart;
  const end = editPane.selectionEnd;
  const value = editPane.value;

  editPane.value = value.slice(0, start) + text + value.slice(end);
  const cursor = start + text.length;
  editPane.selectionStart = editPane.selectionEnd = cursor;

  editPane.dispatchEvent(new Event("input"));
  editPane.focus();
}

btnInsertTable.addEventListener("click", () => {
  insertAtCursor("\n| Colonna 1 | Colonna 2 |\n| --- | --- |\n| valore | valore |\n");
});

btnInsertImage.addEventListener("click", () => {
  if (!currentPath) return;
  imageInput.value = "";
  imageInput.click();
});

imageInput.addEventListener("change", async () => {
  const file = imageInput.files[0];
  if (!file || !currentPath) return;

  const formData = new FormData();
  formData.append("image", file);

  const res = await fetch(buildUrl("/api/images", currentPath), {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    alert((await safeErrorMessage(res)) || "Caricamento immagine fallito");
    return;
  }

  const data = await res.json();
  insertAtCursor(`![${data.name}](${data.path})`);
});

// --- Evidenziazione ---

const HL_OPEN_RE = /<mark class="hl-(yellow|blue|green)">$/;
const HL_CLOSE = "</mark>";

editPane.addEventListener("contextmenu", (event) => {
  const start = editPane.selectionStart;
  const end = editPane.selectionEnd;
  if (start === end) return;
  event.preventDefault();
  event.stopPropagation();
  showHighlightMenu(event, start, end);
});

function showHighlightMenu(event, start, end) {
  hideAllMenus();
  highlightMenu.querySelectorAll(".swatch").forEach((btn) => {
    btn.onclick = () => {
      hideAllMenus();
      applyHighlight(start, end, btn.dataset.color);
    };
  });
  highlightMenu.classList.remove("hidden");
  positionMenu(highlightMenu, event);
}

function applyHighlight(start, end, color) {
  const value = editPane.value;
  const before = value.slice(0, start);
  const after = value.slice(end);
  const openMatch = before.match(HL_OPEN_RE);
  const isWrapped = Boolean(openMatch) && after.startsWith(HL_CLOSE);

  let newValue;
  let newStart;
  let newEnd;

  if (isWrapped) {
    const openTag = openMatch[0];
    if (color === "clear") {
      newValue = before.slice(0, -openTag.length) + value.slice(start, end) + after.slice(HL_CLOSE.length);
      newStart = start - openTag.length;
      newEnd = end - openTag.length;
    } else if (openMatch[1] === color) {
      return;
    } else {
      const newOpen = `<mark class="hl-${color}">`;
      newValue = before.slice(0, -openTag.length) + newOpen + value.slice(start, end) + after;
      newStart = start - openTag.length + newOpen.length;
      newEnd = newStart + (end - start);
    }
  } else {
    if (color === "clear") return;
    const openTag = `<mark class="hl-${color}">`;
    newValue = before + openTag + value.slice(start, end) + HL_CLOSE + after;
    newStart = start + openTag.length;
    newEnd = newStart + (end - start);
  }

  editPane.value = newValue;
  editPane.setSelectionRange(newStart, newEnd);
  editPane.focus();
  editPane.dispatchEvent(new Event("input"));
}

// --- Wiki-link ([[Nota]]) ---

previewPane.addEventListener("click", async (event) => {
  const link = event.target.closest("a.wiki-link, a.wiki-link-broken");
  if (!link) return;
  event.preventDefault();

  if (link.classList.contains("wiki-link")) {
    await openFile(link.dataset.path);
    return;
  }

  const name = link.dataset.path;
  if (!confirm(`La nota "${name}" non esiste. Crearla?`)) return;

  const res = await fetch("/api/files", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parent: currentPath ? dirnameOf(currentPath) : "", name }),
  });

  if (!res.ok) {
    alert((await safeErrorMessage(res)) || "Impossibile creare la nota");
    return;
  }

  const data = await res.json();
  await loadTree();
  await openFile(data.path);
});

const MIRROR_PROPS = [
  "boxSizing",
  "width",
  "fontFamily",
  "fontSize",
  "fontWeight",
  "fontStyle",
  "letterSpacing",
  "wordSpacing",
  "lineHeight",
  "textTransform",
  "textIndent",
  "whiteSpace",
  "paddingTop",
  "paddingRight",
  "paddingBottom",
  "paddingLeft",
  "borderTopWidth",
  "borderRightWidth",
  "borderBottomWidth",
  "borderLeftWidth",
  "tabSize",
];
let mirrorDiv = null;

function getCaretCoords() {
  if (!mirrorDiv) {
    mirrorDiv = document.createElement("div");
    mirrorDiv.style.position = "absolute";
    mirrorDiv.style.visibility = "hidden";
    mirrorDiv.style.left = "-9999px";
    mirrorDiv.style.top = "0";
    mirrorDiv.style.overflowY = "scroll";
    mirrorDiv.style.wordWrap = "break-word";
    document.body.appendChild(mirrorDiv);
  }
  const style = getComputedStyle(editPane);
  MIRROR_PROPS.forEach((prop) => {
    mirrorDiv.style[prop] = style[prop];
  });

  const pos = editPane.selectionStart;
  const before = editPane.value.slice(0, pos);
  mirrorDiv.textContent = before;
  const marker = document.createElement("span");
  marker.textContent = editPane.value.slice(pos) || ".";
  mirrorDiv.appendChild(marker);

  const rect = editPane.getBoundingClientRect();
  return {
    left: rect.left + marker.offsetLeft - editPane.scrollLeft,
    top: rect.top + marker.offsetTop - editPane.scrollTop,
    lineHeight: parseInt(style.lineHeight, 10) || 18,
  };
}

let wlActiveIndex = -1;
let wlQueryStart = -1;

function flattenNotes(nodes, out = []) {
  for (const node of nodes) {
    if (node.type === "file") {
      out.push({ name: node.name.replace(/\.md$/i, ""), path: node.path });
    } else if (node.type === "folder") {
      flattenNotes(node.children, out);
    }
  }
  return out;
}

function getWikilinkQuery() {
  const pos = editPane.selectionStart;
  const before = editPane.value.slice(0, pos);
  const openIdx = before.lastIndexOf("[[");
  if (openIdx === -1) return null;
  const between = before.slice(openIdx + 2);
  if (between.includes("]") || between.includes("[") || between.includes("\n") || between.includes("|")) {
    return null;
  }
  return { start: openIdx, query: between };
}

function updateWikilinkAutocomplete() {
  const query = getWikilinkQuery();
  if (!query) {
    hideWikilinkAutocomplete();
    return;
  }

  const matches = flattenNotes(treeData)
    .filter((note) => note.name.toLowerCase().includes(query.query.toLowerCase()))
    .slice(0, 8);

  if (!matches.length) {
    hideWikilinkAutocomplete();
    return;
  }

  wlQueryStart = query.start;
  wlActiveIndex = 0;
  wikilinkAutocomplete.innerHTML = "";
  matches.forEach((note, index) => {
    const item = document.createElement("div");
    item.className = "wikilink-item" + (index === 0 ? " active" : "");
    item.textContent = note.name;
    item.addEventListener("mousedown", (e) => e.preventDefault());
    item.addEventListener("click", () => selectWikilink(note.name));
    wikilinkAutocomplete.appendChild(item);
  });

  wikilinkAutocomplete.classList.remove("hidden");
  const coords = getCaretCoords();
  wikilinkAutocomplete.style.left = coords.left + "px";
  wikilinkAutocomplete.style.top = coords.top + coords.lineHeight + "px";
}

function hideWikilinkAutocomplete() {
  wikilinkAutocomplete.classList.add("hidden");
  wlActiveIndex = -1;
  wlQueryStart = -1;
}

function selectWikilink(name) {
  const pos = editPane.selectionStart;
  const value = editPane.value;
  const newValue = value.slice(0, wlQueryStart) + `[[${name}]]` + value.slice(pos);
  const cursor = wlQueryStart + name.length + 4;
  editPane.value = newValue;
  editPane.setSelectionRange(cursor, cursor);
  editPane.focus();
  hideWikilinkAutocomplete();
  editPane.dispatchEvent(new Event("input"));
}

editPane.addEventListener("input", updateWikilinkAutocomplete);
editPane.addEventListener("scroll", () => {
  if (!wikilinkAutocomplete.classList.contains("hidden")) updateWikilinkAutocomplete();
});

editPane.addEventListener("keydown", (event) => {
  if (wikilinkAutocomplete.classList.contains("hidden")) return;
  const items = [...wikilinkAutocomplete.querySelectorAll(".wikilink-item")];
  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    items[wlActiveIndex]?.classList.remove("active");
    wlActiveIndex = (wlActiveIndex + (event.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
    items[wlActiveIndex].classList.add("active");
  } else if (event.key === "Enter" || event.key === "Tab") {
    event.preventDefault();
    selectWikilink(items[wlActiveIndex].textContent);
  } else if (event.key === "Escape") {
    hideWikilinkAutocomplete();
  }
});

// --- Modale ---

function showInputModal({ title, defaultValue = "", confirmLabel = "Crea" }) {
  return new Promise((resolve) => {
    modalTitle.textContent = title;
    modalInput.value = defaultValue;
    modalConfirm.textContent = confirmLabel;
    modalOverlay.classList.remove("hidden");
    modalInput.focus();
    modalInput.select();

    function cleanup(result) {
      modalOverlay.classList.add("hidden");
      modalConfirm.removeEventListener("click", onConfirm);
      modalCancel.removeEventListener("click", onCancel);
      modalOverlay.removeEventListener("click", onOverlayClick);
      modalInput.removeEventListener("keydown", onKeydown);
      resolve(result);
    }

    function onConfirm() {
      cleanup(modalInput.value.trim() || null);
    }

    function onCancel() {
      cleanup(null);
    }

    function onOverlayClick(event) {
      if (event.target === modalOverlay) cleanup(null);
    }

    function onKeydown(event) {
      if (event.key === "Enter") {
        event.preventDefault();
        onConfirm();
      } else if (event.key === "Escape") {
        event.preventDefault();
        onCancel();
      }
    }

    modalConfirm.addEventListener("click", onConfirm);
    modalCancel.addEventListener("click", onCancel);
    modalOverlay.addEventListener("click", onOverlayClick);
    modalInput.addEventListener("keydown", onKeydown);
  });
}

// --- Creazione, rinomina, eliminazione ---

async function createFile(parentPath) {
  const name = await showInputModal({ title: "Nome del nuovo file", defaultValue: "Nuova nota" });
  if (!name) return;

  const res = await fetch("/api/files", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parent: parentPath, name }),
  });

  if (!res.ok) {
    alert((await safeErrorMessage(res)) || "Impossibile creare il file");
    return;
  }

  await loadTree();
}

async function createFolder(parentPath) {
  const name = await showInputModal({ title: "Nome della nuova cartella", defaultValue: "Nuova cartella" });
  if (!name) return;

  const res = await fetch("/api/folders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parent: parentPath, name }),
  });

  if (!res.ok) {
    alert((await safeErrorMessage(res)) || "Impossibile creare la cartella");
    return;
  }

  await loadTree();
}

async function renameEntry(node) {
  const newName = prompt("Nuovo nome:", node.name);
  if (!newName || newName === node.name) return;

  const res = await fetch(apiEntryUrl(node.path), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: newName }),
  });

  if (!res.ok) {
    alert((await safeErrorMessage(res)) || "Impossibile rinominare l'elemento");
    return;
  }

  closeEditorIfOpen(node.path, node.type === "folder");
  await loadTree();
}

async function deleteEntry(node) {
  const what = node.type === "folder" ? "la cartella e tutto il suo contenuto" : "il file";
  if (!confirm(`Eliminare ${what} "${node.name}"?`)) return;

  const res = await fetch(apiEntryUrl(node.path), { method: "DELETE" });

  if (!res.ok) {
    alert((await safeErrorMessage(res)) || "Impossibile eliminare l'elemento");
    return;
  }

  closeEditorIfOpen(node.path, node.type === "folder");
  await loadTree();
}

btnNewFile.addEventListener("click", () => createFile(""));
btnNewFolder.addEventListener("click", () => createFolder(""));

// --- Menu contestuale ---

function menuButton(label, handler, danger) {
  const btn = document.createElement("button");
  btn.textContent = label;
  if (danger) btn.classList.add("danger");
  btn.addEventListener("click", () => {
    hideContextMenu();
    handler();
  });
  return btn;
}

function showContextMenu(event, node) {
  event.preventDefault();
  event.stopPropagation();

  contextMenu.innerHTML = "";

  if (node.type === "folder") {
    contextMenu.appendChild(menuButton("Nuovo file", () => createFile(node.path)));
    contextMenu.appendChild(menuButton("Nuova sottocartella", () => createFolder(node.path)));
  }
  contextMenu.appendChild(menuButton("Rinomina", () => renameEntry(node)));
  contextMenu.appendChild(menuButton("Elimina", () => deleteEntry(node), true));

  contextMenu.classList.remove("hidden");
  positionContextMenu(event);
}

function showBackgroundContextMenu(event) {
  contextMenu.innerHTML = "";

  contextMenu.appendChild(menuButton("Nuovo file", () => createFile("")));
  contextMenu.appendChild(menuButton("Nuova cartella", () => createFolder("")));
  contextMenu.appendChild(menuSeparator());
  contextMenu.appendChild(menuLabel("Ordina per"));
  contextMenu.appendChild(
    menuButton((sortMode === "name-asc" ? "✓ " : "") + "Nome (A-Z)", () => setSortMode("name-asc"))
  );
  contextMenu.appendChild(
    menuButton((sortMode === "name-desc" ? "✓ " : "") + "Nome (Z-A)", () => setSortMode("name-desc"))
  );

  contextMenu.classList.remove("hidden");
  positionContextMenu(event);
}

function menuSeparator() {
  const el = document.createElement("div");
  el.className = "context-menu-separator";
  return el;
}

function menuLabel(text) {
  const el = document.createElement("div");
  el.className = "context-menu-label";
  el.textContent = text;
  return el;
}

function positionMenu(menuEl, event) {
  const maxLeft = window.innerWidth - menuEl.offsetWidth - 8;
  const maxTop = window.innerHeight - menuEl.offsetHeight - 8;
  menuEl.style.left = Math.min(event.clientX, Math.max(maxLeft, 8)) + "px";
  menuEl.style.top = Math.min(event.clientY, Math.max(maxTop, 8)) + "px";
}

function positionContextMenu(event) {
  positionMenu(contextMenu, event);
}

function hideContextMenu() {
  hideAllMenus();
}

function hideAllMenus() {
  contextMenu.classList.add("hidden");
  highlightMenu.classList.add("hidden");
  hideWikilinkAutocomplete();
}

sidebarEl.addEventListener("contextmenu", (e) => {
  e.preventDefault();
  e.stopPropagation();
  showBackgroundContextMenu(e);
});

sidebarEl.addEventListener("dragover", (event) => {
  if (!dragSourcePath) return;
  event.preventDefault();
  event.dataTransfer.dropEffect = "move";
});

sidebarEl.addEventListener("drop", async (event) => {
  if (!dragSourcePath) return;
  event.preventDefault();
  await moveEntry(dragSourcePath, dragSourceType, "");
});

document.addEventListener("click", hideContextMenu);
document.addEventListener("contextmenu", (e) => {
  if (!e.target.closest(".tree-label")) hideContextMenu();
});
window.addEventListener("blur", hideContextMenu);

document.addEventListener("keydown", (event) => {
  if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== "s") return;
  event.preventDefault();
  if (currentPath) btnSave.click();
});

// --- Tema chiaro/scuro ---

const THEME_STORAGE_KEY = "dragon-glass-theme";

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  btnThemeToggle.textContent = theme === "light" ? "🌙" : "☀️";
  btnThemeToggle.title = theme === "light" ? "Passa al tema scuro" : "Passa al tema chiaro";
}

function initTheme() {
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  const preferred = window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  applyTheme(stored || preferred);
}

btnThemeToggle.addEventListener("click", () => {
  const next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
  localStorage.setItem(THEME_STORAGE_KEY, next);
  applyTheme(next);
});

initTheme();

loadTree();
