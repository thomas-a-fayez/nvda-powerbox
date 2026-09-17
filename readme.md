# PowerBox for NVDA

**Author:** Thomas A. Fayez  
**Version:** 1.3.0  

PowerBox is a powerful, lightweight multi-tool add-on for NVDA. It maps NVDA gestures to Windows keyboard/media keys, simulates smart mouse clicks with physical cursor routing, provides comprehensive network tools including an accessible high-speed LAN scanner, and introduces **Gesture Layers** for quick access to Terminal environments, network utilities, and everyday applications.

## ✨ The Concept of "Layers"
To avoid shortcut conflicts and finger gymnastics, PowerBox uses a "Layered" approach. You press a prefix shortcut to activate a layer, then press a single letter to execute the action. 
*Pressing `H` inside any layer will open a contextual help dialog showing available keys.*

## ⌨️ Global Shortcuts

### 🎧 Media & System
* **NVDA + Win + A:** Applications Menu
* **NVDA + Win + M:** Volume Mute
* **NVDA + Win + Up/Down:** Volume Up / Down
* **NVDA + Win + P:** Play / Pause Media
* **NVDA + Win + Left/Right:** Previous / Next Track

### 🌐 Browser Navigation
* **NVDA + Win + Backspace:** Browser Back
* **NVDA + Win + Enter:** Browser Forward
* **NVDA + Win + R:** Browser Refresh

### 🖱️ Mouse Simulation (Smart Mouse Routing)
**The Problem:** Have you ever encountered a button or control (for example, in custom installer wizards like Foxit Reader) that NVDA reads via Object Navigation, but pressing `Enter` or `Space` does absolutely nothing?

**The Solution:** PowerBox's Smart Click dynamically calculates the geometric center of the currently focused NVDA navigator object, moves the physical Windows mouse cursor directly to that position, and executes a native hardware click.

**How to use it:**
1. Navigate to the stubborn button using NVDA Object Navigation (`NVDA + Numpad 4 / 6` on Desktop, or `NVDA + Shift + Left / Right Arrows` on Laptop).
2. Press **NVDA + Win + C** to perform a smart left click.

* **NVDA + Win + C:** Smart Left Mouse Click
* **NVDA + Win + X:** Smart Right Mouse Click
* **NVDA + Win + Z:** Smart Double Mouse Click

### 📡 Quick Network Shortcuts
* **NVDA + Win + I:** Speak Local IP *(Press twice quickly to copy to clipboard)*
* **NVDA + Win + Shift + I:** Speak Public IP *(Press twice quickly to copy to clipboard)*

### ❓ Global Help
* **NVDA + Win + H:** Shows the PowerBox Global Help window.

---

## 🌐 Smart Network Layer
**Prefix Shortcut:** `NVDA + Win + N`

Access all network tools conveniently without finger gymnastics. Press the prefix above, followed by:
* **S:** **Scan Local Network:** Launches the high-speed (2-3 seconds) non-blocking LAN scanner. Plays a soft audible pulse while scanning. Pressing `NVDA + Win + N` followed by `S` again while a scan is running will cancel the operation immediately.
* **L:** Speak Local IP
* **Shift + L:** Copy and speak Local IP
* **P:** Speak Public IP
* **Shift + P:** Copy and speak Public IP
* **G:** Speak Default Gateway (Router IP)
* **Shift + G:** Copy and speak Default Gateway (Router IP)
* **H:** Show Layer Help

### Network Scanner Dialog Features
When the scan completes, an accessible dialog appears centered on screen:
* **Enter:** Copies the IP address of the selected device.
* **Alt + I:** Copy IP Address.
* **Alt + M:** Copy MAC Address.
* **Alt + O:** **Open in Web Browser:** Probes common web ports (80, 443, 8080, 8443) and opens the device's web management interface (e.g. router admin page or smart device portal).
* **Alt + R:** Rescan the network.
* **Alt + A:** Copy all details as a formatted line.
* **Alt + C / Escape:** Close the dialog.
* *Includes automatic detection for "This PC", "Router / Default Gateway", and mobile devices with randomized MACs.*

### 📱 Note on Smartphones & Wi-Fi Power Saving
Modern mobile operating systems (Android and iOS) implement aggressive Wi-Fi power-saving mechanisms (Doze / DTIM sleep). When a phone's screen is idle or locked, its Wi-Fi chip may sleep between packet bursts and drop peer-to-peer ARP requests sent from your PC, causing the device to occasionally not respond during a scan. Simply waking up or unlocking the phone's screen will make it immediately discoverable.

Additionally, modern smartphones enable **Private Wi-Fi Address (MAC Randomization)** by default for privacy. PowerBox mathematically detects these addresses via IEEE 802 standards and clearly labels them as `Randomized MAC (Phone / Mobile)`.

---

## 🚀 Quick Apps Layer
**Prefix Shortcut:** `NVDA + Win + Q`

Press the prefix above, followed by one of these keys:
* **C:** Launch Calculator
* **M:** Launch Default Mail
* **B:** Launch Browser Homepage
* **E:** Launch File Explorer (This PC)
* **P:** Launch Media Player
* **H:** Show Layer Help

---

## 💻 Smart Terminal Layer
**Prefix Shortcut:** `NVDA + Win + T`

All terminals intelligently open in the **current File Explorer directory (including Windows 11 Tabs)** you are focusing on! Press the prefix above, followed by:
* **P:** Open PowerShell
* **Shift + P:** Open PowerShell as Administrator
* **C:** Open Command Prompt (CMD)
* **Shift + C:** Open Command Prompt as Administrator
* **W:** Open WSL (Windows Subsystem for Linux)
* **H:** Show Layer Help

---

## ⚙️ Settings
You can configure the feedback mode (Beep, Speech, Both, or Silent) from **NVDA Menu -> Preferences -> Settings -> PowerBox**. All actions, clipboard confirmations, and scanner audio cues strictly respect your chosen feedback mode.

---

## 🙏 Credits & Acknowledgements
* **Tyler Spivey & Joseph Lee:** For the original architecture and structure of modal layer commands (`getScript` overrides), which inspired PowerBox's layer system.
* **NVDA Community & Open Source Contributors:** For inspiration and techniques regarding Windows Explorer Shell COM automation, mouse-to-navigator object routing, and dynamic gesture mapping.
* **Microsoft Windows API:** For native low-level input simulation (`SendInput`) and high-speed network discovery APIs (`iphlpapi.dll`: `SendARP` and `GetBestRoute`).
* **IEEE Standards Association:** For the IEEE 802 Locally Administered Address (LAA) specifications used in mathematical detection of randomized mobile MAC addresses.
* **Python Open Source Community:** For the UDP routable socket technique used for offline-safe local IP detection.
* **ipify.org & maclookup.app:** For providing open API services used to resolve public IP addresses and hardware vendor prefixes.