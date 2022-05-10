import html
import html.entities
import re

import sublime
import sublime_plugin
import timeit

from functools import cached_property, wraps

__all__ = ['XpxTagCompletions']

KIND_ENTITY_MARKUP = (sublime.KIND_ID_MARKUP, 'e', 'Entity')
KIND_ENTITY_SNIPPET = (sublime.KIND_ID_SNIPPET, 'e', 'Entity')
KIND_ATTRIBUTE_SNIPPET = (sublime.KIND_ID_SNIPPET, 'a', 'Attribute')
KIND_TAG_MARKUP = (sublime.KIND_ID_MARKUP, 't', 'Tag')
KIND_TAG_SNIPPET = (sublime.KIND_ID_SNIPPET, 's', 'Tag')
KIND_ATTRIBUTE_VALUE = (sublime.KIND_ID_VARIABLE, 'v', 'Variable')

ENABLE_TIMING = False


boolean_attributes = {
}


def xpx_timing(func):
    @wraps(func)
    def wrap(*args, **kw):
        if ENABLE_TIMING:
            ts = timeit.default_timer()
        result = func(*args, **kw)
        if ENABLE_TIMING:
            te = timeit.default_timer()
            print(f"{func.__name__}({args}, {kw}) took: {1000.0 * (te - ts):2.3f} ms")
        return result
    return wrap


def xpx_match(pattern, string):
    match = pattern.match(string)
    if match:
        return match.group(0)
    else:
        return None


def get_xpx_entity_completions():
    """
    Generate a completion list for XPX entities.
    """
    return sublime.CompletionList(
        [
            sublime.CompletionItem(
                trigger='#00;',
                completion='#${1:00};',
                completion_format=sublime.COMPLETION_FORMAT_SNIPPET,
                kind=KIND_ENTITY_SNIPPET,
                details='Base-10 Unicode character',
            ),
            sublime.CompletionItem(
                trigger='#x0000;',
                completion='#x${1:0000};',
                completion_format=sublime.COMPLETION_FORMAT_SNIPPET,
                kind=KIND_ENTITY_SNIPPET,
                details='Base-16 Unicode character',
            ),
            *(
                sublime.CompletionItem(
                    trigger=entity,
                    annotation=printed,
                    completion=entity,
                    completion_format=sublime.COMPLETION_FORMAT_TEXT,
                    kind=KIND_ENTITY_MARKUP,
                    details=f'Renders as <code>{printed}</code>',
                )
                for entity, printed in html.entities.html5.items()
                if entity.endswith(';')
            )
        ],
        sublime.INHIBIT_WORD_COMPLETIONS
    )


def get_xpx_tag_completions(inside_tag=True):
    """
    Generate a default completion list for XPX
    """
    normal_tags = (
        'cond','csv','debug',
        'function',
        'scope','setarea','sql','while'
    )
    inline_tags = (
        'connect','cookie','create','debug',
        'else','file','function','get','http','include','mail','pdf','pict',
        'set','system','wait','xpath','xproc'
    )
    snippet_tags = (
        ('file close', 'file close=\"$1\" />$0'),
    )

    tag_begin = '' if inside_tag else '<'

    # Ajout de l'expand inline (le deuxième).
    return sublime.CompletionList(
        [
            *(
                sublime.CompletionItem(
                    trigger=tag,
                    annotation='block xpx',
                    completion=f'{tag_begin}{tag}>$0</{tag}>',
                    completion_format=sublime.COMPLETION_FORMAT_SNIPPET,
                    kind=KIND_TAG_MARKUP,
                    details=f'Expands to <code>&lt;{tag}&gt;$0&lt;/{tag}&gt;</code>'
                )
                for tag in normal_tags
            ),
            *(
                sublime.CompletionItem(
                    trigger=tag,
                    annotation='inline xpx',
                    completion=f'{tag_begin}{tag} $0/>',
                    completion_format=sublime.COMPLETION_FORMAT_SNIPPET,
                    kind=KIND_TAG_MARKUP,
                    details=f'Expands to <code>&lt;{tag} /&gt;</code>'
                )
                for tag in inline_tags
            ),
            *(
                sublime.CompletionItem(
                    trigger=tag,
                    annotation='snippet xpx',
                    completion=f'{tag_begin}{completion}',
                    completion_format=sublime.COMPLETION_FORMAT_SNIPPET,
                    kind=KIND_TAG_SNIPPET,
                    details=f'Expands to <code>&lt;{html.escape(completion)}</code>'
                )
                for tag, completion in snippet_tags
            )
        ],
        sublime.INHIBIT_WORD_COMPLETIONS
    )


