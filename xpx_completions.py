"""
XPX — complétion.

    <         balises XPX (bloc : avec balise fermante ; inline : avec « /> »)
    <tag |    attributs de la balise, sauf ceux déjà présents
    attr="|"  valeurs connues de l'attribut
    <function exec="maFonction" |   paramètres lus dans la définition
    $phc|     variables internes XPX
    debugn, debugo, debuga20, setd0, setd1, setsql0, setsql1, whilei
              raccourcis (après « < » ou dans le texte, puis Tab)

exec="|"   noms des fonctions XPX définies dans les dossiers du projet

Réglage (XPX.sublime-settings) :
    "xpx_completions": true             activer la complétion XPX
    "xpx_self_closing_tags": true       insérer « /> » à la fin des balises inline
"""
import html
import os
import re

import sublime
import sublime_plugin

from . import xpx_index, xpx_paths
from .xpx_context import (
    current_attribute, existing_attributes, find_current_tag,
    lower_keys, tag_text)
from .xpx_data import (
    BLOCK, DUAL, ELSE, INLINE, INTERNAL_VARIABLES, SHORTCUTS, TAGS, tag_snippets)

KIND_TAG = (sublime.KIND_ID_MARKUP, 't', 'Balise XPX')
KIND_ATTRIBUTE = (sublime.KIND_ID_MARKUP, 'a', 'Attribut XPX')
KIND_PARAMETER = (sublime.KIND_ID_VARIABLE, 'p', 'Paramètre')
KIND_VALUE = (sublime.KIND_ID_AMBIGUOUS, 'v', 'Valeur')
KIND_VARIABLE = (sublime.KIND_ID_VARIABLE, '$', 'Variable XPX')
KIND_FUNCTION = (sublime.KIND_ID_FUNCTION, 'f', 'Fonction XPX')
KIND_SNIPPET = (sublime.KIND_ID_SNIPPET, 's', 'Raccourci XPX')
KIND_FOLDER = (sublime.KIND_ID_NAVIGATION, 'd', 'Dossier')
KIND_FILE = (sublime.KIND_ID_NAVIGATION, 'f', 'Fichier')


# Cache des paramètres de fonctions : (chemin, mtime, ligne) -> [paramètres]
_parameters_cache = {}


###############################################################################
# Construction des listes

def _expansion(name, attrs, kind, self_closing):
    """Snippet d'une balise (sans le « < » initial)."""
    attrs = (' ' + attrs) if attrs else ''
    if kind == BLOCK:
        return '{}{}>$0</{}>'.format(name, attrs, name)
    if kind == ELSE:
        return '{}{}>$0'.format(name, attrs)
    if self_closing:
        return '{}{}$0 />'.format(name, attrs)
    return '{}{}$0>'.format(name, attrs)


def _tag_variants(name):
    """[(nature, attributs par défaut)] pour une balise."""
    if name == 'function':
        return [(BLOCK, 'name="$1"'), (INLINE, 'exec="$1"')]
    kind = TAGS[name]['kind']
    kinds = [BLOCK, INLINE] if kind == DUAL else [kind]
    return [(k, s) for k in kinds for s in tag_snippets(name, k)]


def tag_completions(self_closing, with_lt):
    begin = '' if with_lt is False else '<'
    items = []
    for name in sorted(TAGS):
        for kind, attrs in _tag_variants(name):
            snippet = _expansion(name, attrs, kind, self_closing)
            preview = re.sub(r'\$\{?\d+\}?', '', '<' + snippet)
            items.append(sublime.CompletionItem(
                trigger=name,
                annotation='{} {}'.format(
                    {BLOCK: 'bloc', INLINE: 'inline', ELSE: ''}.get(kind, ''),
                    re.sub(r'="[^"]*"', '', attrs)).strip(),
                completion=begin + snippet,
                completion_format=sublime.COMPLETION_FORMAT_SNIPPET,
                kind=KIND_TAG,
                details='{} — <code>{}</code>'.format(
                    html.escape(TAGS[name]['doc']), html.escape(preview)),
            ))
    for trigger, (doc, snippet) in sorted(SHORTCUTS.items()):
        items.append(sublime.CompletionItem(
            trigger=trigger,
            annotation='raccourci',
            completion=begin + snippet,
            completion_format=sublime.COMPLETION_FORMAT_SNIPPET,
            kind=KIND_SNIPPET,
            details=html.escape(doc),
        ))
    return items


