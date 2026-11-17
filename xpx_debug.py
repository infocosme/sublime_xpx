"""
XPX Debug — retour au code source depuis un fichier .debug (F12).

Chaque ligne d'un fichier debug commence par un numéro de ligne dans le
fichier XPX source (« 133:VAR ... »). Le fichier source est déduit :
    - en descendant : si un « End of Exec maFonction, line N » est atteint
      sans quitter l'include courant, la ligne appartient au corps de la
      fonction -> fichier de définition de la fonction ;
    - sinon en remontant : dernier « INCLUDE FILE=… », « RETURN IN … » ou,
      à défaut, page de départ de « --- START DEBUG … /page.xpx->… » :
      URL du site, convertie en chemin disque (alias urlXxx -> pathXxx).

F12 :
    ligne numérotée                    fichier source à cette ligne
    INCLUDE FILE= / END INCLUDE FILE=   ce fichier
    RETURN IN ...                       fichier appelant, à la ligne indiquée
    Define function ... from ...        ce fichier, à la ligne indiquée
    End of Exec maFonction, line N      définition de la fonction, ligne N
"""
import bisect
import os
import re

import sublime
import sublime_plugin

from . import xpx_paths

LINE_NUMBER_RE = re.compile(r'^\s*(\d+):')
INCLUDE_RE = re.compile(r'^\s*\d*:?\s*INCLUDE FILE=(.+?)\s*$')
END_INCLUDE_RE = re.compile(r'END INCLUDE FILE=(.+?)\s*-{3,}\s*$')
RETURN_RE = re.compile(r'RETURN IN\s+(.+?)\s*\*+\s*$')
DEFINE_RE = re.compile(r'Define function\s+(\S+)\s+from\s+(.+?)\s*$')
END_EXEC_RE = re.compile(r'End of Exec\s+([^,\s]+),\s*line\s+(\d+)')
START_RE = re.compile(r'---\s*START DEBUG\b.*?\s(/\S+?\.(?:xpx|phc))\S*->')


def _lines(view):
    return view.substr(sublime.Region(0, view.size())).split('\n')


def _normalize(path):
    return os.path.normpath(path.replace('/', os.sep))


def function_definition(window, name):
    """(fichier, ligne) de la définition d'une fonction XPX, ou None."""
    if not window:
        return None
    locations = window.symbol_locations(
        name, sublime.SYMBOL_SOURCE_ANY, sublime.SYMBOL_TYPE_DEFINITION)
    return (locations[0].path, locations[0].row) if locations else None


def markers(lines):
    """Marqueurs du debug : [(ligne, type, valeur)], dans l'ordre.
    Types : include, return, end_exec (nom de fonction), start (URL)."""
    result = []
    for row, line in enumerate(lines):
        if 'INCLUDE FILE=' in line and not END_INCLUDE_RE.search(line):
            match = INCLUDE_RE.search(line)
            if match:
                result.append((row, 'include', match.group(1)))
        elif 'RETURN IN' in line:
            match = RETURN_RE.search(line)
            if match:
                result.append((row, 'return', match.group(1)))
        elif 'End of Exec' in line:
            match = END_EXEC_RE.search(line)
            if match:
                result.append((row, 'end_exec', match.group(1)))
        elif 'START DEBUG' in line:
            match = START_RE.search(line)
            if match:
                result.append((row, 'start', match.group(1)))
    return result


def source_file(view, lines, row, marks=None):
    """Fichier XPX source de la ligne row (index 0) du debug, ou None."""
    if marks is None:
        marks = markers(lines)
    rows = [m[0] for m in marks]
    index = bisect.bisect_right(rows, row)
    # 1. En descendant : corps d'une fonction terminé par « End of Exec ».
    depth = 0
    for _, kind, value in marks[index:]:
        if kind == 'include':
            depth += 1
        elif kind == 'return':
            if depth == 0:
                break  # fin de l'include courant
            depth -= 1
        elif kind == 'end_exec' and depth == 0:
            definition = function_definition(view.window(), value)
            if definition:
                return definition[0]
            break
    # 2. En remontant : dernier marqueur de fichier.
    for _, kind, value in reversed(marks[:index]):
        if kind in ('include', 'return'):
            return _normalize(value)
        if kind == 'start':
            # Page de départ : URL du site (/index.xpx, /tools/... via alias).
            return xpx_paths.url_to_path(view, value)
    return None


