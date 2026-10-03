# PowerBox Changelog

## v2.2.0 - Enterprise Server Power Guard & UEFI Integration

This major update introduces mission-critical safeguards for remote server administration, unified power confirmation workflows, and direct UEFI firmware reboot capabilities.

### 🛡️ Server Guard & Accidental Power Protection:
* **Enterprise Remote Session Detection:** PowerBox now exhaustively detects remote administration sessions across Native Windows RDP, NVDA Remote Legacy (2024.1+), and modern NVDA Remote Core (_remoteClient 2025+).
* **Smart Block for Sleep & Hibernate:** Automatically intercepts and blocks Sleep and Hibernate commands on Windows Servers and active remote sessions to prevent irreversible network disconnections and system lockouts.
* **High-Risk Warnings:** Implemented severe, context-aware warning prompts before executing Shutdown or Firmware Reboot over remote sessions.

### ⚡ Power Management & System Diagnostics:
* **UEFI Firmware Reboot:** Added a new shortcut (`Shift+R` in the System Layer) to directly reboot the computer into motherboard BIOS/UEFI settings using elevated native API calls.
* **Unified Power Confirmations:** Double-press and Modal Dialog confirmation styles now apply globally across all 5 power actions (Shutdown, Restart, Firmware, Sleep, Hibernate).
* **Speech Focus Protection:** Developed a micro-freezing UI dialog technique coupled with immediate `speech.cancelSpeech()` to completely suppress unintended background desktop announcements when confirming power actions.

### ⚙️ Settings Configuration:
* **Server Power Guard Preferences:** Added a dedicated settings dropdown to configure the remote session power guard behavior (Smart Block, Warning Dialog, or Unrestricted).