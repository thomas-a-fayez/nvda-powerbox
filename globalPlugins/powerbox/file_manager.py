# -*- coding: utf-8 -*-
# file_manager.py - Enterprise Files & Storage Power Suite for PowerBox

# Acknowledgment:
# - Active file locking detection and termination utilizes Microsoft Restart Manager API (rstrtmgr.dll).
# - Physical disk space metrics utilize Win32 GetDiskFreeSpaceExW and GetLogicalDriveStringsW via kernel32.dll.
# - High-speed background directory size calculation and SHA-256 chunk streaming support instant cancellation.
# - Intelligent shortcut (.lnk) target resolution uses Windows WScript.Shell COM automation.
# - Language-independent shell inspection captures dynamic localized tab/window titles without punctuation noise.
# - Safe clipboard reading on the main UI thread prevents OLE STA cross-thread exceptions.
# - Uses isolated WinDLL instances to ensure zero ctypes prototype collisions.

import ctypes
from ctypes import wintypes
import os
import re
import hashlib
import threading
import time
import comtypes.client
import wx
import addonHandler
import api
import config
import controlTypes
import gui
import ui
import tones
import winUser
from logHandler import log

# Initialize translation support for this module
addonHandler.initTranslation()

# Isolated Win32 DLL instances
rstrtmgr = ctypes.WinDLL("rstrtmgr", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)

# Win32 Constants & Access Rights
PROCESS_TERMINATE = 0x0001
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
CCH_RM_MAX_APP_NAME = 255
CCH_RM_MAX_SVC_NAME = 63

# Cancellation and Concurrency Tracking
_size_calculating = False
_size_cancel_event = threading.Event()

_hash_calculating = False
_hash_cancel_event = threading.Event()


# Win32 Restart Manager Structures
class RM_UNIQUE_PROCESS(ctypes.Structure):
    _fields_ = [
        ("dwProcessId", wintypes.DWORD),
        ("ProcessStartTime", wintypes.FILETIME),
    ]


class RM_PROCESS_INFO(ctypes.Structure):
    _fields_ = [
        ("Process", RM_UNIQUE_PROCESS),
        ("strAppName", wintypes.WCHAR * (CCH_RM_MAX_APP_NAME + 1)),
        ("strServiceShortName", wintypes.WCHAR * (CCH_RM_MAX_SVC_NAME + 1)),
        ("ApplicationType", ctypes.c_int),
        ("AppStatus", wintypes.ULONG),
        ("TSSessionId", wintypes.DWORD),
        ("bRestartable", wintypes.BOOL),
    ]


# Function Bindings using generic c_void_p for cross-module immunity
rstrtmgr.RmStartSession.argtypes = [ctypes.POINTER(wintypes.DWORD), wintypes.DWORD, wintypes.LPWSTR]
rstrtmgr.RmStartSession.restype = wintypes.DWORD

rstrtmgr.RmRegisterResources.argtypes = [
    wintypes.DWORD, wintypes.UINT, ctypes.POINTER(wintypes.LPCWSTR),
    wintypes.UINT, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p
]
rstrtmgr.RmRegisterResources.restype = wintypes.DWORD

rstrtmgr.RmGetList.argtypes = [
    wintypes.DWORD, ctypes.POINTER(wintypes.UINT), ctypes.POINTER(wintypes.UINT),
    ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD)
]
rstrtmgr.RmGetList.restype = wintypes.DWORD

rstrtmgr.RmEndSession.argtypes = [wintypes.DWORD]
rstrtmgr.RmEndSession.restype = wintypes.DWORD

kernel32.GetDiskFreeSpaceExW.argtypes = [
    wintypes.LPCWSTR,
    ctypes.POINTER(ctypes.c_uint64),
    ctypes.POINTER(ctypes.c_uint64),
    ctypes.POINTER(ctypes.c_uint64)
]
kernel32.GetDiskFreeSpaceExW.restype = wintypes.BOOL

kernel32.GetLogicalDriveStringsW.argtypes = [wintypes.DWORD, wintypes.LPWSTR]
kernel32.GetLogicalDriveStringsW.restype = wintypes.DWORD

user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND

user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int

OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE

TerminateProcess = kernel32.TerminateProcess
TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
TerminateProcess.restype = wintypes.BOOL

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL


