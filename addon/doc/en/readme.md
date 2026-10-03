# PowerBox for NVDA

[English](addon/doc/en/readme.md) | [العربية](addon/doc/ar/readme.md)

**Author:** Thomas A. Fayez  
**Version:** 2.2.0  

PowerBox is an enterprise-grade, high-performance productivity, network analysis, and Windows Server administration add-on designed for speed, comfort, and deep operating system control. It maps ergonomic NVDA gestures to master and per-application volume controls, simulates hardware-scanned smart mouse clicks with automatic cursor routing, provides instant terminal launches in the current folder with real-time environment synchronization, and introduces clean **Modal Gesture Layers** for quick applications, advanced LAN network scanning, real-time socket and security analysis, file and storage diagnostics with locked-file inspection, native NT kernel process freezing, and comprehensive system power management with an intelligent sleep timer.

---

## ✨ The Concept of "Layers" & Dynamic Feedback

To eliminate shortcut conflicts, complex finger gymnastics, and awkward multi-key combinations, PowerBox utilizes a clean "Layered" modal architecture. You press a single prefix shortcut to activate a modal layer, followed by a single key to trigger the action. 

*Pressing `H` inside any active layer will open an accessible contextual help dialog displaying all available keys for that layer.*

### 🔊 Smart Layer Entry & Error Feedback

Entering any layer strictly respects your configured **Feedback Mode** in Settings:

* **Both (Beep and speak):** Plays the layer's distinct audio identification tone and announces the layer name immediately (e.g. *"System Layer"*, *"Files Layer"*, *"Network Layer"*).
* **Speech only:** Announces the layer name clearly without playing any tones.
* **Beep only:** Plays the quick layer identification tone only.
* **None (Silent):** Completely silent operation; enters the layer silently without disturbing you.
* *Pressing an unmapped key inside any active layer also respects your feedback mode (announces "Invalid key", plays a low error tone, or exits silently).*

---

## ⌨️ Global Shortcuts & Smart Mouse Simulation

### 🔒 Secure Desktop & Windows Logon Protection

For system security and to strictly prevent unauthorized privilege escalation, all layered navigation, terminal spawning, and administrative diagnostics are automatically restricted when running on Windows Logon screens, User Account Control (UAC) elevation prompts ("Yes/No" screens), or locked workstations (`Win + L`).

* **Permitted Functions:** **Master System Audio controls** (Mute, Volume Up, Volume Down) remain active to assist blind users with volume adjustment on secure screens.
* **Security Enforcement:** Attempting any restricted shortcut triggers an authoritative 3-stage acoustic security alarm chime accompanied by an explicit warning announcement.

### 🔊 Master System Audio

* **NVDA + Win + Up / Down:** Master Volume Up / Down *(Announces exact level, e.g. Volume: 50%)*.
* **NVDA + Win + M:** Master Volume Mute Toggle *(Instant hardware kernel muting with audible "Muted" / "Unmuted" announcement)*.

### 🎧 Active Application Audio (Per-App Mixer)

Adjust the volume of the currently focused program (such as Firefox, Zoom, Spotify, or VLC) without affecting NVDA's speech or the overall system volume!

* **NVDA + Win + Shift + Up:** Increase Focused App Volume by 5% *(Announces app name and volume, e.g. Firefox: 45%)*.
* **NVDA + Win + Shift + Down:** Decrease Focused App Volume by 5% *(Announces app name and volume, e.g. Firefox: 35%)*.
* **NVDA + Win + Shift + M:** Mute / Unmute Focused App Only *(Mutes the active application without silencing NVDA or other system sounds)*.

### ⏯️ Media & Browser Navigation

* **NVDA + Win + P:** Play / Pause Media.
* **NVDA + Win + Left / Right:** Previous / Next Track.
* **NVDA + Win + Backspace:** Browser Back.
* **NVDA + Win + Enter:** Browser Forward.
* **NVDA + Win + R:** Browser Refresh.

### 🖱️ Smart Mouse Simulation & Context Menus

**The Problem:** Have you ever encountered an inaccessible or custom button (such as in installer wizards like Foxit Reader or custom web applications) that NVDA reads via Object Navigation, but pressing `Enter` or `Space` does absolutely nothing?

**The Solution:** PowerBox's Smart Click dynamically calculates the exact geometric center of the focused NVDA navigator object, routes the physical Windows mouse cursor directly to that coordinate, and executes a native hardware click.

