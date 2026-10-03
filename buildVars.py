# -*- coding: UTF-8 -*-
# Build customizations for PowerBox
# Change this file instead of sconstruct or manifest files, whenever possible.

from site_scons.site_tools.NVDATool.typings import AddonInfo, BrailleTables, SymbolDictionaries
from site_scons.site_tools.NVDATool.utils import _

# Add-on information variables
addon_info = AddonInfo(
	# add-on Name/identifier, internal for NVDA
	addon_name="powerbox",
	# Add-on summary/title, usually the user visible name of the add-on
	# Translators: Summary/title for this add-on to be shown on installation and in add-on store
	addon_summary=_("PowerBox: Essential Windows Productivity Tools"),
	# Add-on description
	# Translators: Long description to be shown for this add-on in add-on store
	addon_description=_("""Enterprise-grade Windows productivity, system diagnostics, and server administration toolkit.
Features clean multi-layered navigation (Quick Apps, Terminals, Network, System & Power, Files & Storage),
real-time process and socket tracking, and comprehensive accessibility controls."""),
	# version
	addon_version="2.2.0",
	# Brief changelog for this version
	# Translators: what's new content for the add-on version to be shown in the add-on store
	addon_changelog=_("""- Enterprise Server Guard: Protects Windows Servers and remote sessions (RDP, NVDA Remote) from accidental Sleep/Hibernate lockouts.
- Unified Power Confirmations: Dialog and double-press confirmations now apply to all power actions (Shutdown, Restart, Firmware, Sleep, Hibernate).
- UEFI Firmware Reboot: Added new shortcut (Shift+R) to directly restart into BIOS/UEFI settings.
- Speech Focus Protection: Suppressed unintended background window announcements when confirming power dialogs.
- Settings Integration: New configurable preferences for the server power guard and unified confirmation styles."""),
	# Author(s)
	addon_author="Thomas A. Fayez <thomas.a.fayez@gmail.com>",
	# URL for the add-on documentation support
	addon_url="https://github.com/thomas-a-fayez/nvda-powerbox",
	# URL for the add-on repository where the source code can be found
	addon_sourceURL="https://github.com/thomas-a-fayez/nvda-powerbox",
	# Documentation file name
	addon_docFileName="readme.html",
	# Minimum NVDA version supported
	addon_minimumNVDAVersion="2024.1",
	# Last NVDA version supported/tested
	addon_lastTestedNVDAVersion="2026.2",
	# Add-on update channel (default is None, denoting stable releases)
	addon_updateChannel=None,
	# Add-on license such as GPL 2
	addon_license="GPL v2",
	# URL for the license document the add-on is licensed under
	addon_licenseURL="https://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
)

# Define the python files that are the sources of your add-on.
pythonSources: list[str] = [
	"addon/globalPlugins/powerbox/*.py",
	"addon/globalPlugins/powerbox/domain_hub/*.py",
]

# Files that contain strings for translation.
i18nSources: list[str] = pythonSources + ["buildVars.py"]

# Files that will be ignored when building the nvda-addon file
excludedFiles: list[str] = []

# Base language for the NVDA add-on
baseLanguage: str = "en"

# Markdown extensions for add-on documentation
markdownExtensions: list[str] = [
	"markdown.extensions.tables",
	"markdown.extensions.fenced_code",
]

# Custom braille translation tables
brailleTables: BrailleTables = {}

# Custom speech symbol dictionaries
symbolDictionaries: SymbolDictionaries = {}