def _trigger_file_feedback(msg, is_success=True, is_copy=False):
    """
    Delivers user feedback strictly respecting configured feedbackMode.
    Vital data payloads (size, drives space, hash, paths) are always spoken,
    while tones are played only in 'beep' and 'both', and '(Copied)' is appended
    only in 'speech' and 'both'.
    """
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")

    # Play distinct chimes only if beep feedback is enabled
    if mode in ("beep", "both"):
        if not is_success:
            tones.beep(250, 60)
        elif is_copy:
            tones.beep(950, 40)
        else:
            tones.beep(850, 40)

    # In 'speech' and 'both', explicitly append '(Copied)'
    # In 'beep' and 'none', speak the pure data payload without adding '(Copied)'
    if is_copy and mode in ("speech", "both"):
        ui.message(f"{msg} {_('(Copied)')}")
    else:
        ui.message(msg)


def _kill_process_pid(pid):
    """Terminates a process PID cleanly."""
    h_proc = OpenProcess(PROCESS_TERMINATE, False, pid)
    if not h_proc or h_proc == INVALID_HANDLE_VALUE:
        return False
    try:
        return bool(TerminateProcess(h_proc, 1))
    finally:
        CloseHandle(h_proc)


def is_drive_root(path_str):
    """Detects whether a path represents a drive root (e.g. C:, C:\\, D:\\)."""
    if not path_str or not isinstance(path_str, str):
        return False
    norm = path_str.replace("/", "\\").rstrip("\\")
    return len(norm) == 2 and norm[1] == ":"


def convert_to_wsl_path(win_path):
    """Converts a standard Windows path (C:\\Folder) to WSL Linux path (/mnt/c/Folder)."""
    if not win_path:
        return ""
    norm = os.path.abspath(win_path).replace("\\", "/")
    if len(norm) >= 2 and norm[1] == ":":
        drive = norm[0].lower()
        return f"/mnt/{drive}{norm[2:]}"
    return norm


def resolve_shortcut_target(file_path):
    """
    Intelligently resolves a Windows shortcut (.lnk) to its real physical target file or folder.
    Falls back gracefully to the original .lnk path if target is unresolved.
    """
    if not file_path or not isinstance(file_path, str) or not file_path.lower().endswith(".lnk"):
        return file_path
    if not os.path.isfile(file_path):
        return file_path

    try:
        wscript = comtypes.client.CreateObject("WScript.Shell", dynamic=True)
        shortcut = wscript.CreateShortcut(file_path)
        target = getattr(shortcut, "TargetPath", None)
        if target and isinstance(target, str) and os.path.exists(target):
            return target
    except Exception as e:
        log.debug("Error resolving shortcut target via WScript: %s" % str(e))

    return file_path


def _extract_drive_letter_from_text(text):
    """Extracts drive root (e.g. C:\\) from names like 'Local Disk (C:)'."""
    if not text:
        return None
    match = re.search(r'\(([A-Za-z]:)\)', text)
    if match:
        d = match.group(1).upper()
        root = d + "\\"
        if os.path.exists(root):
            return root
    return None


def _resolve_desktop_item(item_name):
    """
    Language-independent resolution of Desktop items into physical paths.
    Resolves user home profile folder, .lnk shortcuts, and recognizes virtual icons.
    """
    if not item_name:
        return None, False

    user_home = os.path.expanduser("~")
    user_home_name = os.path.basename(user_home)

    # 1. User Home Profile Folder icon on Desktop (named after current user)
    if item_name.strip().lower() == user_home_name.strip().lower():
        if os.path.exists(user_home):
            return user_home, False

    user_desktop = os.path.join(user_home, "Desktop")
    public_desktop = os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "Desktop")

    # 2. Physical files, folders, and .lnk shortcuts on user and public desktops
    for d in (user_desktop, public_desktop):
        cand = os.path.join(d, item_name)
        if os.path.exists(cand):
            return cand, False
        cand_lnk = os.path.join(d, f"{item_name}.lnk")
        if os.path.exists(cand_lnk):
            return cand_lnk, False

    # 3. Known virtual system icons (This PC, Recycle Bin, Network, Control Panel)
    return None, True