**How to use it:**
1. Navigate to the stubborn control using NVDA Object Navigation (e.g. `NVDA + Numpad 4 / 6` on Desktop, or `NVDA + Shift + Left / Right Arrows` on Laptop).
2. Press **NVDA + Win + C** to execute a smart left click on the object center.

* **NVDA + Win + C:** Smart Left Mouse Click.
* **NVDA + Win + X:** Smart Right Mouse Click.
* **NVDA + Win + Z:** Smart Double Mouse Click.
* **NVDA + Win + A:** Applications Menu *(Modern Windows 11 context menu)*.
* **NVDA + Win + Shift + A:** Classic Context Menu *(Bypasses Windows 11 restrictions to open the full legacy context menu with 7-Zip, WinRAR, etc.)*.

### 📡 Quick Network Shortcuts

* **NVDA + Win + I:** Speak Local IP *(Press twice quickly to copy to clipboard)*.
* **NVDA + Win + Shift + I:** Speak Public IP *(Press twice quickly to copy to clipboard)*.

### ❓ Global Help

* **NVDA + Win + H:** Displays the PowerBox Global Help window listing all shortcuts and current bindings.

---

## ⚡ Smart System & Power Layer
**Prefix Shortcut:** `NVDA + Win + S`

Provides centralized, accessible, accidental-proof power controls, real-time process resource inspection, shell reviving, and full Windows Server session administration. Press the prefix above, followed by:

* **T:** **Set Shutdown Timer:** Opens an accessible configuration dialog to schedule automatic computer shutdown. Choose from quick presets (15m, 30m, 45m, 60m) or enter a custom duration in minutes.
* **Shift + T:** **Query Timer Status:** Speaks the exact time remaining (minutes and seconds) before scheduled shutdown.
* **C:** **Cancel Timer:** Cancels any active shutdown timer immediately.
* **D:** **Shut Down Computer:** Initiates an orderly shutdown with user-selected safety confirmation.
* **R:** **Restart Computer:** Initiates a system restart with user-selected safety confirmation.
* **Shift + R:** **Reboot to UEFI Firmware (BIOS):** Restarts the computer directly into the motherboard's UEFI/BIOS settings. (Requires UEFI hardware support and Administrator privileges).
* **S:** **Sleep Mode:** Puts the computer into low-power standby mode.
* **B:** **Hibernate:** Saves memory state to disk and powers off.
* **L:** **Lock Workstation:** Instantly locks the Windows desktop.
* **P:** **Inspect Active Application:** Instantly announces live physical RAM (Working Set) and CPU usage percentage of the focused application.
* **Shift + P:** **Copy & Speak Active Application Stats:** Copies active application RAM and CPU metrics directly to the clipboard and speaks them.
* **Control + P:** **Server Process Hub & Session Manager:** Launches the enterprise management console. Displays server health status, live CPU% and RAM usage grouped by application, user drill-downs, Arabic-compliant window titles, uptime, process architecture, and full session management (Disconnect, Logoff, Kill Process, Process Suspension).
* **Control + E:** **Smart Explorer Revive / Restart:** Intelligently revives a crashed/dead Windows Explorer shell or restarts a frozen taskbar in seconds without rebooting.
* **H:** Show System Layer Help.

### 🖥️ Server Process Hub & Enterprise Session Manager

Pressing **NVDA + Win + S** followed by **Control + P** launches an accessible, high-performance administrative console built with native Windows Terminal Services APIs (`wtsapi32.dll`). It dynamically monitors user applications, multi-session resource footprints, and active Remote Desktop sessions across Windows 10/11 workstations and Windows Server (RDSH / RemoteApp) environments.

#### Console Navigation & Dialog Features:

