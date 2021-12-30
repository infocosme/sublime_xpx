import sublime, sublime_plugin
import re

# Deux fonctions déjà définies dans HTML : détruites.

def match(rex, str):
    m = rex.match(str)
    if m:
        return m.group(0)
    else:
        return None

def make_completion(tag):
    # make it look like
    # ("table\tTag", "table>$1</table>"),
    return (tag + '\tTag', tag + '>$0</' + tag + '>')

def get_tag_to_attributes():
    """
    Returns a dictionary with attributes accociated to tags
    This assumes that all tags can have global attributes as per MDN:
    https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes
    """

    # Map tags to specific attributes applicable for that tag
    # Cette liste est utilisée pour la suggestion des attributs en fonction de la balise.
    tag_dict = {
        'cond' : ['expr'],
        'connect' : ['base', 'close', 'id', 'info', 'name', 'pass', 'port', 'server', 'socket', 'transaction'],
        'cookie' : ['dir', 'domain', 'name', 'samesite', 'ttl', 'value'],
        'create' : ['dir'],
        'csv' : ['file', 'name', 'sep', 'value'],
        'debug' : ['mode', 'printparam', 'suffix'],
        'else' : ['expr'],
        'file' : ['close', 'content', 'delete', 'eol', 'exist', 'name', 'mode', 'model', 'open', 'path', 'read', 'write', 'xpx'],
        'function' : ['name', 'exec'],
        'get' : ['format', 'name', 'option', 'tag', 'token', 'value'],
        'http' : ['content', 'get', 'headers', 'name', 'port', 'timeout'],
        'include' : ['file', 'option'],
        'mail' : ['cc', 'cci', 'charset', 'file', 'from', 'headers', 'join', 'msg', 'reply', 'smtp', 'subject', 'to', 'type'],
        'noparse' : [],
        'pdf' : ['addpage', 'align', 'bgcolor', 'border', 'calc', 'close', 'color', 'file', 'font', 'frame', 'gettext', 'getx', 'gety', 'href', 'leading', 'line', 'mode', 'name', 'padding', 'pagesize', 'path', 'rect', 'rotate', 'round', 'size', 'style', 'text'],
        'pict' : ['border', 'calc', 'close', 'color', 'content', 'copy', 'dest', 'fill', 'font', 'geth', 'getw', 'height', 'name', 'path', 'position', 'rect', 'rotate', 'size', 'text', 'transparency', 'width', 'x', 'y'],
        'scope' : ['name'],
        'set' : ['bit', 'bitoff', 'biton', 'by', 'charset', 'chartohexa', 'datetime', 'decode64', 'decrypt', 'encode64', 'encrypt', 'expr', 'format', 'global', 'hash', 'hex2bin', 'hexatochar', 'hmac', 'html2text', 'keycode', 'lang', 'len', 'local', 'lowcase', 'ltrim', 'money', 'name', 'noaccent', 'rand', 'replace', 'return', 'rtrim', 'session', 'strcode', 'strdecode', 'strescape', 'svg2pdf', 'trim', 'upcase', 'urlcode', 'value', 'xmlcode'],
        'setarea' : ['name', 'option'],
        'sql' : ['connect', 'maxrows', 'option', 'query', 'start'],
        'wait' : ['value'],
        'while' : ['expr'],
        'xpath' : ['file', 'select', 'value'],
        'xproc' : ['file', 'select', 'value']
    }

    # Assume that global attributes are common to all HTML elements
    global_attributes = [
    ]

    # Extend `global_attributes` by the event handler attributes
    global_attributes.extend([
    ])

    for attributes in tag_dict.values():
        attributes.extend(global_attributes)

    return tag_dict

