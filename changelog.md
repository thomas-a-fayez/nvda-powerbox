# PowerBox Changelog

## v2.0.4 - Enterprise Domain Hub & Reliability Release

This major update introduces the new **Enterprise Domain Hub**, migrates the add-on to the official NV Access build system, enforces in-process native Win32 C LDAP discovery, and brings critical socket diagnostics and accessibility refinements.

### 🌐 Major Features & Highlights:
* **Enterprise Domain Hub (`NVDA+Windows+N` then `Ctrl+S`):**
  * Complete Active Directory computer and server discovery operating seamlessly on local networks and remote VPN tunnels (OpenVPN, WireGuard, IPsec, etc.).
  * **Native In-Process C LDAP Engine (`wldap32.dll`):** Sub-50ms directory queries executed purely in memory without spawning external child processes or command-line footprints, eliminating antivirus false positives (IDP heuristics).
  * **Hardware-Bound Credential Encryption:** Saved domain credentials are protected via Windows DPAPI and locked to the physical computer's hardware fingerprint (Motherboard SMBIOS, System Disk Serial, and MachineGuid). Exported or copied profiles cannot be decrypted on any other machine.
  * **VPN Direct DNS Resolver:** Built-in direct RFC 1035 UDP DNS engine allowing client machines to query internal Domain Controllers directly, bypassing home ISP routers over VPN tunnels.
  * **Remote Administration Suite:** Single-keystroke administrative launchers for interactive Remote PowerShell (`Enter-PSSession` with automated WinRM credential passing), direct File Explorer Admin Shares (`\\IP\c$` with pre-authenticated SMB sessions), and deep Windows Admin Center (WAC) signature probing on ports 6516/443.
  * **Enterprise Export:** Export directory inventory to structured CSV or JSON audit reports.

### 🛠️ Bug Fixes & System Internals:
* **Process Network Tracker Thread Execution:** Fixed an issue where the "Test Port and Latency" button was unresponsive due to an unstarted background worker thread.
* **Smart Listening Port Probing:** Sockets testing across Server Network Hub and Process Network Tracker now intelligently probes local listening service ports (such as web, database, or RDP services) via loopback and accurately reports latency in milliseconds.
* **Strict Ctypes Isolation & Memory Safety:** Replaced all legacy `ctypes.windll` calls with private, thread-isolated `WinDLL` instances in `server_process_hub.py` (`wtsapi32`, `advapi32`, `user32`, `psapi`, `ntdll`) preventing prototype collisions with other installed NVDA add-ons.
* **Speech Focus Protection:** Resolved speech swallowing on dialog dismissal in `file_manager.py` by delaying focus notifications using `wx.CallLater`.
* **UX & Feedback Mode Compliance:** Fixed feedback mode enforcement ensuring action commands remain strictly silent in `none` mode and tone-only in `beep` mode without speech leakage.
* **Accessibility & Screen Reader Refinement:** Cleaned up button labels and accelerator mnemonics to eliminate duplicate shortcut announcements (`Alt+...`) in screen readers.

### 📦 Repository & Add-on Store:
* **Official NV Access AddonTemplate Migration:** Migrated the repository build pipeline to the official SCons and NVDATool infrastructure.
* **Native "What's new" Support:** Configured `addon_changelog` in `buildVars.py` and `manifest.ini` to display release notes natively in the NVDA Add-on Store context menu (NVDA 2026.1+).
* **Updated Translations:** Full localization catalogs updated for Arabic, Spanish, French, and Vietnamese.