# PowerBox for NVDA

**Author:** Thomas A. Fayez  
**Version:** 1.0.0  

PowerBox is a powerful, lightweight multi-tool add-on for NVDA. It maps NVDA gestures to Windows keyboard/media keys, simulates smart mouse clicks, provides network info, and introduces **Gesture Layers** for quick access to Terminal environments and everyday applications.

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

### 🖱️ Mouse Simulation
* **NVDA + Win + C:** Left Mouse Click
* **NVDA + Win + X:** Right Mouse Click
* **NVDA + Win + Z:** Double Mouse Click

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
* **E:** Launch This PC / Explorer
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