# --- Robust Context Resolution Supporting Explorer Tabs, Desktop, and Localized Titles ---
def get_explorer_context():
    """
    Language-independent resolution of Explorer window/tab, focused item, and folder.
    Returns: (is_explorer: bool, selected_item_path: str or None, folder_path: str or None,
              is_virtual: bool, is_system_icon: bool, location_title: str)
    """
    focus = api.getFocusObject()
    if not focus:
        return False, None, None, False, False, ""

    app_name = getattr(getattr(focus, "appModule", None), "appName", "").lower()
    if app_name != "explorer":
        return False, None, None, False, False, ""

    fg_hwnd = user32.GetForegroundWindow()
    if not fg_hwnd:
        return False, None, None, False, False, ""

    root_hwnd = user32.GetAncestor(fg_hwnd, 2) or fg_hwnd
    window_title = winUser.getWindowText(root_hwnd).strip()

    # 1. Desktop Handling (Progman / WorkerW)
    class_buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(root_hwnd, class_buf, 256)
    if class_buf.value in ("Progman", "WorkerW"):
        user_desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        item_name = getattr(focus, "name", "")
        focus_states = getattr(focus, "states", set())
        is_selected = controlTypes.State.SELECTED in focus_states

        if item_name and is_selected:
            phys_path, is_sys = _resolve_desktop_item(item_name)
            if phys_path:
                return True, phys_path, user_desktop, False, False, _("Desktop")
            if is_sys:
                return True, None, user_desktop, True, True, item_name

        return True, None, user_desktop, False, False, _("Desktop")

    # 2. Explorer Window & Tab Inspection via Shell COM
    try:
        shell = comtypes.client.CreateObject("Shell.Application", dynamic=True)
        windows = shell.Windows()

        for w in windows:
            try:
                w_hwnd = getattr(w, "HWND", None)
                if w_hwnd != root_hwnd:
                    continue

                loc_name = getattr(w, "LocationName", "").strip()
                title_lower = window_title.lower()
                is_active_tab = bool(loc_name and (loc_name.lower() in title_lower or title_lower in loc_name.lower()))

                doc = getattr(w, "Document", None)
                folder = getattr(doc, "Folder", None)
                self_item = getattr(folder, "Self", None)
                folder_path = getattr(self_item, "Path", None)

                # Localized dynamic location title
                display_location = loc_name or window_title or _("Virtual Location")

                # Language-independent virtual folder detection
                is_virtual = (
                    not folder_path
                    or not isinstance(folder_path, str)
                    or folder_path.startswith("::")
                    or not os.path.exists(folder_path)
                )

                selected_item_path = None
                focus_states = getattr(focus, "states", set())
                is_item_selected = controlTypes.State.SELECTED in focus_states

                if is_item_selected:
                    drive_cand = _extract_drive_letter_from_text(getattr(focus, "name", ""))
                    if drive_cand:
                        selected_item_path = drive_cand
                    else:
                        try:
                            sel = getattr(doc, "SelectedItems", None)
                            if sel and sel.Count > 0:
                                it = sel.Item(0)
                                p = getattr(it, "Path", None)
                                if p and isinstance(p, str) and not p.startswith("::") and os.path.exists(p):
                                    selected_item_path = p
                                else:
                                    d = _extract_drive_letter_from_text(getattr(it, "Name", ""))
                                    if d:
                                        selected_item_path = d
                        except Exception:
                            pass

                        if not selected_item_path and folder_path and not is_virtual:
                            cand = os.path.join(folder_path, getattr(focus, "name", ""))
                            if os.path.exists(cand):
                                selected_item_path = cand

                if is_active_tab:
                    return True, selected_item_path, folder_path, is_virtual, False, display_location
            except Exception:
                continue
    except Exception:
        pass

    return True, None, None, False, False, window_title or _("Virtual Location")


# --- Unit Formatting According to User Settings ---
def format_file_size(num_bytes):
    """Formats file/folder bytes respecting user's configured fileSizeUnit setting."""
    pref = config.conf.get("powerBox", {}).get("fileSizeUnit", "auto")

    if pref == "mb":
        mb = num_bytes / (1024.0 * 1024.0)
        if mb < 0.01 and num_bytes > 0:
            return f"{num_bytes / 1024.0:.1f} KB"
        return f"{mb:.2f} MB"
    elif pref == "gb":
        gb = num_bytes / (1024.0 * 1024.0 * 1024.0)
        # Prevent 0.00 GB on small files by gracefully displaying in MB
        if gb < 0.01 and num_bytes > 0:
            return f"{num_bytes / (1024.0 * 1024.0):.2f} MB"
        return f"{gb:.2f} GB"

    # Default: Smart Adaptive
    if num_bytes < 1024:
        return f"{num_bytes} Bytes"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024.0:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024.0 * 1024.0):.1f} MB"
    else:
        return f"{num_bytes / (1024.0 * 1024.0 * 1024.0):.2f} GB"


def format_drive_size(num_bytes):
    """Formats drive bytes respecting user's configured driveSizeUnit setting."""
    pref = config.conf.get("powerBox", {}).get("driveSizeUnit", "auto")

    if pref == "gb":
        return f"{num_bytes / (1024.0 ** 3):.1f} GB"
    elif pref == "tb":
        return f"{num_bytes / (1024.0 ** 4):.2f} TB"

    if num_bytes >= 1024.0 ** 4:
        return f"{num_bytes / (1024.0 ** 4):.2f} TB"
    return f"{num_bytes / (1024.0 ** 3):.1f} GB"


