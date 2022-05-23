"""
    Close HTML, XPX TAG
    ~~~~~~~~~~~~~~~~~~~

    Sur appui du / en mode saisie dans un scope text.xpx,
    ré-écriture de la fonction close_tag interne de sublime text (core)
    afin de tenir compte du scope inline XPX (donc en dynamique et en complément du HTML).

    Les noms des balises HTML inline sont déterminées à partir d'un scope dédicacé.
    Les noms des balises XPX inline sont déterminées à partir d'un scope dédicacé.
    Cela permet de ne plus utiliser les listes "en dur" (évolution ST4 qui découpe plus précisément les scopes)

    La méthode :
        - Référencer toutes les balises ouvrantes et fermantes jusqu'au pt courant dans le script.
        - Proposer de fermer la dernière balise ouverte non fermée.

    :copyright: (c) 2017 by Pascal MILON <pmilon@infocosme.com>
"""

import sublime
import sublime_plugin


def get_xpx_list_attributes(view, pt, tag, endpt):
    """
    ATTENTION : Fonction doublée et définie dans xpx_completions (faute de savoir faire marcher l'import...).
    Lecture de tous les attributs du tag demandé du point pt au endpt.
    Si l'un des attributs est exec (function), renvoi également le nom de la fonction.
    """
    #print("get_xpx_list_attributes")
    listAttrName = []
    execName = ""
    mypt = pt + len(tag)
    # Boucle sur toute la chaîne à la recherche des attribut="value".
    while (mypt<endpt):
        # Contrôle de fin de recherche.
        mynext = view.substr(sublime.Region(mypt, mypt+1))
        if ( mynext == '/' or mynext == '>'):
            break
        # Recherche du nom de l'attribut.
        # Recherche en avant du prochain signe de ponctuation.
        myPosPunctuation = view.find_by_class(mypt, True, sublime.CLASS_PUNCTUATION_START)
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
    return listAttrName, execName


class XpxCloseTagCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        #print('run xpx_close_tag:')

        cursorPosition = self.view.sel()[0].begin()
        # print('cursorPosition:', cursorPosition)

        # Création de la liste de tous les tags définis dans le script avant la position du curseur.
        # <script, </script, <div, <cond, </cond, ...
        # Ne pas tenir compte des tags dont le scope est défini sur inline.
        # Parcours de tous le script depuis 0 jusqu'à position en cours.
        myTagsList = []
        myNextPt = 0
        # Recherche de la prochaine balise (ouverture: '<balise' ou fermeture: '</balise') :
        myRegion=self.view.find('(<)(\/?)(\w+)', myNextPt, sublime.IGNORECASE)
        # myDebug=self.view.substr(myRegion)
        # print('myRegion:',myRegion,myDebug)
        while myRegion.end() > 0 and myRegion.end() < cursorPosition:
            # Récupérer le nom de la balise à traiter (sans fioritures)
            myTag = self.view.substr(myRegion)
            # print('myTag lu:',myTag)
            # cas du tag de fermeture
            if '/' in myTag:
                myTagName = myTag[2:]
            else:
                myTagName = myTag[1:]
            # Lecture du scope complet
            bonPourLifo = True
            myPtAfter = myRegion.end()
            # le scope du tag script est le scope global : donc ne pas traiter sinon arrêt de la boucle
            """
            if 'script' not in myTagName:
                # Lecture de la région complète du scope en cours.
                myScopeRegion=self.view.extract_scope(myRegion.end())
                # Lecture du contenu de la région.
                myScopeText=self.view.substr(myScopeRegion)
                # print('myTag:',myTag,'myDebug:',myScopeText)
                # Ne pas tenir compte du tag lu précédemment si il se termine en inline.
                if '/>' in myScopeText:
                    bonPourLifo = False
                    # La lecture du script doit se poursuivre après le faux inline.
                    myPtAfter = myScopeRegion.end()
            """
            # Tag </noparse ne doit pas être inclus dans le traitement car tout le scope meta.tag.noparse.xpx est exclu.
            if (myTagName == 'noparse'):
                bonPourLifo = False
            # Traitement particulier du tag function.
            # Tag function name : il faut l'ajouter dans la pile car tag block (non défini en scope).
            # Tag function exec : il ne faut pas l'ajouter dans la pile car tag inline (non définin en scope).
            if (myTagName == 'function'):
                myfunctionregion = self.view.expand_by_class(myPtAfter,sublime.CLASS_PUNCTUATION_START | sublime.CLASS_PUNCTUATION_END,"<>")
                mylistattributes = get_xpx_list_attributes(self.view, myfunctionregion.begin() , 'function', myfunctionregion.end())
                #print(mylistattributes)
                #print(myTag)
                if (('name' in mylistattributes[0]) or (myTag == "</function")):
                    myTagsList.append((myTag, self.view.scope_name(myRegion.end())))
            # Le tag ne sera pas ajouté à la pile LIFO si le scope contient :
            # 'meta.tag.inline.any.html' (tag inline HTML)
            # 'meta.tag.inline.xpx' (tag inline XPX)
            # 07/10/2019 : 'string.quoted.double.html' (value d'un attribut HTML)
            # 23/05/2022 : 'meta.attribute-with-value.xpx' (value d'un attribut XPX)
            # 23/05/2022 : Suppression de l'utilisation de la liste statique des tags HTM inline au profit du scope.
            #print(self.view.scope_name(myRegion.end()))
            elif bonPourLifo \
            and not 'meta.tag.inline.any.html' in self.view.scope_name(myRegion.end()) \
            and not 'meta.tag.inline.xpx' in self.view.scope_name(myRegion.end()) \
            and not 'meta.attribute-with-value.xpx' in self.view.scope_name(myRegion.end()) \
            and not 'string.quoted.double.html' in self.view.scope_name(myRegion.end()) \
            and not ('meta.tag.xpx' in self.view.scope_name(myRegion.end()) and 'meta.tag.noparse.xpx' in self.view.scope_name(myRegion.end())):
                # Préserver le début de la balise pour déterminer si balise ouverture ou fermeture.
                myTagsList.append((myTag, self.view.scope_name(myRegion.end())))
                #print('myTag stocké',myTag)
            # myPt = myRegion.end()
            # Poursuite de la boucle while.
            myNextPt = myPtAfter
            # Recherche de la prochaine balise (ouverture: '<balise' ou fermeture: '</balise')
            myRegion=self.view.find('(<)(\/?)(\w+)', myNextPt, sublime.IGNORECASE)
            # myDebug=self.view.substr(myRegion)
            # print('myRegion:',myRegion,myDebug)
        #print('myTagsList:', myTagsList)
        #print('myTagsList:', end=" ")
        #for i in range(len(myTagsList)):
        #    print(myTagsList[i][0], end=' ')
        #print()
        
        # Analyse de la liste en mode LIFO afin de sortir le dernier tag non refermé.
        myLifoTags = []
        if len(myTagsList) > 0:
            for x in range(0,len(myTagsList)):
                #print(myTagsList[x][0])
                myTag = myTagsList[x][0]
                #print('tag dans liste:', myTag)
                # tag de fermeture
                if '/' in myTag:
                    #print('tag à fermer:', myLifoTags[len(myLifoTags)-1])
                    #print(len(myLifoTags))
                    if (len(myLifoTags) > 0):
                        #print('tag supprimé',myLifoTags[len(myLifoTags)-1])
                        del myLifoTags[len(myLifoTags)-1]
                        #print("myLifoTags (-):", myLifoTags)
                else:
                    # Ajouter le tag dans la pile sans le < du début de chaîne.
                    #myTag = myTag[1:]
                    myLifoTags.append(myTag[1:])
                    #print("myLifoTags (+):", myLifoTags)
                pass
        #print('myLifoTags:', myLifoTags)

        # Inscrire le / de la commande (dans tous les cas).
        self.view.run_command('insert', {'characters': '/'})

        # prendre le dernier de la liste LIFO.
        if len(myLifoTags) > 0:
            self.view.run_command('insert', {'characters': myLifoTags[len(myLifoTags)-1] + '>'})
