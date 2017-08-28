"""
    Close HTML, XPX TAG
    ~~~~~~~~~~~~~~~~~~~

    Sur appui du / en mode saisie dans un scope text.html.xpx,
    ré-écriture de la fonction close_tag interne de sublime text (core)
    afin de tenir compte du scope inline XPX (donc en dynamique et en complément du HTML).

    Les balises HTML inline sont déterminées à partir d'une liste "en dur" car le scope
    inline est distribué dans html.sublime-syntax y compris sur des balises block.

    :copyright: (c) 2017 by Pascal MILON et Malik BEKHELOUF <pmilon@infocosme.com>
"""

import sublime
import sublime_plugin

class XpxCloseTagCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        # print('run xpx_close_tag:')

        # Les tags HTML ne peuvent pas être traités avec le scope inline car plusieurs tags
        # block HTML sont définis en sublime-syntax en inline pour je ne sais quelle raison.
        # Exemple : table, tr, td, ...

        # Définition de la liste des tags block HTML :
        myHTMLBlockTagsList = ([
            'abbr', 'acronym', 'address', 'applet', 'article', 'aside',
            'audio', 'b', 'basefont', 'bdi', 'bdo', 'big', 'blockquote',
            'body', 'button', 'center', 'canvas', 'caption', 'cdata',
            'cite', 'colgroup', 'code', 'content', 'data', 'datalist',
            'dir', 'div', 'dd', 'del', 'details', 'dfn', 'dl', 'dt', 'element',
            'em', 'embed', 'fieldset', 'figure', 'figcaption', 'font', 'footer',
            'form', 'frame', 'frameset', 'head', 'header', 'h1', 'h2', 'h3',
            'h4', 'h5', 'h6', 'i', 'iframe', 'ins', 'isindex', 'kbd', 'keygen',
            'li', 'label', 'legend', 'main', 'map', 'mark', 'meter',
            'nav', 'noframes', 'noscript', 'object', 'ol', 'optgroup',
            'option', 'output', 'p', 'picture', 'pre', 'q', 'rp',
            'rt', 'rtc', 'ruby', 's', 'samp', 'script', 'section', 'select', 'shadow',
            'small', 'span', 'strong', 'style', 'sub', 'summary', 'sup',
            'table', 'tbody', 'td', 'template', 'textarea', 'tfoot', 'th',
            'thead', 'time', 'title', 'tr', 'tt', 'u', 'ul', 'var',
            'video'
        ])
        # Définition de la liste des tags inline HTML :
        myHTMLInlineTagsList = ([
            'a', 'area', 'audio', 'base', 'br', 'col', 'hr', 'input', 'img', 'link',
            'meta', 'param', 'progress', 'source', 'style', 'track', 'wbr'
        ])

        cursorPosition = self.view.sel()[0].begin()
        # print('cursorPosition:', cursorPosition)

        # Création de la liste de tous les tags définis dans le script avant la position du curseur.
        # <script, </script, <div, <cond, </cond, ...
        # Ne pas tenir compte des tags dont le scope est défini sur inline.
        myTagsList = []
        myPt = 0
        # Recherche de la prochaine balise (ouverture: '<balise' ou fermeture: '</balise')
        myRegion=self.view.find('(<)(\/?)(\w+)', myPt, sublime.IGNORECASE)
        while myRegion.end() > 0 and myRegion.end() < cursorPosition:
            # Récupérer le nom de la balise à traiter (sans fioritures)
            myTag = self.view.substr(myRegion)
            # tag de fermeture
            if '/' in myTag:
                myTagName = myTag[2:]
            else:
                myTagName = myTag[1:]
            # Si le scope contient 'meta.tag.inline.any.xpx', le tag ne sera pas ajouté à la pile LIFO.
            # Si le tag n'est pas présent dans la liste des inline tags HTML, il sera ajouté.
            if not 'meta.tag.inline.any.xpx' in self.view.scope_name(myRegion.end()) and myTagName not in myHTMLInlineTagsList:
                # Préserver le début de la balise pour déterminer si balise ouverture ou fermeture.
                myTagsList.append((myTag, self.view.scope_name(myRegion.end())))
            myPt = myRegion.end()
            # Recherche de la prochaine balise (ouverture: '<balise' ou fermeture: '</balise')
            myRegion=self.view.find('(<)(\/?)(\w+)', myPt, sublime.IGNORECASE)
        # print('myTagsList:', myTagsList)

        # Analyse de la liste en mode LIFO afin de sortir le dernier tag non refermé.
        myLifoTags = []
        if len(myTagsList) > 0:
            for x in range(0,len(myTagsList)):
                # print(myTagsList[x][0])
                myTag = myTagsList[x][0]
                # print('tag dans liste:', myTag)
                # tag de fermeture
                if '/' in myTag:
                    # print('tag à fermer:', myLifoTags[len(myLifoTags)-1])
                    del myLifoTags[len(myLifoTags)-1]
                else:
                    # Ajouter le tag dans la pile sans le < du début de chaîne.
                    myTag = myTag[1:]
                    myLifoTags.append(myTag)
                pass
        # print('myLifoTags:', myLifoTags)

        # Inscrire le / de la commande (dans tous les cas).
        self.view.run_command('insert', {'characters': '/'})

        # prendre le dernier de la liste LIFO.
        if len(myLifoTags) > 0:
            self.view.run_command('insert', {'characters': myLifoTags[len(myLifoTags)-1] + '>'})
