"""
XPX — aperçu des fonctions au survol.

Au survol d'un nom de balise XPX (<set, <cond, ...) :
    aide minimale : description, nature (bloc / inline), attributs.
Au survol d'une variable $maVar$ :
    valeur, valeur résolue, dossier local (variables de chemin), définitions.
Au survol du chemin d'un <include file="..."> :
    chemin local (lien), avertissement si introuvable ou si $url…$ utilisé.
Au survol d'un appel <function exec="maFonction" ... /> :
    lien(s) vers la définition ; avertissement si plusieurs définitions.
Au survol d'une définition <function name="maFonction" ...> :
    nombre et liens des appels (« Aucun appel trouvé » sinon) ;
    avertissement si la fonction est aussi définie ailleurs.

Pourquoi un plugin : l'aperçu natif de Sublime Text (Default/symbol.py) est
désactivé dans les syntaxes de la famille HTML (text.html.*), sauf sur les
attributs class et id. XPX étendant HTML, il faut le fournir ici.

Les fonctions sont trouvées grâce à l'index de Sublime Text, alimenté par :
    Symbol List.tmPreferences            (définitions : function name)
    Indexed Reference List.tmPreferences (appels : function exec)
"""
import html
import os
import webbrowser

import sublime
import sublime_plugin

from .lib import index as xpx_index, paths as xpx_paths
from .lib.data import BLOCK, DUAL, ELSE, INLINE, TAGS

# Nombre maximal d'autres définitions affichées pour une variable.
MAX_OTHER_DEFINITIONS = 5

# Documentation en ligne : une page par balise (ex. XPATH.html).
XPX_DOC_URL = 'https://www.xpx-technologies.net/{}.html'

KIND_LABELS = {
    BLOCK: 'bloc : &lt;{0} …&gt; … &lt;/{0}&gt;',
    INLINE: 'inline : &lt;{0} … /&gt;',
    DUAL: 'bloc ou inline selon l\'usage',
    ELSE: 'alternative dans un bloc &lt;cond&gt;',
}

# Scopes produits par XPX.sublime-syntax.
FUNCTION_SCOPES = ('variable.function.xpx', 'entity.name.function.xpx')

# Nombre maximal de liens affichés par rubrique.
MAX_LINKS = 15

POPUP_CSS = '''
    body { margin: 0; padding: 0.4rem 0.6rem; }
    h1 { font-size: 1rem; margin: 0.3rem 0 0.2rem 0; }
    a { text-decoration: none; }
    .more { color: color(var(--foreground) alpha(0.6)); }
    .warning { color: var(--orangish); }
    .kind { color: color(var(--foreground) alpha(0.7)); font-style: italic; }
    .attrs { margin-top: 0.3rem; }
'''


def function_name_at(view, point):
    """Nom complet de la fonction XPX sous le point, ou None."""
    for scope in FUNCTION_SCOPES:
        if view.match_selector(point, scope):
            region = view.expand_to_scope(point, scope)
            if region:
                name = view.substr(region).strip()
                return name or None
    return None


def location_links(locations):
    """Liens HTML vers une liste de sublime.SymbolLocation."""
    links = []
    for loc in locations[:MAX_LINKS]:
        label = '{}:{}'.format(loc.display_name, loc.row)
        links.append('<a href="{}">{}</a>'.format(
            html.escape(loc.path_encoded_position(), quote=True),
            html.escape(label)))
    hidden = len(locations) - MAX_LINKS
    if hidden > 0:
        links.append('<span class="more">… et {} autre(s)</span>'.format(hidden))
    return '<br>'.join(links)


