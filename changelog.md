# PowerBox Changelog

## v2.1.4 - Real-Time PATH Sync, Desktop Isolation & Documentation Overhaul

This release introduces real-time terminal environment synchronization, pure Win32 desktop isolation safeguards, authoritative acoustic security alarms, and enhanced multilingual documentation styling.

### ⚡ Terminal & System Diagnostics:
* **Real-Time PATH Synchronization:** Terminals launched via PowerBox dynamically query the latest System and User `PATH` environment variables directly from Windows Registry (`HKLM` & `HKCU`), instantly recognizing newly installed developer tools without restarting NVDA.
* **Pure Win32 Desktop Isolation:** Integrated native Windows kernel desktop queries via `user32.OpenInputDesktop` and `GetUserObjectInformationW` to enforce zero-trust privilege separation across Windows Logon, UAC prompts (Consent UI), and lock screens (`Win + L`).
* **Acoustic Security Alarm:** Designed an authoritative 3-stage audio warning chime (650Hz -> 850Hz -> 280Hz) paired with explicit speech alerts when restricted actions are attempted on secure screens.

### 📖 Documentation & Styling:
* **RTL & Dark Mode Documentation:** Rebuilt documentation styles with automatic Right-to-Left (RTL) Arabic typography, dark mode support, and clean semantic heading navigation for NVDA.
* **Synchronized Localization:** Updated translation catalogs across Arabic, Vietnamese, Spanish, and French.