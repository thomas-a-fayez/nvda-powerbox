# PowerBox for NVDA

**Author:** Thomas A. Fayez  
**Version:** 1.4.0  

PowerBox is a powerful, lightweight multi-tool add-on designed for speed, comfort, and productivity. It maps ergonomic NVDA gestures to master and per-application volume controls, simulates smart mouse clicks with automatic cursor routing, provides terminal launches in the current folder, and introduces clean **Gesture Layers** for quick application launching, advanced network auditing with an accessible LAN device scanner, and comprehensive system power management with an intelligent sleep/shutdown timer.

## ✨ The Concept of "Layers"
To avoid shortcut conflicts, complex finger gymnastics, and awkward multi-key combinations, PowerBox utilizes a clean "Layered" architecture. You press a single prefix shortcut to activate a modal layer, followed by a single key to trigger the action. 
*Pressing `H` inside any active layer will open an accessible contextual help dialog displaying all available keys.*

**Smart Layer Entry & Error Feedback:** Entering any layer strictly respects your configured Feedback Mode:
* **Both (Beep and speak):** Plays the layer's distinct audio tone and announces the layer name immediately (e.g. *"System Layer"*, *"Terminal Layer"*).
* **Speech only:** Announces the layer name clearly without any beeps.
* **Beep only:** Plays the quick layer identification tone only.
* **None (Silent):** Completely silent operation; enters the layer silently without disturbing you.
* *Pressing an unmapped key inside any layer also respects your feedback mode (announces "Invalid key", plays a low error tone, or exits silently).*

## ⌨️ Global Shortcuts

### 🔊 Master System Audio
* **NVDA + Win + Up / Down:** Master Volume Up / Down *(Announces exact level, e.g. Volume: 50%)*
* **NVDA + Win + M:** Master Volume Mute Toggle *(Instant hardware kernel muting with audible "Muted" / "Unmuted" announcement)*

### 🎧 Active Application Audio (Per-App Mixer)
Adjust the volume of the currently focused program (such as Firefox, Zoom, Spotify, or VLC) without affecting NVDA's speech or the overall system volume!
* **NVDA + Win + Shift + Up:** Increase Focused App Volume by 5% *(Announces app name and volume, e.g. Firefox: 45%)*
* **NVDA + Win + Shift + Down:** Decrease Focused App Volume by 5% *(Announces app name and volume, e.g. Firefox: 35%)*
* **NVDA + Win + Shift + M:** Mute / Unmute Focused App Only *(Mutes the active application without silencing NVDA or other system sounds)*

### Media & Browser Playback
* **NVDA + Win + P:** Play / Pause Media
* **NVDA + Win + Left/Right:** Previous / Next Track
* **NVDA + Win + Backspace:** Browser Back
* **NVDA + Win + Enter:** Browser Forward
* **NVDA + Win + R:** Browser Refresh

### 🖱️ Smart Mouse Simulation & Context Menus
**The Problem:** Have you ever encountered an inaccessible or custom button (such as in installer wizards like Foxit Reader or custom web applications) that NVDA reads via Object Navigation, but pressing `Enter` or `Space` does absolutely nothing?

**The Solution:** PowerBox's Smart Click solves this instantly. It dynamically calculates the exact geometric center of the focused NVDA navigator object, routes the physical Windows mouse cursor directly to that position, and executes a native hardware click.

**How to use it:**
1. Navigate to the stubborn control using NVDA Object Navigation (e.g. `NVDA + Numpad 4 / 6` on Desktop, or `NVDA + Shift + Left / Right Arrows` on Laptop).
2. Press **NVDA + Win + C** to execute a smart left click on the object center.

* **NVDA + Win + C:** Smart Left Mouse Click
* **NVDA + Win + X:** Smart Right Mouse Click
* **NVDA + Win + Z:** Smart Double Mouse Click
* **NVDA + Win + A:** Applications Menu *(Modern Windows 11 context menu)*
* **NVDA + Win + Shift + A:** Classic Context Menu *(Bypasses Windows 11 restrictions to open the full legacy context menu with 7-Zip, WinRAR, etc.)*

