# PowerBox for NVDA

**Author:** Thomas A. Fayez  
**Version:** 1.2.0  

PowerBox is a powerful, lightweight multi-tool add-on for NVDA. It maps NVDA gestures to Windows keyboard/media keys, simulates smart mouse clicks with physical cursor routing, provides network info, and introduces **Gesture Layers** for quick access to Terminal environments and everyday applications.

## ✨ The Concept of "Layers"
To avoid shortcut conflicts and finger gymnastics, PowerBox uses a "Layered" approach. You press a prefix shortcut to activate a layer, then press a single letter to execute the action. 
*Pressing `H` inside any layer will open a help dialog showing available keys.*

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

**The Solution:** PowerBox's Smart Click solves this! It dynamically calculates the geometric center of the currently focused NVDA navigator object, moves the physical Windows mouse cursor directly to that position, and executes a native hardware click.

**How to use it:**
1. Navigate to the stubborn button using NVDA Object Navigation (`NVDA + Numpad 4 / 6` on Desktop, or `NVDA + Shift + Left / Right Arrows` on Laptop).
2. Press **NVDA + Win + C** to perform a smart left click.

* **NVDA + Win + C:** Smart Left Mouse Click
* **NVDA + Win + X:** Smart Right Mouse Click
* **NVDA + Win + Z:** Smart Double Mouse Click

### 📡 Network Information
* **NVDA + Win + I:** Speak Local IP *(Press twice quickly to copy to clipboard)*
* **NVDA + Win + Shift + I:** Speak Public IP *(Press twice quickly to copy to clipboard)*

### ❓ Global Help
* **NVDA + Win + H:** Shows the PowerBox Global Help window.

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

All terminals intelligently open in the **current File Explorer directory** you are focusing on! Press the prefix above, followed by:
* **P:** Open PowerShell
* **Shift + P:** Open PowerShell as Administrator
* **C:** Open Command Prompt (CMD)
* **Shift + C:** Open Command Prompt as Administrator
* **W:** Open WSL (Windows Subsystem for Linux)
* **H:** Show Layer Help

---

## ⚙️ Settings
You can configure the feedback mode (Beep, Speech, Both, or Silent) from **NVDA Menu -> Preferences -> Settings -> PowerBox**.

---

## 🙏 Credits & Acknowledgements
* **Tyler Spivey & Joseph Lee:** For the original architecture and structure of modal layer commands (`getScript` overrides), which inspired PowerBox's layer system.
* **NVDA Community & Open Source Contributors:** For inspiration and techniques regarding Windows Explorer Shell COM automation and mouse-to-navigator object routing.
* **Python Open Source Community:** For the UDP routable socket technique used for offline-safe local IP detection.
* **ipify.org:** For providing the free, public API service used to resolve external IP addresses.