# --- 1. Path Copier with Smart Shortcut Resolution (p and shift+p) ---
def copy_path(wsl=False):
    """Copies target path as Windows or WSL format, automatically resolving .lnk shortcuts."""
    is_exp, sel_path, folder_path, is_virt, is_sys_icon, loc_title = get_explorer_context()
    if not is_exp:
        _trigger_file_feedback(_("Please open File Explorer to copy path"), is_success=False)
        return

    if is_sys_icon:
        _trigger_file_feedback(_("{item} is a system icon and does not have a physical path").format(item=loc_title), is_success=False)
        return

    target = sel_path or folder_path
    if not target or (target.startswith("::") and not is_drive_root(target)):
        _trigger_file_feedback(_("Cannot copy path in {loc}").format(loc=loc_title), is_success=False)
        return

    # Innovatively resolve .lnk shortcuts to their true physical targets
    resolved_target = resolve_shortcut_target(target)

    res_path = convert_to_wsl_path(resolved_target) if wsl else resolved_target
    api.copyToClip(res_path)

    msg = _("WSL Path: {p}").format(p=res_path) if wsl else _("Path: {p}").format(p=res_path)
    _trigger_file_feedback(msg, is_success=True, is_copy=True)


# --- 2. Item Size Calculator with Cancellation & Shortcut Resolution (s and shift+s) ---
def _calculate_folder_stats(folder_path, cancel_event):
    """
    High-speed directory crawler utilizing cached WIN32_FIND_DATA stats.
    Eliminates hundreds of thousands of redundant disk syscalls, counting every file with 100% accuracy.
    """
    total_size = 0
    file_count = 0
    dir_count = 0
    stack = [folder_path]

    while stack:
        if cancel_event.is_set():
            return None, None, None
        curr_dir = stack.pop()
        try:
            with os.scandir(curr_dir) as it:
                for entry in it:
                    if cancel_event.is_set():
                        return None, None, None
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            dir_count += 1
                            stack.append(entry.path)
                        else:
                            file_count += 1
                            # Retrieve size directly from cached directory entry (0 extra disk syscalls!)
                            total_size += entry.stat(follow_symlinks=False).st_size
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            continue

    return total_size, file_count, dir_count


