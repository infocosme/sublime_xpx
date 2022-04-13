import json
import os

import sublime
import sublime_plugin


def addGotoFunctionInContextMenuXPX():
	"""
	Le sous-menu est organisé en deux parties optionnelles :
		- Partie 1 : Clic-droit sur un function exec : création raccourci vers function name correspondant
		- Partie 2 : Liste des function name défini dans la page courante.

	Recherche toutes les balises <function name=""> du script en cours.
	Ajoute au menu contextuel toutes les entrées.

	Lors du clic sur un nom de fonction, déclenche l'affichage de la ligne correspondante.

	A partir de la window courante, lecture de la view active.
	Recherche de toutes les occurences contenant <function name=.
	Parcours des occurences, affichage du contenu de chaque ligne.

	Le sous-menu créé dynamiquement est ajouté au cache, pas dans le dossier d'installation du package.
	Le sous-menu complète donc le sous-menu défini dans le package.

	Les commandes du context_menu seront ajoutées au menu id xpx en tant que children.

	Pour atteindre tous les contextes, suppression des arguments d'entrées et fondation sur sublime.active_window.
	"""
	encoding = 'utf-8'
	#print("coucou")

	# make sure cache path exists
	cache_path = os.path.join(sublime.cache_path(), "XPX")
	os.makedirs(cache_path, exist_ok=True)

	# Récupération de la vue active (celle affichée).
	mywindow = sublime.active_window()
	myview = mywindow.active_view()

	if not myview.match_selector(myview.window_to_text((0,0)), "text.html.xpx"):
		#print("hors XPX")
		# Pour effacer le menu éventuel déjà créé : écriture d'une occurence vide.
		context_menu = []
		# write the context menu item to the cache path : w et non pas w+.
		with open(os.path.join(cache_path, "Context.sublime-menu"), "w") as cache:
			cache.write(json.dumps(context_menu, cache))
		return None

	else:
		#print("script XPX")
		context_menu = [
	    	{ "caption": "-" },
			{ 
	        	"caption": "XPX",
				"children": []
			}
		]
		# Parcours de toutes les occurences de texte comprenant <function name=.
		affmenu = False
		for myregionfunction in myview.find_all("<function name=\""):
			# A compter de la fin de la région trouvée, extension de la région avec séparateur ".
			myname = myview.substr(myview.expand_by_class(myregionfunction.end(),sublime.CLASS_WORD_START,"\""))
			# Ajout de la ligne sous-menu dans le json texte.
			context_menu[1]['children'].append({ "caption": "Go to function name "+myname[6:len(myname)-2], "command": "xpx_go_to_function_name", "args": {"functionName": myname} })
			# print(myname[6:len(myname)-2])
			affmenu = True
		if not affmenu:
			context_menu = []
		# print(json.dumps(context_menu, sort_keys=True))
		# write the context menu item to the cache path : w et non pas w+.
		with open(os.path.join(cache_path, "Context.sublime-menu"), "w") as cache:
			cache.write(json.dumps(context_menu, cache))


class XpxGoToFunctionNameCommand(sublime_plugin.WindowCommand):
	"""
	Recherche de la chaîne name="[nom de la fonction]" puis déplacement de l'écran.
	"""

	# Dans le cas d'une commande, il est possible de transférer des arguments par args en jSON.
	# Le champ défini dans args est récupérable en ajoutant le même champ au prototype de la fonction.
	def run(self, functionName):
		
		#print("Go to function name "+functionName)
		# Recherche de l'emplacement visé par le functionName : name="nomFonction".
		myview = self.window.active_view()
		# Déplacement de l'écran sur l'emplacement trouvé.
		myview.show_at_center(myview.find(functionName,0))


class EventListener(sublime_plugin.EventListener):

	def on_text_command(self, view, command, args):
		# ST wants to display the context menu
		if command == "context_menu":
			# Dans ce cas, mise à jour du menu contextuel XPX...
			addGotoFunctionInContextMenuXPX()

