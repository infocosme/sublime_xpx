"""
XPX — table unique des balises, attributs et valeurs.

Source unique utilisée par :
    xpx_completions.py   complétion des balises, attributs et valeurs
    xpx_commands.py      fermeture des balises inline (« /> »)

Sources : ancienne table du package (v1.4.2) et référence XPX 4.2
(https://www.xpx-technologies.net/balise_xpx.html).

Pour ajouter une balise ou un attribut : modifier uniquement ce fichier.

Nature d'une balise (clé « kind ») :
    BLOCK   <tag ...> contenu </tag>
    INLINE  <tag ... />            (« /> » souvent omis dans les anciens scripts)
    DUAL    bloc ou inline selon l'usage (array, pdf, xproc)
    ELSE    <else> / <else expr="..."> : ni fermée, ni auto-fermante
La balise function est bloc avec name="..." et inline avec exec="...".
"""

BLOCK = 'block'
INLINE = 'inline'
DUAL = 'dual'
ELSE = 'else'

# Chaque balise :
#   kind        nature (voir ci-dessus)
#   doc         description courte affichée dans la liste de complétion
#   attrs       attributs autorisés (ordre alphabétique)
#   snippets    attributs insérés par défaut avec la balise (un ou plusieurs
#               modèles : une entrée de complétion par modèle)
#   values      valeurs proposées par attribut
TAGS = {
    'array': {
        'kind': DUAL,
        'doc': 'Tableau : déclaration (bloc) ou manipulation / tri (inline)',
        'attrs': ['col', 'delimiter', 'header', 'name', 'option', 'row', 'sort', 'value'],
        'snippets': {
            BLOCK: ['name="$1"'],
            INLINE: ['name="$1" value="$2"', 'sort="$1" col="$2"'],
        },
        'values': {
            'option': ['colpush', 'colshift', 'replace', 'rowpush', 'rowshift', 'set', 'shift'],
        },
    },
    'cond': {
        'kind': BLOCK,
        'doc': 'Condition (avec <else> éventuels)',
        'attrs': ['exist', 'expr', 'notexist'],
        'snippets': ['expr="$1"', 'exist="$1"', 'notexist="$1"'],
    },
    'connect': {
        'kind': INLINE,
        'doc': 'Connexion à une base de données',
        'attrs': ['base', 'close', 'default', 'id', 'info', 'name', 'pass', 'port',
                  'server', 'socket', 'transaction'],
        'snippets': ['id="$1" server="$2" base="$3" name="$4" pass="$5"', 'default="$1"'],
        'values': {
            'server': ['localhost'],
            'transaction': ['normal', 'rollback'],
        },
    },
    'cookie': {
        'kind': INLINE,
        'doc': 'Écriture d\'un cookie',
        'attrs': ['dir', 'domain', 'name', 'samesite', 'ttl', 'value'],
        'snippets': ['name="$1" value="$2"'],
        'values': {
            'samesite': ['Lax', 'Strict'],
        },
    },
    'create': {
        'kind': INLINE,
        'doc': 'Création d\'un dossier',
        'attrs': ['dir'],
        'snippets': ['dir="$1"'],
    },
    'csv': {
        'kind': BLOCK,
        'doc': 'Lecture d\'un fichier CSV (boucle sur les lignes)',
        'attrs': ['file', 'header', 'name', 'sep', 'value'],
        'snippets': ['file="$1" sep="$2" name="$3"'],
        'values': {
            'header': ['keepws', 'none', 'nows'],
            'sep': [';', ',', '\\t'],
        },
    },
    'debug': {
        'kind': INLINE,
        'doc': 'Mode debug',
        'attrs': ['count', 'file', 'level', 'mode', 'printparam', 'suffix'],
        'snippets': ['mode="$1"'],
        'values': {
            'mode': ['auto', 'normal', 'off'],
            'printparam': ['$phcparamcount$'],
        },
    },
    'dir': {
        'kind': INLINE,
        'doc': 'Dossier : liste (tableau name, type, size, moddate) ou création',
        'attrs': ['create', 'list', 'name', 'pattern'],
        'snippets': ['list="$1" name="$2"', 'create="$1"'],
    },
    'else': {
        'kind': ELSE,
        'doc': 'Alternative d\'une condition <cond>',
        'attrs': ['expr'],
        'snippets': ['', 'expr="$1"'],
    },
    'file': {
        'kind': INLINE,
        'doc': 'Fichier : existence, ouverture, lecture, écriture, suppression',
        'attrs': ['close', 'content', 'delete', 'eol', 'exist', 'mode', 'model', 'name',
                  'open', 'option', 'path', 'read', 'write', 'xpx'],
        'snippets': ['open="$1" path="$2" mode="$3"', 'read="$1" content="$2" eol="\\\\n"',
                     'write="$1" content="$2"', 'close="$1"', 'exist="$1" path="$2"',
                     'delete="$1"'],
        'values': {
            'mode': ['append', 'read', 'write'],
            'option': ['parse'],
            'eol': ['\\n', '\\r\\n'],
        },
    },
    'function': {
        'kind': None,  # bloc (name) ou inline (exec) : voir le module
        'doc': 'Fonction XPX : définition (name) ou appel (exec)',
        'attrs': ['exec', 'name'],
    },
    'get': {
        'kind': INLINE,
        'doc': 'Extraction de valeurs d\'une chaîne (séparateur ou format)',
        'attrs': ['format', 'name', 'option', 'tag', 'token', 'value'],
        'snippets': ['value="$1" token="$2" name="$3"', 'value="$1" format="$2"'],
        'values': {
            'option': ['notnull', 'null'],
        },
    },
    'http': {
        'kind': INLINE,
        'doc': 'Requête HTTP/HTTPS (résultat dans content)',
        'attrs': ['content', 'get', 'headers', 'name', 'port', 'timeout'],
        'snippets': ['get="https://$1" content="$2"'],
        'values': {
            'timeout': ['10', '30', '60'],
        },
    },
    'include': {
        'kind': INLINE,
        'doc': 'Inclusion d\'un fichier XPX',
        'attrs': ['file', 'option'],
        'snippets': ['file="$1"', 'option="once" file="$1"'],
        'values': {
            'option': ['noparse', 'once', 'parse'],
        },
    },
    'json': {
        'kind': BLOCK,
        'doc': 'Chargement de JSON dans un tableau XPX',
        'attrs': ['name'],
        'snippets': ['name="$1"'],
    },
    'mail': {
        'kind': INLINE,
        'doc': 'Envoi d\'un e-mail',
        'attrs': ['cc', 'cci', 'charset', 'file', 'from', 'headers', 'join', 'msg', 'reply',
                  'smtp', 'subject', 'to', 'type'],
        'snippets': ['from="$1" to="$2" subject="$3" msg="$4"'],
        'values': {
            'charset': ['iso-8859-1', 'utf-8'],
            'smtp': ['localhost'],
            'type': ['html', 'multipart', 'text'],
        },
    },
    'noparse': {
        'kind': BLOCK,
        'doc': 'Désactive l\'interprétation XPX du contenu',
        'attrs': [],
        'snippets': [''],
    },
    'pdf': {
        'kind': DUAL,
        'doc': 'Génération PDF : document (bloc) ou instruction (inline)',
        'attrs': ['addpage', 'align', 'bgcolor', 'border', 'calc', 'close', 'color',
                  'embcontent', 'embdesc', 'embname', 'embpath', 'embtype', 'file', 'font',
                  'frame', 'gettext', 'getx', 'gety', 'href', 'leading', 'line', 'mode',
                  'name', 'padding', 'pagesize', 'path', 'rect', 'rotate', 'round', 'size',
                  'style', 'text', 'x', 'y'],
        'snippets': {
            BLOCK: ['file="$1" name="$2"'],
            INLINE: ['text="$1" x="$2" y="$3"', 'addpage=""', 'font="$1" size="$2"',
                     'close=""'],
        },
        'values': {
            'align': ['center', 'left', 'right'],
            'font': ['Courier', 'Helvetica', 'Symbol', 'Times', 'ZapfDingbats'],
            'mode': ['clip', 'noclip', 'pagebreak'],
            'style': ['b', 'i', 'n', 'u'],
        },
    },
    'pict': {
        'kind': INLINE,
        'doc': 'Image : redimensionnement, filtre, QR code',
        'attrs': ['border', 'calc', 'close', 'color', 'content', 'copy', 'dest', 'fill',
                  'filter', 'font', 'geth', 'getw', 'height', 'margin', 'name', 'option',
                  'path', 'position', 'qrcode', 'rect', 'rotate', 'size', 'srcparam', 'text',
                  'thickness', 'transparency', 'width', 'x', 'y'],
        'snippets': ['path="$1" dest="$2" width="$3"', 'qrcode="$1" dest="$2"'],
        'values': {
            'filter': ['grayscale'],
            'option': ['quality', 'speed'],
            'position': ['BL', 'BM', 'BR', 'ML', 'MM', 'MR', 'TL', 'TM', 'TR'],
        },
    },
    'scope': {
        'kind': BLOCK,
        'doc': 'Portée locale des variables',
        'attrs': ['name'],
        'snippets': ['name="$1"'],
    },
    'set': {
        'kind': INLINE,
        'doc': 'Affectation d\'une variable',
        'attrs': ['bit', 'bitoff', 'biton', 'by', 'charset', 'chartohexa', 'datetime',
                  'decode64', 'decrypt', 'encode64', 'encrypt', 'expr', 'format', 'global',
                  'hash', 'hex2bin', 'hexatochar', 'hmac', 'html2text', 'keycode', 'lang',
                  'len', 'local', 'lowcase', 'ltrim', 'money', 'name', 'noaccent', 'rand',
                  'replace', 'return', 'rtrim', 'scope', 'session', 'strcode', 'strdecode',
                  'strescape', 'svg2pdf', 'trim', 'upcase', 'urlcode', 'value', 'xmlcode'],
        'snippets': ['name="$1" value="$2"', 'name="$1" expr="$2"', 'global="$1" value="$2"',
                     'return="$1" value="$2"'],
        'values': {
            'charset': ['iso-8859-1', 'utf-8'],
            'format': ['dd/mm/yyyy', 'hh:mn:ss', 'hh:mn:ss.ms', 'tt', 'yymmddhhmnss',
                       'yyyy-mm-dd'],
            'hash': ['md5', 'sha1', 'sha256'],
            'lang': ['en', 'es', 'fr'],
        },
    },
    'setarea': {
        'kind': BLOCK,
        'doc': 'Affectation d\'une variable sur plusieurs lignes',
        'attrs': ['name', 'option'],
        'snippets': ['name="$1"'],
        'values': {
            'option': ['noparse', 'parse'],
        },
    },
    'sql': {
        'kind': BLOCK,
        'doc': 'Requête SQL (boucle sur les lignes du résultat)',
        'attrs': ['connect', 'maxrows', 'name', 'option', 'query', 'start'],
        'snippets': ['query="$1"'],
        'values': {
            'option': ['enter', 'notenter'],
        },
    },
    'system': {
        'kind': INLINE,
        'doc': 'Exécution d\'une commande système',
        'attrs': ['exec'],
        'snippets': ['exec="$1"'],
    },
    'unset': {
        'kind': INLINE,
        'doc': 'Suppression d\'une variable',
        'attrs': ['name'],
        'snippets': ['name="$1"'],
    },
    'wait': {
        'kind': INLINE,
        'doc': 'Pause',
        'attrs': ['value'],
        'snippets': ['value="$1"'],
    },
    'while': {
        'kind': BLOCK,
        'doc': 'Boucle',
        'attrs': ['array', 'expr'],
        'snippets': ['expr="$1"', 'array="$1"'],
    },
    'xpath': {
        'kind': INLINE,
        'doc': 'Requête XPath sur du XML',
        'attrs': ['file', 'select', 'value'],
        'snippets': ['select="$1" file="$2"', 'select="$1" value="$2"'],
    },
    'xproc': {
        'kind': DUAL,
        'doc': 'Parcours d\'éléments XML',
        'attrs': ['file', 'select', 'value'],
        'snippets': {
            BLOCK: ['select="$1" file="$2"', 'select="$1" value="$2"'],
            INLINE: ['select="$1" file="$2"'],
        },
    },
}

