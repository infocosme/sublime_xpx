import html
import html.entities
import re
import gc
import time

import sublime
import sublime_plugin
import timeit
# Utile pour lecture des arguments d'une fonction.
import codecs

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
    
    # Suggestions de tags block : possibilité d'indiquer un attribut par défaut.
    normal_tags = (
        ('cond', ' expr=\"$1\"'),
        ('csv', ''),
        ('debug', ''),
        ('function', ' name=\"$1\"'),
        ('scope', ''),
        ('setarea', ''),
        ('sql', ' query=\"$1\"'),
        ('while', ' expr=\"$1\"'),
    )
    # Suggestions de tags inline : possibilité d'indiquer un attribut par défaut.
    inline_tags = (
        ('connect', ' server=\"$1\" base=\"$2\" name=\"$3\" pass=\"$4\"'),
        ('cookie', ' name=\"$1\"'),
        ('create', ' dir=\"$1\"'),
        ('debug', ''),
        ('dir', ''),
        ('else', ''),
        ('file', ''),
        ('function', ' exec=\"$1\" /'),
        ('get', ''),
        ('get', ' value=\"$1\"'),
        ('http', ' get=\"https://$1\"'),
        ('include', ' file=\"$1\"'),
        ('mail', ' from=\"$1\" to=\"$2\"'),
        ('pdf', ''),
        ('pict', ''),
        ('set', ''),
        ('system', ' exec=\"$1\"'),
        ('wait', ' value=\"$1\"'),
        ('xpath', ''),
        ('xproc', ''),
    )

    tag_begin = '' if inside_tag else '<'

    # 22/08/2022 : Prise en compte d'une nouvelle option du XPX settings.
    # self closing or not for XPX tags.
    settings = sublime.load_settings('XPX.sublime-settings')
    #print("enable_self_closing_xpx_tags: ",settings.get('enable_self_closing_xpx_tags'))

    # Ajout de l'expand inline (le deuxième).
    # 22/08/2022 : Deux possibilités de return avec ou sans self-closing.
    # 22/08/2022 : Suppression du cas snippet jugé obsolète...
    # si option définie alors true or false. Si option non définie alors None (NoneType).
    # Dans le cas d'un test if, les valeurs false et None donneront false toutes les deux.
    if settings.get('enable_self_closing_xpx_tags'):
        return sublime.CompletionList(
            [
                *(
                    sublime.CompletionItem(
                        trigger=tag,
                        annotation='block xpx',
                        completion=f'{tag_begin}{tag}{attributebydefault}>$0</{tag}>',
                        completion_format=sublime.COMPLETION_FORMAT_SNIPPET,
                        kind=KIND_TAG_MARKUP,
                        details=f'Expands to <code>&lt;{tag}{attributebydefault}&gt;&lt;/{tag}&gt;</code>'
                    )
                    for tag, attributebydefault in normal_tags
                ),
                *(
                    sublime.CompletionItem(
                        trigger=tag,
                        annotation='inline xpx',
                        completion=f'{tag_begin}{tag}{attributebydefault}$0 />',
                        completion_format=sublime.COMPLETION_FORMAT_SNIPPET,
                        kind=KIND_TAG_MARKUP,
                        details=f'Expands to <code>&lt;{tag}{attributebydefault}&gt;</code>'
                    )
                    for tag, attributebydefault in inline_tags
                )
            ],
            sublime.INHIBIT_WORD_COMPLETIONS
        )
    else:
        return sublime.CompletionList(
            [
                *(
                    sublime.CompletionItem(
                        trigger=tag,
                        annotation='block xpx',
                        completion=f'{tag_begin}{tag}{attributebydefault}>$0</{tag}>',
                        completion_format=sublime.COMPLETION_FORMAT_SNIPPET,
                        kind=KIND_TAG_MARKUP,
                        details=f'Expands to <code>&lt;{tag}{attributebydefault}&gt;&lt;/{tag}&gt;</code>'
                    )
                    for tag, attributebydefault in normal_tags
                ),
                *(
                    sublime.CompletionItem(
                        trigger=tag,
                        annotation='inline xpx',
                        completion=f'{tag_begin}{tag}{attributebydefault}$0>',
                        completion_format=sublime.COMPLETION_FORMAT_SNIPPET,
                        kind=KIND_TAG_MARKUP,
                        details=f'Expands to <code>&lt;{tag}{attributebydefault}&gt;</code>'
                    )
                    for tag, attributebydefault in inline_tags
                )
            ],
            sublime.INHIBIT_WORD_COMPLETIONS
        )


