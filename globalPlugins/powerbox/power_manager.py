# -*- coding: utf-8 -*-
# power_manager.py - System power management and sleep timer for PowerBox

# Acknowledgment:
# - Workstation locking utilizes Windows user32.dll (LockWorkStation).
# - Power suspension and hibernation utilize powrprof.dll and Windows native shutdown utility.
# - Accessible timer dialog and confirmation workflows follow NV Access standards.

import ctypes
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

# Initialize translation support for this module
addonHandler.initTranslation()

# Global timer tracking
_timer_thread = None
_timer_cancel_event = threading.Event()
_timer_active = False
_timer_end_time = 0.0

# Timestamp tracking for double-press confirmation
_last_press_time = 0.0
_last_press_action = None


def trigger_power_feedback(msg, beep_pitch=500, beep_duration=50):
    """Provides user feedback respecting the configured feedbackMode."""
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")

    if mode in ("beep", "both"):
        tones.beep(beep_pitch, beep_duration)

    if mode in ("speech", "both"):
        ui.message(msg)


# --- Core System Power Actions ---
def lock_workstation():
    """Immediately locks the Windows desktop workstation with speech protection."""
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
    trigger_power_feedback(_("Locking workstation"), 650, 40)
    if mode in ("speech", "both"):
        time.sleep(0.8)
    try:
        ctypes.windll.user32.LockWorkStation()
    except Exception:
        ui.message(_("Failed to lock workstation"))


def sleep_system():
    """Puts the computer into sleep mode with speech protection."""
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
    trigger_power_feedback(_("Entering sleep mode"), 450, 60)
    if mode in ("speech", "both"):
        time.sleep(1.0)
    try:
        ctypes.windll.powrprof.SetSuspendState(False, False, False)
    except Exception:
        ui.message(_("Failed to enter sleep mode"))


def hibernate_system():
    """Hibernates the computer saving state to disk."""
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
    trigger_power_feedback(_("Entering hibernation"), 350, 80)
    if mode in ("speech", "both"):
        time.sleep(1.0)
    try:
        subprocess.Popen(["shutdown", "/h"], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        ui.message(_("Failed to hibernate system"))


def execute_shutdown():
    """Executes an orderly, graceful system shutdown."""
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
    trigger_power_feedback(_("Shutting down computer"), 300, 100)
    if mode in ("speech", "both"):
        time.sleep(1.2)
    try:
        subprocess.Popen(["shutdown", "/s", "/t", "1"], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        ui.message(_("Failed to shut down computer"))


def execute_restart():
    """Executes an orderly, graceful system restart."""
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
    trigger_power_feedback(_("Restarting computer"), 400, 100)
    if mode in ("speech", "both"):
        time.sleep(1.2)
    try:
        subprocess.Popen(["shutdown", "/r", "/t", "1"], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        ui.message(_("Failed to restart computer"))


# --- Confirmation Management ---
def is_second_press(action_type):
    """Checks whether this invocation is the second press within the 2.0-second confirmation window."""
    global _last_press_time, _last_press_action
    return (_last_press_action == action_type and (time.time() - _last_press_time) <= 2.0)


def reset_press_tracking():
    """Resets the double-press confirmation state when the time window expires."""
    global _last_press_time, _last_press_action
    _last_press_time = 0.0
    _last_press_action = None


def request_confirmed_action(action_type):
    """
    Executes shutdown or restart based on the user's preferred confirmation style:
    - 'dialog': Modal confirmation dialog (default focus on NO for safety).
    - 'doublePress': Requires pressing the key twice within 2 seconds.
    """
    global _last_press_time, _last_press_action

    confirm_style = config.conf.get("powerBox", {}).get("powerConfirmStyle", "dialog")
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
    now = time.time()

    is_shutdown = (action_type == "shutdown")
    action_name = _("shut down") if is_shutdown else _("restart")
    exec_func = execute_shutdown if is_shutdown else execute_restart

    if confirm_style == "doublePress":
        if _last_press_action == action_type and (now - _last_press_time) <= 2.0:
            # Second press confirmed within time window
            reset_press_tracking()
            exec_func()
        else:
            # First press: Record timestamp and inform user
            _last_press_action = action_type
            _last_press_time = now
            if mode in ("beep", "both"):
                tones.beep(700, 40)
            ui.message(_("Press again within 2 seconds to confirm {action}").format(action=action_name))
        return

    # Default: Safe Confirmation Dialog on the main UI thread
    def show_dialog():
        gui_parent = getattr(gui, "mainFrame", None)
        if gui_parent:
            gui_parent.prePopup()
        try:
            title = _("Confirm Shutdown") if is_shutdown else _("Confirm Restart")
            question = (
                _("Are you sure you want to shut down your computer?")
                if is_shutdown else
                _("Are you sure you want to restart your computer?")
            )
            res = gui.messageBox(
                question,
                title,
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
                parent=gui_parent
            )
            if res == wx.YES:
                exec_func()
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

        # Sleep in short slices (0.5s) to allow responsive cancellation
        if _timer_cancel_event.wait(0.5):
            return

    if not _timer_cancel_event.is_set():
        _timer_active = False
        _timer_end_time = 0.0
        execute_shutdown()


def start_timer(minutes):
    """Starts or resets the background shutdown timer for the specified minutes."""
    global _timer_thread, _timer_active, _timer_end_time

    # Cancel any previous active timer
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
    """Queries and announces the remaining time on the active shutdown timer."""
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

        # Label & Spin control
        helper = gui.guiHelper.BoxSizerHelper(self, sizer=main_sizer)
        self.spin_ctrl = helper.addLabeledControl(
            _("&Duration (minutes):"),
            wx.SpinCtrl,
            min=1,
            max=720,
            initial=30
        )

        # Quick Preset Buttons Sizer
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