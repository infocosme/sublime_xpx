"""
XPX — variables d'arborescence et chemins des <include>.

Principe : le projet Sublime Text reproduit l'arborescence du serveur. Le
dossier du site dans le projet est donc le DOCUMENT_ROOT : un chemin XPX
commençant par « / » part de ce dossier (« /../httpdocs_tools » désigne le
dossier voisin), un chemin relatif part du dossier du fichier courant.

Réglages (XPX.sublime-settings, ou "settings" du fichier .sublime-project) :
    xpx_functional_folders  dossiers partagés, jamais racine du site
                            (défaut : httpdocs_tools, httpdocs_common)
    xpx_definition_files    fichiers de définitions prioritaires
                            (défaut : inc/global.inc.xpx)
    xpx_site                site dont les surcharges s'appliquent
                            (inc/<site>/xpx.conf, inc/<site>/global.inc.xpx)
    xpx_path_variable_prefix   préfixe des variables de chemin XPX (gRep)
    xpx_url_variable_prefix    préfixe des variables d'URL HTML (gUrl)
    xpx_ignored_folders     dossiers ignorés par l'index (défaut : archives)

Racine du site : premier dossier du projet qui n'est pas un dossier
fonctionnel.

Choix de la définition d'une variable :
    1. surcharge du site choisi (inc/<site>/...)
    2. fichiers de définitions (inc/global.inc.xpx)
    3. définition unique (ou toutes identiques) ailleurs dans le projet
Sinon la variable n'est pas résolue (valeur dynamique ou ambiguë).
"""
import os
import re

import sublime
import sublime_plugin

from . import xpx_index
from .xpx_context import attribute_value_region

VARIABLE_RE = re.compile(r'\$([\w.+\-]+)\$')

DEFAULT_FUNCTIONAL_FOLDERS = ['httpdocs_tools', 'httpdocs_common']
DEFAULT_DEFINITION_FILES = ['inc/global.inc.xpx']


def setting(view, key, default):
    value = view.settings().get(key)
    return default if value is None else value


###############################################################################
# Racine du site et définitions

def site_root(view):
    """Dossier DOCUMENT_ROOT du site, ou None."""
    window = view.window()
    folders = window.folders() if window else []
    functional = {name.lower() for name in
                  setting(view, 'xpx_functional_folders', DEFAULT_FUNCTIONAL_FOLDERS)}
    for folder in folders:
        if os.path.basename(os.path.normpath(folder)).lower() not in functional:
            return folder
    if folders:
        return folders[0]
    file_name = view.file_name()
    return os.path.dirname(file_name) if file_name else None


def _relative(path, root):
    try:
        return os.path.relpath(path, root).replace('\\', '/').lower()
    except ValueError:  # autre lecteur (Windows)
        return path.replace('\\', '/').lower()


def choose_definition(view, definitions, root):
    """Définition retenue parmi plusieurs, ou None si ambiguë."""
    if not definitions:
        return None
    site = setting(view, 'xpx_site', '').strip().lower()
    if site and root:
        prefix = 'inc/{}/'.format(site)
        for_site = [d for d in definitions if _relative(d.path, root).startswith(prefix)]
        if for_site:
            return for_site[-1]
    if root:
        files = [f.replace('\\', '/').lower().lstrip('/') for f in
                 setting(view, 'xpx_definition_files', DEFAULT_DEFINITION_FILES)]
        primary = [d for d in definitions if _relative(d.path, root) in files]
        if primary:
            return primary[-1]  # dernière affectation du fichier
    if len({d.value for d in definitions}) == 1:
        return definitions[0]
    return None


def resolve_variable(view, name, root, seen=None):
    """(valeur entièrement résolue ou None, [variables non résolues])."""
    if name.upper() == 'DOCUMENT_ROOT':
        return '', []  # « $DOCUMENT_ROOT$/inc » équivaut à « /inc »
    seen = seen or set()
    if name in seen:
        return None, [name]  # définition circulaire
    definition = choose_definition(
        view, xpx_index.variable_definitions(view.window(), name), root)
    if definition is None:
        return None, [name]
    return expand(view, definition.value, root, seen | {name})


def expand(view, text, root, seen=None):
    """Remplace les $variables$ de text. (texte ou None, [non résolues])."""
    missing = []

    def replace(match):
        value, unresolved = resolve_variable(view, match.group(1), root, seen)
        if value is None:
            missing.extend(unresolved)
            return match.group(0)
        return value

    result = VARIABLE_RE.sub(replace, text)
    if not missing and '$' in result:
        missing.append('expression dynamique')  # ex. $[formName].table[i]$
    return (None if missing else result), missing


def resolve_path(view, raw):
    """Chemin local d'un chemin XPX. (chemin ou None, [non résolues])."""
    root = site_root(view)
    expanded, missing = expand(view, raw, root)
    if expanded is None:
        return None, missing
    if expanded.startswith('/'):
        if not root:
            return None, []
        return os.path.normpath(os.path.join(root, expanded.lstrip('/'))), []
    # Chemin relatif : relatif au fichier en cours d'exécution, souvent la
    # page appelante. Essais : dossier du fichier, puis racine du site.
    candidates = []
    file_name = view.file_name()
    if file_name:
        candidates.append(os.path.join(os.path.dirname(file_name), expanded))
    if root:
        candidates.append(os.path.join(root, expanded))
    candidates = [os.path.normpath(c) for c in candidates]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate, []
    return (candidates[0] if candidates else None), []