def target_at(view, pt):
    """(fichier, ligne) visé par F12 à la position pt, ou (None, message)."""
    lines = _lines(view)
    row = view.rowcol(pt)[0]
    text = lines[row]

    match = END_EXEC_RE.search(text)
    if match:
        definition = function_definition(view.window(), match.group(1))
        if definition:
            return definition[0], int(match.group(2))
        return None, 'définition de la fonction {} introuvable'.format(match.group(1))

    number = LINE_NUMBER_RE.match(text)

    # RETURN IN : retour dans le fichier appelant, à la ligne de l'include
    # (numéro en début de ligne du debug).
    match = RETURN_RE.search(text)
    if match:
        return _normalize(match.group(1)), int(number.group(1)) if number else 1

    for regex in (INCLUDE_RE, END_INCLUDE_RE):
        match = regex.search(text)
        if match:
            return _normalize(match.group(1)), 1

    match = DEFINE_RE.search(text)
    if match:
        return _normalize(match.group(2)), int(number.group(1)) if number else 1

    if number:
        path = source_file(view, lines, row)
        if path:
            return path, int(number.group(1))
        return None, 'fichier source introuvable pour cette ligne'
    return None, 'ligne sans numéro de ligne source'


class XpxDebugGotoSourceCommand(sublime_plugin.TextCommand):
    """Ouvre le fichier XPX source correspondant à la ligne du debug."""

    def run(self, edit, point=None):
        view = self.view
        pt = view.sel()[0].b if point is None else point
        path, info = target_at(view, pt)
        if path is None:
            sublime.status_message('XPX Debug : ' + info)
            return
        if not os.path.isfile(path):
            sublime.status_message('XPX Debug : fichier introuvable : ' + path)
            return
        view.window().open_file('{}:{}'.format(path, info), sublime.ENCODED_POSITION)

    def is_enabled(self):
        return self.view.match_selector(0, 'text.xpx-debug')


class XpxDebugGotoCommand(sublime_plugin.WindowCommand):
    def run(self, point):
        view = self.window.active_view()
        if view:
            view.run_command('xpx_debug_goto_source', {'point': point})


class XpxDebugGotoListener(sublime_plugin.EventListener):
    """F12 (goto_definition) dans un fichier .debug."""

    def on_window_command(self, window, command_name, args):
        if command_name != 'goto_definition':
            return None
        view = window.active_view()
        if not view or not view.match_selector(0, 'text.xpx-debug'):
            return None
        event = (args or {}).get('event')
        if event:
            pt = view.window_to_text((event['x'], event['y']))
        elif len(view.sel()):
            pt = view.sel()[0].b
        else:
            return None
        return ('xpx_debug_goto', {'point': pt})


###############################################################################
# Suivi d'une variable : historique de ses changements de valeur
#
#   Commande « XPX Debug: Suivre une variable » (palette, menu contextuel).
#   - curseur sur un nom de variable : cette variable ;
#   - sinon : liste des variables modifiées dans le debug.
#   L'historique s'affiche dans un panneau qui reste ouvert ; double-clic sur
#   une ligne du panneau : la ligne correspondante du debug.
#   Changements comptés : SET (dont global et return), variables décrites
#   par le FORMAT d'un <get>, variables numérotées d'un <get token>.
#   Les noms de variables XPX sont sensibles à la casse.
#
#   Portées (scopes) :
#   - GLOBAL est le niveau 1 ; un include n'ajoute pas de niveau ;
#   - chaque appel de fonction (« Exec F » … « End of Exec F ») crée une
#     portée un niveau en dessous de la portée d'appel ;
#   - <set name> écrit dans la portée courante, <set global> dans GLOBAL,
#     <set return> dans la portée du dessus (« Return bloc X ») ;
#   - une variable est cherchée dans la portée courante, puis dans chaque
#     portée supérieure (pile remontée), jusqu'à GLOBAL au pire.
#   Une variable est identifiée par (portée, nom) : le $i$ d'une fonction
#   et le $i$ global ont des historiques distincts.

SET_RE = re.compile(r'^\s*(\d+):SET\s*:\s*(\S+)\s*=>\s?(.*?)\s*$')

