"""
XPX — commandes.

xpx_close_inline_tags
    Ajoute « /> » aux balises XPX inline qui n'en ont pas :
        <set name="a" value="1">      ->  <set name="a" value="1" />
        <include file="x.xpx">        ->  <include file="x.xpx" />
        <function exec="f" p="1">     ->  <function exec="f" p="1" />
    Ne touche qu'aux balises XPX reconnues par la syntaxe : jamais au HTML,
    ni aux commentaires, ni au contenu des <noparse>.
    Ne touche pas aux balises dont la nature est ambiguë (array, pdf, xproc)
    ni à <else>.
    Agit sur la sélection si elle n'est pas vide, sinon sur tout le fichier.
    Une seule annulation (Ctrl+Z) défait l'ensemble des corrections.
"""
import bisect
import re

import sublime
import sublime_plugin

from .xpx_data import INLINE_TAGS

EXEC_RE = re.compile(r'[\s]exec\s*=', re.IGNORECASE)


def inline_tags_to_close(view, regions):
    """Positions des « > » à remplacer par « /> », de la fin vers le début."""
    ends = view.find_by_selector('punctuation.definition.tag.end.xpx')
    end_starts = [e.begin() for e in ends]
    names = view.find_by_selector('entity.name.tag')  # balises XPX et HTML
    targets = []
    for i, name_region in enumerate(names):
        if not view.match_selector(name_region.begin(), 'entity.name.tag.xpx'):
            continue
        if not any(r.contains(name_region) for r in regions):
            continue
        # Balise fermante </...> : ignorée.
        if view.substr(name_region.begin() - 1) == '/':
            continue
        name = view.substr(name_region).lower()
        # Fin de cette balise : première ponctuation de fin après le nom...
        j = bisect.bisect_left(end_starts, name_region.end())
        if j == len(ends):
            continue
        end = ends[j]
        # ... à condition qu'aucune autre balise ne commence avant
        # (sinon la balise n'est pas refermée : on n'y touche pas).
        if i + 1 < len(names) and names[i + 1].begin() < end.begin():
            continue
        if view.substr(end) != '>':
            continue  # déjà « /> »
        if name == 'function':
            text = view.substr(sublime.Region(name_region.end(), end.begin()))
            if not EXEC_RE.search(' ' + text):
                continue  # définition : balise bloc
        elif name not in INLINE_TAGS:
            continue
        targets.append(end)
    return sorted(targets, key=lambda r: r.begin(), reverse=True)


class XpxCloseInlineTagsCommand(sublime_plugin.TextCommand):

    def is_enabled(self):
        return self.view.match_selector(0, 'text.html.xpx')

    def run(self, edit):
        view = self.view
        selections = [r for r in view.sel() if not r.empty()]
        regions = selections or [sublime.Region(0, view.size())]
        targets = inline_tags_to_close(view, regions)
        for end in targets:
            # « > » -> « /> » (en ajoutant une espace si besoin).
            before = view.substr(end.begin() - 1)
            view.replace(edit, end, '/>' if before in ' \t' else ' />')
        where = 'la sélection' if selections else 'le fichier'
        if targets:
            message = 'XPX : {} balise(s) inline fermée(s) par « /> » dans {}'.format(
                len(targets), where)
        else:
            message = 'XPX : aucune balise inline à corriger dans {}'.format(where)
        sublime.status_message(message)