def display_path(view, path):
    """Chemin affiché : relatif au dossier parent de la racine du site."""
    root = site_root(view)
    if root:
        try:
            return os.path.relpath(path, os.path.dirname(os.path.normpath(root)))
        except ValueError:
            pass
    return path


def url_to_path(view, url):
    """Chemin local d'une URL du site (ex. « /tools/xpxForms/x.xpx »).

    Convention : une variable d'URL gUrlXxx a pour équivalent disque la
    variable de chemin gRepXxx. L'URL est d'abord cherchée telle quelle à
    partir de la racine du site, puis via le préfixe gUrl le plus long.
    """
    path, _ = resolve_path(view, url)
    if path and os.path.exists(path):
        return path
    url_prefix = setting(view, 'xpx_url_variable_prefix', 'gUrl')
    path_prefix = setting(view, 'xpx_path_variable_prefix', 'gRep')
    root = site_root(view)
    best = None
    for name in xpx_index.variable_names(view.window()):
        if not name.lower().startswith(url_prefix.lower()):
            continue
        value, _ = resolve_variable(view, name, root)
        if not value or not value.startswith('/') or len(value) < 2:
            continue
        if url == value or url.startswith(value.rstrip('/') + '/'):
            if best is None or len(value) > len(best[1]):
                best = (name, value)
    if best:
        rep_name = path_prefix + best[0][len(url_prefix):]
        candidate, _ = resolve_path(view, '${}${}'.format(rep_name, url[len(best[1]):]))
        if candidate and os.path.exists(candidate):
            return candidate
    return path


###############################################################################
# Contexte sous le curseur

def include_file_region(view, pt):
    """Région du chemin de <include file="..."> contenant pt, ou None."""
    return attribute_value_region(view, pt, 'include', 'file')


def variable_name_at(view, pt):
    """Nom de la variable XPX sous pt, ou None."""
    for scope in ('variable.other.readwrite.xpx', 'variable.language.xpx'):
        if view.match_selector(pt, scope):
            region = view.expand_to_scope(pt, scope)
            if region:
                return view.substr(region)
    return None


def uses_url_variable(view, raw):
    """Vrai si le chemin utilise une variable d'URL (gUrl...)."""
    prefix = setting(view, 'xpx_url_variable_prefix', 'gUrl').lower()
    return bool(prefix) and any(
        name.lower().startswith(prefix) for name in VARIABLE_RE.findall(raw))


###############################################################################
# Commandes

class XpxOpenIncludeCommand(sublime_plugin.TextCommand):
    """Ouvre le fichier d'un <include file="..."> (F12)."""

    def run(self, edit, point=None):
        view = self.view
        pt = view.sel()[0].b if point is None else point
        region = include_file_region(view, pt)
        if not region:
            return
        raw = view.substr(region)
        path, missing = resolve_path(view, raw)
        if path and os.path.isfile(path):
            view.window().open_file(path)
        elif missing:
            sublime.status_message('XPX : variable(s) non résolue(s) : ' + ', '.join(missing))
        else:
            sublime.status_message('XPX : fichier introuvable : ' + (path or raw))


class XpxGotoVariableCommand(sublime_plugin.TextCommand):
    """Ouvre la définition retenue d'une variable XPX (F12)."""

    def run(self, edit, point=None):
        view = self.view
        pt = view.sel()[0].b if point is None else point
        name = variable_name_at(view, pt)
        if not name:
            return
        definitions = xpx_index.variable_definitions(view.window(), name)
        definition = choose_definition(view, definitions, site_root(view))
        if definition:
            view.window().open_file('{}:{}'.format(definition.path, definition.row),
                                    sublime.ENCODED_POSITION)
        elif definitions:
            # Plusieurs définitions différentes : liste de choix.
            items = ['{}:{}  {}'.format(display_path(view, d.path), d.row, d.value)
                     for d in definitions]
            view.window().show_quick_panel(
                items, lambda i: i >= 0 and view.window().open_file(
                    '{}:{}'.format(definitions[i].path, definitions[i].row),
                    sublime.ENCODED_POSITION))
        else:
            sublime.status_message('XPX : définition de ${}$ introuvable'.format(name))


class XpxGotoCommand(sublime_plugin.WindowCommand):
    """Aiguillage de F12 vers l'include ou la variable sous le curseur."""

    def run(self, command, point):
        view = self.window.active_view()
        if view:
            view.run_command(command, {'point': point})


class XpxGotoListener(sublime_plugin.EventListener):
    """F12 (goto_definition) sur un include ou une variable XPX.

    goto_definition est une commande de fenêtre (Default/symbol.py) : elle
    est interceptée par on_window_command, et aussi par on_text_command au
    cas où elle serait lancée depuis la vue (menu contextuel).
    """

    def on_window_command(self, window, command_name, args):
        if command_name != 'goto_definition':
            return None
        return self.redirect(window.active_view(), args)

    def on_text_command(self, view, command_name, args):
        if command_name != 'goto_definition':
            return None
        target = self.redirect(view, args)
        return (target[1]['command'], {'point': target[1]['point']}) if target else None

    @staticmethod
    def redirect(view, args):
        if not view or not view.match_selector(0, 'text.html.xpx'):
            return None
        event = (args or {}).get('event')
        if event:
            pt = view.window_to_text((event['x'], event['y']))
        elif len(view.sel()):
            pt = view.sel()[0].b
        else:
            return None
        if variable_name_at(view, pt):
            command = 'xpx_goto_variable'
        elif include_file_region(view, pt):
            command = 'xpx_open_include'
        else:
            return None
        return ('xpx_goto', {'command': command, 'point': pt})
