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
	addon_version="2.1.2",
	# Brief changelog for this version
	# Translators: what's new content for the add-on version to be shown in the add-on store
	addon_changelog=_("""- Secure Desktop Boundary Lockdown: Integrated pure Win32 Kernel Desktop Isolation (user32.OpenInputDesktop) to prevent unauthorized execution across Windows Logon, UAC (Consent UI), and lock screens.
- Security Alarm & Auditory Cues: Designed an authoritative 3-stage acoustic warning chime paired with explicit speech notifications when restricted actions are attempted.
- Keystroke Performance Optimization: Shifted desktop isolation Win32 prototypes to module-level scope, achieving sub-microsecond gesture routing.
- Storage Metrics Localization: Resolved hardcoded English terms in drive space capacity reporting (check_drives_pulse).
- Documentation & Build Enhancements: Fixed GitHub navigation links for English documentation and improved SCons build pipeline."""),
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