def get_xpx_list_attributes(view, pt, tag, endpt):
    """
    Lecture de tous les attributs du tag demandé du point pt au endpt.
    Si l'un des attributs est exec (function), renvoi également le nom de la fonction.
    """
    #print("get_xpx_list_attributes", time.strftime("%H:%M:%S"))
    listAttrName = []
    execName = ""
    # Début de la lecture des attributs.
    mypt = pt + len(tag)
    #print("mypt:",mypt)
    #print("endpt:",endpt)
    # Boucle sur toute la chaîne à la recherche des attribut="value".
    while (mypt<endpt):
        # Contrôle de fin de recherche.
        mynext = view.substr(sublime.Region(mypt, mypt+1))
        if ( mynext == '/' or mynext == '>'):
            break
        # Recherche du nom de l'attribut.
        # Recherche en avant du prochain signe de ponctuation.
        myPosPunctuation = view.find_by_class(mypt, True, sublime.CLASS_PUNCTUATION_START)
        #print("myPosPunctuation:",myPosPunctuation)
        if (myPosPunctuation<endpt):
            # Contrôle de fin de recherche.
            mynext = view.substr(sublime.Region(myPosPunctuation, myPosPunctuation+1))
            if ( mynext == '/' or mynext == '>'):
                break
            # recherche en arrière du début du mot.
            myPosAttributeName = view.find_by_class(myPosPunctuation, False, sublime.CLASS_WORD_START)
            # Lecture du nom de l'attribut.
            myAttributeName = view.substr(sublime.Region(myPosAttributeName, myPosPunctuation)).strip()
            listAttrName.append(myAttributeName)
            # Recherche de la valeur de l'attribut.
            mypt = myPosPunctuation
            myregion = view.find('=', mypt)
            mypt = myregion.begin()
            myregion = view.find('"', mypt)
            mypt = myregion.begin() + 1
            # Recherche de la fin de la valeur de l'attribut enregistrée entre deux "".
            myregion = view.find('"', mypt)
            myPosPunctuation1 = myregion.end()
            myAttributeValue = view.substr(sublime.Region(mypt, myPosPunctuation1 - 1)).strip()
            if (myAttributeName == "exec"):
                execName = myAttributeValue
            # Poursuite de la recherche.
            mypt = myPosPunctuation1 + 1
        else:
            mypt = myPosPunctuation
    return listAttrName, execName