* **Real-time Server Pulse:** Displays overall server health (Active vs. Disconnected sessions, total application count, and aggregate RAM).
* **Live Instant Filter (`Alt + F`):** Instantly filter applications as you type without losing keyboard focus. Press **Down Arrow** to jump straight into the filtered results.
* **Enter / Alt + V:** **View Users Drill-Down:** Inspect which specific users and Remote Desktop sessions are running the selected application, along with per-user RAM and session states.
* **Alt + T:** **Detailed Application Properties:** Opens a comprehensive, scrollable text viewer displaying live recalculated CPU%, binary executable path, architecture (64-bit / 32-bit), process uptime duration, and Unicode/Arabic window titles.
* **F6 / Alt + S:** **Toggle All Sessions Dashboard:** Instantly switches between the Applications Overview and the Global Server Sessions Manager. In Sessions view, administrators can monitor connected client machine names/IPs (e.g. `CLIENT-PC (10.10.x.x)`), session states, and total RAM consumed per session.
* **Backspace / Alt + B:** Return back to the Applications overview from the User Drill-down view.
* **Alt + E:** **Terminate Application / Process:** Safely terminates the application across all users or for the selected user only, with safe confirmation prompts.
* **Alt + L / Alt + D:** **Logoff or Disconnect Sessions:** Instantly disconnect or log off stale/disconnected sessions directly from the console.
* **Copy Report (`Alt + R`):** Copies a clean diagnostic summary to the clipboard.
* **F5:** Asynchronously refresh all server metrics.
* **Escape / Alt + C:** Close the console.

#### 🎛️ Context Menu Actions (`Shift + F10` or `Applications Key`):

Press `Shift + F10` on any application or user row to access advanced administrative actions:

* **Suspend Application / Process (Freeze):** Uses native Windows NT Kernel APIs (`ntdll.dll: NtSuspendProcess`) to freeze all execution threads of the application instantly, dropping its CPU consumption to 0% and saving battery/heat without closing the program or losing unsaved work.
* **Resume Application / Process:** Resumes suspended execution threads immediately (`NtResumeProcess`), allowing the program to continue running seamlessly.
* **Track Network Connections...:** Launches the dedicated enterprise **Server Network Hub** (`server_network_hub.py`) for the selected application or user, providing multi-user socket attribution and live filtering.
* **End Application / Process:** Terminate rogue tasks with safety verification.
* **Copy Details / Summary:** Quickly export selected row metadata to the clipboard.

#### 🌐 Enterprise Server Network Hub (`server_network_hub.py`):

When launched from the Server Process Hub context menu (`Shift + F10` -> `Track Network Connections...`), a specialized multi-user network console opens:

* **Live User Filter Dropdown (`Alt + U`):** In multi-user server environments, administrators can view all network sockets across the entire server (`All Users`), or switch the dropdown to any specific domain user (e.g. `AD\thomas`) to isolate and audit that employee's network activity in real time.
* **User & Session Attribution Column:** Every socket connection displays the exact domain account and session ID owning the stream (e.g. `AD\thomas (S:38)`). On standalone single-user workstations, this column and the filter dropdown hide automatically for clean simplicity.
* **Three Dedicated Traffic Tabs:**
  * **🌐 Internet Connections Tab:** Shows real external cloud and web servers.
  * **🏠 Local Network (LAN) Tab:** Tracks traffic to local routers, printers, and internal domain servers (`192.168.x.x`, `10.x.x.x`).
  * **💻 Localhost / Listeners Tab:** Inspects internal IPC sockets (`127.0.0.1`) and local listening developer ports (`0.0.0.0:8000`, `3000`).
* **Interactive Enterprise Controls:**
  * **Alt + T:** **Port & Latency Benchmark:** Pressing `Alt + T` (or `Space` / `Enter`) speaks the connection state and ping latency in milliseconds. **Holding Shift while pressing (e.g. `Shift + Space` or `Shift + Enter`) copies the benchmark result to the clipboard and speaks it in one clean action.**
  * **Alt + D:** **Sever Connection (`SetTcpEntry`):** Instantly terminates an individual rogue TCP socket without closing the application or affecting other users.
  * **Alt + I:** Clear inactive/closed sockets history.
  * **Alt + V:** Check IP security reputation on VirusTotal.
  * **Alt + O:** Open remote server address in default browser.
  * **Alt + E:** Emergency kill switch across all application PIDs.

#### 💡 Design Philosophy: Smart Noise Filtering & Enterprise Scope

Unlike the standard Windows Task Manager—which overwhelms screen reader users with over 150 non-interactive operating system daemons, driver containers, and background services (such as `svchost.exe` and driver hooks)—PowerBox intentionally adopts a **Noise-Free, Application-Centric Philosophy**:

