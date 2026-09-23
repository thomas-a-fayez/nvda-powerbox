# -*- coding: utf-8 -*-
# process_inspector.py - Active application CPU and RAM inspector for PowerBox

# Acknowledgment:
# Uses isolated Win32 kernel instances and native performance counters to measure
# per-process CPU percentage and Working Set memory without ctypes pointer conflicts.

import ctypes
from ctypes import wintypes
import os
import threading
import time
import wx
import addonHandler
import api
import config
import ui
import tones
from logHandler import log

# Initialize translation support for this module
addonHandler.initTranslation()

# Win32 Process Access Rights
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

# Private, isolated Win32 DLL instances (prevents cross-module ctypes pollution)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)


class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


# Function Bindings with Native Standard wintypes.FILETIME
OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL

GetProcessTimes = kernel32.GetProcessTimes
GetProcessTimes.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(wintypes.FILETIME),
    ctypes.POINTER(wintypes.FILETIME),
    ctypes.POINTER(wintypes.FILETIME),
    ctypes.POINTER(wintypes.FILETIME)
]
GetProcessTimes.restype = wintypes.BOOL

try:
    GetProcessMemoryInfo = kernel32.K32GetProcessMemoryInfo
except AttributeError:
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    GetProcessMemoryInfo = psapi.GetProcessMemoryInfo

GetProcessMemoryInfo.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX),
    wintypes.DWORD
]
GetProcessMemoryInfo.restype = wintypes.BOOL


def _filetime_to_uint64(ft):
    """Converts native wintypes.FILETIME struct into 64-bit integer."""
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime


def trigger_inspector_feedback(msg, is_success=True, is_copy=False):
    """Provides user feedback respecting the configured feedbackMode in PowerBox."""
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")

    if mode in ("beep", "both"):
        if not is_success:
            tones.beep(250, 60)
        elif is_copy:
            tones.beep(950, 40)
        else:
            tones.beep(850, 45)

    if mode in ("speech", "both"):
        ui.message(msg)


def _get_process_cpu_and_ram(h_process, sample_interval=0.3):
    """
    Calculates CPU% and physical RAM usage across a high-precision wall-clock interval.
    Normalizes across logical CPU cores to align with Windows Task Manager.
    """
    creation_time = wintypes.FILETIME()
    exit_time = wintypes.FILETIME()
    kernel_time_1 = wintypes.FILETIME()
    user_time_1 = wintypes.FILETIME()

    # Sample 1
    if not GetProcessTimes(h_process, ctypes.byref(creation_time), ctypes.byref(exit_time),
                           ctypes.byref(kernel_time_1), ctypes.byref(user_time_1)):
        return None, None

    t1 = time.perf_counter()
    time.sleep(sample_interval)

    # Sample 2
    kernel_time_2 = wintypes.FILETIME()
    user_time_2 = wintypes.FILETIME()

    if not GetProcessTimes(h_process, ctypes.byref(creation_time), ctypes.byref(exit_time),
                           ctypes.byref(kernel_time_2), ctypes.byref(user_time_2)):
        return None, None

    t2 = time.perf_counter()
    wall_delta = t2 - t1

    # FILETIME is in 100-nanosecond units (10,000,000 units = 1 second)
    proc_delta = (_filetime_to_uint64(kernel_time_2) - _filetime_to_uint64(kernel_time_1)) + \
                 (_filetime_to_uint64(user_time_2) - _filetime_to_uint64(user_time_1))

    proc_seconds = proc_delta / 10000000.0
    num_cores = os.cpu_count() or 1

    cpu_percent = 0.0
    if wall_delta > 0:
        cpu_percent = (proc_seconds / wall_delta) * 100.0 / num_cores

    cpu_percent = min(100.0, max(0.0, cpu_percent))

    # Calculate Working Set RAM in MB
    counters = PROCESS_MEMORY_COUNTERS_EX()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
    ram_mb = 0.0
    if GetProcessMemoryInfo(h_process, ctypes.byref(counters), counters.cb):
        ram_mb = counters.WorkingSetSize / (1024.0 * 1024.0)

    return cpu_percent, ram_mb


def _format_memory_string(ram_mb):
    """Formats RAM into human-friendly MB or GB."""
    if ram_mb >= 1024.0:
        return _("{size:.1f} GB").format(size=ram_mb / 1024.0)
    return _("{size:.0f} MB").format(size=ram_mb)


def _inspect_worker(hwnd, app_name, copy_to_clip=False):
    """Background worker thread to guarantee NVDA never freezes during measurement."""
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

    if not pid.value:
        msg = _("Could not identify the active process")
        wx.CallAfter(trigger_inspector_feedback, msg, False, False)
        return

    # Windows 7+ only requires PROCESS_QUERY_LIMITED_INFORMATION for ProcessTimes & MemoryInfo
    h_process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)

    if not h_process or h_process == INVALID_HANDLE_VALUE:
        msg = _("Access denied for {app}").format(app=app_name)
        wx.CallAfter(trigger_inspector_feedback, msg, False, False)
        return

    try:
        cpu_pct, ram_mb = _get_process_cpu_and_ram(h_process)
        if cpu_pct is None or ram_mb is None:
            msg = _("Could not read resources for {app}").format(app=app_name)
            wx.CallAfter(trigger_inspector_feedback, msg, False, False)
            return

        ram_display = _format_memory_string(ram_mb)
        result_msg = _("{app}: {ram}, CPU {cpu:.1f}%").format(
            app=app_name,
            ram=ram_display,
            cpu=cpu_pct
        )

        if copy_to_clip:
            api.copyToClip(result_msg)
            feedback_msg = _("{info} (Copied)").format(info=result_msg)
            wx.CallAfter(trigger_inspector_feedback, feedback_msg, True, True)
        else:
            wx.CallAfter(trigger_inspector_feedback, result_msg, True, False)

    except Exception as e:
        log.error("PowerBox process inspector failed: %s" % str(e))
        msg = _("Error inspecting process")
        wx.CallAfter(trigger_inspector_feedback, msg, False, False)
    finally:
        CloseHandle(h_process)


def inspect_active_process(copy_to_clip=False):
    """Main entry point called when pressing 'p' or 'shift+p' in the System Layer."""
    try:
        focus_obj = api.getFocusObject()
        if not focus_obj or not getattr(focus_obj, "windowHandle", None):
            trigger_inspector_feedback(_("No active window found"), False, False)
            return

        hwnd = focus_obj.windowHandle

        # Retrieve application name
        app_module = getattr(focus_obj, "appModule", None)
        if app_module and getattr(app_module, "appName", None):
            app_name = app_module.appName
        elif focus_obj.name:
            app_name = focus_obj.name[:35]
        else:
            app_name = _("Application")

        # Launch calculation in daemon thread
        t = threading.Thread(
            target=_inspect_worker,
            args=(hwnd, app_name, copy_to_clip),
            daemon=True
        )
        t.start()

    except Exception as e:
        log.error("PowerBox inspector dispatch error: %s" % str(e))
        trigger_inspector_feedback(_("Failed to start process inspector"), False, False)