def get_xpx_tag_attributes(view, tag, region):
    """
    Returns a dictionary with attributes associated to tags
    """
    #print("get_xpx_tag_attributes", time.strftime("%H:%M:%S"))
    # Map tags to specific attributes applicable for that tag
    # 22/08/2022 : ajout attribut exist au tag cond et attribut srcparam au tag pict.
    xpx_tag_attr_dict = {
        'cond': ['expr', 'exist'],
        'connect': ['base', 'close', 'id', 'info', 'name', 'pass', 'port', 'server', 'socket', 'transaction'],
        'cookie' : ['dir', 'domain', 'name', 'samesite', 'ttl', 'value'],
        'create' : ['dir'],
        'csv' : ['file', 'name', 'sep', 'value'],
        'debug' : ['mode', 'printparam', 'suffix'],
        'dir' : ['create', 'list', 'name'],
        'else' : ['expr'],
        'file' : ['close', 'content', 'delete', 'eol', 'exist', 'name', 'mode', 'model', 'open', 'path', 'read', 'write', 'xpx'],
        'function' : ['name', 'exec'],
        'get' : ['format', 'name', 'option', 'tag', 'token', 'value'],
        'http' : ['content', 'get', 'headers', 'name', 'port', 'timeout'],
        'include' : ['file', 'option'],
        'mail' : ['cc', 'cci', 'charset', 'file', 'from', 'headers', 'join', 'msg', 'reply', 'smtp', 'subject', 'to', 'type'],
        'noparse' : [],
        'pdf' : ['addpage', 'align', 'bgcolor', 'border', 'calc', 'close', 'color', 'file', 'font', 'frame', 'gettext', 'getx', 'gety', 'href', 'leading', 'line', 'mode', 'name', 'padding', 'pagesize', 'path', 'rect', 'rotate', 'round', 'size', 'style', 'text'],
        'pict' : ['border', 'calc', 'close', 'color', 'content', 'copy', 'dest', 'fill', 'font', 'geth', 'getw', 'height', 'name', 'path', 'position', 'rect', 'rotate', 'size', 'srcparam', 'text', 'transparency', 'width', 'x', 'y'],
        'scope' : ['name'],
        'set' : ['bit', 'bitoff', 'biton', 'by', 'charset', 'chartohexa', 'datetime', 'decode64', 'decrypt', 'encode64', 'encrypt', 'expr', 'format', 'global', 'hash', 'hex2bin', 'hexatochar', 'hmac', 'html2text', 'keycode', 'lang', 'len', 'local', 'lowcase', 'ltrim', 'money', 'name', 'noaccent', 'rand', 'replace', 'return', 'rtrim', 'session', 'strcode', 'strdecode', 'strescape', 'svg2pdf', 'trim', 'upcase', 'urlcode', 'value', 'xmlcode'],
        'setarea' : ['name', 'option'],
        'sql' : ['connect', 'maxrows', 'option', 'query', 'start'],
        'wait' : ['value'],
        'while' : ['expr'],
        'xpath' : ['file', 'select', 'value'],
        'xproc': ['file', 'select', 'value']
    }
    #print("view:",view)
    #print("tag:",tag,len(tag))
    #print("region:",region)
    # Suppression systématique des attributs déjà positionné dans le tag.
    if (region is not None):
        myattributesalreadypresent = get_xpx_list_attributes(view, region.begin(), tag, region.end())
        #print("myattributesalreadypresent:",myattributesalreadypresent)
        if (len(myattributesalreadypresent[0])>0):
            # Traitement spécifique pour le tag function exec
            # Objectif : complétion des arguments du function name correspondant.
            # à partir du nom de la fonction recherchée myresult[1].
            if (tag == 'function'):
                # exec en tant que membre de la liste des attributs ?
                if "exec" in myattributesalreadypresent[0]:
                    #print("Recherche du prototype function ", end="")
                    # Recherche d'une entrée symbol correspondant au nom de la fonction.
                    mywindow = sublime.active_window()
                    # Recherche dans l'index projet (tous les fichiers du projet)
                    # Recherche dans les symbols définition.
                    # Recherche dans les symbols function.
                    mylocations=mywindow.symbol_locations(myattributesalreadypresent[1],sublime.SYMBOL_SOURCE_INDEX,sublime.SYMBOL_TYPE_DEFINITION,sublime.KIND_ID_FUNCTION)
                    if (len(mylocations)>0):
                        # En cas de file trouvé, affichage de chacun des files trouvés (normalement un seul).
                        for l in mylocations:
                            content = None
                            try:
                                with codecs.open(l.path, 'r', encoding='utf-8') as file:
                                    content = file.read()
                            except:
                                pass
                            if content:
                                myfunctionview = mywindow.create_output_panel('myfunctionfile', unlisted=True)
                                myfunctionview.settings().set("translate_tabs_to_spaces", False)
                                myfunctionview.settings().set("auto_indent", False)
                                myfunctionview.run_command('insert', {"characters": content})
                                myfunctionview.assign_syntax("XPX.sublime-syntax")
                                myfunctionpt = myfunctionview.text_point(l.row-1,l.col-1)
                                myfunctionregion = myfunctionview.expand_by_class(myfunctionpt,sublime.CLASS_PUNCTUATION_START | sublime.CLASS_PUNCTUATION_END,"<>")
                                myfunctionattributes = get_xpx_list_attributes(myfunctionview,myfunctionregion.begin(),'function',myfunctionregion.end())
                                for a in myfunctionattributes[0]:
                                    if a not in xpx_tag_attr_dict["function"]:
                                        xpx_tag_attr_dict["function"].append(a)
                                mywindow.destroy_output_panel('myfunctionfile')
            # Effacement de tous les attributs déjà présents sur le tag en cours.
            for a in myattributesalreadypresent[0]:
                if (a in xpx_tag_attr_dict[tag]):
                    xpx_tag_attr_dict[tag].remove(a)
            # effacement du name dans la complétion si exec présent sur le tag en cours.
            if ("exec" in myattributesalreadypresent[0]):
                xpx_tag_attr_dict["function"].remove("name")
            # effacement du exec dans la complétion si name présent sur le tag en cours.
            if ("name" in myattributesalreadypresent[0]):
                xpx_tag_attr_dict["function"].remove("exec")
    return xpx_tag_attr_dict