* **Smart Heuristic Filtering:** The console automatically filters out Windows 11 internal component tasks (e.g. `SystemApps`), driver service containers, and non-interactive `SYSTEM` daemons. This delivers a clean, high-signal view dedicated exclusively to **real, user-facing applications** and heavy background runtimes (e.g. multi-process browsers, Edge WebView2 instances, and developer IDEs).
* **Role-Based Security & Permissions Boundaries:**
  * **When Run as Administrator:** Unlocks full administrative capabilities across the entire server—allowing administrators to monitor all domain users (`DOMAIN\User`), aggregate multi-user instances (e.g., combining 100+ Edge processes across sessions), identify disconnected session memory leaks, and terminate processes or log off remote users.
  * **When Run as Standard User:** Gracefully respects Windows OS security boundaries without errors. Users have full control over their own applications and local session, while cross-session modifications for other colleagues are safely restricted.
* **User Accounts & Connected Client Resolution:** Accounts are displayed using standard Windows security naming conventions (`DOMAIN\User` in Active Directory environments or `COMPUTER\User` on standalone workstations). The Sessions view (`F6`) explicitly resolves the physical remote client computer name and IP address (e.g. `MACHINE-NAME (192.168.x.x)`), providing invaluable network transparency.
* **Window Titles Behavior (Local vs. RemoteApp Isolation):** Interactive window and tab titles (including full Arabic Unicode text) are captured when querying applications within the caller's active session. In multi-user remote environments (RDS / RemoteApp), Windows kernel security boundaries intentionally enforce desktop isolation between sessions to prevent cross-session window snooping.
* **Safety by Design (Screen Reader Protection):** Critical core Windows architecture and NVDA's own internal processes (such as `nvda.exe` and `nvda_synthDriverHost.exe`) are deliberately protected and excluded from termination actions to prevent accidental loss of speech synthesis or system lockouts.

### 🛡️ Server Guard & Accidental Power Protection
To prevent catastrophic data loss and remote disconnections, PowerBox enforces an enterprise-grade **4-Tier Server Guard** alongside unified power confirmations.

**1. Enterprise Server & Remote Session Guard:**
If PowerBox detects that the operating system is Windows Server, or if you are connected via a remote session (Native Windows RDP or **NVDA Remote** across all versions), it automatically intervenes to protect your session:
* **Smart Block (Default):** Instantly blocks the **Sleep** and **Hibernate** commands. It emits a security tone and speaks a clear warning that these actions are disabled to prevent irreversible remote connection loss.
* **High-Risk Warning:** For **Shutdown** or **Firmware Reboot** on remote sessions, it forces a severe warning dialog notifying you that executing the command will permanently terminate the remote connection and may require physical intervention.

**2. Unified Power Confirmations:**
All power actions (Shutdown, Restart, Firmware Reboot, Sleep, Hibernate) strictly follow your configured confirmation style in Settings:
* **Confirmation Dialog (Default & Recommended):** Pops up an accessible dialog asking for confirmation, with initial focus intentionally placed on **[No]** to prevent accidental `Enter` presses.
* **Double-Press Confirmation:** Requires pressing the action key (e.g., `D` or `S`) twice within 2 seconds. If you change your mind and do not press the key again, PowerBox safely dismisses the layer.

*Additionally, when a shutdown timer reaches 60 seconds remaining, PowerBox plays a distinctive dual warning chime and speaks an alert, giving you time to cancel if you are still working.*

---

## 📁 Smart Files & Storage Layer
**Prefix Shortcut:** `NVDA + Win + F`

Comprehensive file diagnostics, real-time storage pulse, checksum verification, and locked-file management. Press the prefix above, followed by:

* **S:** **Calculate Item Size:** Context-aware size calculator:
  * **Focused File:** Instantly announces physical file size.
  * **Focused Folder:** Recursively calculates true folder size, file count, and subdirectory count in the background with an audible progress ticker. Pressing `S` again cancels instantly.
  * **Selected Drive or Empty Background:** Instantly announces the active drive's full partition metrics (Free space, percentage free, Used space, and Total capacity).