def get_attribute_to_values():
    """
    Returns a dictionary with properties accociated to attribute
    """

    # Map attributes to specific properties applicable for that attribute
    # Cette liste est utilisée pour la suggestion des propriétés en fonction de l'attribut.
    attribute_dict = {
        # <pdf>
        'align' : ['center', 'left', 'right'],
        # <mail>
        'charset' : ['iso-8859-1', 'utf-8'],
        # <pdf>
        'font' : ['Courier', 'Helvetica', 'Times', 'Symbol', 'ZapfDingbats'],
        # <set>
        'format' : ['yyyy-mm-dd', 'yymmddhhmnss', 'tt'],
        'hash' : ['md5', 'sha1', 'sha256'],
        # <debug> <file> <pdf>
        'mode' : ['<debug mode:', 'auto', 'normal', 'off', '<file mode:', 'append', 'read', 'write', '<pdf mode:', 'clip', 'noclip', 'pagebreak'],
        # <include> <sql>
        'option' : ['<include option:', 'noparse', 'once', 'parse', '<setarea option:', 'parse', 'noparse', '<sql option:', 'enter', 'notenter'],
        # <cookie>
        'samesite' : ['Lax', 'Strict'],
        # <connect>
        'server' : ['localhost'],
        # <mail>
        'smtp' : ['localhost'],
        # <pdf>
        'style' : ['b', 'i', 'n', 'u'],
        # <http>
        'timeout' : ['30', '60'],
        # <connect>
        'transaction' : ['normal', 'rollback'],
        # <mail>
        'type' : ['html', 'multipart', 'text']
    }

    # Assume that global attributes are common to all HTML elements
    global_values = [
    ]

    # Extend `global_attributes` by the event handler attributes
    global_values.extend([
    ])

    for value in attribute_dict.values():
        value.extend(global_values)

    return attribute_dict