def get_xpx_attribute_values(myAttributeName):
    """
    Fonction créée pour XPX.
    Returns a dictionary with values associated to attributes.
    """
    #print("get_xpx_attribute_values")
    # Map attributes to specific values applicable for that attribute
    # First: Attribute name, Second: Tag name to associate.
    attribute_dict = {
        'align' : {
            'pdf': ['center', 'left', 'right']
        },
        'charset' : {
            'set': ['iso-8859-1', 'utf-8'],
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
        #print("entity_completions")
        return get_xpx_entity_completions()

    @cached_property
    def tag_attributes(self):
        """
        Déclenchement : Un tag vient d'être saisi, un espace déclenche la proposition des attributs possibles.
        Objectif :      Renvoi d'un dictionnaire des possibles : tous les tags avec leurs attributs possibles.
        """
        #print("tag_attributes")
        return get_xpx_tag_attributes(view=None, tag='', region=None)

    @cached_property
    def tag_abbreviations(self):
        #print("tag_abbreviations")
        return get_xpx_tag_completions(inside_tag=False)

    @cached_property
    def tag_completions(self):
        #print("tag_completions")
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
        #print("tag_name_completions")
        return sublime.CompletionList(
            [
                sublime.CompletionItem(
                    trigger=tag,
                    annotation='xpx',
                    completion_format=sublime.COMPLETION_FORMAT_TEXT,
                    kind=KIND_TAG_MARKUP,
                    details=f'Expands to <code>{html.escape(tag)}</code>'
                )
                for tag in get_xpx_tag_attributes(view, '', None)
            ],
            sublime.INHIBIT_WORD_COMPLETIONS
        )

    @xpx_timing
    def on_query_completions(self, view, prefix, locations):
        """
        Fonction générale de complétion : tout part de cette fonction.
        """
        #print("on_query_completions", time.strftime("%H:%M:%S"))
        #print(view)
        #print(prefix)
        #print(locations)
        #return None

        # Autorisé uniquement sur un source XPX.
        if not view.match_selector(locations[0], "text.xpx"):
            return None

        # Complétion XPX uniquement si non interdit en configuration du langage.
        settings = sublime.load_settings('XPX.sublime-settings')
        if settings.get('disable_default_completions'):
            return None

        # Lecture du caret avant et après afin de déterminer un contexte de complétion.
        pt = locations[0] - len(prefix) - 1
        ch = view.substr(sublime.Region(pt, pt + 1))

        # Complétion normale : on démarre une balise donc on affiche les balises XPX possibles.
        # Se déclenche uniquement à la première tentative de complétion sur <.
        if ch == '<':
            # Autorisé au sein d'un source XPX mais pas dans un tag existant : uniquement sur une zone vierge.
            if view.match_selector(locations[0], "text.xpx - meta.tag.xpx"):
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
        # Autorisé sur un tag XPX mais pas dans un attribut : uniquement en dehors d'un attribut.
        #print("test attribute completion")
        if view.match_selector(locations[0], "meta.tag.xpx - meta.attribute-with-value.xpx"):
            if ch in ' \f\n\t':
                return self.attribute_completions(view, locations[0], prefix)

        # Autorisé sur un attribut XPX mais pas sur le nom de l'attribut : uniquement dans la valeur de l'attribut.
        if view.match_selector(locations[0], "meta.attribute-with-value.xpx - entity.other.attribute-name.xpx"):
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
        #print("expand_tag_attributes")
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
        Déclenchement : Un premier caractère est saisi dans un scope attribut.
        Objectif :      Renvoi d'une CompletionList contenant les attributs possibles pour le tag en cours.
        """
        #print("attribute_completions")
        #print(view)
        #print(pt)
        #print("prefix:",prefix,len(prefix))
        # Complément avec un éventuel prototype de fonction.
        # Contrôle si la complétion a été demandée (view, pt) sur un function exec dont la valeur existe.
        # Recherche du prototype correspondant parmi les symbol.
        # Renvoi des attributs du prototype trouvé.
        
        # Lecture de la région tag dans laquelle la complétion est demandée.
        myregiontag = view.expand_by_class(pt,sublime.CLASS_PUNCTUATION_START | sublime.CLASS_PUNCTUATION_END,"<>")
        #print("region:",myregiontag)
        # Lecture du début de la région.
        ptfindtag = myregiontag.begin()+1
        # Lecture du nom du tag de la région courante.
        tag = view.substr(view.word(ptfindtag))
        #print("tag:",tag,len(tag))
        # La liste de complétion est filtrée sur les entrées attributes calculées en haut.
        # Suppression du test sur attributes boolean.
        #            completion=f'{attr}{suffix}' if attr in boolean_attributes else f'{attr}="$1"{suffix}',
        # Suppression du suffix.
        # Ajout des view et pt dans prototype tag_attributes afin de pouvoir compléter avec le prototype function éventuel.
        return sublime.CompletionList(
            [
                sublime.CompletionItem(
                    trigger=attr,
                    annotation='xpx',
                    completion=f'{attr}="$1"$0',
                    completion_format=sublime.COMPLETION_FORMAT_SNIPPET,
                    kind=KIND_ATTRIBUTE_SNIPPET
                )
                for attr in get_xpx_tag_attributes(view, tag, myregiontag).get(tag, [])
            ],
            sublime.INHIBIT_WORD_COMPLETIONS
        )

    def value_attribute_completions(self, view, pt, prefix):
        """
        Recherche du nom d'attribut concerné à partir de pt.
        prefix n'est pas renseigné.
        """
        #print("value_attribute_completions")
        # Recherche du nom de l'attribut.
        myPosPunctuation = view.find_by_class(pt, False, sublime.CLASS_PUNCTUATION_START)
        myPosAttributeName = view.find_by_class(myPosPunctuation, False, sublime.CLASS_WORD_START)
        myAttributeName = view.substr(sublime.Region(myPosAttributeName, myPosPunctuation))
        #print(myAttributeName)

        # Recherche du nom du tag.
        ptfindtag = view.expand_by_class(pt,sublime.CLASS_PUNCTUATION_START | sublime.CLASS_PUNCTUATION_END,"<>").begin()+1
        myTagName = view.substr(view.expand_by_class(ptfindtag,sublime.CLASS_WORD_START | sublime.CLASS_WORD_END))
        #print(myTagName)

        """
        # Tentative de completion du function exec avec la liste des fonctions du projet.
        # A priori, impossible selon les auteurs de ST.
        # Pas de fonction API disponible pour parcourir les symbols XPX de type function.
        if (myTagName == "function" and myAttributeName == "exec"):
            #print("Recherche des function name disponibles")
            #print(view.indexed_symbol_regions())
            #print(view.window().project_data())
            #print(view.window().folders())
            #print(len(gc.get_objects()))
            counter = {}
            for obj in gc.get_objects():
                #print(type(obj).__name__)
                #if isinstance(obj, list):
                #    if ("xpxForms.blocChamps" in obj):
                #    print(obj)
                #    print()
                if type(obj).__name__ not in counter:
                    counter[type(obj).__name__] = 0
                counter[type(obj).__name__] += 1
            print(counter)
        """
        """
        view.window().run_command("hide_panel")
        view.window().run_command("show_panel", { "panel": "find_in_files", "where": "<project>" })
        #view.window().run_command("find_all")
        """
        """
        for region, symbol_name in view.symbols():
            print(symbol_name, end=":")
        print()
        """
        #print(view.symbols())
        # got the classic tag,attribute, now find all values that match
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
                sublime.INHIBIT_WORD_COMPLETIONS + sublime.INHIBIT_EXPLICIT_COMPLETIONS
            )
        return None