PANEL_NAME = 'xpx_debug_variable'
REGION_KEY = 'xpx_debug_variable'
MAX_VALUE_LENGTH = 120
GLOBAL = 'GLOBAL'

# VAR nom ORIGINE=valeur (longueur), éventuellement en chaîne :
#   VAR i GLOBAL=(1)VAR gGroupe1 GLOBAL=Client (6)
# ORIGINE : GLOBAL, nom de fonction (portée locale), SQL, SYS, CONFIG, UNKNOWN.
VAR_LINK_RE = re.compile(r'VAR (\S+) ([^=\s]+?)=\(([^)]*)\)(?=VAR )')
VAR_LAST_RE = re.compile(r'.*\bVAR (\S+) ([^=\s]+?)=(.*?) \(\d+\)\s*$')
EXEC_RE = re.compile(r'^\s*\d+:Exec (\S+)\s*$')
END_EXEC_LINE_RE = re.compile(r'^\s*\d+:End of Exec ([^,\s]+),')
GET_TOKEN_RE = re.compile(r'^\s*(\d+):GET TOKEN (\d+): ?(.*?)\s*$')
GET_FORMAT_RE = re.compile(r'^\s*(\d+):GET: (\S+) = ?(.*?)\s*$')
RETURN_BLOC_RE = re.compile(r'Return bloc\s+(\S+)')
PARAM_RE = re.compile(r'^\s*\d+:FUNCTION PARAM (\S+) = ?(.*?)\s*$')
DOLLAR_RE = re.compile(r'\$([^$]+)\$')
BRACKET_RE = re.compile(r'\[([^\[\]$]*)\]')
OTHER_ORIGINS = ('SQL', 'SYS', 'CONFIG')


def resolve_name(expr, values):
    """Nom calculé : $formName$.label -> myForm.label ; None si impossible."""
    if '$' not in expr:
        return expr
    failed = []

    def index(match):
        if match.group(1) in values:
            return values[match.group(1)]
        failed.append(1)
        return ''

    def inner(match):
        name = BRACKET_RE.sub(index, match.group(1))
        if '(' in name or name not in values:
            failed.append(1)
            return ''
        return values[name]

    result = DOLLAR_RE.sub(inner, expr)
    return None if failed or '$' in result else result


class Scope:
    def __init__(self, name, level, call):
        self.name = name      # GLOBAL ou nom de la fonction
        self.level = level    # 1 = GLOBAL
        self.call = call      # numéro d'appel de la fonction
        self.vars = {}

    @property
    def label(self):
        if self.level == 1:
            return 'GLOBAL (1)'
        return '{} #{} ({})'.format(self.name, self.call, self.level)


class Visible:
    """Valeurs visibles depuis la portée courante : locale, puis chaque
    portée supérieure jusqu'à GLOBAL, puis valeurs SQL/SYS/CONFIG lues."""

    def __init__(self, scan):
        self.scan = scan

    def _find(self, name):
        scope = self.scan.find(name)
        if scope is not None:
            return scope.vars
        return self.scan.other if name in self.scan.other else None

    def __contains__(self, name):
        return self._find(name) is not None

    def __getitem__(self, name):
        return self._find(name)[name]

    def get(self, name, default=None):
        d = self._find(name)
        return d[name] if d is not None else default


