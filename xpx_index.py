"""
XPX — index du projet.

L'API de Sublime Text ne permet pas d'énumérer les symboles de son index :
le package parcourt donc lui-même, en arrière-plan, les fichiers des
dossiers du projet et relève :
    - les définitions de fonctions   <function name="...">
    - les définitions de variables   <set name|global="..." value="...">
    - les variables des fichiers xpx.conf (lignes « nom valeur »)
L'index est mis à jour à chaque enregistrement d'un fichier.
Les dossiers du réglage xpx_ignored_folders (défaut : archives) sont ignorés.

Utilisé par :
    xpx_completions.py   noms de fonctions dans exec="...", variables
    xpx_paths.py         résolution des chemins des <include>
    xpx_hover.py         valeurs des variables au survol
"""
import collections
import os
import re
import threading

import sublime_plugin

XPX_EXTENSIONS = ('.xpx', '.phc')
CONF_FILE_NAME = 'xpx.conf'
SKIPPED_FOLDERS = {'.git', '.svn', '.hg', 'node_modules', '__pycache__'}

FUNCTION_DEF_RE = re.compile(rb'<function\s+name\s*=\s*"([^"$]+)"', re.IGNORECASE)
SET_TAG_RE = re.compile(rb'<set\b([^>]*)>', re.IGNORECASE)
ATTRIBUTE_RE = re.compile(rb'([\w.-]+)\s*=\s*"([^"]*)"')
CONF_LINE_RE = re.compile(rb'^[ \t]*([A-Za-z_][\w.]*)[ \t]+(.*?)[ \t]*$', re.MULTILINE)

# Définition d'une variable : fichier, ligne (1..n), valeur brute.
Definition = collections.namedtuple('Definition', 'path row value')

# Contenu indexé d'un fichier.
FileEntry = collections.namedtuple('FileEntry', 'mtime functions variables')

_files = {}             # chemin -> FileEntry
_scanned_folders = set()
_ignored_folders = {'archives'}  # réglage xpx_ignored_folders
_lock = threading.Lock()


###############################################################################
# Analyse d'un fichier

def _decode(data):
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return data.decode('cp1252', errors='replace')


def _row(data, offset):
    return data.count(b'\n', 0, offset) + 1


def _parse_xpx(data):
    functions = [_decode(m.group(1)) for m in FUNCTION_DEF_RE.finditer(data)]
    variables = []
    for match in SET_TAG_RE.finditer(data):
        attrs = {k.lower(): v for k, v in ATTRIBUTE_RE.findall(match.group(1))}
        name = attrs.get(b'name') or attrs.get(b'global')
        value = attrs.get(b'value')
        if name and value is not None and b'$' not in name:
            variables.append((_decode(name), _row(data, match.start()), _decode(value)))
    return functions, variables


def _parse_conf(data):
    variables = []
    for match in CONF_LINE_RE.finditer(data):
        variables.append((_decode(match.group(1)), _row(data, match.start()),
                          _decode(match.group(2))))
    return [], variables


def is_indexed_file(path):
    name = os.path.basename(path).lower()
    return name.endswith(XPX_EXTENSIONS) or name == CONF_FILE_NAME


def update_file(path):
    """(Ré)indexe un fichier si nécessaire."""
    try:
        mtime = os.path.getmtime(path)
        entry = _files.get(path)
        if entry and entry.mtime == mtime:
            return
        with open(path, 'rb') as f:
            data = f.read()
        if os.path.basename(path).lower() == CONF_FILE_NAME:
            functions, variables = _parse_conf(data)
        else:
            functions, variables = _parse_xpx(data)
        _files[path] = FileEntry(mtime, functions, variables)
    except OSError:
        _files.pop(path, None)


def _scan_folders(folders):
    with _lock:
        for folder in folders:
            for root, dirs, files in os.walk(folder):
                dirs[:] = [d for d in dirs if d not in SKIPPED_FOLDERS
                           and d.lower() not in _ignored_folders]
                for file_name in files:
                    path = os.path.join(root, file_name)
                    if is_indexed_file(path):
                        update_file(path)


def is_ignored(path):
    """Vrai si le fichier est dans un dossier ignoré (ex. archives)."""
    parts = os.path.normcase(os.path.dirname(path)).replace('\\', '/').split('/')
    return any(part.lower() in _ignored_folders for part in parts)


def set_ignored_folders(names):
    """Applique le réglage xpx_ignored_folders (réindexe si nécessaire)."""
    global _ignored_folders
    names = {n.lower() for n in names}
    if names != _ignored_folders:
        _ignored_folders = names
        _files.clear()
        _scanned_folders.clear()


def ensure_scanned(window):
    """Lance en arrière-plan le parcours des dossiers non encore indexés."""
    if not window:
        return
    view = window.active_view()
    if view:
        ignored = view.settings().get('xpx_ignored_folders')
        if ignored is not None:
            set_ignored_folders(ignored)
    folders = [f for f in window.folders() if f not in _scanned_folders]
    if folders:
        _scanned_folders.update(folders)
        threading.Thread(target=_scan_folders, args=(folders,), daemon=True).start()


###############################################################################
# Consultation

def _entries(window):
    """(chemin, FileEntry) des fichiers situés dans les dossiers du projet."""
    folders = [os.path.normcase(os.path.join(f, '')) for f in
               (window.folders() if window else [])]
    for path, entry in list(_files.items()):
        if not folders or any(os.path.normcase(path).startswith(f) for f in folders):
            yield path, entry


def functions(window):
    """{nom de fonction: fichier de définition}."""
    result = {}
    for path, entry in _entries(window):
        for name in entry.functions:
            result.setdefault(name, path)
    return result


def variable_definitions(window, name):
    """[Definition] d'une variable (les noms XPX sont sensibles à la casse)."""
    return [Definition(path, row, value)
            for path, entry in sorted(_entries(window))
            for var, row, value in entry.variables
            if var == name]


def variable_names(window):
    """Noms de toutes les variables définies dans le projet."""
    names = set()
    for _, entry in _entries(window):
        for var, _, _ in entry.variables:
            names.add(var)
    return sorted(names, key=str.lower)


###############################################################################

class XpxIndexListener(sublime_plugin.EventListener):
    """Tient l'index à jour."""

    def on_load_project_async(self, window):
        ensure_scanned(window)

    def on_activated_async(self, view):
        if view.match_selector(0, 'text.html.xpx'):
            ensure_scanned(view.window())

    def on_post_save_async(self, view):
        path = view.file_name()
        if path and is_indexed_file(path) and not is_ignored(path):
            update_file(path)