def calculate_size(copy_to_clip=False):
    """Context-aware size calculation for Drive, File, or Directory with full usage stats."""
    global _size_calculating, _size_cancel_event

    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")

    # Toggle Cancellation: If already calculating, cancel immediately!
    if _size_calculating:
        _size_cancel_event.set()
        _size_calculating = False
        if mode in ("speech", "both"):
            ui.message(_("Folder size calculation canceled"))
        if mode in ("beep", "both"):
            tones.beep(400, 40)
        return

    is_exp, sel_path, folder_path, is_virt, is_sys_icon, loc_title = get_explorer_context()
    if not is_exp:
        _trigger_file_feedback(_("Please select an item in File Explorer to calculate size"), is_success=False)
        return

    if is_sys_icon:
        focus_name = getattr(api.getFocusObject(), "name", loc_title)
        _trigger_file_feedback(_("{name} is a system icon and has no physical size").format(name=focus_name), is_success=False)
        return

    target = sel_path or folder_path
    if not target or (target.startswith("::") and not is_drive_root(target)):
        _trigger_file_feedback(_("Cannot calculate size in {loc}. Please select a physical file, folder, or drive").format(loc=loc_title), is_success=False)
        return

    # Resolve .lnk shortcuts to their true targets
    target = resolve_shortcut_target(target)

    # Scenario A: Drive root (e.g. C:, C:\, D:\) -> Instant full partition stats (Free, Used, Total)
    if is_drive_root(target):
        d_root = target.replace("/", "\\").rstrip("\\") + "\\"
        free_bytes = ctypes.c_uint64(0)
        total_bytes = ctypes.c_uint64(0)
        total_free = ctypes.c_uint64(0)
        if kernel32.GetDiskFreeSpaceExW(d_root, ctypes.byref(free_bytes), ctypes.byref(total_bytes), ctypes.byref(total_free)):
            tot_val = total_bytes.value
            free_val = free_bytes.value
            used_val = tot_val - free_val if tot_val >= free_val else 0

            free_fmt = format_drive_size(free_val)
            tot_fmt = format_drive_size(tot_val)
            used_fmt = format_drive_size(used_val)
            pct = (free_val / tot_val * 100.0) if tot_val > 0 else 0.0

            d_name = d_root.rstrip("\\").rstrip(":")
            msg = _("Drive {d}: {free} free ({pct:.0f}%), {used} used, Total: {tot}").format(
                d=d_name, free=free_fmt, pct=pct, used=used_fmt, tot=tot_fmt
            )
            if copy_to_clip:
                api.copyToClip(msg)
            _trigger_file_feedback(msg, is_success=True, is_copy=copy_to_clip)
            return

    name = os.path.basename(target.rstrip("\\/")) or target

    # Scenario B: Physical File -> Instant size
    if os.path.isfile(target):
        try:
            sz = os.path.getsize(target)
            msg = _("File {name}: {size}").format(name=name, size=format_file_size(sz))
            if copy_to_clip:
                api.copyToClip(msg)
            _trigger_file_feedback(msg, is_success=True, is_copy=copy_to_clip)
        except Exception:
            _trigger_file_feedback(_("Error reading file size"), is_success=False)
        return

    # Scenario C: Directory -> Calculate in background with cancellation & audible ticker
    _size_cancel_event.clear()
    _size_calculating = True

    if mode in ("speech", "both"):
        ui.message(_("Calculating size for {name}, please wait...").format(name=name))

    def folder_worker():
        global _size_calculating
        ticker_stop = threading.Event()

        if mode in ("beep", "both"):
            def ticker_loop():
                while not ticker_stop.is_set() and not _size_cancel_event.is_set():
                    tones.beep(750, 15)
                    if ticker_stop.wait(0.35) or _size_cancel_event.is_set():
                        break

            threading.Thread(target=ticker_loop, daemon=True).start()

        bytes_total = None
        f_cnt = 0
        d_cnt = 0
        try:
            bytes_total, f_cnt, d_cnt = _calculate_folder_stats(target, _size_cancel_event)
        finally:
            ticker_stop.set()
            _size_calculating = False

        if not _size_cancel_event.is_set() and bytes_total is not None:
            res = _("Folder {name}: {size} ({files} files, {dirs} folders)").format(
                name=name, size=format_file_size(bytes_total), files=f_cnt, dirs=d_cnt
            )
            if copy_to_clip:
                api.copyToClip(res)
            wx.CallAfter(_trigger_file_feedback, res, True, copy_to_clip)

    threading.Thread(target=folder_worker, daemon=True).start()


# --- 3. Drives Space Pulse (d and shift+d) ---
def _query_all_drives_space():
    """Queries total and free disk space across ALL physical/logical drives."""
    drives = []
    buf = ctypes.create_unicode_buffer(1024)
    len_ret = kernel32.GetLogicalDriveStringsW(1024, buf)
    if len_ret == 0:
        return []

    raw_str = buf[:len_ret]
    drive_letters = [d for d in raw_str.split("\x00") if d]

    for d in drive_letters:
        free_bytes = ctypes.c_uint64(0)
        total_bytes = ctypes.c_uint64(0)
        total_free = ctypes.c_uint64(0)
        if kernel32.GetDiskFreeSpaceExW(d, ctypes.byref(free_bytes), ctypes.byref(total_bytes), ctypes.byref(total_free)):
            tot = total_bytes.value
            free = free_bytes.value
            pct_free = (free / tot * 100.0) if tot > 0 else 0.0
            drives.append({
                "drive": d.rstrip("\\").rstrip(":"),
                "free_bytes": free,
                "total_bytes": tot,
                "pct_free": pct_free
            })
    return drives


def check_drives_pulse(copy_to_clip=False):
    """Reports full drive metrics (Free, Used, Total) across ALL drives on the computer/server."""
    drives = _query_all_drives_space()
    if not drives:
        _trigger_file_feedback(_("Failed to query drive space"), is_success=False)
        return

    lines = []
    for d in drives:
        free_fmt = format_drive_size(d["free_bytes"])
        tot_fmt = format_drive_size(d["total_bytes"])
        used_bytes = d["total_bytes"] - d["free_bytes"] if d["total_bytes"] >= d["free_bytes"] else 0
        used_fmt = format_drive_size(used_bytes)
        warn = _(" [LOW SPACE]") if d["pct_free"] < 15.0 else ""
        
        lines.append(
            f"{d['drive']}: {free_fmt} free ({d['pct_free']:.0f}%), {used_fmt} used, Total: {tot_fmt}{warn}"
        )

    full_msg = " | ".join(lines)
    if copy_to_clip:
        api.copyToClip("\n".join(lines))

    _trigger_file_feedback(full_msg, is_success=True, is_copy=copy_to_clip)