def get_list_attributes(view, pt, tagname, endpt):
    #print("get_list_attributes")

    listAttrName = []
    execName = ""
    #print("pt:", end="")
    #print(pt, end=" ")
    #print("end:", end="")
    #print(endpt)
    mypt = pt + len(tagname)
    while (mypt<endpt):
        # Recherche du nom de l'attribut.
        myPosPunctuation = view.find_by_class(mypt, True, sublime.CLASS_PUNCTUATION_START)
        #print(myPosPunctuation)
        mynext = view.substr(sublime.Region(myPosPunctuation, myPosPunctuation+1))
        if ( mynext == '/' or mynext == '>'):
            break
        myPosAttributeName = view.find_by_class(myPosPunctuation, False, sublime.CLASS_WORD_START)
        myAttributeName = view.substr(sublime.Region(myPosAttributeName, myPosPunctuation))
        listAttrName.append(myAttributeName)
        #print(myAttributeName)
        mypt = myPosPunctuation
        #print(view.substr(sublime.Region(mypt, mypt+1)))
        #print(mypt)
        mynext = view.substr(sublime.Region(mypt, mypt+3))
        #print(mynext)
        if (mynext == '=""'):
            myPosPunctuation1 = mypt + 2
        else:
            myPosPunctuation1 = view.find_by_class(mypt, True, sublime.CLASS_PUNCTUATION_START)
        #print(myPosPunctuation1)
        myAttributeValue = view.substr(sublime.Region(mypt+2, myPosPunctuation1))
        if (myAttributeName == "exec"):
            execName = myAttributeValue
        #print("val:'", end="")
        #print(myAttributeValue, end="'")
        #print()
        mypt = myPosPunctuation1
    return listAttrName, execName


def get_xpx_tag_attributes(view, pt):
    """
    Returns a dictionary with attributes accociated to tags
    """
    # Map tags to specific attributes applicable for that tag
    tag_attr_dict = {
        'cond': ['expr'],
        'connect': ['base', 'close', 'id', 'info', 'name', 'pass', 'port', 'server', 'socket', 'transaction'],
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
        'xproc': ['file', 'select', 'value']
    }

    # Assume that global attributes are common to all XPX elements
    # Pas d'attributs globaux en XPX : désactivation du code.
    """
    global_attributes = (
    )

    for attributes in tag_attr_dict.values():
        attributes.extend(global_attributes)
    """

    # Complément avec un éventuel prototype de fonction.
    # Contrôle si la complétion a été demandée (view, pt) sur un function exec dont la valeur existe.
    # Recherche du prototype correspondant parmi les symbol.
    # Renvoi des attributs du prototype trouvé.
    
    # Lecture de la région tag dans laquelle la complétion est demandée.
    myregionfunction = view.expand_by_class(pt,sublime.CLASS_PUNCTUATION_START | sublime.CLASS_PUNCTUATION_END,"<>")
    #print(myregionfunction)
    #print(view.substr(myregionfunction))
    # Lecture du début de la région.
    ptfindtag = myregionfunction.begin()+1
    # Lecture du nom du tag de la région courante.
    # myTagName=view.substr(view.expand_by_class(ptfindtag,sublime.CLASS_WORD_START | sublime.CLASS_WORD_END))
    myTagName = view.substr(view.word(ptfindtag))
    if (myTagName == 'function'):
        #print("completion dans function")
        myresult = get_list_attributes(view, ptfindtag-1, myTagName, myregionfunction.end())
        #print(myresult[0])
        #print(myresult[1])
        if ('exec' in myresult[0]):
            #print("Recherche du prototype function ", end="")
            #print(myresult[1])
            mywindow = sublime.active_window()
            # Recherche d'une entrée symbol correspondant au nom de la fonction.
            mylocations=mywindow.symbol_locations("<function name=\"xpxForms.writeCache\" formName=\"\">",sublime.SYMBOL_SOURCE_INDEX,sublime.SYMBOL_TYPE_DEFINITION)
            #print(mylocations)
    
    return tag_attr_dict