def attribute_completions(names, kind=KIND_ATTRIBUTE, annotation='xpx'):
    return [
        sublime.CompletionItem(
            trigger=name,
            annotation=annotation,
            completion='{}="$1"$0'.format(name),
            completion_format=sublime.COMPLETION_FORMAT_SNIPPET,
            kind=kind,
        )
        for name in names
    ]


def value_completions(values):
    return [
        sublime.CompletionItem(
            trigger=value,
            annotation='xpx',
            completion=value,
            completion_format=sublime.COMPLETION_FORMAT_TEXT,
            kind=KIND_VALUE,
        )
        for value in values
    ]


def variable_completions():
    return [
        sublime.CompletionItem(
            trigger=name,
            annotation='interne',
            completion=name + '$',
            completion_format=sublime.COMPLETION_FORMAT_TEXT,
            kind=KIND_VARIABLE,
            details=html.escape(doc),
        )
        for name, doc in sorted(INTERNAL_VARIABLES.items())
    ]


###############################################################################
# Paramètres d'une fonction XPX (lus dans sa définition)

def _read_file(path):
    with open(path, 'rb') as f:
        data = f.read()
    for encoding in ('utf-8', 'cp1252'):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    return data.decode('utf-8', errors='replace')


def function_parameters(window, function_name):
    """Paramètres déclarés dans <function name="function_name" ...>."""
    if not window or not function_name:
        return []
    locations = window.symbol_locations(
        function_name, sublime.SYMBOL_SOURCE_ANY, sublime.SYMBOL_TYPE_DEFINITION)
    for loc in locations:
        try:
            key = (loc.path, os.path.getmtime(loc.path), loc.row)
        except OSError:
            continue
        if key not in _parameters_cache:
            try:
                lines = _read_file(loc.path).splitlines()
            except OSError:
                continue
            # La balise de définition peut s'étaler sur plusieurs lignes.
            text = '\n'.join(lines[loc.row - 1:loc.row + 20])
            begin = text.lower().find('<function')
            end = text.find('>', begin)
            attrs = existing_attributes(text[begin:end if end >= 0 else None])
            _parameters_cache[key] = [
                a for a in attrs if a.lower() not in ('name', 'exec')]
        if _parameters_cache[key]:
            return _parameters_cache[key]
    return []


###############################################################################
# Chemin d'un <include file="...">

def include_completions(view, pt, prefix):
    """Variables de chemin ($gRep…$) en début de valeur, puis contenu du
    dossier désigné par le début du chemin (après un « / »)."""
    region = xpx_paths.include_file_region(view, pt)
    if not region:
        return None
    window = view.window()
    xpx_index.ensure_scanned(window)
    before = view.substr(sublime.Region(region.begin(), pt - len(prefix)))

    if before in ('', '$'):
        var_prefix = xpx_paths.setting(view, 'xpx_path_variable_prefix', 'gRep').lower()
        lead = '' if before == '$' else '$'
        items = []
        for name in xpx_index.variable_names(window):
            if var_prefix and not name.lower().startswith(var_prefix):
                continue
            path, _ = xpx_paths.resolve_path(view, '$' + name + '$')
            items.append(sublime.CompletionItem(
                trigger=name,
                annotation=xpx_paths.display_path(view, path) if path else '?',
                completion=lead + name + '$/',
                completion_format=sublime.COMPLETION_FORMAT_TEXT,
                kind=KIND_VARIABLE,
            ))
        return sublime.CompletionList(items, sublime.INHIBIT_WORD_COMPLETIONS)

    if '/' not in before:
        return None
    folder, _ = xpx_paths.resolve_path(view, before[:before.rfind('/') + 1])
    if not folder or not os.path.isdir(folder):
        return None
    try:
        entries = sorted(os.listdir(folder), key=str.lower)
    except OSError:
        return None
    items = []
    for entry in entries:
        if entry.startswith('.'):
            continue
        is_dir = os.path.isdir(os.path.join(folder, entry))
        items.append(sublime.CompletionItem(
            trigger=entry,
            annotation='dossier' if is_dir else '',
            completion=entry + ('/' if is_dir else ''),
            completion_format=sublime.COMPLETION_FORMAT_TEXT,
            kind=KIND_FOLDER if is_dir else KIND_FILE,
        ))
    return sublime.CompletionList(items, sublime.INHIBIT_WORD_COMPLETIONS)