# --- 4. File Lock Inspector (l and shift+l) ---
def find_locking_processes(file_path):
    """Uses Windows Restart Manager API to identify processes locking a file/folder."""
    session_handle = wintypes.DWORD(0)
    session_key = ctypes.create_unicode_buffer(33)
    if rstrtmgr.RmStartSession(ctypes.byref(session_handle), 0, session_key) != 0:
        return []

    try:
        path_ptr = wintypes.LPCWSTR(file_path)
        path_array = (wintypes.LPCWSTR * 1)(path_ptr)
        if rstrtmgr.RmRegisterResources(session_handle, 1, path_array, 0, None, 0, None) != 0:
            return []

        n_proc_info_needed = wintypes.UINT(0)
        n_proc_info = wintypes.UINT(0)
        reboot_reasons = wintypes.DWORD(0)

        res = rstrtmgr.RmGetList(
            session_handle, ctypes.byref(n_proc_info_needed),
            ctypes.byref(n_proc_info), None, ctypes.byref(reboot_reasons)
        )
        if res == 234 and n_proc_info_needed.value > 0:  # ERROR_MORE_DATA
            count = n_proc_info_needed.value
            proc_array = (RM_PROCESS_INFO * count)()
            n_proc_info.value = count
            if rstrtmgr.RmGetList(
                session_handle, ctypes.byref(n_proc_info_needed),
                ctypes.byref(n_proc_info), ctypes.byref(proc_array), ctypes.byref(reboot_reasons)
            ) == 0:
                lockers = []
                for i in range(n_proc_info.value):
                    p = proc_array[i]
                    app = p.strAppName or _("Unknown Application")
                    svc = p.strServiceShortName or ""
                    lockers.append({
                        "pid": p.Process.dwProcessId,
                        "app_name": app,
                        "service_name": svc,
                        "session_id": p.TSSessionId
                    })
                return lockers
        return []
    finally:
        rstrtmgr.RmEndSession(session_handle)


class FileLockDialog(wx.Dialog):
    """Accessible dialog presenting applications locking a file with termination controls."""

    def __init__(self, parent, target_path, lockers):
        name = os.path.basename(target_path.rstrip("\\/")) or target_path
        super(FileLockDialog, self).__init__(
            parent,
            title=_("Locked File - {name}").format(name=name),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(740, 460)
        )
        self.target_path = target_path
        self.lockers = lockers

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        info_label = wx.StaticText(
            self,
            label=_("The following applications are holding this file. Terminate them to unlock:")
        )
        main_sizer.Add(info_label, 0, wx.ALL, 10)

        self.list_ctrl = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN)
        self.list_ctrl.InsertColumn(0, _("Application"), width=220)
        self.list_ctrl.InsertColumn(1, _("PID"), width=100)
        self.list_ctrl.InsertColumn(2, _("Session"), width=100)
        self.list_ctrl.InsertColumn(3, _("Service Name"), width=240)

        for idx, l in enumerate(self.lockers):
            self.list_ctrl.InsertItem(idx, l["app_name"])
            self.list_ctrl.SetItem(idx, 1, str(l["pid"]))
            self.list_ctrl.SetItem(idx, 2, str(l["session_id"]))
            self.list_ctrl.SetItem(idx, 3, l["service_name"])

        main_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.term_btn = wx.Button(self, label=_("&Terminate Process"))
        self.term_all_btn = wx.Button(self, label=_("Terminate &All"))
        self.copy_btn = wx.Button(self, label=_("Copy &Details"))
        self.close_btn = wx.Button(self, wx.ID_CANCEL, label=_("&Close"))

        btn_sizer.Add(self.term_btn, 0, wx.RIGHT, 6)
        btn_sizer.Add(self.term_all_btn, 0, wx.RIGHT, 6)
        btn_sizer.Add(self.copy_btn, 0, wx.RIGHT, 6)
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(self.close_btn, 0)

        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(main_sizer)

        self.term_btn.Bind(wx.EVT_BUTTON, self.on_term_selected)
        self.term_all_btn.Bind(wx.EVT_BUTTON, self.on_term_all)
        self.copy_btn.Bind(wx.EVT_BUTTON, self.on_copy_details)

        if self.lockers:
            self.list_ctrl.Select(0)
            self.list_ctrl.Focus(0)
        self.CenterOnScreen()

    def on_term_selected(self, event):
        idx = self.list_ctrl.GetFirstSelected()
        if idx == wx.NOT_FOUND:
            return
        l = self.lockers[idx]
        if _kill_process_pid(l["pid"]):
            ui.message(_("Terminated {app} (PID: {pid})").format(app=l["app_name"], pid=l["pid"]))
            self.EndModal(wx.ID_OK)
        else:
            ui.message(_("Failed to terminate process (Admin privileges recommended)"))

    def on_term_all(self, event):
        success = sum(1 for l in self.lockers if _kill_process_pid(l["pid"]))
        ui.message(_("Terminated {s} of {t} locking processes").format(s=success, t=len(self.lockers)))
        self.EndModal(wx.ID_OK)

    def on_copy_details(self, event):
        lines = [f"{l['app_name']} (PID: {l['pid']}) - Session: {l['session_id']}" for l in self.lockers]
        api.copyToClip("\n".join(lines))
        ui.message(_("Locking process details copied to clipboard"))