class XpxTagCompletions(sublime_plugin.EventListener):
    """
    Provide tag completions for HTML
    It matches just after typing the first letter of a tag name
    """
    def __init__(self):
        completion_list = self.default_completion_list()
        self.prefix_completion_dict = {}
        # construct a dictionary where the key is first character of
        # the completion list to the completion
        for s in completion_list:
            prefix = s[0][0]
            self.prefix_completion_dict.setdefault(prefix, []).append(s)

        # construct a dictionary from (tag, attribute[0]) -> [attribute]
        self.tag_to_attributes = get_tag_to_attributes()

        # construct a dictionary from (attribute, propertie[0]) -> [propertie]
        self.attribute_to_values = get_attribute_to_values()

    def on_query_completions(self, view, prefix, locations):
        # Only trigger within XPX
        if not view.match_selector(locations[0], "text.html.xpx"):
            return []

        # Complétion XPX sur les valeurs d'attributs.
        is_inside_attribute = view.match_selector(locations[0],
                "text.html.xpx meta.attribute-with-value string.quoted.double")

        # check if we are inside a tag
        # tag XPX reconnu ou début de tag inconnu.
        is_inside_tag = view.match_selector(locations[0],
                "text.html.xpx meta.tag - text.html.xpx punctuation.definition.tag.begin")

        return self.get_completions(view, prefix, locations, is_inside_tag, is_inside_attribute)

    def get_completions(self, view, prefix, locations, is_inside_tag, is_inside_attribute):

        pt = locations[0] - len(prefix) - 1
        ch = view.substr(sublime.Region(pt, pt + 1))

        # print('prefix: "', prefix, '"')
        # print('location0:', locations[0])
        # print('substr:', view.substr(sublime.Region(locations[0], locations[0] + 3)), '!end!')
        # print('is_inside_tag', is_inside_tag)
        # print('ch:', ch)

        completion_list = []

        if is_inside_attribute:
            completion_list = self.get_values_completions(view, locations[0], prefix)
            return (completion_list, sublime.INHIBIT_WORD_COMPLETIONS)

        # Définir la liste sur les attributs du tag courant.
        if is_inside_tag and ch != '<':
            if ch in [' ', '\t', '\n']:
                # maybe trying to type an attribute
                completion_list = self.get_attribute_completions(view, locations[0], prefix)
            # only ever trigger completion inside a tag if the previous character is a <
            # this is needed to stop completion from happening when typing attributes
            # return (completion_list, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
            return (completion_list, sublime.INHIBIT_WORD_COMPLETIONS)

        # 23/08/2017 : Permettre la complétion des balises XPX à partir de rien (CTRL+Espace)
        # Définir la liste sur la liste complète des tags XPX : l'utilisateur ne se rappelle pas du nom de la balise.
        if prefix == '' and ch != '<':
            # completion_list = self.default_xpx_tags_list()
            completion_list = []
            # return (completion_list, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
            return (completion_list, sublime.INHIBIT_WORD_COMPLETIONS)
        if prefix == '' and ch == '<':
            # need completion list to match
            # return ([], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
            return ([], sublime.INHIBIT_WORD_COMPLETIONS)

        # match completion list using prefix
        # L'utilisateur teste une première lettre pour filtrer les noms de balises.
        completion_list = self.prefix_completion_dict.get(prefix[0], [])

        # if the opening < is not here insert that
        # Cas d'une demande d'auto-complétion sans saisie préalable du < (Ctrl+Espace).
        if ch != '<':
            completion_list = [(pair[0], '<' + pair[1]) for pair in completion_list]

        flags = 0
        if is_inside_tag:
            # flags = sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS
            flags = sublime.INHIBIT_WORD_COMPLETIONS

        return (completion_list, flags)

    def default_xpx_tags_list(self):
        """
        Generate a default completion list for XPX Tags
        Aide à la recherche du nom de la balise.
        """

        default_list = []
        # Liste des tags XPX normaux : de type block ?
        # 'cond', 'function', 'noparse', 'scope', 'setarea', 'sql', 'while'
        normal_tags = ([
        ])

        for tag in normal_tags:
            default_list.append(make_completion(tag))
            default_list.append(make_completion(tag.upper()))

        # Cette liste est utilisée pour remplir la suggestion de balise à la frappe.
        # L'expand de balise s'effectue sur le premier snippet ne contenant que 2 arguments.
        # set name value sera ignoré vs set namevalue qui sera accepté.
        default_list += ([
            ('cond\tXPX', '<cond $1>$0</cond>\n'),
            ('connect\tXPX', '<connect $1>\n'),
            ('cookie\tXPX', '<cookie name=\"$1\">'),
            ('create\tXPX', '<create dir=\"$1\">'),
            ('csv\tXPX', '<csv $1>$0</csv>\n'),
            ('debug\tXPX', '<debug>'),
            ('else\tXPX', '<else>'),
            ('file\tXPX', '<file>'),
            ('function\tXPX', '<function name=\"$1\">$0</function>'),
            ('get\tXPX', '<get value=\"$1\">'),
            ('http\tXPX', '<http name=\"$1\" get=\"$2\" timeout=\"$3\" content=\"$4\">'),
            ('include\tXPX', '<include file=\"$1\">'),
            ('mail\tXPX', '<mail smtp=\"$1\"\n\t\tfrom=\"$2\"\n\t\tto=\"$3\"\n\t\tsubject=\"$4\"\n\t\ttype=\"$5\">'),
            ('noparse\tXPX', '<noparse>$0</noparse>'),
            ('pdf\tXPX', '<pdf>'),
            ('pict\tXPX', '<pict name=\"$1\" dest=\"$2\">'),
            ('scope\tXPX', '<scope>$0</scope>'),
            ('set\tXPX', '<set>'),
            ('setarea\tXPX', '<setarea name=\"$1\">$0</setarea>'),
            ('sql\tXPX', '<sql query=\"$1\">$0</sql>'),
            ('wait\tXPX', '<wait value=\"$1\">'),
            ('while\tXPX', '<while expr=\"$1\">$0</while>'),
            ('xpath\tXPX', '<xpath>'),
            ('xproc\tXPX', '<xproc>')
        ])

        return default_list

    def default_completion_list(self):
        """
        Generate a default completion list for HTML
        """
        default_list = []
        normal_tags = ([
        ])

        for tag in normal_tags:
            default_list.append(make_completion(tag))
            default_list.append(make_completion(tag.upper()))

        # Cette liste est utilisée pour remplir la suggestion de balise à la frappe.
        # L'expand de balise s'effectue sur le premier snippet ne contenant que 2 arguements.
        # "set name value" sera ignoré vs "set namevalue" qui sera accepté.
        default_list += ([
            ('cond\tXPX', 'cond expr=\"$1\">\n\t$2\n</cond>$0'),
            ('cond else\tXPX', 'cond expr=\"$1\">\n\t$2\n<else>\n\t$3\n</cond>$0'),
            ('cond else expr\tXPX', 'cond expr=\"$1\">\n\t$2\n<else expr=\"$3\">\n\t$4\n<else>\n\t$5\n</cond>$0'),
            ('connect\tXPX', 'connect server=\"$1\" base=\"$2\" name=\"$3\" pass=\"$4\">'),
            ('cookie name\tXPX', 'cookie name=\"$1\">'),
            ('create dir\tXPX', 'create dir=\"$1\">'),
            ('csv name\tXPX', 'csv name=\"$1\">'),
            ('csv file\tXPX', 'csv file=\"$1\">'),
            ('debug\tXPX', 'debug>'),
            ('else\tXPX', 'else>'),
            ('else expr\tXPX', 'else expr=\"$1\">'),
            ('file\tXPX', 'file>'),
            ('function name\tXPX', 'function name=\"$1\">$0</function>'),
            ('get valueformat\tXPX', 'get value=\"$1\" format=\"$2\">'),
            ('get valuetoken\tXPX', 'get value=\"$1\" token=\"$2\" name=\"$3\">'),
            ('http\tXPX', 'http name=\"$1\" get=\"$2\" timeout=\"$3\" content=\"$4\">'),
            ('include file\tXPX', 'include file=\"$1\">'),
            ('mail\tXPX', 'mail smtp=\"$1\"\n\t\tfrom=\"$2\"\n\t\tto=\"$3\"\n\t\tsubject=\"$4\"\n\t\ttype=\"$5\">'),
            ('noparse\tXPX', 'noparse>$0</noparse>'),
            ('pdf\tXPX', 'pdf>'),
            ('pict name\tXPX', 'pict name=\"$1\" dest=\"$2\">'),
            ('scope\tXPX', 'scope>$0</scope>'),
            ('set namevalue\tXPX', 'set name=\"$1\" value=\"$2\">'),
            ('set nameexpr\tXPX', 'set name=\"$1\" expr=\"$2\">'),
            ('set nameencode64\tXPX', 'set name=\"$1\" encode64=\"$2\">'),
            ('set namehash\tXPX', 'set name=\"$1\" value=\"$2\" hash=\"$3\" hmac=\"$4\">'),
            ('set datetime\tXPX', 'set datetime=\"$1\" format=\"$2\">'),
            ('set global\tXPX', 'set global=\"$1\">'),
            ('set namedebug1\tXPX', 'set name=\"phcdebug\" value=\"1\">'),
            ('set namedebug0\tXPX', 'set name=\"phcdebug\" value=\"0\">'),
            ('setarea name\tXPX', 'setarea name=\"$1\">$0</setarea>'),
            ('sql query\tXPX', 'sql query=\"$1\">$0</sql>'),
            ('wait value\tXPX', 'wait value=\"$1\">'),
            ('while expr\tXPX', 'while expr=\"$1\">$0</while>'),
            ('xpath\tXPX', 'xpath>$0</xpath>'),
            ('xproc\tXPX', 'xproc>$0</xproc>')
        ])

        return default_list

    def get_attribute_completions(self, view, pt, prefix):
        SEARCH_LIMIT = 500
        search_start = max(0, pt - SEARCH_LIMIT - len(prefix))
        line = view.substr(sublime.Region(search_start, pt + SEARCH_LIMIT))

        line_head = line[0:pt - search_start]
        line_tail = line[pt - search_start:]

        # find the tag from end of line_head
        i = len(line_head) - 1
        tag = None
        space_index = len(line_head)
        while i >= 0:
            c = line_head[i]
            if c == '<':
                # found the open tag
                tag = line_head[i + 1:space_index]
                break
            elif c == ' ':
                space_index = i
            i -= 1

        # check that this tag looks valid
        if not tag or not tag.isalnum():
            return []

        # determines whether we need to close the tag
        # default to closing the tag
        suffix = '>'

        for c in line_tail:
            if c == '>':
                # found end tag
                suffix = ''
                break
            elif c == '<':
                # found another open tag, need to close this one
                break

        if suffix == '' and not line_tail.startswith(' ') and not line_tail.startswith('>'):
            # add a space if not there
            suffix = ' '

        # got the tag, now find all attributes that match
        attributes = self.tag_to_attributes.get(tag, [])
        # ("class\tAttr", "class="$1">"),
        attri_completions = [(a + '\tAttr', a + '="$1"' + suffix) for a in attributes]
        return attri_completions

    # pt = locations[0]
    # prefix : mot sur lequel la complétion est demandée : partie avant le curseur.
    # locations[0] : Position du curseur au moment du clic.
    def get_values_completions(self, view, pt, prefix):

        # print('prefix: "', prefix, '"')
        # print('pt: "', pt, '"')

        myPosPunctuation = view.find_by_class(pt, False, sublime.CLASS_PUNCTUATION_START)
        # print('myPosPunctuation: "', myPosPunctuation ,'"')
        myPosAttributeName = view.find_by_class(myPosPunctuation, False, sublime.CLASS_WORD_START)
        # print('myPosAttributeName: "', myPosAttributeName ,'"')
        myAttributeName = view.substr(sublime.Region(myPosAttributeName, myPosPunctuation))
        # print('myAttributeName: "', myAttributeName ,'"')

        # got the attribute name, now find all properties values that match
        values = self.attribute_to_values.get(myAttributeName, [])
        # ("class\tAttr", "class"),
        values_completions = [(value + '\tXPX value', value) for value in values]
        return values_completions

