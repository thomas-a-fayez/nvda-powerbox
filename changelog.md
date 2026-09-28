# PowerBox Changelog

## v2.1.2 - Secure Desktop Isolation, Kernel Hardening & Performance Optimization

This update introduces kernel-level desktop isolation safeguards, authoritative acoustic security alarms, keystroke latency optimization, and localized storage diagnostics.

### 🛡️ Security & Kernel Hardening:
* **Pure Win32 Desktop Isolation:** Integrated native Windows kernel desktop queries via `user32.OpenInputDesktop` and `GetUserObjectInformationW` to enforce strict zero-trust boundary protection across Windows Logon, UAC elevation prompts (Consent UI), and lock screens (`Win+L`).
* **Authoritative Security Alarm:** Implemented a deliberate 3-stage acoustic warning chime (650Hz -> 850Hz -> 280Hz) paired with explicit speech notifications when restricted actions are attempted on secure screens.
* **Sub-Microsecond Keystroke Latency:** Optimized Win32 function bindings and isolated DLL instances to module-level scope, eliminating per-keystroke prototype resolution overhead.

### 🌐 Bug Fixes & Localization:
* **Drive Space Translation Fix:** Resolved an internationalization bug in `file_manager.py` (`check_drives_pulse`) where storage metrics terms ("free", "used", "Total") were hardcoded in English.
* **Documentation Navigation:** Refined English markdown navigation links on GitHub to eliminate 404 errors while maintaining seamless offline HTML help generation.
* **Updated Translations:** Synchronized translation catalogs across Arabic, Vietnamese, Spanish, and French.