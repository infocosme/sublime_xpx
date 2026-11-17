"""
XPX — fermeture automatique des balises.

À la frappe de « / » juste après « < », insère le nom de la dernière balise
restée ouverte puis « > » :   <cond ...> ... </   ->   </cond>

Remplace, dans les fichiers XPX, la commande close_tag de Sublime Text qui
ne connaît pas les balises XPX inline souvent écrites sans « /> »
(<set ...>, <include ...>, <else>) et proposerait de les fermer.

Balises ignorées pour la pile des balises ouvertes :
    - balises XPX inline (table xpx_data.INLINE_TAGS), <function exec="...">,
      <else> ;
    - balises auto-fermantes « /> » ;
    - éléments HTML vides (<br>, <img>, <input>, ...) ;
    - commentaires et chaînes (pas de nom de balise reconnu par la syntaxe).
Une balise fermante referme la dernière balise ouverte de même nom, ainsi
que les balises restées ouvertes au-dessus d'elle.

Raccourci : Default.sublime-keymap (touche « / »).
"""
import bisect
import re

import sublime
import sublime_plugin

from .xpx_data import INLINE_TAGS

HTML_VOID_ELEMENTS = frozenset((
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta',
    'param', 'source', 'track', 'wbr'))

EXEC_RE = re.compile(r'\sexec\s*=', re.IGNORECASE)


def open_tags(view, pt):
    """Pile des balises ouvertes avant pt (nom avec sa casse d'origine)."""
    names = [r for r in view.find_by_selector('entity.name.tag') if r.end() <= pt]
    ends = view.find_by_selector('punctuation.definition.tag.end')
    end_starts = [e.begin() for e in ends]
    stack = []
    for i, name_region in enumerate(names):
        name = view.substr(name_region)
        lower = name.lower()
        is_xpx = view.match_selector(name_region.begin(), 'entity.name.tag.xpx')
        closing = view.substr(name_region.begin() - 1) == '/'

        if closing:
            # Referme la dernière balise ouverte de même nom.
            for j in range(len(stack) - 1, -1, -1):
                if stack[j].lower() == lower:
                    del stack[j:]
                    break
            continue

        # Fin de la balise ouvrante : première ponctuation de fin après le nom,
        # à condition qu'aucune autre balise ne commence avant.
        k = bisect.bisect_left(end_starts, name_region.end())
        if k == len(ends):
            continue
        end = ends[k]
        next_name = names[i + 1].begin() if i + 1 < len(names) else None
        if end.begin() >= pt or (next_name is not None and next_name < end.begin()):
            continue  # balise pas encore terminée : ignorée
        if view.substr(end) == '/>':
            continue  # auto-fermante

        if is_xpx:
            if lower in INLINE_TAGS or lower == 'else':
                continue
            if lower == 'function':
                attrs = view.substr(sublime.Region(name_region.end(), end.begin()))
                if EXEC_RE.search(' ' + attrs):
                    continue  # appel de fonction : inline
        elif lower in HTML_VOID_ELEMENTS:
            continue

        stack.append(name)
    return stack


class XpxCloseTagCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        view = self.view
        closed = False
        for region in reversed(list(view.sel())):
            view.erase(edit, region)
            pt = region.begin()
            stack = open_tags(view, pt)
            text = '/' + (stack[-1] + '>' if stack else '')
            view.insert(edit, pt, text)
            closed = closed or bool(stack)

        # Balise fermante seule sur sa ligne : réalignement sur la balise
        # ouvrante (règles d'Indentation Rules.tmPreferences).
        if closed and all(self.alone_on_line(r.begin()) for r in view.sel()):
            view.run_command('reindent', {'single_line': True})

    def alone_on_line(self, pt):
        line = self.view.line(pt)
        before = self.view.substr(sublime.Region(line.begin(), pt))
        return re.match(r'^[ \t]*</[^<>]*>$', before) is not None