### 📡 Quick Network Shortcuts
* **NVDA + Win + I:** Speak Local IP *(Press twice quickly to copy to clipboard)*
* **NVDA + Win + Shift + I:** Speak Public IP *(Press twice quickly to copy to clipboard)*

### ❓ Global Help
* **NVDA + Win + H:** Displays the PowerBox Global Help window listing all shortcuts and current bindings.

---

## ⚡ Smart System & Power Layer
**Prefix Shortcut:** `NVDA + Win + S`

Provides centralized, accessible, and accidental-proof power controls for Windows. Press the prefix above, followed by:
* **T:** **Set Shutdown Timer:** Opens an accessible configuration dialog to schedule automatic computer shutdown. Choose from quick presets (15m, 30m, 45m, 60m) or enter a custom duration in minutes.
* **Shift + T:** **Query Timer Status:** Speaks the exact time remaining (minutes and seconds) before scheduled shutdown.
* **C:** **Cancel Timer:** Cancels any active shutdown timer immediately.
* **D:** **Shut Down Computer:** Initiates an orderly shutdown with user-selected safety confirmation.
* **R:** **Restart Computer:** Initiates a system restart with user-selected safety confirmation.
* **S:** **Sleep Mode:** Puts the computer into low-power standby mode.
* **B:** **Hibernate:** Saves memory state to disk and powers off.
* **L:** **Lock Workstation:** Instantly locks the Windows desktop.
* **H:** Show System Layer Help.

### 🛡️ Accidental Shutdown Protection
To prevent data loss, PowerBox supports two configurable confirmation styles in Settings:
1. **Confirmation Dialog (Default & Recommended):** Pops up an accessible dialog asking for confirmation, with initial focus intentionally placed on **[No]** to prevent accidental Enter presses.
2. **Double-Press Confirmation:** Requires pressing `D` or `R` twice within 2 seconds. If you change your mind and do not press the key again, PowerBox automatically dismisses the layer and restores normal keyboard functionality after 2 seconds.

*Additionally, when a shutdown timer reaches 60 seconds remaining, PowerBox plays a distinctive dual warning chime and speaks an alert, giving you time to cancel if you are still working.*

---

## 🌐 Smart Network Layer
**Prefix Shortcut:** `NVDA + Win + N`

Unified network diagnostics and auditing tools. Press the prefix above, followed by:
* **S:** **Scan Local Network:** Launches the high-speed (2-3 seconds) non-blocking LAN scanner. Plays an audible pulse during scanning. Pressing `NVDA + Win + N` then `S` again while scanning cancels immediately.
* **L:** Speak Local IP
* **Shift + L:** Copy and speak Local IP
* **P:** Speak Public IP
* **Shift + P:** Copy and speak Public IP
* **G:** Speak Default Gateway (Router IP)
* **Shift + G:** Copy and speak Default Gateway (Router IP)
* **H:** Show Network Layer Help

### Network Scanner Dialog Features
When the scan completes, an accessible, centered dialog presents all discovered hosts:
* **Enter / Alt + I:** Copy IP Address of selected device.
* **Alt + M:** Copy MAC Address.
* **Alt + O:** **Open in Web Browser:** Concurrently probes common web ports (80, 443, 8080, 8443) in ~200ms and opens the device's web management portal (e.g. router admin or smart printer).
* **Alt + R:** Rescan the network directly from the dialog.
* **Alt + A:** Copy all details (IP, Name, Vendor, MAC) as a clean formatted line.
* **Alt + C / Escape:** Close dialog.
* *Intelligently tags **(This PC)**, **Router / Default Gateway**, and mobile devices using private randomized MACs (IEEE 802 LAA).*