* **Shift + S:** **Copy Item Size:** Copies the formatted size metrics to the clipboard and speaks them.
* **D:** **Drives Space Pulse:** Announces total capacity, used space, free space, and percentage free across **all** local and external drives (C:, D:, E:), with low space alerts (< 15%).
* **Shift + D:** **Copy Drives Report:** Copies the full multi-drive storage report to the clipboard and speaks it.
* **L:** **File Lock Inspector (Who Locks This File?):** Uses native Windows Restart Manager API (`rstrtmgr.dll`) to detect applications or services holding the selected file/folder. If locked, opens an accessible dialog to terminate locking processes.
* **Shift + L:** **Copy Lock Details:** Copies locking application names and PIDs directly to the clipboard.
* **C:** **File Checksum & Matcher:** Computes the cryptographic hash (SHA-256, MD5, or SHA-1 based on settings) of the selected file. **Intelligently compares against clipboard:** if a candidate hash was previously copied, announces an instant `HASH MATCH!` or `HASH MISMATCH!` verification.
* **Shift + C:** **Copy Checksum:** Copies the computed file hash directly to the clipboard.
* **N:** **Instant New File (Touch):** Prompts with an accessible dialog displaying the destination folder path to instantly create an empty file (e.g. `notes.txt`, `script.py`) in 0.01 seconds without slow context menus.
* **P:** **Copy Windows Path:** Copies the full path of the selected item or current folder. Automatically resolves Desktop `.lnk` shortcuts to their true target executable or folder!
* **Shift + P:** **Copy WSL Linux Path:** Converts and copies the selected path into WSL Linux format (e.g. `/mnt/c/Projects/app.py`).
* **H:** Show Files Layer Help.

---

## 🌐 Smart Network Layer
**Prefix Shortcut:** `NVDA + Win + N`

Unified network diagnostics, auditing, and live socket tracking tools. Press the prefix above, followed by:

* **S:** **Scan Local Network:** Launches the high-speed (2-3 seconds) non-blocking LAN scanner. Plays an audible pulse during scanning. Pressing `NVDA + Win + N` then `S` again while scanning cancels immediately.
* **C:** **Track Active App Network Connections:** Opens the real-time, 3-tier process socket and security tracker for the currently focused application.
* **L:** Speak Local IP.
* **Shift + L:** Copy and speak Local IP.
* **P:** Speak Public IP.
* **Shift + P:** Copy and speak Public IP.
* **G:** Speak Default Gateway (Router IP).
* **Shift + G:** Copy and speak Default Gateway (Router IP).
* **H:** Show Network Layer Help.

### 🌐 Real-Time Process Network Tracker Console (`process_network_tracker.py`)

Pressing **NVDA + Win + N** followed by **C** launches a high-speed, live socket and security analyzer for the active application. Built on native IP Helper APIs (`GetExtendedTcpTable`, `GetExtendedUdpTable`), it segregates traffic into three dedicated, non-disruptive tabs without focus-stealing:

* **🌐 Internet Connections Tab:** Shows real external web/cloud servers (Google, WhatsApp, CDNs, Fastly).
* **🏠 Local Network (LAN) Tab:** Tracks connections to routers, local printers, or domain servers (`192.168.x.x`, `10.x.x.x`).
* **💻 Localhost / Listeners Tab:** Inspects internal IPC sockets (`127.0.0.1`) and local listening dev ports (`0.0.0.0:8000`, `3000`) cleanly isolated from internet traffic.

#### Features & Superpowers:

* **Non-Disruptive Live Refresh:** Updates in-place every 2.5 seconds without resetting focus, clearing the list, or cutting off NVDA speech.
* **Retain Closed Connections (`Closed`):** Fleeting connections remain visible in the history so you never miss momentary background pings. Press **Alt + I** (`Clear Inactive`) to wipe history and start fresh.
* **Alt + T:** **Ultra-Fast Port & Latency Probe (0.2s):** Tests connection latency in milliseconds directly without opening any modal popups. 
  * **Pressing normally (`Space`, `Enter`, or `Alt + T`):** Speaks the connection state and ping latency.
  * **Holding Shift while pressing (`Shift + Space`, `Shift + Enter`):** Copies the benchmark result to clipboard and speaks it in one clean action.
* **Alt + D:** **Drop / Sever Connection:** Terminates a single active TCP socket instantly using native `SetTcpEntry(MIB_TCP_STATE_DELETE_TCB)` without closing the application.
* **Alt + V:** **Check Threat on VirusTotal:** Opens real-time security reputation reports for public remote IPs.
* **Alt + O:** **Open in Browser:** Opens web server addresses directly in default web browser.
* **Alt + E:** **Emergency End App:** Emergency kill switch terminating the application across all its PIDs if rogue or malicious behavior is detected.
* **Context Menu (`Shift + F10`):** Offers direct, accessible actions including separate items for `Test Port and Latency` and `Test Port and Copy Result`.

