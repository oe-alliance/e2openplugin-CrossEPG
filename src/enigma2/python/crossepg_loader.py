from __future__ import print_function
from future.utils import raise_
import six

if six.PY3:
	from types import MethodType as instancemethod
else:
	import new	
import _enigma
import os
import sys
from shutil import copyfile

from enigma import getDesktop, eTimer, eConsoleAppContainer
from boxbranding import getImageDistro
from Components.ActionMap import NumberActionMap
from Components.config import config
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.Sources.Progress import Progress
from Components.Sources.StaticText import StaticText

from Screens.MessageBox import MessageBox
from Screens.Screen import Screen

from . crossepglib import *
from . crossepg_locale import _




class CrossEPG_Loader(Screen):
	def __init__(self, session, pcallback=None, noosd=False):
		self.session = session
		if (getDesktop(0).size().width() < 800):
			skin = "%s/skins/downloader_sd.xml" % os.path.dirname(sys.modules[__name__].__file__)
			self.isHD = 0
		else:
			skin = "%s/skins/downloader_hd.xml" % os.path.dirname(sys.modules[__name__].__file__)
			self.isHD = 1
		f = open(skin, "r")
		self.skin = f.read()
		f.close()
		Screen.__init__(self, session)
		self.skinName = "downloader"
		Screen.setTitle(self, _("CrossEPG"))

		self["background"] = Pixmap()
		self["action"] = Label(_("Loading data"))
		self["summary_action"] = StaticText(_("Loading data"))
		self["status"] = Label("")
		self["progress"] = ProgressBar()
		self["progress"].hide()
		self["progress_text"] = Progress()

		self.retValue = True
		self.config = CrossEPG_Config()
		self.config.load()
		if getImageDistro() in ('openvix'):
			self.db_root = config.misc.epgcachepath.value + 'crossepg'
		else:
			self.db_root = self.config.db_root
		if not pathExists(self.db_root):
			if not createDir(self.db_root):
				self.db_root = "/hdd/crossepg"

		self.pcallback = pcallback
		self.wrapper = None

		self.pcallbacktimer = eTimer()
		self.pcallbacktimer.callback.append(self.doCallback)

		if pathExists("/usr/crossepg"):
			self.home_directory = "/usr/crossepg"
		elif pathExists("/var/crossepg"):
			self.home_directory = "/var/crossepg"
		else:
			print("[CrossEPG_Config] ERROR!! CrossEPG binaries non found")

		# check for common patches
		#	Explanation of different kind of EPG patches in images:
		#	- No patch used: The box (Enigma2) needs to be restarted to load the EPG data. While starting GUI can freeze/crash.
		#	- CrossEPG patch:loading data with crossepg patch v2
		#	- EPG patch: EPG data is written in epg.dat. At the end the "load" command is given to read epg.dat
		#	- Oudeis patch: EPG data is immediately loaded and accessible, even while the xmltv-plugin is running. Normaly there are no issues while loading.
		#	- Pli patch: Same as Oudeis patch but the xmltv-plugin runs in a seperate "thread" so no issues at all in the GUI or other components.		

		if six.PY2:
			try:
				self.xepgpatch = new.instancemethod(_enigma.eEPGCache_crossepgImportEPGv21, None, eEPGCache)
				print("[CrossEPG_Loader] patch crossepg v2.1 found")
			except Exception as e:
				print("[CrossEPG_Loader] patch crossepg v2.1 not found e = %s" % e)
				self.xepgpatch = None

			try:
				self.epgpatch = new.instancemethod(_enigma.eEPGCache_load, None, eEPGCache)
				print("[CrossEPG_Loader] patch epgcache.load() found")
			except Exception as e:
				print("[CrossEPG_Loader] patch epgcache.load() not found e = %s" % e)
				self.epgpatch = None

			try:
				self.edgpatch = new.instancemethod(_enigma.eEPGCache_reloadEpg, None, eEPGCache)
				print("[CrossEPG_Loader] patch EDG NEMESIS found")
			except Exception as e:
				print("[CrossEPG_Loader] patch EDG NEMESIS not found e = %s" % e)		
				self.edgpatch = None

			try:
				self.oudeispatch = new.instancemethod(_enigma.eEPGCache_importEvent, None, eEPGCache)
				print("[CrossEPG_Loader] patch Oudeis found")
			except Exception as e:
				print("[CrossEPG_Loader] patch Oudeis not found e = %s" % e)		
				self.oudeispatch = None
		else:
			try:
				self.xepgpatch = instancemethod(_enigma.eEPGCache_crossepgImportEPGv21, eEPGCache)
				print("[CrossEPG_Loader] patch crossepg v2.1 found")
			except Exception as e:
				print("[CrossEPG_Loader] patch crossepg v2.1 not found e = %s" % e)
				self.xepgpatch = None

			try:
				self.epgpatch = instancemethod(_enigma.eEPGCache_load, eEPGCache)
				print("[CrossEPG_Loader] patch epgcache.load() found")
			except Exception as e:
				print("[CrossEPG_Loader] patch epgcache.load() not found e = %s" % e)
				self.epgpatch = None

			try:
				self.edgpatch = instancemethod(_enigma.eEPGCache_reloadEpg, eEPGCache)
				print("[CrossEPG_Loader] patch EDG NEMESIS found")
			except Exception as e:
				print("[CrossEPG_Loader] patch EDG NEMESIS not found e = %s" % e)		
				self.edgpatch = None

			try:
				self.oudeispatch = instancemethod(_enigma.eEPGCache_importEvent, eEPGCache)
				print("[CrossEPG_Loader] patch Oudeis found")
			except Exception as e:
				print("[CrossEPG_Loader] patch Oudeis not found e = %s" % e)		
				self.oudeispatch = None				

		if self.xepgpatch:
			self.timer = eTimer()
			self.timer.callback.append(self.loadEPG2)
			self.timer.start(200, 1)

		elif self.epgpatch:
			self.timer = eTimer()
			self.timer.callback.append(self.loadEPG)
			self.timer.start(200, 1)

		elif self.edgpatch:
			self.timer = eTimer()
			self.timer.callback.append(self.loadEDG)
			self.timer.start(200, 1)

		elif self.oudeispatch:
			self["actions"] = NumberActionMap(["WizardActions", "InputActions"],
			{
				"back": self.quit
			}, -1)

			self.wrapper = CrossEPG_Wrapper()
			self.wrapper.addCallback(self.wrapperCallback)

			self.timeout = eTimer()
			self.timeout.callback.append(self.quit)

			self.hideprogress = eTimer()
			self.hideprogress.callback.append(self["progress"].hide)

			self.epg_channel = None
			self.epg_tuple = ()
			self.epg_starttime = 0
			self.epg_length = 0
			self.epg_name = ""

			self.wrapper.init(CrossEPG_Wrapper.CMD_CONVERTER, self.db_root)
		else:
			print("No patch found... please reboot enigma2 manually")
			self.closeAndCallback(True)

		if not noosd:
			self.onFirstExecBegin.append(self.firstExec)

	def firstExec(self):
		if self.isHD:
			self["background"].instance.setPixmapFromFile("%s/images/background_hd.png" % (os.path.dirname(sys.modules[__name__].__file__)))
		else:
			self["background"].instance.setPixmapFromFile("%s/images/background.png" % (os.path.dirname(sys.modules[__name__].__file__)))

	def loadEPG2(self):
		print("[CrossEPG_Loader] loading data with crossepg patch v2")
		if six.PY3:
			_enigma.eEPGCache_crossepgImportEPGv21(None, self.db_root)
		else:
			self.xepgpatch(eEPGCache.getInstance(), self.db_root)			
		self.closeAndCallback(True)

	def loadEPG(self):
		print("[CrossEPG_Loader] loading data with epg patch")
		if six.PY3:	
			source1 = os.path.join(self.db_root, "ext.epg.dat")
			dest1 = config.misc.epgcache_filename.value 
			dest2 = "/hdd/epg.dat"
			try:
				print("[CrossEPG_Loader:copyEPG] source = %s, dest = %s" % (source1, dest1))		
				copyfile(source1, dest1)
			except Exception as e:
				print("[CrossEPG_Loader] exception copying data1  e = %s" % e)
				print("[CrossEPG_Loader:copyEPG] source = %s, dest = %s" % (source1, dest2))			
				try:			
					copyfile(source1, dest2)
				except Exception as e:
					print("[CrossEPG_Loader] exception copying data2  e = %s" % e)
					return			
			from enigma import eEPGCache
			epgcache = eEPGCache.getInstance()
			epgcache.load()
			print("[CrossEPG_Loader:loadEPG] complete")		
			self.closeAndCallback(True)
		else:
			try:
				cmd = "%s/crossepg_epgcopy %s/ext.epg.dat %s" % (self.home_directory, self.db_root, config.misc.epgcache_filename.value)
			except Exception as e:
				print("[CrossEPG_Loader] exception loading data with epg patch e = %s" % e)			
				cmd = "%s/crossepg_epgcopy %s/ext.epg.dat /hdd/epg.dat" % (self.home_directory, self.db_root)
			print("[CrossEPG_Loader:loadEPG] %s" % (cmd))
			try:
				global container  # Need to keep a ref alive...
	
				def appClosed(retval):
					global container
					print("[CrossEPG_Loader:loadEPG] loadEPG complete, result: ", retval)
					if six.py2:
						self.epgpatch(eEPGCache.getInstance())
					self.closeAndCallback(True)
					container = None
	
				def dataAvail(data):
					print("[CrossEPG_Loader:loadEPG]", data.rstrip())
					container = eConsoleAppContainer()
					if container.execute(cmd):
						raise_(Exception, "Failed to execute: " + cmd)
					container.appClosed.append(appClosed)
					container.dataAvail.append(dataAvail)
			except Exception as e:
				print("[CrossEPG_Loader:loadEPG] loadEPG FAILED: ", e)

	def loadEDG(self):
		print("[CrossEPG_Loader:loadEDG] %s" % (cmd))
		cmd = "%s/crossepg_epgcopy %s/ext.epg.dat %s/epg.dat" % (self.home_directory, self.db_root, config.nemepg.path.value)
		try:
			global container  # Need to keep a ref alive...

			def appClosed(retval):
				global container
				print("[CrossEPG_Loader:loadEDG] loadEDG complete, result: ", retval)
				self.edgpatch(eEPGCache.getInstance())
				self.closeAndCallback(True)
				container = None

			def dataAvail(data):
				print("[CrossEPG_Loader:loadEDG]", data.rstrip())
			container = eConsoleAppContainer()
			if container.execute(cmd):
				raise_(Exception, "[CrossEPG_Loader:loadEDG] Failed to execute: " + cmd)
			container.appClosed.append(appClosed)
			container.dataAvail.append(dataAvail)
		except Exception as e:
			print("[CrossEPG_Loader:loadEDG] loadEDG FAILED: ", e)

	def wrapperCallback(self, event, param):
		if event == CrossEPG_Wrapper.EVENT_READY:
			self.wrapper.text()

		elif event == CrossEPG_Wrapper.EVENT_END:
			self.wrapper.quit()

		elif event == CrossEPG_Wrapper.EVENT_ACTION:
			self["action"].text = param

		elif event == CrossEPG_Wrapper.EVENT_STATUS:
			self["status"].text = param

		elif event == CrossEPG_Wrapper.EVENT_PROGRESS:
			self["progress"].setValue(param)
			self["progress_text"].setValue(param)

		elif event == CrossEPG_Wrapper.EVENT_CHANNEL:
			if self.epg_channel:
				if len(self.epg_tuple) > 0:
					self.oudeispatch(eEPGCache.getInstance(), self.epg_channel, self.epg_tuple)
					self.epg_tuple = ()
			self.epg_channel = param

		elif event == CrossEPG_Wrapper.EVENT_STARTTIME:
			self.epg_starttime = param

		elif event == CrossEPG_Wrapper.EVENT_LENGTH:
			self.epg_length = param

		elif event == CrossEPG_Wrapper.EVENT_NAME:
			self.epg_name = param

		elif event == CrossEPG_Wrapper.EVENT_DESCRIPTION:
			if self.epg_channel:
				self.epg_tuple += ((self.epg_starttime, self.epg_length, self.epg_name, self.epg_name, param, 0),)

		elif event == CrossEPG_Wrapper.EVENT_PROGRESSONOFF:
			if param:
				self.hideprogress.stop()
				self["progress"].setValue(0)
				self["progress"].show()
				self["progress_text"].setValue(0)
			else:
				self["progress"].setValue(100)
				self.hideprogress.start(500, 1)
				self["progress_text"].setValue(100)
		elif event == CrossEPG_Wrapper.EVENT_QUIT:
			if self.epg_channel:
				if len(self.epg_tuple) > 0:
					self.oudeispatch(eEPGCache.getInstance(), self.epg_channel, self.epg_tuple)
			self.closeAndCallback(self.retValue)

		elif event == CrossEPG_Wrapper.EVENT_ERROR:
			self.session.open(MessageBox, _("CrossEPG error: %s") % (param), type=MessageBox.TYPE_INFO, timeout=20)
			self.retValue = False
			self.quit()

	def quit(self):
		if self.wrapper:
			if self.wrapper.running():
				self.retValue = False
				self.wrapper.quit()
				return

		self.closeAndCallback(False)

	def closeAndCallback(self, ret):
		self.retValue = ret
		self.close(ret)
		self.pcallbacktimer.start(0, 1)

	def doCallback(self):
		if self.pcallback:
			self.pcallback(self.retValue)
