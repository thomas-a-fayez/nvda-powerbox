# -*- coding: utf-8 -*-
# power_manager.py - Enterprise Power Management, Server Guard, and Sleep Timer for PowerBox

# Acknowledgment:
# - Workstation locking utilizes native Windows user32.dll (LockWorkStation).
# - Power suspension and hibernation utilize powrprof.dll and Windows native shutdown utility.
# - Native UEFI firmware reboot utilizes Windows kernel shutdown command (shutdown /r /fw) with privilege elevation fallback.
# - Zero-latency server and remote session detection inspects Windows Registry (InstallationType),
#   Win32 RDP metrics (user32.GetSystemMetrics: SM_REMOTESESSION), and live NVDA Remote session states
#   across both legacy add-on (runningPlugins introspection) and modern core _remoteClient.
# - Asynchronous non-blocking threading pattern applied uniformly across all power execution actions.
# - Accessible timer dialog and confirmation workflows follow NV Access standards.
# - Uses isolated WinDLL instances to eliminate cross-module ctypes prototype collisions.

import ctypes
from ctypes import wintypes
import os
import sys
import subprocess
import threading
import time
import wx
import addonHandler
import api
import config
import gui
import ui
import tones
from logHandler import log

# Initialize translation support for this module
addonHandler.initTranslation()

# Isolated Win32 DLL instances preventing prototype clashes
user32 = ctypes.WinDLL("user32", use_last_error=True)
powrprof = ctypes.WinDLL("powrprof", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

# 64-bit safe function prototypes
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND

user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int

user32.LockWorkStation.argtypes = []
user32.LockWorkStation.restype = wintypes.BOOL

powrprof.SetSuspendState.argtypes = [wintypes.BOOLEAN, wintypes.BOOLEAN, wintypes.BOOLEAN]
powrprof.SetSuspendState.restype = wintypes.BOOLEAN

shell32.ShellExecuteW.argtypes = [
    wintypes.HWND,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    ctypes.c_int
]
shell32.ShellExecuteW.restype = wintypes.HINSTANCE

# Win32 Metrics
SM_REMOTESESSION = 0x1000

# Global timer tracking
_timer_thread = None
_timer_cancel_event = threading.Event()
_timer_active = False
_timer_end_time = 0.0

# Timestamp tracking for double-press confirmation
_last_press_time = 0.0
_last_press_action = None


def trigger_power_feedback(msg, beep_pitch=500, beep_duration=50):
    """Provides user feedback respecting configured feedbackMode."""
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")

    if mode in ("beep", "both"):
        tones.beep(beep_pitch, beep_duration)

    if mode in ("speech", "both"):
        ui.message(msg)


# --- 4-Tier Server & Remote Session Detection Engine ---
def is_windows_server():
    """Detects whether host operating system is Windows Server via registry."""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
            0,
            winreg.KEY_READ
        ) as k:
            val, _ = winreg.QueryValueEx(k, "InstallationType")
            return str(val).strip().lower() == "server"
    except Exception:
        return False