# Balises XPX toujours inline (sans balise fermante) : utilisées par la
# commande qui ajoute les « /> » manquants et par l'indentation.
INLINE_TAGS = frozenset(name for name, tag in TAGS.items() if tag['kind'] == INLINE)

# Variables internes XPX : nom -> description.
INTERNAL_VARIABLES = {
    'phcversion': 'Version XPX (lecture)',
    'phcerr': 'Numéro d\'erreur (lecture)',
    'phcerrmsg': 'Message d\'erreur (lecture)',
    'phcsessionid': 'Identifiant de session (lecture)',
    'phcdebug': 'Mode debug (lecture/écriture)',
    'phcoutput': 'Espaces et retours chariot : 1 = lignes vides, 2 = CR (lecture/écriture)',
    'phccharset': 'Encodage, défaut iso-8859-1 (lecture/écriture)',
    'phcdateformat': 'Format de date, 1 à 4 (lecture/écriture)',
    'phclooplimit': 'Limite anti-boucle infinie, défaut 500 000 (lecture/écriture)',
    'phcfloatprecision': 'Précision des calculs flottants (lecture/écriture)',
    'phcparamcount': 'Nombre de paramètres reçus (lecture)',
    'sqlrowcount': 'Nombre de lignes de la dernière requête SQL',
    'sqlnumrow': 'Numéro de la ligne SQL courante',
    'sqlid': 'Identifiant auto-incrément du dernier INSERT',
    'sqlerr': 'Numéro d\'erreur SQL',
    'sqlerrmsg': 'Message d\'erreur SQL',
    'csvrowcount': 'Nombre de lignes CSV',
    'csvnumrow': 'Numéro de la ligne CSV courante',
    'csvcolcount': 'Nombre de colonnes CSV',
    'xprocrowcount': 'Nombre de résultats XPROC',
    'xprocnumrow': 'Numéro du résultat XPROC courant',
    'xproc.content': 'Contenu de l\'élément XML courant',
    'xproc.name': 'Nom de l\'élément XML courant',
    'xproc.attributes': 'Attributs de l\'élément XML courant',
}


