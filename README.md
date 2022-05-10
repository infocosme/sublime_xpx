# XPX syntax

Plugin Sublime Text 4 (>= v3092)

## Contenu

Langage XPX développé par la société Infocosme (XHTML par cgi-bin, parser spécifique).
Fonctionnalités livrées :
* syntaxe XPX (balises, attributs, variables)
* auto-complétion (balises, attributs, valeurs)
* snippets divers
* close_tag re-écrit pour prendre en compte les balises inline XPX

Un thème est proposé (surtout pour l'exemple d'utilisation des scopes de la syntaxe), les goûts et les couleurs ne se partagent pas tout le temps... :-)

Sincères salutations.
P. Milon

## Installation
Utiliser le plug-in "Package Control" pour installer le plug-in XPX.
Dans la rubrique "install Package", chercher le plug-in nommé "XPX".
## Personnalisation
### Thème par défaut
Le thème XPX livré par défaut est une copie du thème Monokai personnalisé avec les régions du XPX sublime-syntax.
### Les régions XPX
L'analyse syntaxique se déclenche après celle du HTML standard (HTML, javascript, CSS).
La balise <noparse> permet d'interrompre l'analyse syntaxique XPX tout en préservant celle du HTML standard (HTML, javascript, CSS).
Les variables XPX sont identifiées quelque soit leur emplacement (sauf dans une région <noparse>).
Liste des régions disponibles :
* text.html.xpx : La région principale
* entity.name.tag.xpx : mot clé d'une balise XPX
* meta.tag.block.noparse.xpx : région complète constituée de tout le block <noparse>.
* meta.tag.inline.any.xpx : région constituée de toutes les balises XPX inline.
* entity.other.attribute-name.xpx : mot clé d'un attribut XPX d'une balise XPX.
* entity.other.attribute-value.xpx : contenu d'un attribut XPX : la valeur.
* entity.other.attribute-name.query.xpx : mot clé de l'attribut query de la balise <sql>.
* punctuation.definition.string.begin.xpx : symbole de début de ponctuation d'un attribut XPX.
* punctuation.definition.string.end.xpx : symbole de fin de ponctuation d'un attribut XPX.
* variable.other.readwrite.xpx : région constitué du nom d'une variable XPX ($maVariable$).
* variable.other.readwrite.included.xpx : région constituée d'une variable incluse à l'intérieur d'une variable XPX ($maVariable[includedVariable]$).

