"""
XPX — analyse du texte autour du curseur (fonctions communes).
"""
import re

import sublime

# Nombre de caractères examinés autour du curseur pour retrouver la balise.
SEARCH_LIMIT = 3000

TAG_OPEN_RE = re.compile(r'<([A-Za-z]+)')
ATTRIBUTE_RE = re.compile(r'([^\s=<>/"\']+)\s*=\s*(?:"((?:\\.|[^"\\])*)"|\'([^\']*)\')')



def find_current_tag(view, pt):
    """(nom, début) de la balise XPX ouvrante contenant pt, sinon (None, None).

    La recherche se fait à rebours sur le texte, en ne retenant que les noms
    reconnus comme balises XPX par la syntaxe (entity.name.tag.xpx).
    """
    start = max(0, pt - SEARCH_LIMIT)
    text = view.substr(sublime.Region(start, pt))
    for match in reversed(list(TAG_OPEN_RE.finditer(text))):
        name_pt = start + match.start(1)
        if view.match_selector(name_pt, 'entity.name.tag.xpx'):
            return match.group(1).lower(), start + match.start()
        if view.match_selector(name_pt, 'entity.name.tag'):
            return None, None  # balise HTML
    return None, None


def tag_text(view, tag_begin, pt):
    """Texte de la balise : de « < » jusqu'au prochain « < » après le curseur."""
    after = view.substr(sublime.Region(pt, min(view.size(), pt + SEARCH_LIMIT)))
    end = after.find('<')
    if end >= 0:
        after = after[:end]
    return view.substr(sublime.Region(tag_begin, pt)) + after


def existing_attributes(text):
    """{nom: valeur} des attributs présents dans le texte d'une balise.
    Les noms gardent leur casse d'origine (paramètres : formName, ...)."""
    return {m.group(1): (m.group(2) if m.group(2) is not None else m.group(3))
            for m in ATTRIBUTE_RE.finditer(text)}


def lower_keys(attrs):
    return {name.lower(): value for name, value in attrs.items()}


def current_attribute(view, pt):
    """Nom de l'attribut XPX dont la valeur contient pt."""
    region = view.expand_to_scope(pt, 'meta.attribute-with-value.xpx')
    if not region:
        return None
    match = re.match(r'\s*([^\s=]+)', view.substr(region))
    return match.group(1).lower() if match else None


def attribute_value_region(view, pt, tag_name, attr_name):
    """Région du contenu (sans guillemets) de l'attribut attr_name de la
    balise tag_name si pt s'y trouve, sinon None."""
    if not view.match_selector(pt, 'meta.tag.xpx meta.string.xpx'):
        return None
    tag, _ = find_current_tag(view, pt)
    if tag != tag_name or current_attribute(view, pt) != attr_name:
        return None
    region = view.expand_to_scope(pt, 'meta.string.xpx')
    if not region:
        return None
    a, b = region.begin(), region.end()
    if view.substr(a) in '"\'':
        a += 1
    if b > a and view.substr(b - 1) in '"\'':
        b -= 1
    return sublime.Region(a, b)