def inspect_file_lock(copy_to_clip=False):
    """Inspects processes locking the selected file or folder."""
    is_exp, sel_path, folder_path, is_virt, is_sys_icon, loc_title = get_explorer_context()
    if not is_exp:
        _trigger_file_feedback(_("Please select an item in File Explorer to inspect locks"), is_success=False)
        return

    if is_sys_icon:
        _trigger_file_feedback(_("{item} is a system icon and cannot be locked by applications").format(item=loc_title), is_success=False)
        return

    target = sel_path or folder_path
    if not target or (target.startswith("::") and not is_drive_root(target)):
        _trigger_file_feedback(_("Cannot inspect file locks in {loc}. Please select a physical file, folder, or drive").format(loc=loc_title), is_success=False)
        return

    # Resolve .lnk shortcuts to inspect the actual target program or folder
    target = resolve_shortcut_target(target)
    name = os.path.basename(target.rstrip("\\/")) or target

    def lock_worker():
        lockers = find_locking_processes(target)
        if not lockers:
            wx.CallAfter(_trigger_file_feedback, _("{name} is not locked by any application").format(name=name), True, False)
            return

        if copy_to_clip:
            lines = [f"{l['app_name']} (PID: {l['pid']})" for l in lockers]
            res_str = f"Locked: {', '.join(lines)}"
            api.copyToClip(res_str)
            wx.CallAfter(_trigger_file_feedback, res_str, True, True)
            return

        def show_dialog():
            gui_parent = getattr(gui, "mainFrame", None)
            if gui_parent:
                gui_parent.prePopup()
            try:
                dlg = FileLockDialog(gui_parent, target, lockers)
                dlg.ShowModal()
                dlg.Destroy()
            finally:
                if gui_parent:
                    gui_parent.postPopup()

        wx.CallAfter(show_dialog)

    threading.Thread(target=lock_worker, daemon=True).start()


# --- 5. File Checksum & Hash Matcher with Safe Cancellation (c and shift+c) ---
def _calculate_file_hash(file_path, algorithm, cancel_event):
    """Computes file hash via 64KB chunk streaming with safe cancellation support."""
    try:
        h = getattr(hashlib, algorithm, hashlib.sha256)()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                # Check if cancellation was requested during chunk reading
                if cancel_event.is_set():
                    return None
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        log.error("Error reading file for hash: %s" % str(e))
        return None