def is_remote_session():
    """
    Exhaustively and accurately detects active remote management sessions across all NVDA versions:
    1. Win32 Kernel: Native Remote Desktop (RDP / Terminal Services SM_REMOTESESSION).
    2. NVDA 2024.1+ (Legacy Add-on): Live plugin instance inspection via globalPluginHandler.runningPlugins.
    3. NVDA 2025.1 / 2026+ (Core Module): Direct inspection of _remoteClient active sessions and transports.
    """
    # 1. Native Windows RDP Session Check (Win32 Kernel)
    try:
        if user32.GetSystemMetrics(SM_REMOTESESSION) != 0:
            return True
    except Exception:
        pass

    # 2. Check live running GlobalPlugins (NVDA 2024.1+ Legacy Add-on)
    try:
        import globalPluginHandler
        for p in getattr(globalPluginHandler, "runningPlugins", []):
            mod_name = getattr(p.__class__, "__module__", "").lower()
            if "remoteclient" in mod_name:
                if hasattr(p, "is_connected") and callable(p.is_connected):
                    try:
                        if p.is_connected() is True:
                            return True
                    except Exception:
                        pass
                for t_name in ("slave_transport", "master_transport", "transport", "sd_relay"):
                    t_obj = getattr(p, t_name, None)
                    if t_obj and getattr(t_obj, "connected", False) is True:
                        return True
                if getattr(p, "slave_session", None) is not None or getattr(p, "master_session", None) is not None:
                    return True
    except Exception as e:
        log.debug("PowerBox: Error inspecting runningPlugins for Remote Add-on: %s" % str(e))

    # 3. Modern NVDA Remote Core Module (_remoteClient in NVDA 2025.1 / 2026+)
    try:
        import sys
        remote_modules = [
            m for k, m in sys.modules.items()
            if m and (k == "_remoteClient" or k.startswith("_remoteClient."))
        ]

        for mod in remote_modules:
            for attr_name in dir(mod):
                try:
                    obj = getattr(mod, attr_name, None)
                    if not obj:
                        continue

                    if getattr(obj, "connected", False) is True:
                        return True

                    if hasattr(obj, "is_connected") and callable(obj.is_connected):
                        try:
                            if obj.is_connected() is True:
                                return True
                        except Exception:
                            pass

                    for t_attr in ("transport", "_transport", "slave_transport", "master_transport", "relayTransport"):
                        t_inst = getattr(obj, t_attr, None)
                        if t_inst:
                            if getattr(t_inst, "connected", False) is True or getattr(t_inst, "_connected", False) is True:
                                return True
                            sock = getattr(t_inst, "transport", None)
                            if sock and getattr(sock, "connected", False) is True:
                                return True

                    for s_attr in ("session", "_session", "current_session", "_current_session", "master_session", "slave_session"):
                        s_inst = getattr(obj, s_attr, None)
                        if s_inst:
                            if getattr(s_inst, "connected", False) is True:
                                return True
                            s_trans = getattr(s_inst, "transport", None) or getattr(s_inst, "_transport", None)
                            if s_trans and getattr(s_trans, "connected", False) is True:
                                return True
                except Exception:
                    continue
    except Exception as e:
        log.debug("PowerBox: Error detecting NVDA Remote core session: %s" % str(e))

    return False


def is_server_or_remote():
    """Consolidated check determining if system requires remote power protection."""
    return is_windows_server() or is_remote_session()


# --- Harmonized Core System Power Actions (Non-Blocking Daemon Threads) ---
def lock_workstation():
    """Immediately locks the Windows desktop workstation with non-blocking speech protection."""
    trigger_power_feedback(_("Locking workstation"), 650, 40)

    def worker():
        mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
        if mode in ("speech", "both"):
            time.sleep(0.6)
        try:
            user32.LockWorkStation()
        except Exception:
            wx.CallAfter(ui.message, _("Failed to lock workstation"))

    threading.Thread(target=worker, daemon=True).start()


def execute_sleep():
    """Puts computer into sleep mode asynchronously with speech protection."""
    trigger_power_feedback(_("Entering sleep mode"), 450, 60)

    def worker():
        mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
        if mode in ("speech", "both"):
            time.sleep(0.8)
        try:
            powrprof.SetSuspendState(False, False, False)
        except Exception:
            wx.CallAfter(ui.message, _("Failed to enter sleep mode"))

    threading.Thread(target=worker, daemon=True).start()


