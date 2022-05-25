# XPX syntax

Plugin Sublime Text 4 (>= v4126)

## Contenu

Le langage de script XPX est développé et maintenu par la société Infocosme (XHTML par cgi-bin, parser spécifique).
Ce langage de script est distribué librement sur simple demande auprès d'Infocosme (Formulaire de demande sur site web).

Ce plug-in a été entièrement ré-écrit pour correspondre aux nouveaux standards ST4.
A partir de la version 1.2.5, les syntaxes sont enfin à jour ST4.

Fonctionnalités livrées :
* syntaxe XPX (tags, attributes, values, variables)
* auto-complete (tags, attributes, values)
* snippets divers
* close_tag re-écrit pour prendre en compte les balises inline XPX
* commande contextuelle goto definition function
* menu contextuel show function (all function name du projet)

Le thème de couleur proposé est une surcharge du thème Monokai livré par ST4.
Chaque utilisateur reste libre de choisir son propre thème et de le surcharger avec l'exemple livré.
Un thème est proposé (surtout pour l'exemple d'utilisation des scopes de la syntaxe).
Les goûts et les couleurs ne se partagent pas tout le temps... :-)

Sincères salutations.
P. Milon

## Installation
Utiliser le plug-in "Package Control" pour installer le plug-in XPX.
Dans la rubrique "install Package", chercher le plug-in nommé "XPX".
## Personnalisation
Les paramètres de personnalisation sont enregistrés dans "/AppdData/Roaming/Sublime Text/Packages"
Ce dossier est accessible via la commande "Préférences / Browse Packages..."
Ne pas confondre le thème (les boutons, l'interface claire ou foncée, la sidebar, ...) avec le color-scheme (la coloration
syntaxique d'un fichier source)
### Color Scheme
Un color-scheme n'est pas lié à un package en particulier. Il peut être défini pour faire varier la coloration
syntaxique pour chaque syntaxe utilisée dans le projet.
Un exemple de .sublime-color-scheme est livré par défaut : Monokai.sublime-color-scheme.Exemple
Cet exemple contient des exemples de personnalisation de scope XPX.
Les choix de color-scheme sont enregistrés dans "/AppdData/Roaming/Sublime Text/Packages/User"
Les color scheme sont appliqués par ordre de priorité (de la plus faible à la plus grande) :
* "Preferences / Settings" (Valable en l'absence de préférence définie sur la syntaxe du fichier ouvert) : 
	- Editer le fichier de configuration des préférences du user.
	- Le fichier est enregistré dans "/AppdData/Roaming/Sublime Text/Packages/User/Preferences.sublime-settings"
* "Preferences / Select Color Scheme..." : Permet de choisir dans une liste le color-scheme du user.
* "Preferences / Setting - Syntax Specific" (Prioritaire sur les préférences globales du user) : 
	- Editer le fichier de configuration pour un syntaxe en particulier
	- Le fichier est enregistré dans "/AppdData/Roaming/Sublime Text/Packages/User/[syntax].sublime-settings"
	- à définir à partir d'un fichier ouvert dans l'extension ciblée
* "Preferences / Customize Color Scheme..." :
	- Editer les rules du color-scheme en cours.
### Les régions XPX
L'analyse syntaxique se déclenche après celle du HTML standard (HTML, javascript, CSS).
La balise <noparse> permet d'interrompre l'analyse syntaxique XPX tout en préservant celle du HTML standard (HTML, javascript, CSS).
Les variables XPX sont identifiées quelque soit leur emplacement (sauf dans une région <noparse>).
Liste des régions disponibles :
* text.xpx : La région principale
* meta.tag.xpx : scope définissant le nom d'un tag XPX
* meta.tag.block.xpx : région constituée de toutes les balises XPX block.
* meta.tag.inline.xpx : région constituée de toutes les balises XPX inline.
* meta.tag.function.xpx : région complète constituée de tout le block <function>.
* meta.tag.noparse.xpx : région complète constituée de tout le block <noparse>.
* entity.other.attribute-name.xpx : mot clé d'un attribut XPX d'une balise XPX.
* entity.other.attribute-value.xpx : contenu d'un attribut XPX : la valeur.
* entity.other.attribute-name.query.xpx : mot clé de l'attribut query de la balise <sql>.
* punctuation.definition.string.begin.xpx : symbole de début de ponctuation d'un attribut XPX.
* punctuation.definition.string.end.xpx : symbole de fin de ponctuation d'un attribut XPX.
* variable.other.xpx : région constitué du nom d'une variable XPX ($maVariable$).
* variable.other.xpx.embedded : région constituée d'une variable imbriquée dans une variable XPX ($maVariable[embeddedVariable]$).

