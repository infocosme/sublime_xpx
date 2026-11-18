"""
XPX — mise à jour de l'index du projet (écouteur).

La logique de l'index est dans lib/index.py.
"""
import sublime_plugin

from .lib.index import ensure_scanned, is_ignored, is_indexed_file, update_file


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