def get_xpx_attribute_values(myAttributeName):
    """
    Fonction créée pour XPX.
    Returns a dictionary with values accociated to attributes.
    """
    # Map attributes to specific values applicable for that attribute
    # First: Attribute name, Second: Tag name to associate.
    attribute_dict = {
        'align' : {
            'pdf': ['center', 'left', 'right']
        },
        'charset' : {
            'mail': ['iso-8859-1', 'utf-8']
        },
        'font' : {
            'pdf': ['Courier', 'Helvetica', 'Times', 'Symbol', 'ZapfDingbats']
        },
        'format' : {
            'set': ['yyyy-mm-dd', 'yymmddhhmnss', 'tt']
        },
        'hash' : {
            'set': ['md5', 'sha1', 'sha256']
        },
        'mode' : {
            'debug': ['auto', 'normal', 'off'],
            'file': ['append', 'read', 'write'],
            'pdf': ['clip', 'noclip', 'pagebreak']
        },
        'option' : {
            'include': ['noparse', 'once', 'parse'], 
            'setarea': ['parse', 'noparse'],
            'sql': ['enter', 'notenter']
        },
        'samesite' : {
            'cookie': ['Lax', 'Strict']
        },
        'server' : {
            'connect': ['localhost']
        },
        'smtp' : {
            'mail': ['localhost']
        },
        'style' : {
            'pdf': ['b', 'i', 'n', 'u']
        },
        'timeout' : {
            'http': ['30', '60']
        },
        'transaction' : {
            'connect': ['normal', 'rollback']
        },
        'type' : {
            'mail': ['html', 'multipart', 'text']
        }
    }
    if myAttributeName in attribute_dict.keys():
        return attribute_dict.get(myAttributeName, [])
    return None