class DebugScan:
    """Lecture complète du debug : portées, valeurs et changements.
    events : {(portée, nom): [(ligne debug, ligne source, valeur,
              nom brut ou None, origine ou None, libellé de portée)]}."""

    def __init__(self, lines, stop_row=None):
        self.events = {}
        self.stack = [Scope(GLOBAL, 1, 0)]
        self.other = {}
        self.calls = {}
        self.checked = 0      # lectures VAR dont la portée a pu être vérifiée
        self.agreed = 0       # ... et conformes au modèle
        self.visible = Visible(self)
        self._run(lines, stop_row)

    # -- portées ---------------------------------------------------------

    @property
    def top(self):
        return self.stack[-1]

    def find(self, name):
        """Portée la plus proche (pile remontée) où « name » existe."""
        for scope in reversed(self.stack):
            if name in scope.vars:
                return scope
        return None

    def _caller(self, wanted=None):
        """Portée du dessus pour un set return (nommée par « Return bloc »)."""
        for scope in reversed(self.stack[:-1]):
            if wanted is None or scope.name == wanted or \
                    (wanted == GLOBAL and scope.level == 1):
                return scope
        return self.stack[-2] if len(self.stack) > 1 else self.stack[0]

    def _add(self, scope, name, row, source_row, value, raw, origin):
        scope.vars[name] = value
        self.events.setdefault((scope.name, name), []).append(
            (row, source_row, value, raw, origin, scope.label))

    def _read(self, name, origin, value):
        """Ligne VAR : valeur lue dans la portée « origin »."""
        if origin == GLOBAL:
            expected = self.stack[0]
        else:
            expected = next((sc for sc in reversed(self.stack[1:])
                             if sc.name == origin), None)
            if expected is None:
                self.other[name] = value
                return
        # Contrôle : la portée prévue par le modèle est-elle celle du debug ?
        predicted = self.find(name)
        if predicted is not None:
            self.checked += 1
            if predicted is expected:
                self.agreed += 1
        expected.vars[name] = value

    # -- lecture ---------------------------------------------------------

    def _run(self, lines, stop_row):
        target = None    # portée cible de la balise : « global » ou « return »
        returned = None  # libellé affiché
        get_vars = set()
        get_name = None
        tokens = None    # [portée, nom, ligne, ligne source, nombre, nom brut]
        pending = None   # portée de la fonction appelée, avant son démarrage

        def flush_tokens():
            if tokens:
                scope, name, row, source_row, count, raw = tokens
                self._add(scope, name, row, source_row, str(count), raw,
                          'get token : nombre')

        for row, line in enumerate(lines):
            if stop_row is not None and row > stop_row:
                break
            if pending is not None and ('XPX TAG:' in line or
                                        'Starting function execution' in line):
                # Paramètres évalués : la fonction démarre dans sa portée.
                self.stack.append(pending)
                pending = None
            if 'XPX TAG:' in line:
                flush_tokens()
                target = returned = None
                get_vars = set()
                get_name = None
                tokens = None
            elif 'Exec ' in line and EXEC_RE.match(line):
                name = EXEC_RE.match(line).group(1)
                self.calls[name] = self.calls.get(name, 0) + 1
                # Les paramètres sont évalués dans la portée d'appel.
                pending = Scope(name, self.top.level + 1, self.calls[name])
            elif 'End of Exec' in line:
                match = END_EXEC_LINE_RE.match(line)
                if match and len(self.stack) > 1:
                    names = [s.name for s in self.stack[1:]]
                    if match.group(1) in names:
                        while self.stack[-1].name != match.group(1):
                            self.stack.pop()
                    self.stack.pop()
            elif 'FUNCTION PARAM' in line:
                match = PARAM_RE.match(line)
                if match:
                    value = match.group(2)
                    if '$' in value:
                        value = resolve_name(value, self.visible) or value
                    (pending or self.top).vars[match.group(1)] = value
            elif 'PARSE: Param NAME Value ' in line:
                get_name = line.split('PARSE: Param NAME Value ', 1)[1].strip()
            elif 'PARSE: Param GLOBAL ' in line:
                target, returned = 'global', 'global'
            elif 'Return bloc' in line:
                match = RETURN_BLOC_RE.search(line)
                target = ('return', match.group(1) if match else None)
                returned = 'return → ' + (match.group(1) if match else 'appelant')
            elif 'GET TOKEN ' in line:
                match = GET_TOKEN_RE.match(line)
                if match and get_name:
                    raw = get_name
                    if tokens is None:
                        name = resolve_name(raw, self.visible) or raw
                        tokens = [self.top, name, 0, 0, 0, raw if name != raw else None]
                    number = int(match.group(2))
                    self._add(tokens[0], tokens[1] + str(number), row,
                              int(match.group(1)), match.group(3),
                              raw + str(number) if tokens[5] else None, 'get token')
                    tokens[2:5] = [row, int(match.group(1)), max(tokens[4], number)]
            elif 'GET: ' in line:
                match = GET_FORMAT_RE.match(line)
                if match:
                    key, value = match.group(2), match.group(3)
                    if re.match(r'var\d*$', key):
                        get_vars.add(value)
                    elif key in get_vars:
                        self._add(self.top, key, row, int(match.group(1)), value,
                                  None, 'get format')
            elif 'VAR ' in line:
                if 'ESCAPE STR' in line:
                    continue
                for match in VAR_LINK_RE.finditer(line):
                    self._read(match.group(1), match.group(2), match.group(3))
                match = VAR_LAST_RE.match(line)
                if match:
                    self._read(match.group(1), match.group(2), match.group(3))
            elif 'SET' in line:
                match = SET_RE.match(line)
                if match:
                    raw, value = match.group(2), match.group(3)
                    name = resolve_name(raw, self.visible) or raw
                    if target == 'global':
                        scope = self.stack[0]
                    elif target:
                        scope = self._caller(target[1])
                    else:
                        scope = self.top
                    self._add(scope, name, row, int(match.group(1)), value,
                              raw if name != raw else None, returned)
        flush_tokens()

    def scope_of(self, name):
        """Portée où « name » est visible à l'endroit atteint."""
        scope = self.find(name)
        return scope.name if scope is not None else self.top.name