###############################################################################
# Noms des fonctions du projet (pour exec="...")

def function_name_completions(view):
    window = view.window()
    xpx_index.ensure_scanned(window)
    functions = xpx_index.functions(window)
    # Fonctions du fichier courant, même non enregistré.
    text = view.substr(sublime.Region(0, view.size())).encode('utf-8', errors='replace')
    for match in xpx_index.FUNCTION_DEF_RE.finditer(text):
        functions.setdefault(match.group(1).decode('utf-8', errors='replace'),
                             view.file_name() or '')
    return [
        sublime.CompletionItem(
            trigger=name,
            annotation=os.path.basename(path),
            completion=name,
            completion_format=sublime.COMPLETION_FORMAT_TEXT,
            kind=KIND_FUNCTION,
        )
        for name, path in sorted(functions.items(), key=lambda item: item[0].lower())
    ]


###############################################################################

class XpxCompletionListener(sublime_plugin.ViewEventListener):

    @classmethod
    def is_applicable(cls, settings):
        return settings.get('syntax', '').endswith('/XPX.sublime-syntax')

    def on_query_completions(self, prefix, locations):
        view = self.view
        settings = view.settings()
        if not settings.get('xpx_completions', True):
            return None

        pt = locations[0]
        start = pt - len(prefix)
        if not view.match_selector(pt, 'text.html.xpx - comment'):
            return None
        before = view.substr(start - 1) if start > 0 else ''
        self_closing = settings.get('xpx_self_closing_tags', True)

        # Chemin d'un <include file="..."> (avant les variables internes).
        if xpx_paths.include_file_region(view, pt):
            return include_completions(view, pt, prefix)

        # $phc... : variables internes.
        if before == '$':
            return sublime.CompletionList(variable_completions())

        # Valeur d'un attribut XPX.
        if view.match_selector(pt, 'meta.tag.xpx meta.string.xpx'):
            tag, _ = find_current_tag(view, start)
            attr = current_attribute(view, pt)
            if tag == 'function' and attr == 'exec':
                return sublime.CompletionList(
                    function_name_completions(view), sublime.INHIBIT_WORD_COMPLETIONS)
            if not tag or not attr:
                return None
            values = TAGS.get(tag, {}).get('values', {}).get(attr)
            if values:
                return sublime.CompletionList(
                    value_completions(values), sublime.INHIBIT_WORD_COMPLETIONS)
            return None

        # Nom d'une balise juste après « < ».
        if before == '<':
            return sublime.CompletionList(tag_completions(self_closing, with_lt=False))

        # Attributs dans une balise XPX.
        check_pt = max(start - 1, 0)
        if view.match_selector(check_pt, 'meta.tag.xpx - meta.string.xpx'):
            if before not in (' ', '\t', '\n', '\f'):
                return None
            tag, tag_begin = find_current_tag(view, start)
            if not tag:
                return None
            present = lower_keys(existing_attributes(tag_text(view, tag_begin, start)))
            return sublime.CompletionList(
                self.attribute_items(tag, present), sublime.INHIBIT_WORD_COMPLETIONS)

        # Texte libre : abréviations (« cond » + Tab -> <cond expr=""></cond>).
        if prefix and view.match_selector(
                pt, 'text.html.xpx - meta.tag - meta.string - source'):
            return sublime.CompletionList(tag_completions(self_closing, with_lt=True))

        return None

    def attribute_items(self, tag, present):
        if tag == 'function':
            if 'exec' in present:
                params = function_parameters(self.view.window(), present['exec'])
                return attribute_completions(
                    [p for p in params if p.lower() not in present],
                    kind=KIND_PARAMETER, annotation='paramètre')
            if 'name' in present:
                return []
            return attribute_completions(['exec', 'name'])
        attrs = TAGS.get(tag, {}).get('attrs', [])
        return attribute_completions([a for a in attrs if a not in present])
