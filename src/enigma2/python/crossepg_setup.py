from __future__ import print_function
from __future__ import absolute_import

import os
from time import *

from enigma import getDesktop
from boxbranding import getImageDistro
from Components.ActionMap import NumberActionMap
from Components.Button import Button
from Components.config import KEY_LEFT, KEY_RIGHT, KEY_HOME, KEY_END, KEY_0, KEY_ASCII, ConfigYesNo, ConfigSelection, ConfigClock, config, configfile
from Components.ConfigList import ConfigListScreen
from Components.Harddisk import harddiskmanager
from Components.Label import Label
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Setup import SetupSummary
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

from . crossepglib import *
from . crossepg_locale import _


class CrossEPG_Setup(ConfigListScreen, Screen):
	def __init__(self, session):
		if (getDesktop(0).size().width() < 800):
			skin = "%s/skins/setup_sd.xml" % (os.path.dirname(sys.modules[__name__].__file__))
		else:
			skin = "%s/skins/setup_hd.xml" % (os.path.dirname(sys.modules[__name__].__file__))
		f = open(skin, "r")
		self.skin = f.read()
		f.close()
		Screen.__init__(self, session)
		self.setup_title = _("CrossEPG Setup")
		Screen.setTitle(self, self.setup_title)

		patchtype = getEPGPatchType()
		if patchtype == 0 or patchtype == 1 or patchtype == 3:
			self.fastpatch = True
		else:
			self.fastpatch = False

		self.session = session

		self.config = CrossEPG_Config()
		self.config.load()

		self.lamedbs = self.config.getAllLamedbs()

		self.lamedbs_desc = []
		self.mountpoint = []
		self.mountdescription = []
		self.automatictype = []

		self.show_extension = self.config.show_extension
		self.show_plugin = self.config.show_plugin
		self.show_force_reload_as_plugin = self.config.show_force_reload_as_plugin

		if getImageDistro() not in ("openvix",  ):
			## make devices entries
			if self.config.isQBOXHD():
				self.mountdescription.append(_("Internal flash"))
				self.mountpoint.append("/var/crossepg/data")

			for partition in harddiskmanager.getMountedPartitions():
				if (partition.mountpoint != '/') and (partition.mountpoint != '') and self.isMountedInRW(partition.mountpoint):
					self.mountpoint.append(partition.mountpoint + "/crossepg")

					if partition.description != '':
						self.mountdescription.append(partition.description)
					else:
						self.mountdescription.append(partition.mountpoint)

			if not self.config.isQBOXHD():		# for other decoders we add internal flash as last entry (it's unsuggested)
				self.mountdescription.append(_("Internal flash (unsuggested)"))
				self.mountpoint.append(self.config.home_directory + "/data")

		# make lamedb entries
		for lamedb in self.lamedbs:
			if lamedb == "lamedb":
				self.lamedbs_desc.append(_("main lamedb"))
			else:
				self.lamedbs_desc.append(lamedb.replace("lamedb.", "").replace(".", " "))

		# make automatic type entries
		self.automatictype.append(_("disabled"))
		self.automatictype.append(_("once a day"))
		self.automatictype.append(_("every hour (only in standby)"))

		self.onChangedEntry = []
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=self.session, on_change=self.changedEntry)

		self["information"] = Label("")
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("OK"))
		self["key_yellow"] = Button()
		self["key_blue"] = Button("")
		self["config_actions"] = NumberActionMap(["SetupActions", "InputAsciiActions", "KeyboardInputActions", "ColorActions", "MenuActions"],
		{
			"gotAsciiCode": self.keyGotAscii,
			"cancel": self.keyCancel,
			"red": self.keyCancel,
			"green": self.keySave,
			"left": self.keyLeft,
			"right": self.keyRight,
			"home": self.keyHome,
			"end": self.keyEnd,
			"menu": self.keyCancel,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal
		}, -1) # to prevent left/right overriding the listbox

		self.makeList()
		if not self.setInfo in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.setInfo)

	# for summary:
	def changedEntry(self):
		self.item = self["config"].getCurrent()
		for x in self.onChangedEntry:
			x()
		try:
			if isinstance(self["config"].getCurrent()[1], ConfigYesNo) or isinstance(self["config"].getCurrent()[1], ConfigSelection):
				self.createSetup()
		except:
			pass

	def getCurrentEntry(self):
		return self["config"].getCurrent() and self["config"].getCurrent()[0] or ""

	def getCurrentValue(self):
		return self["config"].getCurrent() and str(self["config"].getCurrent()[1].getText()) or ""

	def createSummary(self):
		return SetupSummary

	def isMountedInRW(self, path):
		testfile = os.path.join(path, "tmp-rw-test")
		try:
			open(testfile, "wb").close()
			os.unlink(testfile)
		except:
			return False
		return True

	def showWarning(self):
		self.session.open(MessageBox, _("PLEASE READ!\nA hard drive or an usb pen is STRONGLY SUGGESTED. If you still want use your internal flash pay attention to:\n(1) If you don't have enough free space your box may completely block and you need to flash it again\n(2) Many write operations on your internal flash may damage your flash memory"), type=MessageBox.TYPE_ERROR)

	def keyLeft(self):
		self["config"].handleKey(KEY_LEFT)
		self.update()
		#self.setInfo()

	def keyRight(self):
		self["config"].handleKey(KEY_RIGHT)
		self.update()
		#self.setInfo()

	def keyHome(self):
		self["config"].handleKey(KEY_HOME)
		self.update()
		#self.setInfo()

	def keyEnd(self):
		self["config"].handleKey(KEY_END)
		self.update()
		#self.setInfo()

	def keyGotAscii(self):
		self["config"].handleKey(KEY_ASCII)
		self.update()

	def keyNumberGlobal(self, number):
		self["config"].handleKey(KEY_0 + number)
		self.update()
		#self.setInfo()

	def makeList(self):
		self.list = []

		if getImageDistro() not in ("openvix",  ):
			device_default = None
			i = 0
			for mountpoint in self.mountpoint:
				if mountpoint == self.config.db_root:
					device_default = self.mountdescription[i]
				i += 1

			## default device is really important... if miss a default we force it on first entry and update now the main config
			if device_default == None:
				self.config.db_root = self.mountpoint[0]
				device_default = self.mountdescription[0]
		print("[crosssepg_setup] self.config.db_root = %s" % self.config.db_root)
		lamedb_default = _("main lamedb")
		if self.config.lamedb != "lamedb":
			lamedb_default = self.config.lamedb.replace("lamedb.", "").replace(".", " ")

		scheduled_default = None
		if self.config.download_standby_enabled:
			scheduled_default = _("every hour (only in standby)")
		elif self.config.download_daily_enabled:
			scheduled_default = _("once a day")
		else:
			scheduled_default = _("disabled")

		if getImageDistro() not in ("openvix",  ):
			self.list.append((_("Storage device"), ConfigSelection(self.mountdescription, device_default)))
		if len(self.lamedbs_desc) > 1:
			self.list.append((_("Preferred lamedb"), ConfigSelection(self.lamedbs_desc, lamedb_default)))

		self.list.append((_("Enable csv import"), ConfigYesNo(self.config.csv_import_enabled > 0)))
		if getImageDistro() not in ("openvix",  ):
			self.list.append((_("Force epg reload on boot"), ConfigYesNo(self.config.force_load_on_boot > 0)))
		self.list.append((_("Scheduled download"), ConfigSelection(self.automatictype, scheduled_default)))

		if self.config.download_daily_enabled:
			ttime = localtime()
			ltime = (ttime[0], ttime[1], ttime[2], self.config.download_daily_hours, self.config.download_daily_minutes, ttime[5], ttime[6], ttime[7], ttime[8])
			self.list.append((_("Scheduled download at"), ConfigClock(mktime(ltime))))

		if not self.fastpatch:
			self.list.append((_("Reboot after a scheduled download"), ConfigYesNo(self.config.download_daily_reboot > 0)))
			self.list.append((_("Reboot after a manual download"), ConfigYesNo(self.config.download_manual_reboot > 0)))
		self.list.append((_("Show as plugin"), ConfigYesNo(self.config.show_plugin > 0)))
		self.list.append((_("Show as extension"), ConfigYesNo(self.config.show_extension > 0)))
		if getImageDistro() not in ("openvix",  ):
			self.list.append((_("Show 'Force reload' as plugin"), ConfigYesNo(self.config.show_force_reload_as_plugin > 0)))

		self["config"].list = self.list
		self["config"].setList(self.list)
		self.setInfo()

	def update(self):
		redraw = False
		if getImageDistro() not in ("openvix",  ):
			self.config.db_root = self.mountpoint[self.list[0][1].getIndex()]
			i = 1
		else:
			i = 0

		if len(self.lamedbs_desc) > 1:
			self.config.lamedb = self.lamedbs[self.list[i][1].getIndex()]
			i += 1

		self.config.csv_import_enabled = int(self.list[i][1].getValue())

		if getImageDistro() not in ("openvix",  ):
			self.config.force_load_on_boot = int(self.list[i + 1][1].getValue())
		else:
			i -= 1

		dailycache = self.config.download_daily_enabled
		standbycache = self.config.download_standby_enabled
		if getImageDistro() not in ("openvix",  ):
			if self.list[i + 2][1].getIndex() == 0:
				self.config.download_daily_enabled = 0
				self.config.download_standby_enabled = 0
			elif self.list[i + 2][1].getIndex() == 1:
				self.config.download_daily_enabled = 1
				self.config.download_standby_enabled = 0
			else:
				self.config.download_daily_enabled = 0
				self.config.download_standby_enabled = 1
		else:
			if int(self.list[i + 2][1].getIndex()) == 0:
				self.config.download_daily_enabled = 0
				self.config.download_standby_enabled = 0
			elif int(self.list[i + 2][1].getIndex()) == 1:
				self.config.download_daily_enabled = 1
				self.config.download_standby_enabled = 0
			elif int(self.list[i + 2][1].getIndex()) == 2:
				self.config.download_daily_enabled = 0
				self.config.download_standby_enabled = 1

		if dailycache != self.config.download_daily_enabled or standbycache != self.config.download_standby_enabled:
			redraw = True

		i += 3
		if dailycache:
			self.config.download_daily_hours = self.list[i][1].getValue()[0]
			self.config.download_daily_minutes = self.list[i][1].getValue()[1]
			i += 1

		if not self.fastpatch:
			self.config.download_daily_reboot = int(self.list[i][1].getValue())
			self.config.download_manual_reboot = int(self.list[i + 1][1].getValue())
			i += 2

		self.config.show_plugin = int(self.list[i][1].getValue())
		self.config.show_extension = int(self.list[i + 1][1].getValue())
		if getImageDistro() not in ("openvix",  ):
			self.config.show_force_reload_as_plugin = int(self.list[i + 2][1].getValue())
		else:
			i += 1

		if redraw:
			self.makeList()

	def setInfo(self):
		index = self["config"].getCurrentIndex()
		if getImageDistro() in ("openvix",  ):
			index += 1
		if index == 0:
			self["information"].setText(_("Drive where you save data.\nThe drive MUST be mounted in rw. If you can't see your device here probably is mounted as read only or autofs handle it only in read only mode. In case of mount it manually and try again"))
			return
		if len(self.lamedbs_desc) <= 1:
			index += 1
		if index == 1:
			self["information"].setText(_("Lamedb used for epg.dat conversion.\nThis option doesn't work with crossepg patch v2"))
			return
		if index == 2:
			self["information"].setText(_("Import *.csv and *.bin from %s/import or %s/import\n(*.bin are binaries with a csv as stdout)") % (self.config.db_root, self.config.home_directory))
			return
		if getImageDistro() in ("openvix",  ):
			index += 1
		if index == 3:
			self["information"].setText(_("Reload epg at every boot.\nNormally it's not necessary but recover epg after an enigma2 crash"))
			return
		if index == 4:
			if self.config.download_standby_enabled:
				self["information"].setText(_("When the decoder is in standby opentv providers will be automatically downloaded every hour.\nXMLTV providers will be always downloaded only once a day"))
				return
			elif self.config.download_daily_enabled:
				self["information"].setText(_("Download epg once a day"))
				return
			else:
				self["information"].setText(_("Scheduled download disabled"))
				return
		if self.config.download_daily_enabled == 0:
			index += 1
		if index == 5:
			if self.config.download_standby_enabled or self.config.download_daily_enabled:
				self["information"].setText(_("Time for scheduled daily download"))
				return
		if self.fastpatch:
			index += 2
		if index == 6:
			self["information"].setText(_("Automatically reboot the decoder after a scheduled download"))
			return
		if index == 7:
			self["information"].setText(_("Automatically reboot the decoder after a manual download"))
			return
		if index == 8:
			self["information"].setText(_("Show crossepg in plugin menu"))
			return
		if index == 9:
			self["information"].setText(_("Show crossepg in extensions menu"))
			return
		if index == 10:
			self["information"].setText(_("Show crossepg force load in plugin menu"))
			return

	def cancelConfirm(self, result):
		if not result:
			return

		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()

	def keySave(self):
		self.config.last_full_download_timestamp = 0
		self.config.last_partial_download_timestamp = 0
		self.config.configured = 1
		self.config.save()
		if getImageDistro() not in ("openvix",  ):
			try:
				if self.config.db_root[-8:] == "crossepg":
					config.misc.epgcache_filename.setValue(self.config.db_root[:-9] + "/epg.dat")
				else:
					config.misc.epgcache_filename.setValue(self.config.db_root + "/epg.dat")
				config.misc.epgcache_filename.callNotifiersOnSaveAndCancel = True
				config.misc.epgcache_filename.save()
				configfile.save()
			except Exception as e:
				print("[crossepg_setup:keySave] custom epgcache filename not supported by current enigma2 version")
		print("[crosssepg_setup][key_save] self.config.db_root = %s" % self.config.db_root)
		if getEPGPatchType() == -1:
			# exec crossepg_prepare_pre_start for unpatched images
			os.system(self.config.home_directory + "/crossepg_prepare_pre_start.sh")

		if self.show_extension != self.config.show_extension or self.show_plugin != self.config.show_plugin:
			for plugin in plugins.getPlugins(PluginDescriptor.WHERE_PLUGINMENU):
				if plugin.name == "CrossEPG Downloader":
					plugins.removePlugin(plugin)

			for plugin in plugins.getPlugins(PluginDescriptor.WHERE_EXTENSIONSMENU):
				if plugin.name == "CrossEPG Downloader":
					plugins.removePlugin(plugin)

			plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))

		if getImageDistro() not in ("openvix",  ):
			if (self.config.db_root == self.config.home_directory + "/data" and not self.config.isQBOXHD()) or self.config.db_root.startswith('/etc/enigma2'):
				self.showWarning()
		else:
			if config.misc.epgcache_filename.value.startswith('/etc/enigma2'):
				self.showWarning()

		self.close()