def execute_hibernate():
    """Hibernates computer asynchronously saving state to disk."""
    trigger_power_feedback(_("Entering hibernation"), 350, 80)

    def worker():
        mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
        if mode in ("speech", "both"):
            time.sleep(0.8)
        try:
            subprocess.Popen(["shutdown", "/h"], creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            wx.CallAfter(ui.message, _("Failed to hibernate system"))

    threading.Thread(target=worker, daemon=True).start()


def execute_shutdown():
    """Executes an orderly, graceful system shutdown asynchronously."""
    trigger_power_feedback(_("Shutting down computer"), 300, 100)

    def worker():
        mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
        if mode in ("speech", "both"):
            time.sleep(1.0)
        try:
            subprocess.Popen(["shutdown", "/s", "/t", "1"], creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            wx.CallAfter(ui.message, _("Failed to shut down computer"))

    threading.Thread(target=worker, daemon=True).start()


def execute_restart():
    """Executes an orderly, graceful system restart asynchronously."""
    trigger_power_feedback(_("Restarting computer"), 400, 100)

    def worker():
        mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
        if mode in ("speech", "both"):
            time.sleep(1.0)
        try:
            subprocess.Popen(["shutdown", "/r", "/t", "1"], creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            wx.CallAfter(ui.message, _("Failed to restart computer"))

    threading.Thread(target=worker, daemon=True).start()


def execute_restart_firmware():
    """
    Reboots the computer directly into UEFI / BIOS firmware setup asynchronously.
    Executes directly with clean timeout, falling back to elevated ShellExecuteW ('runas')
    only when required to modify UEFI NVRAM boot variables smoothly.
    """
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
    trigger_power_feedback(_("Restarting computer to UEFI firmware..."), 450, 100)

    def worker():
        # Allow speech synthesizer time to complete the full announcement cleanly
        if mode in ("speech", "both"):
            time.sleep(1.2)

        try:
            # 1. Attempt direct execution with 2-second delay for smooth OS transition
            res = subprocess.run(
                ["shutdown", "/r", "/fw", "/t", "2"],
                creationflags=subprocess.CREATE_NO_WINDOW,
                capture_output=True,
                text=True
            )

            # 2. If direct execution failed due to elevation requirement, elevate via ShellExecuteW
            if res.returncode != 0:
                ret = shell32.ShellExecuteW(
                    None,
                    "runas",
                    "shutdown.exe",
                    "/r /fw /t 2",
                    None,
                    0
                )
                if (ret or 0) <= 32:
                    err_msg = _("Reboot to firmware failed. Your computer may not support UEFI firmware directly, or Administrator privileges are required.")
                    wx.CallAfter(ui.message, err_msg)
                    if mode in ("beep", "both"):
                        tones.beep(250, 80)
        except Exception as e:
            log.error("PowerBox: Failed to execute reboot to firmware: %s" % str(e))
            err_msg = _("Failed to execute reboot to firmware.")
            wx.CallAfter(ui.message, err_msg)
            if mode in ("beep", "both"):
                tones.beep(250, 80)

    threading.Thread(target=worker, daemon=True).start()


# --- Centralized Layer Dispatcher & Confirmation Engine ---
def is_second_press(action_type):
    """Checks whether this invocation is the second press within the 2.0-second confirmation window."""
    global _last_press_time, _last_press_action
    return (_last_press_action == action_type and (time.time() - _last_press_time) <= 2.0)


def reset_press_tracking():
    """Resets the double-press confirmation state when the time window expires."""
    global _last_press_time, _last_press_action
    _last_press_time = 0.0
    _last_press_action = None


def handle_power_action(plugin, action_type):
    """
    Centralized architectural dispatcher managing layer lifecycle, double-press timing,
    and server warning dialogs without key-trapping or focus conflicts.
    """
    guard_setting = config.conf.get("powerBox", {}).get("serverPowerGuard", "smartBlock")
    is_remote = is_server_or_remote()
    confirm_style = config.conf.get("powerBox", {}).get("powerConfirmStyle", "dialog")

    # Scenario A: Sleep & Hibernate Smart Block on server/remote session
    if action_type in ("sleep", "hibernate") and is_remote and guard_setting == "smartBlock":
        plugin._cancel_double_press_timer()
        plugin.keepLayerActive = False
        reset_press_tracking()
        if is_windows_server():
            msg = _("Sleep and Hibernate are disabled on Windows Server to prevent system outages.")
        else:
            msg = _("Sleep and Hibernate are disabled during remote sessions to prevent connection loss.")
        trigger_power_feedback(msg, 250, 80)
        return

    # Determine if a specialized remote warning dialog is required:
    is_remote_warn = is_remote and (
        (action_type in ("sleep", "hibernate") and guard_setting == "warnDialog") or
        (action_type in ("shutdown", "restart_firmware") and guard_setting != "disabled")
    )

    # Scenario B: Modal Dialog Required (either user preference OR enforced remote warning dialog)
    if confirm_style == "dialog" or is_remote_warn:
        plugin._cancel_double_press_timer()
        plugin.keepLayerActive = False
        reset_press_tracking()
        request_confirmed_action(action_type)
        return

    # Scenario C: Double-Press Confirmation (for local PC or routine restart)
    if confirm_style == "doublePress":
        if not is_second_press(action_type):
            plugin.keepLayerActive = True
            plugin._cancel_double_press_timer()
            plugin._double_press_timer = wx.CallLater(2100, plugin._on_double_press_expired)
            request_confirmed_action(action_type)
        else:
            plugin._cancel_double_press_timer()
            plugin.keepLayerActive = False
            request_confirmed_action(action_type)


def request_confirmed_action(action_type):
    """
    Unified power dispatcher enforcing Server Guard and user-selected confirmation style:
    - Covers: 'shutdown', 'restart', 'restart_firmware', 'sleep', 'hibernate'.
    - Server Guard: Automatically blocks or warns before destructive actions on remote environments.
    - Confirmation: Modal dialog (focus on [No]) or double-press confirmation.
    """
    global _last_press_time, _last_press_action

    # Action metadata mapping
    action_dispatch = {
        "shutdown": {
            "name": _("shut down"),
            "title": _("Confirm Shutdown"),
            "prompt": _("Are you sure you want to shut down your computer?"),
            "func": execute_shutdown
        },
        "restart": {
            "name": _("restart"),
            "title": _("Confirm Restart"),
            "prompt": _("Are you sure you want to restart your computer?"),
            "func": execute_restart
        },
        "restart_firmware": {
            "name": _("restart to UEFI firmware"),
            "title": _("Confirm Reboot to Firmware"),
            "prompt": _("Are you sure you want to restart into UEFI firmware settings?"),
            "func": execute_restart_firmware
        },
        "sleep": {
            "name": _("sleep"),
            "title": _("Confirm Sleep"),
            "prompt": _("Are you sure you want to put your computer into sleep mode?"),
            "func": execute_sleep
        },
        "hibernate": {
            "name": _("hibernate"),
            "title": _("Confirm Hibernate"),
            "prompt": _("Are you sure you want to hibernate your computer?"),
            "func": execute_hibernate
        },
    }

    target = action_dispatch.get(action_type)
    if not target:
        return

    # Determine remote warning state
    guard_setting = config.conf.get("powerBox", {}).get("serverPowerGuard", "smartBlock")
    is_remote = is_server_or_remote()
    is_remote_warn = is_remote and (
        (action_type in ("sleep", "hibernate") and guard_setting == "warnDialog") or
        (action_type in ("shutdown", "restart_firmware") and guard_setting != "disabled")
    )

    # Context-aware warning prompts on remote sessions
    if is_remote_warn:
        if action_type in ("sleep", "hibernate"):
            target["prompt"] = _("HIGH RISK WARNING: This is a Windows Server or remote session. Putting this machine to sleep will disconnect all users and may require physical power-on. Are you sure?")
        elif action_type == "shutdown":
            target["prompt"] = _("REMOTE SESSION WARNING: You are connected remotely. Shutting down this computer will terminate all connections and require manual power-on or IPMI to turn it back on. Are you sure?")
        elif action_type == "restart_firmware":
            target["prompt"] = _("REMOTE SESSION WARNING: You are connected remotely. Rebooting into UEFI firmware will terminate remote access and keep the machine in BIOS setup until manually rebooted. Are you sure?")

    confirm_style = config.conf.get("powerBox", {}).get("powerConfirmStyle", "dialog")
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
    now = time.time()

    # 1. Double-Press Confirmation Style
    if confirm_style == "doublePress" and not is_remote_warn:
        if _last_press_action == action_type and (now - _last_press_time) <= 2.0:
            reset_press_tracking()
            target["func"]()
        else:
            _last_press_action = action_type
            _last_press_time = now
            if mode in ("beep", "both"):
                tones.beep(700, 40)
            ui.message(_("Press again within 2 seconds to confirm {action}").format(action=target["name"]))
        return

    # 2. Default: Modal Confirmation Dialog on the main UI thread (Initial focus on NO)
    def show_dialog():
        gui_parent = getattr(gui, "mainFrame", None)
        if gui_parent:
            gui_parent.prePopup()
        try:
            icon = wx.ICON_EXCLAMATION if is_remote_warn else wx.ICON_WARNING
            res = gui.messageBox(
                target["prompt"],
                target["title"],
                wx.YES_NO | wx.NO_DEFAULT | icon,
                parent=gui_parent
            )
            if res == wx.YES:
                import speech
                # 1. Cancel any pending speech from the dialog closing
                speech.cancelSpeech()
                
                # 2. Execute the power action in the background immediately
                target["func"]()
                
                # 3. Micro-freeze the main thread explicitly for 0.8s BEFORE destroying the dialog
                # This prevents Windows from firing a 'gainFocus' event to the background app
                # ensuring NVDA remains completely silent while the shutdown command takes effect.
                time.sleep(0.8)
        finally:
            if gui_parent:
                gui_parent.postPopup()

    wx.CallAfter(show_dialog)


# --- Shutdown / Sleep Timer Engine ---
def _timer_worker(total_seconds):
    """Background countdown worker thread."""
    global _timer_active, _timer_end_time
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
    warning_given = False

    while not _timer_cancel_event.is_set():
        remaining = _timer_end_time - time.time()

        if remaining <= 0:
            break

        # 60-Second Warning Alert
        if remaining <= 60 and not warning_given:
            warning_given = True
            if mode in ("beep", "both"):
                tones.beep(600, 100)
                time.sleep(0.1)
                tones.beep(400, 100)
            if mode in ("speech", "both"):
                ui.message(_("Warning: Computer will shut down in 1 minute."))

        if _timer_cancel_event.wait(0.5):
            return

    if not _timer_cancel_event.is_set():
        _timer_active = False
        _timer_end_time = 0.0
        execute_shutdown()


def start_timer(minutes):
    """Starts or resets the background shutdown timer for the specified minutes."""
    global _timer_thread, _timer_active, _timer_end_time

    cancel_timer(silent=True)
    _timer_cancel_event.clear()
    _timer_active = True
    _timer_end_time = time.time() + (minutes * 60)

    trigger_power_feedback(
        _("Shutdown timer set for {mins} minutes").format(mins=minutes),
        750, 40
    )

    _timer_thread = threading.Thread(target=_timer_worker, args=(minutes * 60,), daemon=True)
    _timer_thread.start()


def cancel_timer(silent=False):
    """Cancels the active shutdown timer if running."""
    global _timer_active, _timer_end_time

    if not _timer_active:
        if not silent:
            trigger_power_feedback(_("No active shutdown timer"), 250, 60)
        return

    _timer_cancel_event.set()
    _timer_active = False
    _timer_end_time = 0.0

    if not silent:
        trigger_power_feedback(_("Shutdown timer canceled"), 400, 50)


def get_timer_status():
    """Queries and announces remaining time on the active shutdown timer."""
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")

    if not _timer_active:
        if mode in ("beep", "both"):
            tones.beep(250, 50)
        ui.message(_("No active shutdown timer"))
        return

    remaining_seconds = max(0, int(_timer_end_time - time.time()))
    mins = remaining_seconds // 60
    secs = remaining_seconds % 60

    if mode in ("beep", "both"):
        tones.beep(550, 40)

    if mins > 0:
        ui.message(_("Shutdown scheduled in {m} minutes, {s} seconds").format(m=mins, s=secs))
    else:
        ui.message(_("Shutdown scheduled in {s} seconds").format(s=secs))


# --- Windows Explorer Smart Revive / Restart Engine ---
def _is_explorer_alive():
    """Ultra-fast detection checking if Windows Explorer shell is currently running."""
    return bool(user32.FindWindowW("Shell_TrayWnd", None) or user32.FindWindowW("Progman", None))


def _restart_explorer_worker(was_running):
    """Background worker handling both hung restart and clean revive states."""
    if was_running:
        subprocess.run(
            ["taskkill", "/f", "/im", "explorer.exe"],
            creationflags=subprocess.CREATE_NO_WINDOW,
            capture_output=True
        )
        time.sleep(0.3)

    try:
        subprocess.Popen(["explorer.exe"])
        msg = _("Windows Explorer restarted") if was_running else _("Windows Explorer started")
        wx.CallAfter(trigger_power_feedback, msg, 650, 45)
    except Exception:
        err_msg = _("Failed to start Windows Explorer")
        wx.CallAfter(trigger_power_feedback, err_msg, 250, 60)


def restart_explorer():
    """Entry point intelligently determining whether to restart or revive Windows Explorer."""
    was_running = _is_explorer_alive()
    init_msg = _("Restarting Windows Explorer...") if was_running else _("Starting Windows Explorer...")
    trigger_power_feedback(init_msg, 500, 40)
    threading.Thread(target=_restart_explorer_worker, args=(was_running,), daemon=True).start()


# --- Accessible Timer Configuration Dialog ---
class TimerDialog(wx.Dialog):
    """An accessible dialog allowing users to pick presets or enter custom shutdown minutes."""

    def __init__(self, parent):
        super(TimerDialog, self).__init__(
            parent,
            title=_("Set Shutdown Timer"),
            style=wx.DEFAULT_DIALOG_STYLE,
            size=(420, 260),
        )

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        helper = gui.guiHelper.BoxSizerHelper(self, sizer=main_sizer)
        self.spin_ctrl = helper.addLabeledControl(
            _("&Duration (minutes):"),
            wx.SpinCtrl,
            min=1,
            max=720,
            initial=30
        )

        # Quick Preset Buttons
        preset_box = wx.StaticBox(self, label=_("Quick Presets"))
        preset_sizer = wx.StaticBoxSizer(preset_box, wx.HORIZONTAL)

        for duration in (15, 30, 45, 60):
            btn = wx.Button(self, label=_("{m}m").format(m=duration))
            btn.Bind(wx.EVT_BUTTON, lambda evt, d=duration: self.spin_ctrl.SetValue(d))
            preset_sizer.Add(btn, 1, wx.ALL, 3)

        main_sizer.Add(preset_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        # Dialog Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.start_btn = wx.Button(self, wx.ID_OK, label=_("&Start Timer"))
        self.start_btn.SetDefault()
        self.close_btn = wx.Button(self, wx.ID_CANCEL, label=_("&Cancel"))

        btn_sizer.Add(self.start_btn, 0, wx.RIGHT, 6)
        btn_sizer.Add(self.close_btn, 0)
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 12)

        self.SetSizer(main_sizer)
        self.CenterOnScreen()

    def get_minutes(self):
        return self.spin_ctrl.GetValue()


def show_timer_dialog():
    """Safely presents the accessible timer setup dialog on the main UI thread."""
    gui_parent = getattr(gui, "mainFrame", None)
    if gui_parent:
        gui_parent.prePopup()
    try:
        dlg = TimerDialog(gui_parent)
        if dlg.ShowModal() == wx.ID_OK:
            minutes = dlg.get_minutes()
            start_timer(minutes)
        dlg.Destroy()
    finally:
        if gui_parent:
            gui_parent.postPopup()