def calculate_file_checksum(copy_to_clip=False):
    """
    Calculates file checksum, supports toggle cancellation, safe main-thread clipboard
    reading, and strictly respects user's configured feedbackMode.
    """
    global _hash_calculating, _hash_cancel_event

    # Retrieve user-configured feedback mode
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")

    # 1. Toggle Cancellation: If a hash calculation is already in progress, cancel immediately!
    if _hash_calculating:
        _hash_cancel_event.set()
        _hash_calculating = False
        if mode in ("speech", "both"):
            ui.message(_("Checksum computation canceled"))
        if mode in ("beep", "both"):
            tones.beep(400, 40)
        return

    # 2. Resolve Explorer context and focused item
    is_exp, sel_path, folder_path, is_virt, is_sys_icon, loc_title = get_explorer_context()
    if not is_exp:
        _trigger_file_feedback(_("Please open File Explorer to calculate checksum"), is_success=False)
        return

    # Verify that the target is not a system shell icon
    if is_sys_icon:
        _trigger_file_feedback(_("{item} is a system icon and does not have a checksum").format(item=loc_title), is_success=False)
        return

    target = sel_path
    if not target:
        _trigger_file_feedback(_("Please select a physical file to calculate checksum"), is_success=False)
        return

    # 3. Resolve Windows shortcuts (.lnk) to compute hash on the actual target binary
    target = resolve_shortcut_target(target)

    if not os.path.isfile(target):
        _trigger_file_feedback(_("Please select a physical file to calculate checksum"), is_success=False)
        return

    # Retrieve user-selected default hashing algorithm from settings
    algo = config.conf.get("powerBox", {}).get("hashAlgorithm", "sha256")
    name = os.path.basename(target)

    # 4. Safely query clipboard on the MAIN UI thread before dispatching worker to prevent OLE STA crashes
    clip_text = ""
    try:
        clip_text = (api.getClipData() or "").strip().lower()
    except Exception:
        pass

    try:
        file_size = os.path.getsize(target)
    except Exception:
        file_size = 0

    _hash_cancel_event.clear()
    _hash_calculating = True

    # Announce start only for large files (> 10MB) to keep small files instantaneous
    is_large = (file_size > 10 * 1024 * 1024)
    if is_large and mode in ("speech", "both"):
        ui.message(_("Computing {algo} for {name}, please wait...").format(algo=algo.upper(), name=name))

    def hash_worker():
        global _hash_calculating
        ticker_stop = threading.Event()

        # Emit audible pulse ticks for large files during background calculation
        if is_large and mode in ("beep", "both"):
            def ticker_loop():
                while not ticker_stop.is_set() and not _hash_cancel_event.is_set():
                    tones.beep(750, 15)
                    if ticker_stop.wait(0.35) or _hash_cancel_event.is_set():
                        break
            threading.Thread(target=ticker_loop, daemon=True).start()

        computed_hash = None
        try:
            # Stream file data in chunks
            computed_hash = _calculate_file_hash(target, algo, _hash_cancel_event)
        finally:
            ticker_stop.set()
            _hash_calculating = False

        # If operation was canceled by user, exit quietly
        if _hash_cancel_event.is_set():
            return

        # Handle read error or access violation
        if not computed_hash:
            wx.CallAfter(_trigger_file_feedback, _("Failed to compute checksum"), False, False)
            return

        # Compare against safely captured clipboard string (match length and hex validity)
        is_comparing = (len(clip_text) == len(computed_hash) and all(c in "0123456789abcdef" for c in clip_text))

        if is_comparing:
            if clip_text == computed_hash.lower():
                msg = _("HASH MATCH! Authentic {algo}: {h}").format(algo=algo.upper(), h=computed_hash)
            else:
                msg = _("HASH MISMATCH! Computed: {comp} | Expected: {clip}").format(comp=computed_hash, clip=clip_text)
        else:
            # Explicitly inform user whether clipboard held a candidate hash or not
            msg = _("{algo}: {h} (No hash found in clipboard to compare)").format(algo=algo.upper(), h=computed_hash)

        # Copy pure digest to clipboard if copy_to_clip was requested
        if copy_to_clip:
            api.copyToClip(computed_hash)

        # Dispatch feedback to UI thread without baking '(Copied)' into msg text
        wx.CallAfter(_trigger_file_feedback, msg, True, copy_to_clip)

    threading.Thread(target=hash_worker, daemon=True).start()


# --- 6. Instant File Creator / Touch (n) ---
def create_new_file():
    """Presents a clean accessible input dialog to instantly create a file in current folder."""
    is_exp, sel_path, folder_path, is_virt, is_sys_icon, loc_title = get_explorer_context()
    if not is_exp:
        _trigger_file_feedback(_("Please open a folder in File Explorer to create a file"), is_success=False)
        return

    if is_virt or not folder_path or not os.path.isdir(folder_path):
        _trigger_file_feedback(_("Cannot create a file in {loc}. Please open a physical folder").format(loc=loc_title), is_success=False)
        return

    target_dir = folder_path

    def show_input():
        gui_parent = getattr(gui, "mainFrame", None)
        if gui_parent:
            gui_parent.prePopup()
        try:
            prompt_msg = _("Create file in: {dest}\nEnter file name with extension (e.g. notes.txt, script.py):").format(dest=target_dir)
            dlg = wx.TextEntryDialog(
                gui_parent,
                prompt_msg,
                _("Create New File")
            )
            if dlg.ShowModal() == wx.ID_OK:
                file_name = dlg.GetValue().strip()
                if file_name:
                    full_path = os.path.join(target_dir, file_name)
                    if os.path.exists(full_path):
                        ui.message(_("File already exists: {name}").format(name=file_name))
                    else:
                        with open(full_path, "w", encoding="utf-8") as f:
                            pass
                        msg = _("File {name} created successfully").format(name=file_name)
                        _trigger_file_feedback(msg, is_success=True)
            dlg.Destroy()
        finally:
            if gui_parent:
                gui_parent.postPopup()

    wx.CallAfter(show_input)