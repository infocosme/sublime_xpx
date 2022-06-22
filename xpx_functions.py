import json
import os

import sublime
import sublime_plugin

"""
	Sur clic-droit à l'intérieur d'une balise "function exec" : 
		Création dynamique d'une commande contextuelle nommée "Goto Definition [Nom de la fonction décrite dans exec]".
	Dans un script contenant des function name :
		Création dynamique d'un menu contextuel nommé "Show Function" et listant toutes les "function name" du script.
"""

def getListFunctionName(myview):
	"""
	Listing de toutes les définitions de function dans la vue courante.
	"""
	maliste = []
	# Parcours de toutes les occurences de texte comprenant <function name=.
	for myregionfunction in myview.find_all("<function name=\""):
		# A compter de la fin de la région trouvée, extension de la région avec séparateur ".
		myname = myview.substr(myview.expand_by_class(myregionfunction.end()+1,sublime.CLASS_WORD_START | sublime.CLASS_WORD_END,"\""))
		# Ajout de la ligne de commande dans le sous-menu XPX du menu contextuel.
		maliste.append(myname)
	return maliste


class XpxContextMenuFindFunctionDefCommand(sublime_plugin.TextCommand):
	"""
	Commande volatile dans le menu contextuel.
	Proposition d'atteindre la définition de la fonction sur laquelle le clic-droit est effectué (n'importe où sur la ligne).
	Recherche du contenu de toute la balise cliquée puis contrôle si la balise est "function" puis "exec" puis lancement commande.
	"""	
	def getFunctionName(self, event):
		# Récupération du nom de la fonction concernée.
		pt = self.view.window_to_text((event["x"], event["y"]))
		# Est-ce que nous sommes sur une balise function ?
		# 22/06/2022 : Correction bug : remplacement de meta.tag.function.begin.xpx par meta.tag.function.xpx.
		if self.view.match_selector(pt,'meta.tag.function.xpx'):
			# Lecture du début de la balise function.
			ptfindfunction = self.view.expand_by_class(pt,sublime.CLASS_PUNCTUATION_START | sublime.CLASS_PUNCTUATION_END,"<>").begin()+1
			#if (self.view.substr(self.view.expand_by_class(ptfindfunction,sublime.CLASS_WORD_START | sublime.CLASS_WORD_END)) == "function"):
			ptfindexec = self.view.expand_by_class(ptfindfunction,sublime.CLASS_WORD_START | sublime.CLASS_WORD_END).end()+3
			if (self.view.substr(self.view.expand_by_class(ptfindexec,sublime.CLASS_WORD_START | sublime.CLASS_WORD_END)) == "exec"):
				ptfindname = self.view.expand_by_class(ptfindexec,sublime.CLASS_WORD_START | sublime.CLASS_WORD_END).end()+3
				myname = self.view.substr(self.view.expand_by_class(ptfindname,sublime.CLASS_WORD_START+sublime.CLASS_WORD_END,"\""))
				return myname
		# Dans les autres cas, on annule l'option.
		return None

	def want_event(self):
		return True

	def is_visible(self, event):
		return self.getFunctionName(event) is not None
	
	def description(self, event):
		functionName = self.getFunctionName(event)
		# Limitation de la longueur du texte dans le menu
		if len(functionName) > 64:
			functionName = functionName[0:64] + "..."
		return "Goto Definition " + functionName

	def run(self, edit, event):
		"""
		Exécution de la commande :
		Ouvrir le fichier source contenant la définition de la function right-cliquée.
		"""
		flags = sublime.ENCODED_POSITION | sublime.FORCE_GROUP
		# Récupération du nom de la fonction ciblée.
		functionName = self.getFunctionName(event)
		mywindow = sublime.active_window()
		# Recherche d'une entrée symbol correspondant au nom de la fonction.
		mylocations=mywindow.symbol_locations(functionName,sublime.SYMBOL_SOURCE_INDEX,sublime.SYMBOL_TYPE_DEFINITION,sublime.KIND_ID_FUNCTION)
		if (len(mylocations)>0):
			# En cas de file trouvé, affichage de chacun des files trouvés (normalement un seul).
			for l in mylocations:
				myview = mywindow.open_file(l.path_encoded_position(), flags)


class EventListener(sublime_plugin.EventListener):
	"""
	Ajout d'une écoute d'event pour déclencher la gestion du menu contextuel à chaque clic-droit.
	Valable uniquement pour les function name présents dans le view en cours.
	ATTENTION : le menu contextuel ne peut être modifié qu'ici.
	A l'intérieur d'un TextCommand, le menu contextuel est déjà ouvert, donc si modifications il y a,
	ces modifications n'apparaitraient qu'au prochain affichage : au prochain clic-droit.
	"""
	def on_text_command(self, view, command, args):
		# ST wants to display the context menu
		if command == "context_menu":
			"""
			Commande volatile dans le menu contextuel.
			Le sous-menu ne se déclenche qu'en cas de fichier possédant une région syntaxe XPX.
			Recherche toutes les balises <function name=""> du script en cours.
			Ajoute au menu contextuel toutes les entrées correspondantes.
			La commande correspondante à chaque entrée déplace l'affichage sur la ligne correspondante (show_center).
			Fonctionnement :
				Recherche de toutes les occurences contenant <function name=.
				Parcours des occurences, insertion du contenu de chaque ligne au menu contextuel.
				Si aucune occurence trouvée, création d'un sous-menu artificiel vide (pour effacement).
				Le sous-menu créé dynamiquement est ajouté au cache, pas dans le dossier d'installation du package.
				Le sous-menu complète donc le sous-menu défini dans le package.
			A chaque déclenchement, le sous menu contextuel est entièrement ré-écrit ce qui provoque son effacement le cas échéant.
			"""
			if view.match_selector(view.window_to_text((0,0)), "text.xpx"):
				# Recherche d'éventuelles occurences.
				maliste = getListFunctionName(view)
				if (len(maliste)>0):
					# Initialisation du menu contextuel à afficher.
					context_menu = [
						{ 
				        	"caption": "Show Function",
							"children": []
						}
					]
					# Parcours de toutes les occurences de texte comprenant <function name=.
					for mafonction in maliste:
						# Ajout de la ligne de commande dans le sous-menu XPX du menu contextuel.
						context_menu[0]['children'].append({ "caption": mafonction, "command": "xpx_goto_function_name", "args": {"functionName": mafonction} })
				else:
					context_menu = []
			else:
				context_menu = []
			# make sure cache path exists
			cache_path = os.path.join(sublime.cache_path(), "XPX")
			os.makedirs(cache_path, exist_ok=True)
			# write the context menu item to the cache path : w et non pas w+.
			# Ecriture systématique du context-menu pour actualisation en permanence (à chaque changement de view).
			encoding = 'utf-8'
			with open(os.path.join(cache_path, "Context.sublime-menu"), "w") as cache:
				cache.write(json.dumps(context_menu))


class XpxGotoFunctionNameCommand(sublime_plugin.WindowCommand):
	"""
	Déclenchement du scroll de la view courante sur la définition du function name demandé.
	Dans le cas d'une commande, il est possible de transférer des arguments par args en jSON.
	Le champ défini dans args est récupérable en ajoutant le même champ au prototype de la fonction.
	"""
	def run(self, functionName):
		# Recherche de l'emplacement visé par le functionName : name="nomFonction".
		myview = self.window.active_view()
		# Déplacement de l'écran sur l'emplacement trouvé.
		myview.show_at_center(myview.find("name=\""+functionName+"\"",0))