### 📡 Network Scanner Dialog Features

When the scan completes, an accessible, centered dialog presents all discovered hosts:

* **Enter / Alt + I:** Copy IP Address of selected device.
* **Alt + M:** Copy MAC Address.
* **Alt + O:** **Open in Web Browser:** Concurrently probes common web ports (80, 443, 8080, 8443) in ~200ms and opens the device's web management portal (e.g. router admin or smart printer).
* **Alt + R:** Rescan the network directly from the dialog.
* **Alt + A:** Copy all details (IP, Name, Vendor, MAC) as a clean formatted line.
* **Alt + C / Escape:** Close dialog.
* *Intelligently tags **(This PC)**, **Router / Default Gateway**, and mobile devices using private randomized MACs (IEEE 802 LAA).*

#### 📱 Note on Smartphones & Wi-Fi Power Saving

Modern mobile operating systems (Android and iOS) implement aggressive Wi-Fi power-saving mechanisms (Doze / DTIM sleep). When a phone's screen is idle or locked, its Wi-Fi chip sleeps between packet bursts and drops peer-to-peer ARP requests sent from your PC, causing the device to occasionally not respond during a scan. Simply waking up or unlocking the phone's screen will make it immediately discoverable.

Additionally, modern smartphones enable **Private Wi-Fi Address (MAC Randomization)** by default for privacy. PowerBox mathematically detects these addresses via IEEE 802 standards and clearly labels them as `Randomized MAC (Phone / Mobile)`.

---

## 🚀 Quick Apps Layer
**Prefix Shortcut:** `NVDA + Win + Q`

Instant application launching without searching through Start menus. Press the prefix above, followed by:

* **C:** Launch Calculator.
* **M:** Launch Default Mail Application.
* **B:** Launch Default Browser Homepage.
* **E:** Launch File Explorer (This PC).
* **P:** Launch Default Media Player.
* **H:** Show Quick Apps Help.

---

## 💻 Smart Terminal Layer
**Prefix Shortcut:** `NVDA + Win + T`

All terminals open targeted directly at the <strong>current File Explorer directory (including Windows 11 Tabs)</strong> you are currently browsing!

* **⚡ Real-Time PATH Environment Synchronization:** Terminals launched via PowerBox dynamically query the latest System and User `PATH` environment variables directly from the Windows Registry (HKLM & HKCU). Newly installed developer tools, Python scripts, or command-line utilities (such as Git, Gettext, Node) are instantly recognized in opened terminals without needing to restart NVDA!

Press the prefix above, followed by:

* **P:** Open PowerShell in current folder.
* **Shift + P:** Open PowerShell as Administrator in current folder.
* **C:** Open Command Prompt (CMD) in current folder.
* **Shift + C:** Open Command Prompt as Administrator in current folder.
* **W:** Open WSL (Windows Subsystem for Linux) in current folder.
* **H:** Show Terminal Layer Help.

---

## ⚙️ Settings Configuration

Configure PowerBox preferences from **NVDA Menu -> Preferences -> Settings -> PowerBox**:

* **Action feedback mode:** Choose between *No feedback (Silent)*, *Beep only*, *Speak action name*, or *Beep and speak*. Controls tones, layer entry announcements, action names, and completion chimes. *(Data queries like drive space, folder size, hash, and CPU metrics always speak their essential values cleanly)*.
* **Power actions confirmation style:** Applies to Shutdown, Restart, Firmware, Sleep, and Hibernate. Choose between *Confirmation dialog (Recommended)* or *Press key twice within 2 seconds*.
* **Server and remote sessions power guard:** Choose how to protect RDP and NVDA Remote sessions from accidental disconnection: *Smart Block (Recommended)*, *Always Show High-Risk Warning Dialog*, or *Unrestricted*.
* **Files and folders size format:** Choose between *Smart Adaptive (Recommended)*, *Always Megabytes (MB)*, or *Always Gigabytes (GB)*.
* **Drives storage space format:** Choose between *Smart Adaptive (Recommended)*, *Always Gigabytes (GB)*, or *Always Terabytes (TB)*.
* **Default file checksum algorithm:** Choose your preferred default hashing digest between *SHA-256 (Standard & Secure)*, *MD5 (Fast)*, or *SHA-1*.

---

## 🙏 Credits & Acknowledgements