class XpxFunctionHoverListener(sublime_plugin.ViewEventListener):

    @classmethod
    def is_applicable(cls, settings):
        return settings.get('syntax', '').endswith('/XPX.sublime-syntax')

    def on_hover(self, point, hover_zone):
        if hover_zone != sublime.HOVER_TEXT:
            return
        if not self.view.settings().get('show_definitions', True):
            return

        if self.view.match_selector(point, 'entity.name.tag.xpx'):
            body = self.tag_body(point)
            if body:
                self.show(point, body)
            return

        variable = xpx_paths.variable_name_at(self.view, point)
        if variable:
            body = self.variable_body(variable)
            if body:
                self.show(point, body)
            return

        include = xpx_paths.include_file_region(self.view, point)
        if include:
            self.show(point, self.include_body(self.view.substr(include)))
            return

        name = function_name_at(self.view, point)
        window = self.view.window()
        if not name or not window:
            return

        definitions = window.symbol_locations(
            name, sublime.SYMBOL_SOURCE_ANY, sublime.SYMBOL_TYPE_DEFINITION)

        if self.view.match_selector(point, 'variable.function.xpx'):
            body = self.exec_body(definitions)
        else:
            references = window.symbol_locations(
                name, sublime.SYMBOL_SOURCE_ANY, sublime.SYMBOL_TYPE_REFERENCE)
            body = self.name_body(point, definitions, references)

        self.show(point, body)

    def show(self, point, body):
        content = '<body id="xpx-hover"><style>{}</style>{}</body>'.format(
            POPUP_CSS, body)
        self.view.show_popup(
            content,
            flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
            location=point,
            max_width=1024,
            on_navigate=self.navigate)

    def tag_body(self, point):
        """Survol d'un nom de balise XPX : aide minimale."""
        region = self.view.expand_to_scope(point, 'entity.name.tag.xpx')
        name = self.view.substr(region).lower() if region else ''
        tag = TAGS.get(name)
        if not tag:
            return None
        if name == 'function':
            kind = 'bloc avec name="…" (définition), inline avec exec="…" (appel)'
        else:
            kind = KIND_LABELS.get(tag['kind'], '').format(html.escape(name))
        attrs = ', '.join(tag['attrs']) if tag['attrs'] else 'aucun'
        return (
            '<h1>&lt;{}&gt;</h1>'.format(html.escape(name))
            + '<div>{}</div>'.format(html.escape(tag['doc'], quote=False))
            + '<div class="kind">{}</div>'.format(kind)
            + '<div class="attrs"><b>Attributs :</b> {}</div>'.format(html.escape(attrs, quote=False))
            + '<div class="attrs"><a href="{}">Documentation de &lt;{}&gt;</a></div>'.format(
                XPX_DOC_URL.format(name.upper()), html.escape(name, quote=False)))

    def variable_body(self, name):
        """Survol d'une variable : valeur, valeur résolue, définitions."""
        view = self.view
        definitions = xpx_index.variable_definitions(view.window(), name)
        if not definitions:
            return None
        root = xpx_paths.site_root(view)
        chosen = xpx_paths.choose_definition(view, definitions, root)
        body = '<h1>${}$</h1>'.format(html.escape(name, quote=False))
        if chosen:
            body += '<div>Valeur : <code>{}</code></div>'.format(
                html.escape(chosen.value, quote=False))
            expanded, missing = xpx_paths.expand(view, chosen.value, root)
            if expanded is not None and expanded != chosen.value:
                body += '<div>Résolue : <code>{}</code></div>'.format(
                    html.escape(expanded, quote=False))
            elif missing:
                body += '<div class="warning">Non résolue : {}</div>'.format(
                    html.escape(', '.join(missing), quote=False))
            prefix = xpx_paths.setting(view, 'xpx_path_variable_prefix', 'path').lower()
            if prefix and name.lower().startswith(prefix):
                body += self.path_line(chosen.value, 'Dossier')
            body += '<div class="attrs">Définition : {}</div>'.format(
                self.definition_link(chosen))
        else:
            body += '<div class="warning">⚠ Plusieurs valeurs possibles</div>'
        others = [d for d in definitions if d is not chosen]
        if others:
            body += '<div class="attrs">Autres définitions ({}) :<br>{}</div>'.format(
                len(others), '<br>'.join(
                    '{} <code>{}</code>'.format(
                        self.definition_link(d), html.escape(d.value, quote=False))
                    for d in others[:MAX_OTHER_DEFINITIONS]))
        return body

    def include_body(self, raw):
        """Survol du chemin d'un <include file="...">."""
        body = '<h1>Include</h1>' + self.path_line(raw, 'Fichier')
        if xpx_paths.uses_url_variable(self.view, raw):
            body += ('<div class="warning">⚠ Convention : un include doit utiliser '
                     'une variable de chemin XPX ($path…$), pas une variable '
                     'd\'URL ($url…$)</div>')
        return body

    def path_line(self, raw, label):
        """Ligne « label : chemin local » avec lien s'il existe."""
        view = self.view
        path, missing = xpx_paths.resolve_path(view, raw)
        if missing:
            return '<div class="warning">⚠ Variable(s) non résolue(s) : {}</div>'.format(
                html.escape(', '.join(missing), quote=False))
        if not path:
            return ''
        shown = html.escape(xpx_paths.display_path(view, path), quote=False)
        if os.path.isfile(path):
            return '<div>{} : <a href="{}">{}</a></div>'.format(
                label, html.escape(path + ':1', quote=True), shown)
        if os.path.isdir(path):
            return '<div>{} : {}</div>'.format(label, shown)
        return '<div class="warning">⚠ {} introuvable : {}</div>'.format(label, shown)

    def definition_link(self, definition):
        label = '{}:{}'.format(
            xpx_paths.display_path(self.view, definition.path), definition.row)
        return '<a href="{}">{}</a>'.format(
            html.escape('{}:{}'.format(definition.path, definition.row), quote=True),
            html.escape(label, quote=False))

    @staticmethod
    def exec_body(definitions):
        """Survol d'un appel exec="..." : uniquement la (les) définition(s)."""
        if not definitions:
            return '<h1>Aucune définition trouvée</h1>'
        if len(definitions) == 1:
            return '<h1>Définition :</h1>' + location_links(definitions)
        return ('<h1 class="warning">⚠ {} définitions (ambiguïté) :</h1>'
                .format(len(definitions)) + location_links(definitions))

    def name_body(self, point, definitions, references):
        """Survol d'une définition name="..." : uniquement les appels,
        plus un avertissement si la fonction est définie ailleurs."""
        if references:
            body = '<h1>Appels ({}) :</h1>'.format(len(references))
            body += location_links(references)
        else:
            body = '<h1>Aucun appel trouvé</h1>'

        others = [d for d in definitions if not self.is_here(d, point)]
        if others:
            body += ('<h1 class="warning">⚠ Autre(s) définition(s) :</h1>'
                     + location_links(others))
        return body

    def is_here(self, location, point):
        """La définition indexée est-elle celle qui est survolée ?"""
        file_name = self.view.file_name()
        if not file_name:
            return False
        same_file = (os.path.normcase(os.path.normpath(location.path))
                     == os.path.normcase(os.path.normpath(file_name)))
        row = self.view.rowcol(point)[0] + 1
        return same_file and location.row == row

    def navigate(self, href):
        if href.startswith(('http://', 'https://')):
            webbrowser.open_new_tab(href)
            self.view.hide_popup()
            return
        window = self.view.window()
        if window:
            window.open_file(href, sublime.ENCODED_POSITION)
        self.view.hide_popup()