def set_events(lines):
    return DebugScan(lines).events


def _short(value):
    value = value.replace('\t', ' ')
    if len(value) > MAX_VALUE_LENGTH:
        return value[:MAX_VALUE_LENGTH] + '…'
    return value


BLOCK_END_RE = re.compile(r'^\s*\d+:\s*$')
NAME_CHARS_RE = re.compile(r'[\w.+\-\[\]$]+')


def key_at(view, pt, events):
    """((portée, nom), expression brute) sous la position pt, ou (None, None).
    $x$ -> x ; un nom calculé ($formName$.label) est résolu avec les
    valeurs visibles à cette ligne du debug."""
    line = view.line(pt)
    text = view.substr(line)
    column = pt - line.a
    for match in NAME_CHARS_RE.finditer(text):
        if match.start() <= column <= match.end():
            token = match.group(0)
            break
    else:
        return None, None
    lines = _lines(view)
    row = view.rowcol(pt)[0]
    # État à la fin de l'analyse de la balise (lignes VAR lues), avant le SET.
    end = row
    while end + 1 < len(lines) and not BLOCK_END_RE.match(lines[end + 1]) \
            and not SET_RE.match(lines[end]):
        end += 1
    state = DebugScan(lines, stop_row=end - 1 if SET_RE.match(lines[end]) else end)
    values = state.visible

    plain = token.strip('$')
    expr = None
    if '$' not in plain and '[' not in plain:
        name = plain
    elif token.startswith('$') and token.endswith('$') and token.count('$') == 2:
        # $tab[i]$ : variable indicée
        name = BRACKET_RE.sub(lambda m: values.get(m.group(1), m.group(0)), plain)
        expr = token if name != plain else None
    else:
        name = resolve_name(token, values)
        expr = token if name else None
        name = name or token
    if not name:
        return None, None

    # Changement enregistré sur cette ligne même (SET, GET…) : sa portée.
    for key, history in events.items():
        if key[1] == name and any(h[0] == row for h in history):
            return key, expr
    return (state.scope_of(name), name), expr


def _key_label(key):
    return '${}$ — {}'.format(key[1], key[0])


class XpxDebugPanelFillCommand(sublime_plugin.TextCommand):
    """Remplace le contenu du panneau (interne)."""

    def run(self, edit, text=''):
        self.view.set_read_only(False)
        self.view.replace(edit, sublime.Region(0, self.view.size()), text)
        self.view.set_read_only(True)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(0, 0))


