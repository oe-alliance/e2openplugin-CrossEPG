# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import

import os
import gettext

from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE


PluginLanguageDomain = "CrossEPG"
PluginLanguagePath = "SystemPlugins/CrossEPG/po"


def localeInit():
	gettext.bindtextdomain(PluginLanguageDomain, resolveFilename(SCOPE_PLUGINS, PluginLanguagePath))


def _(txt):
	if gettext.dgettext(PluginLanguageDomain, txt):
		return gettext.dgettext(PluginLanguageDomain, txt)
	else:
		print("[" + PluginLanguageDomain + "] fallback to default translation for " + txt)
		return gettext.gettext(txt)


language.addCallback(localeInit())
