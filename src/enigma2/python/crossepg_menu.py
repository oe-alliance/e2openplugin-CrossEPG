from __future__ import print_function
from __future__ import absolute_import

from time import *

from enigma import *
import _enigma
from boxbranding import getImageDistro
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.Label import Label
from Components.Harddisk import harddiskmanager
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText
from Components.PluginComponent import plugins
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap

from . crossepglib import *
from . crossepg_info import CrossEPG_Info
from . crossepg_about import CrossEPG_About
from . crossepg_providers import CrossEPG_Providers
from . crossepg_setup import CrossEPG_Setup
from . crossepg_downloader import CrossEPG_Downloader
from . crossepg_importer import CrossEPG_Importer
from . crossepg_converter import CrossEPG_Converter
from . crossepg_loader import CrossEPG_Loader
from . crossepg_ordering import CrossEPG_Ordering
from . crossepg_rytec_update import CrossEPG_Rytec_Update
from . crossepg_xepgdb_update import CrossEPG_Xepgdb_Update
from . crossepg_defragmenter import CrossEPG_Defragmenter
from . crossepg_locale import _





class CrossEPG_Menu(Screen):
	def __init__(self, session):
		if (getDesktop(0).size().width() < 800):
			skin = "%s/skins/menu_sd.xml" % os.path.dirname(sys.modules[__name__].__file__)
		else:
			skin = "%s/skins/menu_hd.xml" % os.path.dirname(sys.modules[__name__].__file__)
		f = open(skin, "r")
		self.skin = f.read()
		f.close()
		Screen.__init__(self, session)
		try:
			from . version import version
			self.setup_title = _("CrossEPG") + " - " + version[:5]
			Screen.setTitle(self, self.setup_title)
		except Exception as e:
			self.setup_title = _("CrossEPG") + " - " + _("unknown version")
			Screen.setTitle(self, self.setup_title)

		self.config = CrossEPG_Config()
		self.config.load()
		self.patchtype = getEPGPatchType()

		self.onChangedEntry = []
		l = []
		l.append(self.buildListEntry(_("Configure"), "configure.png"))
		l.append(self.buildListEntry(_("OpenTV providers"), "opentv.png"))
		l.append(self.buildListEntry(_("XMLTV providers"), "xmltv.png"))
		# l.append(self.buildListEntry(_("XEPGDB providers"), "xepgdb.png"))
		l.append(self.buildListEntry(_("Scripts providers"), "scripts.png"))
		# l.append(self.buildListEntry(_("MHW2 providers"), "opentv.png"))
		l.append(self.buildListEntry(_("Providers start order"), "reorder.png"))
		l.append(self.buildListEntry(_("Update rytec providers"), "rytec_small.png"))
		# l.append(self.buildListEntry(_("Update xepgdb providers"), "xepgdb.png"))
		l.append(self.buildListEntry(_("Download now"), "download.png"))
		l.append(self.buildListEntry(_("Defragment database"), "conversion.png"))
		if getImageDistro() not in ("openvix", ):
			l.append(self.buildListEntry(_("Force csv import now"), "csv.png"))
			l.append(self.buildListEntry(_("Force epg.dat conversion now"), "conversion.png"))
			l.append(self.buildListEntry(_("Force epg reload"), "reload.png"))
		l.append(self.buildListEntry(_("Info about database"), "dbinfo.png"))
		l.append(self.buildListEntry(_("About"), "about.png"))

		self["list"] = List(l)
		self["setupActions"] = ActionMap(["SetupActions", 'ColorActions', "MenuActions"],
		{
			"cancel": self.quit,
			"ok": self.openSelected,
			"green": self.openSelected,
			"menu": self.quit,
		}, -2)
		self["key_red"] = Button(_("Close"))
		self["key_green"] = Button(_("OK"))

		if self.config.configured == 0:
			self.onFirstExecBegin.append(self.openSetup)

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return str(self["list"].getCurrent()[1])

	def getCurrentValue(self):
		return ""

	def createSummary(self):
		return CrossEPG_MenuSummary

	def buildListEntry(self, description, image):
		png = resolveFilename(SCOPE_CURRENT_SKIN, "skin-default/crossepg/" + image)
		if png == None or not os.path.exists(png):
			png = "%s/images/%s" % (os.path.dirname(sys.modules[__name__].__file__), image)
		pixmap = LoadPixmap(cached=True, path=png)
		return((pixmap, description))

	def openSetup(self):
		self.session.open(CrossEPG_Setup)

	def openSelected(self):
		index = self["list"].getIndex()
		if index == 0:
			self.session.open(CrossEPG_Setup)
			return
		if index == 1:
			self.session.open(CrossEPG_Providers, "opentv")
			return
		if index == 2:
			self.session.open(CrossEPG_Providers, "xmltv")
			return
		if index == 3:
			self.session.open(CrossEPG_Providers, "script")
			return
		if index == 4:
			self.session.open(CrossEPG_Ordering)
			return
		if index == 5:
			self.session.open(CrossEPG_Rytec_Update)
			return
		if index == 6:
			self.config.load()
			self.config.deleteLog()
			self.downloader()
			return
		if index == 7:
			self.session.open(CrossEPG_Defragmenter)
			return
		if getImageDistro() == "openvix":
			index += 3
		if index == 8:
			self.importer()
			return
		if index == 9:
			self.converter()
			return
		if index == 10:
			self.loader()
			return
		if index == 11:
			self.session.open(CrossEPG_Info)
			return
		if index == 12:
			self.session.open(CrossEPG_About)
			return

	def quit(self):
		self.close()

	def downloader(self):
		self.config.load()
		self.session.openWithCallback(self.downloadCallback, CrossEPG_Downloader, self.config.providers)

	def downloadCallback(self, ret):
		if ret:
			if self.config.csv_import_enabled == 1:
				self.importer()
			else:
				if self.patchtype != 3:
					self.converter()
				else:
					self.loader()

	def importer(self):
		self.session.openWithCallback(self.importerCallback, CrossEPG_Importer)

	def importerCallback(self, ret):
		if ret:
			if self.patchtype != 3:
				self.converter()
			else:
				self.loader()

	def converter(self):
		self.session.openWithCallback(self.converterCallback, CrossEPG_Converter)

	def converterCallback(self, ret):
		if ret:
			if self.patchtype != -1:
				self.loader()
			else:
				if self.config.download_manual_reboot:
					self.session.open(TryQuitMainloop, 3)

	def loader(self):
		self.session.open(CrossEPG_Loader)


class CrossEPG_MenuSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["SetupTitle"] = StaticText(_(parent.setup_title))
		self["SetupEntry"] = StaticText("")
		self["SetupValue"] = StaticText("")
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		self.parent.onChangedEntry.append(self.selectionChanged)
		self.parent["list"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def removeWatcher(self):
		self.parent.onChangedEntry.remove(self.selectionChanged)
		self.parent["list"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		self["SetupEntry"].text = self.parent.getCurrentEntry()
		self["SetupValue"].text = self.parent.getCurrentValue()