### 📱 Note on Smartphones & Wi-Fi Power Saving
Modern mobile operating systems (Android and iOS) implement aggressive Wi-Fi power-saving mechanisms (Doze / DTIM sleep). When a phone's screen is idle or locked, its Wi-Fi chip sleeps between packet bursts and drops peer-to-peer ARP requests sent from your PC, causing the device to occasionally not respond during a scan. Simply waking up or unlocking the phone's screen will make it immediately discoverable.

Additionally, modern smartphones enable **Private Wi-Fi Address (MAC Randomization)** by default for privacy. PowerBox mathematically detects these addresses via IEEE 802 standards and clearly labels them as `Randomized MAC (Phone / Mobile)`.

---

## 🚀 Quick Apps Layer
**Prefix Shortcut:** `NVDA + Win + Q`

Instant application launching without searching through Start menus. Press the prefix above, followed by:
* **C:** Launch Calculator
* **M:** Launch Default Mail Application
* **B:** Launch Default Browser Homepage
* **E:** Launch File Explorer (This PC)
* **P:** Launch Default Media Player
* **H:** Show Quick Apps Help

---

## 💻 Smart Terminal Layer
**Prefix Shortcut:** `NVDA + Win + T`

All terminals open targeted directly at the <strong>current File Explorer directory (including Windows 11 Tabs)</strong> you are currently browsing! Press the prefix above, followed by:
* **P:** Open PowerShell in current folder
* **Shift + P:** Open PowerShell as Administrator in current folder
* **C:** Open Command Prompt (CMD) in current folder
* **Shift + C:** Open Command Prompt as Administrator in current folder
* **W:** Open WSL (Windows Subsystem for Linux) in current folder
* **H:** Show Terminal Layer Help

---

## ⚙️ Settings Configuration
Configure PowerBox preferences from **NVDA Menu -> Preferences -> Settings -> PowerBox**:
* **Action feedback mode:** Choose between *No feedback (Silent)*, *Beep only*, *Speak action name*, or *Beep and speak*. This setting globally controls:
  * Audio tones and spoken announcements when entering/exiting layers.
  * Keyboard actions, smart clicks, and application launching feedback.
  * Clipboard copy confirmation tones and messages.
  * Network scanner background pulses and completion chimes.
* **Shutdown and restart confirmation style:** Choose between *Confirmation dialog (Recommended)* or *Press key twice within 2 seconds*.

---

## 🙏 Credits & Acknowledgements
* **Tyler Spivey & Joseph Lee:** For the original architecture and structure of modal layer commands (`getScript` and `script_error` overrides), which inspired PowerBox's layered gesture system.
* **Héctor J. Benítez Corredera & Rui Fontes:** For the hardware scancode emulation concepts (`MapVirtualKeyW`) and context menu mouse routing derived from their `remapApplicationsKey` add-on.
* **NVDA Community & Open Source Contributors:** For inspiration and techniques regarding Windows Explorer Shell COM automation, mouse-to-navigator object routing, and dynamic gesture resolution via `inputCore`.
* **NV Access Standards:** For modal dialog lifecycle management patterns (`prePopup` and `postPopup`) and SettingsPanel integration.
* **Microsoft Windows API:** For native low-level input simulation (`SendInput`), master volume querying & direct kernel muting (`IAudioEndpointVolume`), per-application audio session mixer controls (`IAudioSessionManager2`, `ISimpleAudioVolume` via ctypes), power management (`user32.dll`: `LockWorkStation`, `powrprof.dll`: `SetSuspendState`), and network discovery APIs (`iphlpapi.dll`: `SendARP`, `GetBestRoute`, `GetIpNetTable`).
* **IEEE Standards Association:** For the IEEE 802 Locally Administered Address (LAA) specifications used in mathematical detection of randomized mobile MAC addresses.
* **Python Open Source Community:** For the UDP routable socket technique (credited to Christian Kauhaus) used for offline-safe local IP detection.
* **ipify.org & maclookup.app:** For providing open API services used to resolve public IP addresses and hardware vendor prefixes.