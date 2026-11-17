# XPX pour Sublime Text

Package Sublime Text 4 (build 4200 ou supérieur) pour le langage de script **XPX**.

XPX est un langage de script de type XHTML développé et maintenu par la société Infocosme
(parser spécifique, exécution par cgi-bin). Il est distribué librement sur simple demande
auprès d'Infocosme. Documentation : https://www.xpx-technologies.net/balise_xpx.html

La version 1.5.0 est une réécriture complète du package, conforme aux conventions actuelles
de Sublime Text 4.

## Installation

Avec **Package Control** : `Ctrl+Maj+P` › « Package Control: Install Package » › **XPX**.

Les fichiers `.xpx` et `.phc` s'ouvrent automatiquement avec la syntaxe XPX.

## Fonctionnalités

### Coloration syntaxique

- Balises XPX (`<set>`, `<cond>`, `<sql>`, `<function>`…), attributs et valeurs.
- Variables `$maVariable$`, y compris les variables imbriquées (écrites sans `$`) :
  `$tab[indice]$`, `$tab[indice][col]$`, `$nom(1,len)$`.
- Variables internes : `$phcerrmsg$`, `$sqlrowcount$`, `$xproc.content$`…
- Expressions de `expr="…"` : opérateurs (`<`, `<=`, `?=`, `!?=`, `!`, `&&`…), nombres, chaînes.
- Requêtes SQL de `<sql query="…">` colorées comme du SQL.
- Balises et variables XPX reconnues aussi dans le JavaScript (`<script>`, `onclick="…"`)
  et le CSS (`<style>`, `style="…"`).
- `<noparse>` : contenu traité comme du HTML standard, sans XPX.
- Les commentaires HTML `<!-- -->` restent des commentaires.
- Un `$` isolé (jQuery `$(...)`, montant « 10 $ ») n'est jamais pris pour une variable.

### Navigation dans les fonctions

| Action | Raccourci |
|---|---|
| Fonctions du fichier courant | `Ctrl+R` |
| Fonctions de tout le projet (tous les dossiers) | `Ctrl+Maj+R` |
| Aller à la définition d'une fonction (`exec="…"`) | `F12` |
| Liste des appels d'une fonction | `Maj+F12` |
| Revenir en arrière | `Alt+-` |

Au **survol** d'un nom de fonction :
- sur un appel `exec="…"` : lien vers la définition (avertissement si plusieurs définitions) ;
- sur une définition `name="…"` : nombre et liens des appels (« Aucun appel trouvé » sinon),
  avertissement si la fonction est aussi définie ailleurs.

### Variables d'arborescence et `<include>`

Le projet Sublime Text reproduit l'arborescence du serveur : le dossier du site est le
DOCUMENT_ROOT, « / » des chemins XPX (`/../httpdocs_tools` désigne le dossier voisin).
Le package relève les définitions `<set name="…" value="…">` du projet et résout les
variables qui s'enchaînent (`$gRepToolsXPXForms$` → `$gRepTools$/xpxForms` →
`/../httpdocs_tools/xpxForms`).

- `F12` sur le chemin d'un `<include file="…">` : ouvre le fichier.
- `F12` sur une variable `$…$` : va à sa définition.
- Survol du chemin d'un include : chemin réel, avertissement si le fichier est introuvable
  ou si une variable d'URL (`$gUrl…$`) est utilisée au lieu d'une variable de chemin
  (`$gRep…$`).
- Survol d'une variable : valeur, valeur résolue, dossier réel, définition(s).
- Complétion dans `file="…"` : variables `$gRep…$`, puis contenu du dossier.

Choix de la valeur d'une variable : surcharge du site choisi (`xpx_site`), sinon fichier de
définitions (`inc/global.inc.xpx`), sinon définition unique dans le projet. Les dossiers
`archives` sont ignorés. Voir les réglages ci-dessous.

### Complétion

- Après `<` : balises XPX avec leurs attributs usuels. Les balises bloc sont insérées avec leur
  balise fermante, les balises inline avec ` />`.
- Dans une balise : ses attributs (sauf ceux déjà présents).
- Dans une valeur : valeurs connues (`mode`, `option`, `charset`…).
- Dans `<function exec="…">` : noms des fonctions définies dans les dossiers du projet,
  puis paramètres de la fonction choisie.
- Après `$` : variables internes XPX.
- Raccourcis (après `<` ou dans le texte, puis `Tab`) :

| Raccourci | Insère |
|---|---|
| `debugn` / `debugo` | `<debug mode="normal" />` / `<debug mode="off" />` |
| `debuga20` | `<debug mode="auto" count="20" />` |
| `setd0` / `setd1` | `<set global="phcdebug" value="0" />` / `value="1"` |
| `setsql0` / `setsql1` | `<set global="sqlescapestr" value="0" />` / `value="1"` |
| `whilei` | boucle `<while>` avec compteur |

### Édition

- **Fermeture automatique** : `/` tapé après `<` ferme la dernière balise ouverte, en ignorant
  les balises XPX inline (`<set …>`, `<include …>`, `<else>`…).
- **Indentation automatique** des blocs XPX (`<cond>`, `<else>`, `<while>`, `<sql>`,
  `<function name>`…).