class XpxTagCompletions(sublime_plugin.EventListener):
    """
    Provide tag completions for XPX
    """

    @cached_property
    def entity_completions(self):
        return get_xpx_entity_completions()

    @cached_property
    def tag_abbreviations(self):
        return get_xpx_tag_completions(inside_tag=False)

    @cached_property
    def tag_completions(self):
        return get_xpx_tag_completions(inside_tag=True)

    @cached_property
    def tag_name_completions(self, view, pt):
        """
        Create a completion list with all known tag names (mais sans les < et > de la syntaxe).
        Uniquement les noms des balises.
        Cas exceptionnel d'une complétion demandée sur un <>.

        It uses the keys of `self.tag_attributes` dictionary as it contains
        all known/supported tag names and is available/cached anyway.
        """
        return sublime.CompletionList(
            [
                sublime.CompletionItem(
                    trigger=tag,
                    annotation='xpx',
                    completion_format=sublime.COMPLETION_FORMAT_TEXT,
                    kind=KIND_TAG_MARKUP,
                    details=f'Expands to <code>{html.escape(tag)}</code>'
                )
                for tag in get_xpx_tag_attributes(view, pt)
            ],
            sublime.INHIBIT_WORD_COMPLETIONS
        )

    @xpx_timing
    def on_query_completions(self, view, prefix, locations):
        """
        Fonction générale de complétion : tout part de cette fonction.
        """

        # Complétion XPX uniquement dans un source XPX.
        if not view.match_selector(locations[0], "text.html.xpx"):
            return None

        # Complétion XPX uniquement si non interdit en configuration du langage.
        settings = sublime.load_settings('XPX.sublime-settings')
        if settings.get('disable_default_completions'):
            return None

        # Lecture du caret avant et après afin de déterminer un contexte de complétion.
        pt = locations[0] - len(prefix) - 1
        ch = view.substr(sublime.Region(pt, pt + 1))

        # Complétion sur les codes HTML.
        # Inutile donc en XPX, déjà pris en compte en HTML.
        #if ch == '&':
        #    return self.entity_completions

        # Complétion normale : on démarre une balise donc on affiche les balises XPX possibles.
        # Se déclenche uniquement à la première tentative de complétion sur <.
        if ch == '<':
            if view.match_selector(locations[0], "text.html.xpx - (meta.tag.block.any.xpx | meta.tag.inline.any.xpx)"):
                # If the caret is in front of `>` complete only tag names.
                # see: https://github.com/sublimehq/sublime_text/issues/3508
                ch = view.substr(sublime.Region(locations[0], locations[0] + 1))
                if ch == '>':
                    return self.tag_name_completions(view, locations[0])
                return self.tag_completions

        # Complétion des nom de propriété : attributs
        # Note: Exclude opening punctuation to enable abbreviations
        #       if the caret is located directly in front of a xpx tag.
        # Si la demande de complétion se déclenche dans une balise XPX alors on recherche les attributs possibles.
        # Le scope doit être balise XPX sans propriété avec valeur : donc normalement emplacement d'un nouvel attribut.
        # Le caret précédent doit obligatoirement être un séparateur entre la balise et le nom de l'attribut.
        if view.match_selector(locations[0], "(meta.tag.block.any.xpx | meta.tag.inline.any.xpx) - (entity.name.tag.xpx | entity.other.attribute-name.xpx | entity.other.attribute-value.xpx)"):
            if ch in ' \f\n\t':
                return self.attribute_completions(view, locations[0], prefix)

        if view.match_selector(locations[0], "text.html.xpx meta.attribute-with-value.html string.quoted.double.html - entity.other.attribute-name.xpx"):
            return self.value_attribute_completions(view, locations[0], prefix)

        # Sinon rien.
        return None

    def expand_tag_attributes(self, view, locations):
        """
        The method responds to on_query_completions, but conceptually it's
        expanding expressions, rather than completing words.

        It expands these simple expressions:

            tag.class -> <tag class="class"></tag>
            tag#id    -> <tag id="id"></tag>
        
        Recherche des balises possibles et des snippets possibles.
        """

        # Get the contents of each line, from the beginning of the line to
        # each point
        lines = [
            view.substr(sublime.Region(view.line(pt).a, pt))
            for pt in locations
        ]

        # Reverse the contents of each line, to simulate having the regex
        # match backwards
        lines = [line[::-1] for line in lines]

        # Check the first location looks like an expression
        pattern = re.compile(r"([-\w]+)([.#])(\w+)")
        expr = xpx_match(pattern, lines[0])
        if not expr:
            return None

        # Ensure that all other lines have identical expressions
        for line in lines[1:]:
            ex = xpx_match(pattern, line)
            if ex != expr:
                return None

        # Return the completions
        arg, op, tag = pattern.match(expr).groups()

        arg = arg[::-1]
        tag = tag[::-1]
        expr = expr[::-1]

        attr = 'class' if op == '.' else 'id'
        snippet = f'<{tag} {attr}=\"{arg}\">$0</{tag}>'

        return sublime.CompletionList(
            [
                sublime.CompletionItem(
                    trigger=expr,
                    completion=snippet,
                    completion_format=sublime.COMPLETION_FORMAT_SNIPPET,
                    kind=KIND_TAG_MARKUP,
                    details=f'Expands to <code>{html.escape(snippet)}</code>'
                )
            ],
            sublime.INHIBIT_WORD_COMPLETIONS
        )

    def attribute_completions(self, view, pt, prefix):
        """
        Recherche des attributs possibles pour le tag courant.
        """

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
            return None

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

        if suffix == '' and line_tail[0] not in ' >':
            # add a space if not there
            suffix = ' '

        # ensure the user can always tab to the end of the completion
        suffix += '$0'

        # got the tag, now find all attributes that match
        # La liste de complétion est filtrée sur les entrées attributes calculées en haut.
        # Suppression du test sur attributes boolean.
        #            completion=f'{attr}{suffix}' if attr in boolean_attributes else f'{attr}="$1"{suffix}',
        # Ajout des view et pt dans prototype tag_attributes afin de pouvoir compléter avec le prototype function éventuel.
        return sublime.CompletionList(
            [
                sublime.CompletionItem(
                    trigger=attr,
                    annotation='xpx',
                    completion=f'{attr}="$1"{suffix}',
                    completion_format=sublime.COMPLETION_FORMAT_SNIPPET,
                    kind=KIND_ATTRIBUTE_SNIPPET
                )
                for attr in get_xpx_tag_attributes(view, pt).get(tag, [])
            ],
            sublime.INHIBIT_WORD_COMPLETIONS
        )

    def value_attribute_completions(self, view, pt, prefix):
        """
        Recherche du nom d'attribut concerné à partir de pt.
        prefix n'est pas renseigné.
        """
        # Recherche du nom de l'attribut.
        myPosPunctuation = view.find_by_class(pt, False, sublime.CLASS_PUNCTUATION_START)
        myPosAttributeName = view.find_by_class(myPosPunctuation, False, sublime.CLASS_WORD_START)
        myAttributeName = view.substr(sublime.Region(myPosAttributeName, myPosPunctuation))

        # Recherche du nom du tag.
        ptfindtag = view.expand_by_class(pt,sublime.CLASS_PUNCTUATION_START | sublime.CLASS_PUNCTUATION_END,"<>").begin()+1
        myTagName=view.substr(view.expand_by_class(ptfindtag,sublime.CLASS_WORD_START | sublime.CLASS_WORD_END))

        # got the tag,attribute, now find all values that match
        if get_xpx_attribute_values(myAttributeName):
            return sublime.CompletionList(
                [
                    sublime.CompletionItem(
                        trigger=val,
                        annotation='xpx',
                        completion=val,
                        completion_format=sublime.COMPLETION_FORMAT_TEXT,
                        kind=KIND_ATTRIBUTE_VALUE
                    )
                    for val in get_xpx_attribute_values(myAttributeName).get(myTagName, [])
                ],
                sublime.INHIBIT_WORD_COMPLETIONS
            )
        return None