def tag_snippets(name, kind):
    """Modèles d'attributs par défaut d'une balise pour une nature donnée."""
    snippets = TAGS[name].get('snippets', [''])
    if isinstance(snippets, dict):
        return snippets.get(kind, [''])
    return snippets


# Raccourcis : abréviation -> (description, snippet sans le « < » initial).
# Utilisables après « < » ou directement dans le texte (Tab).
SHORTCUTS = {
    'debugn': ('Debug en mode normal', 'debug mode="normal" />$0'),
    'debugo': ('Debug désactivé', 'debug mode="off" />$0'),
    'debuga20': ('Debug automatique sur 20 appels', 'debug mode="auto" count="${1:20}" />$0'),
    'setd0': ('Désactive phcdebug', 'set global="phcdebug" value="0" />$0'),
    'setd1': ('Active phcdebug', 'set global="phcdebug" value="1" />$0'),
    'setsql0': ('Désactive l\'échappement SQL automatique',
                'set global="sqlescapestr" value="0" />$0'),
    'setsql1': ('Active l\'échappement SQL automatique',
                'set global="sqlescapestr" value="1" />$0'),
    'whilei': ('Boucle avec compteur',
               'set name="${1:i}" value="${2:0}" />\n'
               '<while expr="\\$$1\\$ < ${3:10}">\n'
               '\t$0\n'
               '\t<set name="$1" expr="\\$$1\\$+1" />\n'
               '</while>'),
}