- **Commentaire** : `Ctrl+/`.
- **Commande** `Ctrl+Maj+P` › « XPX: Fermer les balises inline par « /> » » : ajoute ` />`
  aux balises XPX inline qui n'en ont pas, sur la sélection ou tout le fichier
  (une seule annulation `Ctrl+Z`).

### Fichiers de debug (`.debug`)

Les traces produites par `<debug>` (dossier `cgi-bin/xpxdebug`, extension `.debug`)
s'ouvrent avec la syntaxe **XPX Debug** :

- Début de l'analyse de chaque balise surligné ; numéros de ligne source mis en évidence.
- `EXPR … RESULT: true` / `false` colorés, SQL exécuté coloré comme du SQL.
- Erreurs (`XPXERR=1…`, `SQL ERROR`) en rouge, avertissements (`XPXERR=0 <message>`) en orange.

**`F12` depuis une ligne du debug** : ouvre le code source à la ligne correspondante,
en suivant les `INCLUDE FILE`, les corps de fonctions (`End of Exec`) et la page de départ.
Sur `RETURN IN`, ouvre le fichier appelant à la ligne de reprise.

**Suivre une variable** : clic droit sur une variable › « XPX Debug : suivre cette variable »,
ou `Ctrl+Maj+P` › « XPX Debug: Suivre une variable » (liste des variables si le curseur
n'est sur aucune). Un panneau, qui reste ouvert, liste chaque changement de valeur :
ligne du debug, fichier et ligne source, portée, valeur, « (inchangée) » si la valeur ne
change pas. Double-clic sur une ligne du panneau : la ligne du debug (puis `F12` : le code
source). Les lignes concernées sont soulignées dans le debug ; « XPX Debug: Effacer le suivi
de variable » les efface.

- Changements suivis : `<set>` (repérés `[global]` ou `[return → …]`), variables du
  `format` d'un `<get>` (`[get format]`), variables numérotées d'un `<get token>`
  (`[get token]`, la variable racine recevant le nombre d'éléments).
- Noms calculés résolus avec les valeurs du moment : `$formName$.label` → `myForm.label`,
  `gUser$gEspace[i]$` → `gUserClient` (`[via …]` rappelle l'expression d'origine).
- Portées : `GLOBAL` (niveau 1) ; chaque appel de fonction ajoute un niveau (un include
  non). `<set name>` écrit dans la portée en cours, `<set global>` dans `GLOBAL`,
  `<set return>` dans la portée du dessus ; une variable est cherchée dans la portée en
  cours puis en remontant la pile jusqu'à `GLOBAL`. Une variable locale et une globale de
  même nom ont des historiques distincts. Le panneau indique le taux de concordance entre
  ces portées et celles que donne le debug (lignes `VAR`).
- Les noms de variables sont sensibles à la casse.

## Réglages

`Preferences › Settings - Syntax Specific` (avec un fichier XPX ouvert) :

```jsonc
{
	"xpx_completions": true,        // complétion XPX
	"xpx_self_closing_tags": true,  // balises inline insérées avec « /> »
	"tab_size": 3,
	"translate_tabs_to_spaces": false,

	// Arborescence (peut aussi être placé dans le .sublime-project)
	"xpx_functional_folders": ["httpdocs_tools", "httpdocs_common"],
	"xpx_definition_files": ["inc/global.inc.xpx"],
	"xpx_site": "",
	"xpx_path_variable_prefix": "gRep",
	"xpx_url_variable_prefix": "gUrl",
	"xpx_ignored_folders": ["archives"],
}
```

Exemple de réglage propre à un projet (`Project › Edit Project`) :

```jsonc
{
	"folders": [ … ],
	"settings": {
		"xpx_site": "malibu"
	}
}
```

## Couleurs

Le package n'impose aucun color scheme : les scopes XPX suivent les conventions de Sublime Text
et sont colorés par n'importe quel thème.

Pour personnaliser les couleurs XPX, ouvrir `Preferences › Customize Color Scheme` et y copier
le contenu du fichier d'exemple `XPX.sublime-color-scheme.example` livré avec le package
(`Preferences › Browse Packages…` › `XPX`).

Principaux scopes :

| Élément | Scope |
|---|---|
| Nom de balise | `entity.name.tag.xpx` |
| Nom d'attribut | `entity.other.attribute-name.xpx` |
| Valeur d'attribut | `string.quoted.double.xpx` |
| Variable | `variable.other.readwrite.xpx` |
| Variable imbriquée | `variable.other.embedded.xpx` |
| Variable interne | `variable.language.xpx` |
| Définition de fonction | `entity.name.function.xpx` |
| Appel de fonction | `variable.function.xpx` |
| Paramètre de fonction | `variable.parameter.xpx` |
| Debug : début de balise | `meta.block-start.xpx-debug` |
| Debug : erreur / avertissement | `invalid.illegal.error.xpx-debug` / `invalid.deprecated.warning.xpx-debug` |

## Tests

Le dossier `tests/` contient les tests de syntaxe (XPX et XPX Debug) et d'indentation :
ouvrir un fichier `syntax_test_*` puis `Ctrl+B`.

## Auteur

P. Milon — Infocosme
