"""
XPX — F12 sur le chemin d'un <include> ou sur une variable $...$.

La résolution des variables et des chemins est dans lib/paths.py.
"""
import os

import sublime
import sublime_plugin

from .lib import index as xpx_index
from .lib.paths import (
    choose_definition, display_path, include_file_region, resolve_path, site_root, variable_name_at)


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