* **Tyler Spivey & Joseph Lee:** For the original architecture and structure of modal layer commands (`getScript` and `script_error` overrides), which inspired PowerBox's layered gesture system.
* **Héctor J. Benítez Corredera & Rui Fontes:** For the hardware scancode emulation concepts (`MapVirtualKeyW`) and context menu mouse routing derived from their `remapApplicationsKey` add-on.
* **NVDA Community & Open Source Contributors:** For inspiration and techniques regarding Windows Explorer Shell COM automation, Windows 11 active tab resolution without C++ assertions, mouse-to-navigator object routing, and dynamic gesture mapping.
* **NV Access Standards:** For modal dialog lifecycle management patterns (`prePopup` and `postPopup`) and SettingsPanel integration.
* **Microsoft Windows API & Terminal Services:**
  * **Audio & Input:** Native low-level input simulation (`SendInput`), master volume querying & direct kernel muting (`IAudioEndpointVolume`), and per-application audio session mixer controls (`IAudioSessionManager2`, `ISimpleAudioVolume` via ctypes).
  * **System Power & Shell:** Power management (`user32.dll`: `LockWorkStation`, `powrprof.dll`: `SetSuspendState`), shell change notification (`shell32.dll`: `SHChangeNotify`) with Explorer Shell COM item selection (`SelectItem`) for instant focus on created files, and intelligent Explorer shell restart and revival via process monitoring and subprocess creation.
  * **Secure Desktop & Boundary Isolation:** Native Win32 Desktop Isolation APIs (`user32.dll`: `OpenInputDesktop`, `GetUserObjectInformationW`, `CloseDesktop`) enforcing strict zero-trust privilege separation across Windows Logon, UAC elevation (Consent UI), and lock screens, coupled with automated method-level runtime wrapping against custom gesture remappings, and deliberate multi-frequency acoustic alert synthesis.
  * **Process Inspection, Freezing & Memory:** Native performance counters (`time.perf_counter`), process time delta calculations (`GetProcessTimes`), working set memory metrics (`kernel32.dll`: `K32GetProcessMemoryInfo`, `psapi.dll`: `GetProcessMemoryInfo` via isolated WinDLL instances), image path querying (`QueryFullProcessImageNameW`), architecture detection (`IsWow64Process`), Unicode window enumeration (`EnumWindows`, `GetWindowTextW`), and native NT kernel process freezing/resuming (`ntdll.dll`: `NtSuspendProcess`, `NtResumeProcess`).
  * **File Diagnostics & Restart Manager:** Microsoft Restart Manager API (`rstrtmgr.dll`: `RmStartSession`, `RmRegisterResources`, `RmGetList`, `RmEndSession`) for active file lock detection, and `WScript.Shell` COM automation for resolving shortcut (`.lnk`) targets.
  * **Storage & Drives:** Physical partition storage metrics via Win32 `GetDiskFreeSpaceExW` and `GetLogicalDriveStringsW`.
  * **Network Discovery & Sockets:** Low-level ARP discovery (`iphlpapi.dll`: `SendARP`, `GetBestRoute`, `GetIpNetTable`), extended IPv4 TCP/UDP table enumeration (`GetExtendedTcpTable`, `GetExtendedUdpTable`), and individual TCP connection dropping (`SetTcpEntry`).
  * **Enterprise Remote Desktop & Sessions:** Microsoft Windows Terminal Services API (`wtsapi32.dll`: `WTSEnumerateSessionsW`, `WTSEnumerateProcessesW`, `WTSQuerySessionInformationW`, `WTSDisconnectSession`, `WTSLogoffSession`) and Security Account Manager API (`advapi32.dll`: `LookupAccountSidW`) for multi-session process aggregation and client IP resolution.
  * **Smart Path & Environment Synchronization:** Real-time environment synchronization reading fresh System and User `PATH` variables from Windows Registry (`winreg`, `kernel32.dll`: `SetEnvironmentVariableW`).
* **IEEE Standards Association:** For the IEEE 802 Locally Administered Address (LAA) specifications used in mathematical detection of randomized mobile MAC addresses.
* **Python Open Source Community:** For the UDP routable socket technique (credited to Christian Kauhaus) used for offline-safe local IP detection.
* **ipify.org & maclookup.app:** For providing open API services used to resolve public IP addresses and hardware vendor prefixes.
* **Translators:**
  * **[nguyenninhhoang](https://github.com/ninhhoang205/):** Vietnamese translation and localization improvements.