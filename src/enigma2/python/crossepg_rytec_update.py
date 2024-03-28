from __future__ import print_function
from __future__ import absolute_import
import six

import random
import re
import os
import xml.etree.cElementTree
import gzip
if six.PY2:
	import httplib
	from urllib2 import urlopen, HTTPError, URLError
	from StringIO import StringIO
else:
	import http.client as httplib
	from urllib.request import urlopen, Request # raises ImportError in Python 2
	from urllib.error import HTTPError, URLError # raises ImportError in Python 2
	from io import BytesIO

from enigma import getDesktop, eTimer
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.Sources.Progress import Progress
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN


from . crossepglib import *
from . crossepg_locale import _


class CrossEPG_Rytec_Source(object):
	def __init__(self):
		self.channels_urls = []
		self.epg_urls = []
		self.description = ""


class CrossEPG_Rytec_Update(Screen):
	def __init__(self, session):
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

		self.onChangedEntry = []
		self.sources = []
		self.session = session
		self.mirrors = []

		self["background"] = Pixmap()
		self["action"] = Label(_("Updating rytec providers..."))
		self["summary_action"] = StaticText(_("Updating rytec providers..."))
		self["status"] = Label("")
		self["progress"] = ProgressBar()
		self["progress"].hide()
		self["progress_text"] = Progress()

		self.config = CrossEPG_Config()
		self.config.load()

		self.timer = eTimer()
		self.timer.callback.append(self.start)

		self.onFirstExecBegin.append(self.firstExec)

	def firstExec(self):
		if self.isHD:
			png = resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/crossepg/background_hd.png")
			if png == None or not os.path.exists(png):
				png = "%s/images/background_hd.png" % os.path.dirname(sys.modules[__name__].__file__)
		else:
			png = resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/crossepg/background.png")
			if png == None or not os.path.exists(png):
				png = "%s/images/background.png" % os.path.dirname(sys.modules[__name__].__file__)
		self["background"].instance.setPixmapFromFile(png)
		self.timer.start(100, 1)

	def start(self):
		self.loadSourceList()
		if self.load():
			self.save(self.config.home_directory + "/providers/")
			self.session.open(MessageBox, _("%d providers updated") % len(self.sources), type=MessageBox.TYPE_INFO, timeout=5)
		else:
			self.session.open(MessageBox, _("Cannot retrieve rytec sources"), type=MessageBox.TYPE_ERROR, timeout=10)
		self.close()

	def loadSourceList(self):
		try:
#			url = "http://rytecepg.dyndns.tv/epg_data/crossepgsources.gz"			# currently not available
#			distro = getImageDistro()
#			if distro in ("openvix", "openbh"):
			url = "http://www.openvix.co.uk/crossepgsources.gz"				# so use OpenViX url as holder
			print("[crossepg_rytec_update:loadSourceList] downloading source list from %s" % url)
			response = urlopen(url)
			content_raw = response.read()
			CType = response.info().getheader('Content-Type') if six.PY2 else response.getheader("Content-Type")
			if 'gzip' in CType:
				if six.PY2:
					self.mirrors = [x.strip() for x in gzip.GzipFile(fileobj=StringIO(content_raw)).read().strip().split("\n")]
				else:
					self.mirrors = gzip.GzipFile(fileobj=BytesIO(content_raw), mode='rb').read()
					self.mirrors = six.ensure_str(self.mirrors).strip().split("\n")
				random.shuffle(self.mirrors)
				print("[crossepg_rytec_update:loadSourceList] mirrors2 %s" % self.mirrors)
			else:
				print("[crossepg_rytec_update:loadSourceList] Fetched data is not Gzip format")
				print("[crossepg_rytec_update:loadSourceList] content_raw:", content_raw)
		except Exception as e:
			print("[crossepg_rytec_update:loadSourceList] error fetching:", e)

	def load(self):
		ret = False
		for mirror in self.mirrors:
			mirror = mirror.replace('\t', '')
			try:
				print("[crossepg_rytec_update:load] downloading from %s" % (mirror))
				smirror = mirror.lstrip("http://")
				host = smirror.split("/")[0]
				path = smirror.lstrip(host)
				conn = httplib.HTTPConnection(host)
				conn.request("GET", path)
				httpres = conn.getresponse()
				print("[crossepg_rytec_update:load] host =%s, path=%s, httpres=%s" % (host, path, httpres))
				if httpres.status == 200:
					f = open("/tmp/crossepg_rytec_tmp", "w")
					databytes = httpres.read()
					datastr = six.ensure_str(databytes)
					f.write(datastr)
					f.close()
					self.loadFromFile("/tmp/crossepg_rytec_tmp")
					os.unlink("/tmp/crossepg_rytec_tmp")
					ret = True
				else:
					print("[crossepg_rytec_update:load] http error: %d (%s)" % (httpres.status, mirror))
			except Exception as e:
				print("[crossepg_rytec_update:load] exception =%s" % e)
		return ret

	def getServer(self, description):
		for source in self.sources:
			if source.description == description:
				return source
		return None

	def loadFromFile(self, filename):
		mdom = xml.etree.cElementTree.parse(filename)
		root = mdom.getroot()

		for node in root:
			if node.tag == "source":
				source = CrossEPG_Rytec_Source()
				source.channels_urls.append(node.get("channels"))
				for childnode in node:
					if childnode.tag == "description":
						source.description = childnode.text
					elif childnode.tag == "url":
						source.epg_urls.append(childnode.text)

				oldsource = self.getServer(source.description)
				if oldsource == None:
					self.sources.append(source)
				else:
					if len(source.epg_urls) > 0:
						if source.epg_urls[0] not in oldsource.epg_urls:
							oldsource.epg_urls.append(source.epg_urls[0])
					if len(source.channels_urls) > 0:
						if source.channels_urls[0] not in oldsource.channels_urls:
							oldsource.channels_urls.append(source.channels_urls[0])

	def save(self, destination):
		os.system("rm -f " + destination + "/rytec_*.conf")
		for source in self.sources:
			p = re.compile('[/:()<>|?*\s-]|(\\\)')
			filename = p.sub('_', source.description).lower()
			if filename[:6] != "rytec_":
				filename = "rytec_" + filename
			f = open(destination + "/" + filename + ".conf", "w")
			f.write("description=" + source.description + "\n")
			f.write("protocol=xmltv\n")
			count = 0
			for url in source.channels_urls:
				f.write("channels_url_" + str(count) + "=" + url + "\n")
				count += 1

			count = 0
			for url in source.epg_urls:
				f.write("epg_url_" + str(count) + "=" + url + "\n")
				count += 1
			f.write("preferred_language=eng")
			f.close()