class XpxDebugTrackVariableCommand(sublime_plugin.TextCommand):

    def is_enabled(self, name=None, event=None):
        return self.view.match_selector(0, 'text.xpx-debug')

    def is_visible(self, name=None, event=None):
        return self.is_enabled()

    def want_event(self):
        return True

    def run(self, edit, name=None, event=None):
        view = self.view
        self.expr = None
        lines = _lines(view)
        scan = DebugScan(lines)
        events = scan.events
        self.scan = scan

        key = None
        if name is not None:
            key = (scan.scope_of(name), name)
        else:
            if event:
                pt = view.window_to_text((event['x'], event['y']))
            elif len(view.sel()):
                pt = view.sel()[0].b
            else:
                pt = None
            if pt is not None:
                found, expr = key_at(view, pt, events)
                if found and (found in events or expr or view.match_selector(
                        pt, 'variable.other.readwrite.xpx')):
                    key = found
                    self.expr = expr

        if key is not None:
            self.show_history(key, lines, events)
            return

        if not events:
            sublime.status_message('XPX Debug : aucun changement de valeur dans ce fichier')
            return
        keys = sorted(events, key=lambda k: (k[1].lower(), k[0] != GLOBAL, k[0]))
        items = [
            sublime.QuickPanelItem(
                trigger=k[1],
                details='dernière valeur : ' + _short(events[k][-1][2]),
                annotation='{} — {} changement(s)'.format(k[0], len(events[k])),
                kind=(sublime.KIND_ID_VARIABLE, '$', 'Variable'))
            for k in keys
        ]
        view.window().show_quick_panel(
            items,
            lambda i: i >= 0 and self.show_history(keys[i], lines, events),
            placeholder='Variable à suivre (sensible à la casse)')

    def show_history(self, key, lines, events):
        view = self.view
        window = view.window()
        debug_path = view.file_name() or ''
        debug_name = os.path.basename(debug_path) or 'debug'
        history = events.get(key, [])
        name = key[1]

        try:
            marks = markers(lines)
            rows = []
            previous = None
            for number, (row, source_row, value, raw, origin, scope) in \
                    enumerate(history, 1):
                source = source_file(view, lines, row, marks)
                source_label = '{}:{}'.format(
                    os.path.basename(source) if source else '?', source_row)
                note = '   (inchangée)' if value == previous else ''
                if origin:
                    note += '   [{}]'.format(origin)
                if raw:
                    note += '   [via {}]'.format(raw)
                rows.append('{:>4}  {}:{:<6}  {:<30}  {:<24}  {} = {}{}'.format(
                    number, debug_name, row + 1, source_label, scope, name,
                    _short(value), note))
                previous = value
            if history:
                text = 'Variable {} : {} changement(s) de valeur — {}\n'.format(
                    _key_label(key), len(history), debug_name)
            else:
                text = ('Variable {} : aucun changement de valeur '
                        'dans {}.\n'.format(_key_label(key), debug_name))
            if self.expr:
                text += 'Nom calculé depuis {}\n'.format(self.expr)
            others = [k[0] for k in events if k[1] == name and k != key]
            if others:
                text += 'Même nom dans d\'autres portées : {}\n'.format(
                    ', '.join(sorted(set(others))))
            scan = getattr(self, 'scan', None)
            if scan and scan.checked:
                text += 'Portées vérifiées sur les lectures VAR : {:.1f} % ({}/{})\n'.format(
                    100.0 * scan.agreed / scan.checked, scan.agreed, scan.checked)
            if history:
                text += ('Double-clic sur une ligne : aller à la ligne du debug '
                         '(puis F12 : code source).\n\n')
                text += '\n'.join(rows) + '\n'
        except Exception:
            import traceback
            text = 'XPX Debug : erreur pendant le suivi de ${}$\n\n{}'.format(
                name, traceback.format_exc())

        panel = window.find_output_panel(PANEL_NAME) or window.create_output_panel(PANEL_NAME)
        settings = panel.settings()
        settings.set('result_file_regex', r'^\s*\d+\s+(\S+\.debug):(\d+)')
        settings.set('result_base_dir', os.path.dirname(debug_path))
        settings.set('word_wrap', False)
        settings.set('line_numbers', False)
        settings.set('gutter', False)
        settings.set('scroll_past_end', False)
        panel.run_command('xpx_debug_panel_fill', {'text': text})
        window.run_command('show_panel', {'panel': 'output.' + PANEL_NAME})

        # Lignes concernées soulignées dans le debug.
        view.add_regions(
            REGION_KEY,
            [view.line(view.text_point(row, 0)) for row, *_ in history],
            scope='region.yellowish',
            flags=sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE
            | sublime.DRAW_SOLID_UNDERLINE)


class XpxDebugClearTrackingCommand(sublime_plugin.TextCommand):
    """Efface le soulignement et ferme le panneau du suivi de variable."""

    def is_enabled(self):
        return bool(self.view.get_regions(REGION_KEY))

    def run(self, edit):
        self.view.erase_regions(REGION_KEY)
        window = self.view.window()
        if window and window.active_panel() == 'output.' + PANEL_NAME:
            window.run_command('hide_panel')
