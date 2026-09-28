# PowerBox Changelog

## v2.1.1 - Localization & Storage Translation Fix

This maintenance release addresses an internationalization (i18n) issue in storage capacity metrics and synchronizes translation catalogs.

### 🌐 What's New in v2.1.1:
* **Drive Space Translation Fix:** Resolved an issue in `file_manager.py` (`check_drives_pulse`) where storage metrics terms ("free", "used", "Total") were hardcoded in English instead of utilizing localized formatting strings.
* **Offline Documentation Navigation:** Refined relative documentation links to guarantee seamless offline HTML browsing across all languages without broken references.
* **Updated Translations:** Synchronized localization catalogs (`nvda.po`) across Vietnamese, Arabic, Spanish, and French.
* **Core Stability:** Retained all v2.1.0 official AddonTemplate build infrastructure and network socket diagnostics improvements.