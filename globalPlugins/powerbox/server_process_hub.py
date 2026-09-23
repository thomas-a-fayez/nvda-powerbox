# -*- coding: utf-8 -*-
# server_process_hub.py - Enterprise Server Process Hub & Session Manager for PowerBox
# (PART 1: Native Win32 Core, WTS Session Querying, and Aggregation Engine)

# Acknowledgment:
# Utilizes native Windows Terminal Services APIs (wtsapi32.dll), Security Account APIs (advapi32.dll),
# Window Management APIs (user32.dll), and Kernel Process APIs (kernel32.dll) to dynamically aggregate
# user applications, multi-session footprints, live CPU usage, client IPs, uptime, and Unicode window titles.

import ctypes
from ctypes import wintypes
import os
import threading
import time
from collections import defaultdict
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

# Win32 Process Access Flags & Constants
WTS_CURRENT_SERVER_HANDLE = wintypes.HANDLE(0).value
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_TERMINATE = 0x0001
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

# WTS Session Information Query Classes
WTSUserName = 5
WTSWinStationName = 6
WTSDomainName = 7
WTSConnectState = 8
WTSClientName = 10
WTSClientAddress = 14

# WTS Session States
WTS_SESSION_STATES = {
    0: _("Active"),
    1: _("Connected"),
    2: _("ConnectQuery"),
    3: _("Shadow"),
    4: _("Disconnected"),
    5: _("Idle"),
    6: _("Listen"),
    7: _("Reset"),
    8: _("Down"),
    9: _("Init"),
}

# Refined OS session helpers & background daemon blacklist
SESSION_INFRASTRUCTURE_BLACKLIST = {
    "dwm.exe", "ctfmon.exe", "rdpclip.exe", "sihost.exe", "taskhostw.exe",
    "fontdrvhost.exe", "logonui.exe", "consent.exe", "shellexperiencehost.exe",
    "searchhost.exe", "startmenuexperiencehost.exe", "textinputhost.exe",
    "runtimebroker.exe", "systemsettings.exe", "lockapp.exe", "rdpinput.exe",
    "csrss.exe", "winlogon.exe", "conhost.exe", "svchost.exe",
    "applicationframehost.exe", "shellhost.exe", "securityhealthsystray.exe",
    # NVDA self-protection
    "nvda.exe", "nvda_synthdriverhost.exe", "nvdahelperremoteloader.exe"
}

# Universal Ghost / Hidden / Message-Only Window Titles Filter
# Excludes internal framework and IME helper windows across all GUI software
GHOST_WINDOW_TITLES = {
    "msctfime ui", "default ime", "wineventwindow", "gdi+ window",
    "firefox media keys", "olemainthreadwndname", "hidden window",
    "dummy window", "system resource monitor", "d3d9 window",
    "battery watcher", "cicero ui wnd frame", "worker window"
}


# Win32 Structures
class FILETIME(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD)
    ]

    def to_uint64(self):
        return (self.dwHighDateTime << 32) | self.dwLowDateTime


class WTS_PROCESS_INFO(ctypes.Structure):
    _fields_ = [
        ("SessionId", wintypes.DWORD),
        ("ProcessId", wintypes.DWORD),
        ("pProcessName", wintypes.LPWSTR),
        ("pUserSid", ctypes.c_void_p),
    ]


class WTS_SESSION_INFO(ctypes.Structure):
    _fields_ = [
        ("SessionId", wintypes.DWORD),
        ("pWinStationName", wintypes.LPWSTR),
        ("State", ctypes.c_int),
    ]


class WTS_CLIENT_ADDRESS(ctypes.Structure):
    _fields_ = [
        ("AddressFamily", wintypes.DWORD),
        ("Address", ctypes.c_ubyte * 20),
    ]


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


# Win32 API Function Bindings
wtsapi32 = ctypes.windll.wtsapi32
advapi32 = ctypes.windll.advapi32
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.windll.user32

WTSEnumerateProcesses = wtsapi32.WTSEnumerateProcessesW
WTSEnumerateProcesses.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
    ctypes.POINTER(ctypes.POINTER(WTS_PROCESS_INFO)),
    ctypes.POINTER(wintypes.DWORD)
]
WTSEnumerateProcesses.restype = wintypes.BOOL

WTSEnumerateSessions = wtsapi32.WTSEnumerateSessionsW
WTSEnumerateSessions.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
    ctypes.POINTER(ctypes.POINTER(WTS_SESSION_INFO)),
    ctypes.POINTER(wintypes.DWORD)
]
WTSEnumerateSessions.restype = wintypes.BOOL

WTSQuerySessionInformation = wtsapi32.WTSQuerySessionInformationW
WTSQuerySessionInformation.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, ctypes.c_int,
    ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.DWORD)
]
WTSQuerySessionInformation.restype = wintypes.BOOL

WTSFreeMemory = wtsapi32.WTSFreeMemory
WTSFreeMemory.argtypes = [ctypes.c_void_p]
WTSFreeMemory.restype = None

WTSDisconnectSession = wtsapi32.WTSDisconnectSession
WTSDisconnectSession.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL]
WTSDisconnectSession.restype = wintypes.BOOL

WTSLogoffSession = wtsapi32.WTSLogoffSession
WTSLogoffSession.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL]
WTSLogoffSession.restype = wintypes.BOOL

LookupAccountSid = advapi32.LookupAccountSidW
LookupAccountSid.argtypes = [
    wintypes.LPCWSTR, ctypes.c_void_p,
    wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
    wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
    ctypes.POINTER(wintypes.DWORD)
]
LookupAccountSid.restype = wintypes.BOOL

OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE

TerminateProcess = kernel32.TerminateProcess
TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
TerminateProcess.restype = wintypes.BOOL

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL

GetProcessTimes = kernel32.GetProcessTimes
GetProcessTimes.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(FILETIME),
    ctypes.POINTER(FILETIME),
    ctypes.POINTER(FILETIME),
    ctypes.POINTER(FILETIME)
]
GetProcessTimes.restype = wintypes.BOOL

QueryFullProcessImageName = kernel32.QueryFullProcessImageNameW
QueryFullProcessImageName.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
QueryFullProcessImageName.restype = wintypes.BOOL

try:
    IsWow64Process = kernel32.IsWow64Process
    IsWow64Process.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
    IsWow64Process.restype = wintypes.BOOL
except AttributeError:
    IsWow64Process = None

try:
    GetProcessMemoryInfo = kernel32.K32GetProcessMemoryInfo
except AttributeError:
    GetProcessMemoryInfo = ctypes.windll.psapi.GetProcessMemoryInfo

GetProcessMemoryInfo.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX),
    wintypes.DWORD
]
GetProcessMemoryInfo.restype = wintypes.BOOL

# Window Enumeration Bindings (Unicode & Arabic support)
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
EnumWindows = user32.EnumWindows
EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
EnumWindows.restype = wintypes.BOOL

GetWindowTextLengthW = user32.GetWindowTextLengthW
GetWindowTextLengthW.argtypes = [wintypes.HWND]
GetWindowTextLengthW.restype = ctypes.c_int

GetWindowTextW = user32.GetWindowTextW
GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
GetWindowTextW.restype = ctypes.c_int

GetWindowThreadProcessId = user32.GetWindowThreadProcessId
GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
GetWindowThreadProcessId.restype = wintypes.DWORD


def _trigger_hub_feedback(msg, is_success=True):
    """Provides user feedback respecting user's configured feedbackMode."""
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")

    if mode in ("beep", "both"):
        if is_success:
            tones.beep(850, 40)
        else:
            tones.beep(250, 60)

    if mode in ("speech", "both"):
        ui.message(msg)


def _format_ram(mb):
    """Formats RAM into human-friendly string."""
    if mb >= 1024.0:
        return _("{val:.1f} GB").format(val=mb / 1024.0)
    return _("{val:.0f} MB").format(val=mb)


def _format_uptime(seconds):
    """Formats uptime seconds into readable duration."""
    if seconds < 60:
        return _("{s} seconds").format(s=int(seconds))
    mins = int(seconds // 60)
    hours = int(mins // 60)
    days = int(hours // 24)
    if days > 0:
        return _("{d}d {h}h").format(d=days, h=hours % 24)
    if hours > 0:
        return _("{h}h {m}m").format(h=hours, m=mins % 60)
    return _("{m} minutes").format(m=mins)


def _resolve_sid_to_username(pUserSid, sid_cache):
    """Converts a binary user SID into DOMAIN\\Username using memory caching."""
    if not pUserSid:
        return _("SYSTEM / Service")

    if pUserSid in sid_cache:
        return sid_cache[pUserSid]

    name_buf = ctypes.create_unicode_buffer(256)
    name_len = wintypes.DWORD(256)
    dom_buf = ctypes.create_unicode_buffer(256)
    dom_len = wintypes.DWORD(256)
    sid_type = wintypes.DWORD()

    if LookupAccountSid(None, pUserSid, name_buf, ctypes.byref(name_len), dom_buf, ctypes.byref(dom_len), ctypes.byref(sid_type)):
        account = f"{dom_buf.value}\\{name_buf.value}" if dom_buf.value else name_buf.value
    else:
        account = _("Unknown User")

    sid_cache[pUserSid] = account
    return account


def _query_session_client_info(session_id):
    """Queries client machine name and IP address using WTSQuerySessionInformation."""
    client_name = ""
    client_ip = ""

    # Query Client Name
    p_buf = ctypes.c_void_p()
    bytes_ret = wintypes.DWORD()
    if WTSQuerySessionInformation(WTS_CURRENT_SERVER_HANDLE, session_id, WTSClientName, ctypes.byref(p_buf), ctypes.byref(bytes_ret)):
        try:
            if p_buf.value:
                client_name = ctypes.wstring_at(p_buf.value)
        finally:
            WTSFreeMemory(p_buf)

    # Query Client IP Address
    p_buf = ctypes.c_void_p()
    bytes_ret = wintypes.DWORD()
    if WTSQuerySessionInformation(WTS_CURRENT_SERVER_HANDLE, session_id, WTSClientAddress, ctypes.byref(p_buf), ctypes.byref(bytes_ret)):
        try:
            if p_buf.value:
                addr = ctypes.cast(p_buf, ctypes.POINTER(WTS_CLIENT_ADDRESS)).contents
                # AddressFamily == 2 corresponds to AF_INET (IPv4)
                if addr.AddressFamily == 2:
                    raw_ip = addr.Address[2:6]
                    client_ip = f"{raw_ip[0]}.{raw_ip[1]}.{raw_ip[2]}.{raw_ip[3]}"
        finally:
            WTSFreeMemory(p_buf)

    if client_ip and client_name:
        return f"{client_name} ({client_ip})"
    elif client_name:
        return client_name
    elif client_ip:
        return client_ip
    return _("Console / Local")


def _get_process_memory_details(pid):
    """Safely queries working set and peak working set in MB for a specific PID."""
    h_proc = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h_proc or h_proc == INVALID_HANDLE_VALUE:
        return 0.0, 0.0

    try:
        counters = PROCESS_MEMORY_COUNTERS_EX()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
        if GetProcessMemoryInfo(h_proc, ctypes.byref(counters), counters.cb):
            ram = counters.WorkingSetSize / (1024.0 * 1024.0)
            peak = counters.PeakWorkingSetSize / (1024.0 * 1024.0)
            return ram, peak
    except Exception:
        pass
    finally:
        CloseHandle(h_proc)
    return 0.0, 0.0


def _get_process_extended_info(pid):
    """Retrieves executable path, architecture, and uptime for a given PID."""
    h_proc = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h_proc or h_proc == INVALID_HANDLE_VALUE:
        return _("Access Denied / Protected"), _("Unknown"), 0.0

    path = _("Not available")
    arch = _("64-bit")
    uptime_sec = 0.0

    try:
        # Path
        path_buf = ctypes.create_unicode_buffer(1024)
        buf_size = wintypes.DWORD(1024)
        if QueryFullProcessImageName(h_proc, 0, path_buf, ctypes.byref(buf_size)):
            path = path_buf.value

        # Architecture
        if IsWow64Process:
            is_wow64 = wintypes.BOOL()
            if IsWow64Process(h_proc, ctypes.byref(is_wow64)):
                arch = _("32-bit (WoW64)") if is_wow64.value else _("64-bit")

        # Uptime
        creation_time = FILETIME()
        exit_time = FILETIME()
        kernel_time = FILETIME()
        user_time = FILETIME()
        if GetProcessTimes(h_proc, ctypes.byref(creation_time), ctypes.byref(exit_time), ctypes.byref(kernel_time), ctypes.byref(user_time)):
            ft = creation_time.to_uint64()
            if ft > 0:
                posix_start = (ft - 116444736000000000) / 10000000.0
                uptime_sec = max(0.0, time.time() - posix_start)

    except Exception as e:
        log.debug("Error getting process extended info: %s" % str(e))
    finally:
        CloseHandle(h_proc)

    return path, arch, uptime_sec


def _get_app_window_titles(target_pids):
    """
    Collects visible, minimized, and background window titles matching target PIDs.
    Filters out ghost/helper windows and preserves Unicode & Arabic titles with zero corruption.
    """
    titles = []
    pid_set = set(target_pids)

    def enum_proc(hwnd, lparam):
        pid = wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pid_set:
            length = GetWindowTextLengthW(hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                GetWindowTextW(hwnd, buffer, length + 1)
                title = buffer.value.strip()
                if title and title.lower() not in GHOST_WINDOW_TITLES and title not in titles:
                    titles.append(title)
        return True

    EnumWindows(WNDENUMPROC(enum_proc), 0)
    return titles


def _measure_pids_cpu(pids, sample_interval=0.25):
    """Calculates combined CPU% usage across target PIDs."""
    if not pids:
        return 0.0

    creation_time = FILETIME()
    exit_time = FILETIME()
    handles = []

    for pid in pids:
        h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if h and h != INVALID_HANDLE_VALUE:
            handles.append(h)

    if not handles:
        return 0.0

    try:
        sample1 = {}
        for h in handles:
            k = FILETIME()
            u = FILETIME()
            if GetProcessTimes(h, ctypes.byref(creation_time), ctypes.byref(exit_time), ctypes.byref(k), ctypes.byref(u)):
                sample1[h] = (k.to_uint64(), u.to_uint64())

        t1 = time.perf_counter()
        time.sleep(sample_interval)
        t2 = time.perf_counter()
        wall_delta = t2 - t1

        total_proc_delta = 0
        for h in handles:
            if h in sample1:
                k = FILETIME()
                u = FILETIME()
                if GetProcessTimes(h, ctypes.byref(creation_time), ctypes.byref(exit_time), ctypes.byref(k), ctypes.byref(u)):
                    proc_k_delta = k.to_uint64() - sample1[h][0]
                    proc_u_delta = u.to_uint64() - sample1[h][1]
                    total_proc_delta += (proc_k_delta + proc_u_delta)

        proc_seconds = total_proc_delta / 10000000.0
        num_cores = os.cpu_count() or 1
        cpu_pct = 0.0
        if wall_delta > 0:
            cpu_pct = (proc_seconds / wall_delta) * 100.0 / num_cores
        return min(100.0, max(0.0, cpu_pct))

    finally:
        for h in handles:
            CloseHandle(h)


def _kill_process_pid(pid):
    """Terminates a single process PID cleanly."""
    h_proc = OpenProcess(PROCESS_TERMINATE, False, pid)
    if not h_proc or h_proc == INVALID_HANDLE_VALUE:
        return False
    try:
        return bool(TerminateProcess(h_proc, 1))
    finally:
        CloseHandle(h_proc)


def collect_server_process_data():
    """
    Scans sessions and processes across the entire machine/server.
    Executes a high-speed global CPU snapshot across all processes in a single 250ms pass.
    """
    sessions_map = {}
    p_session_info = ctypes.POINTER(WTS_SESSION_INFO)()
    session_count = wintypes.DWORD(0)

    if WTSEnumerateSessions(WTS_CURRENT_SERVER_HANDLE, 0, 1, ctypes.byref(p_session_info), ctypes.byref(session_count)):
        try:
            for i in range(session_count.value):
                s = p_session_info[i]
                sid = s.SessionId
                state_str = WTS_SESSION_STATES.get(s.State, _("Unknown"))
                client_desc = _query_session_client_info(sid)
                sessions_map[sid] = {
                    "session_id": sid,
                    "state": state_str,
                    "client": client_desc,
                    "user": _("Unknown User"),
                    "ram_mb": 0.0,
                    "pids_count": 0
                }
        finally:
            WTSFreeMemory(p_session_info)

    p_proc_info = ctypes.POINTER(WTS_PROCESS_INFO)()
    proc_count = wintypes.DWORD(0)

    if not WTSEnumerateProcesses(WTS_CURRENT_SERVER_HANDLE, 0, 1, ctypes.byref(p_proc_info), ctypes.byref(proc_count)):
        return None, list(sessions_map.values())

    sid_cache = {}
    raw_processes = []
    pid_to_handle = {}
    sample1 = {}
    creation_time = FILETIME()
    exit_time = FILETIME()

    try:
        for i in range(proc_count.value):
            p = p_proc_info[i]
            session_id = p.SessionId
            pid = p.ProcessId
            proc_name = p.pProcessName or ""
            proc_lower = proc_name.lower()

            if session_id == 0 or proc_lower in SESSION_INFRASTRUCTURE_BLACKLIST:
                continue

            username = _resolve_sid_to_username(p.pUserSid, sid_cache)
            # Exclude driver containers and background services running as SYSTEM
            if username == _("SYSTEM / Service"):
                continue

            # Exclude Windows 11 internal component tasks located in SystemApps
            exe_path = _get_process_extended_info(pid)[0].lower()
            if "systemapps" in exe_path:
                continue

            raw_processes.append((proc_lower, proc_name, session_id, pid, username))

            # Associate primary user with session
            if session_id in sessions_map and sessions_map[session_id]["user"] == _("Unknown User") and username != _("SYSTEM / Service"):
                sessions_map[session_id]["user"] = username

            # Open handle for CPU measurement
            h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if h and h != INVALID_HANDLE_VALUE:
                pid_to_handle[pid] = h
                k = FILETIME()
                u = FILETIME()
                if GetProcessTimes(h, ctypes.byref(creation_time), ctypes.byref(exit_time), ctypes.byref(k), ctypes.byref(u)):
                    sample1[pid] = (k.to_uint64(), u.to_uint64())

        # Global 250ms interval for all processes simultaneously
        t1 = time.perf_counter()
        time.sleep(0.25)
        t2 = time.perf_counter()
        wall_delta = t2 - t1
        num_cores = os.cpu_count() or 1

        pid_cpu = {}
        for pid, h in pid_to_handle.items():
            if pid in sample1:
                k = FILETIME()
                u = FILETIME()
                if GetProcessTimes(h, ctypes.byref(creation_time), ctypes.byref(exit_time), ctypes.byref(k), ctypes.byref(u)):
                    proc_k_delta = k.to_uint64() - sample1[pid][0]
                    proc_u_delta = u.to_uint64() - sample1[pid][1]
                    proc_sec = (proc_k_delta + proc_u_delta) / 10000000.0
                    pct = 0.0
                    if wall_delta > 0:
                        pct = (proc_sec / wall_delta) * 100.0 / num_cores
                    pid_cpu[pid] = min(100.0, max(0.0, pct))
                CloseHandle(h)

    finally:
        WTSFreeMemory(p_proc_info)
        for pid, h in pid_to_handle.items():
            try:
                CloseHandle(h)
            except Exception:
                pass

    # Pass 2: Aggregate by application name and by session
    apps_data = defaultdict(lambda: {
        "app_name": "",
        "total_ram": 0.0,
        "total_peak_ram": 0.0,
        "total_cpu": 0.0,
        "users": defaultdict(lambda: {
            "user_name": "",
            "session_id": 0,
            "session_state": "",
            "ram_mb": 0.0,
            "cpu_pct": 0.0,
            "pids": []
        })
    })

    for proc_lower, proc_name, session_id, pid, username in raw_processes:
        ram_mb, peak_mb = _get_process_memory_details(pid)
        cpu = pid_cpu.get(pid, 0.0)
        state_str = sessions_map.get(session_id, {}).get("state", _("Active"))

        # Add to session totals
        if session_id in sessions_map:
            sessions_map[session_id]["ram_mb"] += ram_mb
            sessions_map[session_id]["pids_count"] += 1

        app_bucket = apps_data[proc_lower]
        app_bucket["app_name"] = proc_name
        app_bucket["total_ram"] += ram_mb
        app_bucket["total_peak_ram"] += peak_mb
        app_bucket["total_cpu"] += cpu

        user_bucket = app_bucket["users"][(username, session_id)]
        user_bucket["user_name"] = username
        user_bucket["session_id"] = session_id
        user_bucket["session_state"] = state_str
        user_bucket["ram_mb"] += ram_mb
        user_bucket["cpu_pct"] += cpu
        user_bucket["pids"].append(pid)

    processed_apps = []
    for proc_lower, data in apps_data.items():
        users_list = list(data["users"].values())
        users_list.sort(key=lambda u: u["ram_mb"], reverse=True)
        top_user = users_list[0] if users_list else None

        all_pids = []
        for u in users_list:
            all_pids.extend(u["pids"])

        processed_apps.append({
            "app_name": data["app_name"],
            "total_ram": data["total_ram"],
            "total_peak_ram": data["total_peak_ram"],
            "total_cpu": data["total_cpu"],
            "users_count": len(users_list),
            "top_user_name": top_user["user_name"] if top_user else "-",
            "top_user_ram": top_user["ram_mb"] if top_user else 0.0,
            "all_pids": all_pids,
            "users": users_list
        })

    processed_apps.sort(key=lambda a: a["total_ram"], reverse=True)
    
    # Filter sessions to non-zero interactive sessions
    sessions_list = [s for s in sessions_map.values() if s["session_id"] != 0]
    sessions_list.sort(key=lambda s: s["ram_mb"], reverse=True)

    return processed_apps, sessions_list


# (PART 2: Accessible Dialogs, Global Sessions Dashboard, and Interaction Controller)


# --- Accessible Application Details Dialog ---
class AppDetailsDialog(wx.Dialog):
    """
    Exhaustive details window presenting live recalculated CPU%, executable path,
    process architecture, uptime, and clean Arabic/Unicode window titles.
    """

    def __init__(self, parent, app_data):
        super(AppDetailsDialog, self).__init__(
            parent,
            title=_("Application Details - {app}").format(app=app_data["app_name"]),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(780, 540),
        )

        self.app_data = app_data
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.text_ctrl = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        )
        ui_font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        ui_font.SetPointSize(10)
        self.text_ctrl.SetFont(ui_font)

        main_sizer.Add(self.text_ctrl, 1, wx.EXPAND | wx.ALL, 12)

        # Action Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.copy_btn = wx.Button(self, label=_("Copy &Details"))
        self.close_btn = wx.Button(self, wx.ID_CANCEL, label=_("&Close"))

        btn_sizer.Add(self.copy_btn, 0, wx.RIGHT, 8)
        btn_sizer.Add(self.close_btn, 0)
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 12)

        self.SetSizer(main_sizer)
        self.CenterOnScreen()

        self.copy_btn.Bind(wx.EVT_BUTTON, self.on_copy)
        self.text_ctrl.SetValue(_("Recalculating live CPU usage, uptime, and window titles, please wait..."))

        threading.Thread(target=self._generate_fresh_report, daemon=True).start()

    def _generate_fresh_report(self):
        app = self.app_data
        pids = app["all_pids"]

        # 1. Fresh live CPU recalculation
        fresh_cpu = _measure_pids_cpu(pids, sample_interval=0.3)

        # 2. Fresh RAM recalculation
        fresh_ram = sum(_get_process_memory_details(p)[0] for p in pids)
        fresh_peak = sum(_get_process_memory_details(p)[1] for p in pids)

        # 3. Path, Architecture, Uptime (from primary PID)
        sample_pid = pids[0] if pids else 0
        exe_path, arch, uptime_sec = _get_process_extended_info(sample_pid)

        # 4. Visible & background window titles (Filtered and Arabic compliant)
        window_titles = _get_app_window_titles(pids)

        report_lines = [
            _("=== Application Details Report ==="),
            _("Application: {app}").format(app=app["app_name"]),
            _("Binary Path: {path}").format(path=exe_path),
            _("Architecture: {arch}").format(arch=arch),
            _("Process Uptime: {uptime}").format(uptime=_format_uptime(uptime_sec)),
            _("Active Users Count: {cnt}").format(cnt=app["users_count"]),
            _("Running Processes (PIDs): {cnt}").format(cnt=len(pids)),
            _("Live CPU Usage: {cpu:.1f}%").format(cpu=fresh_cpu),
            _("Total Working Set RAM: {ram}").format(ram=_format_ram(fresh_ram)),
            _("Peak Working Set RAM: {ram}").format(ram=_format_ram(fresh_peak)),
            "",
            _("--- Open Windows & Tabs Titles ({count}) ---").format(count=len(window_titles)),
        ]

        if window_titles:
            for idx, title in enumerate(window_titles, 1):
                report_lines.append(f"  {idx}. {title}")
        else:
            report_lines.append(_("  (No interactive windows found)"))

        report_lines.append("")
        report_lines.append(_("--- User Accounts Breakdown ---"))

        for u in app["users"]:
            report_lines.append(
                f"• {u['user_name']} | Session: {u['session_id']} ({u['session_state']}) | "
                f"RAM: {_format_ram(u['ram_mb'])} | CPU: {u['cpu_pct']:.1f}% | PIDs: {len(u['pids'])}"
            )

        report_lines.append("")
        report_lines.append(_("Process IDs (PIDs): ") + ", ".join(str(p) for p in pids))

        final_text = "\n".join(report_lines)
        wx.CallAfter(self._update_text, final_text)

    def _update_text(self, text):
        self.text_ctrl.SetValue(text)
        self.text_ctrl.SetFocus()

    def on_copy(self, event):
        api.copyToClip(self.text_ctrl.GetValue())
        _trigger_hub_feedback(_("Application details copied to clipboard"), is_success=True)


# --- Enterprise Server Process & Session Management Console ---
class ServerProcessHubDialog(wx.Dialog):
    """
    Enterprise management console supporting Applications Overview,
    User Drill-Down, and Global Sessions Management with full RemoteApp compatibility.
    """

    VIEW_APPS = 0
    VIEW_USERS = 1
    VIEW_SESSIONS = 2

    def __init__(self, parent):
        super(ServerProcessHubDialog, self).__init__(
            parent,
            title=_("Server Process Hub - Enterprise Manager"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )

        self.current_view = self.VIEW_APPS
        self.apps_data = []
        self.sessions_list = []
        self.selected_app = None
        self.filtered_apps = []

        # Responsive Dialog Sizing (78% of active monitor work area)
        display_rect = wx.Display().GetClientArea()
        dialog_width = max(960, int(display_rect.width * 0.78))
        dialog_height = max(620, int(display_rect.height * 0.78))
        self.SetSize((dialog_width, dialog_height))
        self.SetMinSize((880, 520))

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 1. Header Server Health Status
        self.status_label = wx.StaticText(self, label=_("Scanning server sessions and processes..."))
        font_header = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font_header.SetWeight(wx.FONTWEIGHT_BOLD)
        self.status_label.SetFont(font_header)
        main_sizer.Add(self.status_label, 0, wx.ALL | wx.EXPAND, 12)

        # 2. Live Search & Filter Bar
        search_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.search_title = wx.StaticText(self, label=_("&Filter Application:"))
        self.search_ctrl = wx.TextCtrl(self)
        search_sizer.Add(self.search_title, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        search_sizer.Add(self.search_ctrl, 1, wx.EXPAND)
        main_sizer.Add(search_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # 3. Accessible Multi-column ListCtrl
        self.list_ctrl = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN
        )
        main_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # 4. Action Buttons Sizer
        self.btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.action_btn1 = wx.Button(self, label=_("&View Users (Enter)"))
        self.details_btn = wx.Button(self, label=_("&Details..."))
        self.switch_mode_btn = wx.Button(self, label=_("&All Sessions (F6)"))
        self.action_btn2 = wx.Button(self, label=_("&End App Across Server"))
        self.copy_btn = wx.Button(self, label=_("Copy &Report"))
        self.refresh_btn = wx.Button(self, label=_("Re&fresh (F5)"))
        self.close_btn = wx.Button(self, label=_("&Close (Esc)"))

        self.btn_sizer.Add(self.action_btn1, 0, wx.RIGHT, 6)
        self.btn_sizer.Add(self.details_btn, 0, wx.RIGHT, 6)
        self.btn_sizer.Add(self.switch_mode_btn, 0, wx.RIGHT, 6)
        self.btn_sizer.Add(self.action_btn2, 0, wx.RIGHT, 6)
        self.btn_sizer.Add(self.copy_btn, 0, wx.RIGHT, 6)
        self.btn_sizer.Add(self.refresh_btn, 0, wx.RIGHT, 6)
        self.btn_sizer.AddStretchSpacer()
        self.btn_sizer.Add(self.close_btn, 0)

        main_sizer.Add(self.btn_sizer, 0, wx.EXPAND | wx.ALL, 12)
        self.SetSizer(main_sizer)

        # Global Key Interceptors (Backspace for Back, Esc for Close, F6 for Switch View)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        self.Bind(wx.EVT_SIZE, self.on_dialog_resize)

        # Search Control Navigation: Down Arrow smoothly moves to list without focus stealing
        self.search_ctrl.Bind(wx.EVT_TEXT, self.on_filter_changed)
        self.search_ctrl.Bind(wx.EVT_KEY_DOWN, self.on_search_key_down)

        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated)
        self.list_ctrl.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)

        self.action_btn1.Bind(wx.EVT_BUTTON, self.on_primary_action)
        self.details_btn.Bind(wx.EVT_BUTTON, self.on_show_details)
        self.switch_mode_btn.Bind(wx.EVT_BUTTON, self.on_toggle_sessions_mode)
        self.action_btn2.Bind(wx.EVT_BUTTON, self.on_secondary_action)
        self.copy_btn.Bind(wx.EVT_BUTTON, self.on_copy_action)
        self.refresh_btn.Bind(wx.EVT_BUTTON, self.on_refresh)
        self.close_btn.Bind(wx.EVT_BUTTON, lambda evt: self.EndModal(wx.ID_CANCEL))

        self.CenterOnScreen()
        self.start_async_data_load()

    def on_search_key_down(self, event):
        """Allows user to press Down Arrow inside search box to move focus to the list."""
        if event.GetKeyCode() == wx.WXK_DOWN:
            self.list_ctrl.SetFocus()
            if self.filtered_apps:
                self.list_ctrl.Select(0)
                self.list_ctrl.Focus(0)
            return
        event.Skip()

    def on_dialog_resize(self, event):
        """Maintains proportional column expansion on window resize."""
        event.Skip()
        wx.CallAfter(self._adjust_column_widths)

    def _adjust_column_widths(self):
        """Calculates dynamic column widths preventing text cramping."""
        client_width = self.list_ctrl.GetClientSize().width - 25
        if client_width <= 0:
            return

        if self.current_view == self.VIEW_APPS:
            self.list_ctrl.SetColumnWidth(0, int(client_width * 0.25))  # Application
            self.list_ctrl.SetColumnWidth(1, int(client_width * 0.16))  # Total RAM
            self.list_ctrl.SetColumnWidth(2, int(client_width * 0.14))  # Total CPU
            self.list_ctrl.SetColumnWidth(3, int(client_width * 0.13))  # Users
            self.list_ctrl.SetColumnWidth(4, int(client_width * 0.32))  # Top Consumer
        elif self.current_view == self.VIEW_USERS:
            self.list_ctrl.SetColumnWidth(0, int(client_width * 0.34))  # User Account
            self.list_ctrl.SetColumnWidth(1, int(client_width * 0.18))  # Session ID
            self.list_ctrl.SetColumnWidth(2, int(client_width * 0.22))  # Session State
            self.list_ctrl.SetColumnWidth(3, int(client_width * 0.26))  # User RAM
        elif self.current_view == self.VIEW_SESSIONS:
            self.list_ctrl.SetColumnWidth(0, int(client_width * 0.28))  # User Account
            self.list_ctrl.SetColumnWidth(1, int(client_width * 0.14))  # Session ID
            self.list_ctrl.SetColumnWidth(2, int(client_width * 0.18))  # Session State
            self.list_ctrl.SetColumnWidth(3, int(client_width * 0.22))  # Client IP / Machine
            self.list_ctrl.SetColumnWidth(4, int(client_width * 0.18))  # Total Session RAM

    def on_char_hook(self, event):
        """Global key interceptor guaranteeing Backspace returns, F6 toggles, and Esc exits."""
        key = event.GetKeyCode()
        if key == wx.WXK_BACK:
            # Let backspace delete text when search control has focus
            if wx.Window.FindFocus() == self.search_ctrl:
                event.Skip()
                return

            if self.current_view == self.VIEW_USERS:
                self.show_apps_view(set_focus=True)
                return

        elif key == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
            return
        elif key == wx.WXK_F5:
            self.on_refresh()
            return
        elif key == wx.WXK_F6:
            self.on_toggle_sessions_mode(None)
            return

        event.Skip()

    def start_async_data_load(self):
        """Asynchronously queries the system so UI never freezes."""
        self.status_label.SetLabel(_("Refreshing server metrics (RAM, CPU, and Sessions), please wait..."))

        def worker():
            apps, sessions = collect_server_process_data()
            wx.CallAfter(self._on_data_loaded, apps, sessions)

        threading.Thread(target=worker, daemon=True).start()

    def _on_data_loaded(self, apps, sessions):
        if apps is None:
            self.status_label.SetLabel(_("Failed to query Terminal Services. Administrator privileges recommended."))
            return

        self.apps_data = apps
        self.sessions_list = sessions

        if self.current_view == self.VIEW_SESSIONS:
            self.show_sessions_view(set_focus=True)
        else:
            self.show_apps_view(set_focus=True)

    def show_apps_view(self, set_focus=True):
        """Builds and displays the clean 5-column Applications view."""
        self.current_view = self.VIEW_APPS
        self.search_ctrl.Enable(True)
        self.search_title.SetLabel(_("&Filter Application:"))
        self.action_btn1.SetLabel(_("&View Users (Enter)"))
        self.action_btn1.Enable(True)
        self.details_btn.Enable(True)
        self.switch_mode_btn.SetLabel(_("&All Sessions (F6)"))
        self.action_btn2.SetLabel(_("&End App Across Server"))
        self.action_btn2.Enable(True)

        active_s = sum(1 for s in self.sessions_list if s["state"] == _("Active"))
        disc_s = sum(1 for s in self.sessions_list if s["state"] == _("Disconnected"))
        total_ram = sum(a["total_ram"] for a in self.apps_data)

        self.status_label.SetLabel(
            _("Server Pulse: {act} Active, {disc} Disconnected Sessions | {apps} User Apps ({ram})").format(
                act=active_s, disc=disc_s, apps=len(self.apps_data), ram=_format_ram(total_ram)
            )
        )

        self.list_ctrl.ClearAll()
        self.list_ctrl.InsertColumn(0, _("Application"))
        self.list_ctrl.InsertColumn(1, _("Total RAM"))
        self.list_ctrl.InsertColumn(2, _("Total CPU"))
        self.list_ctrl.InsertColumn(3, _("Active Users"))
        self.list_ctrl.InsertColumn(4, _("Top Consumer"))

        filter_text = self.search_ctrl.GetValue().strip().lower()
        if filter_text:
            self.filtered_apps = [a for a in self.apps_data if filter_text in a["app_name"].lower()]
        else:
            self.filtered_apps = self.apps_data

        for idx, app in enumerate(self.filtered_apps):
            self.list_ctrl.InsertItem(idx, app["app_name"])
            self.list_ctrl.SetItem(idx, 1, _format_ram(app["total_ram"]))
            self.list_ctrl.SetItem(idx, 2, f"{app['total_cpu']:.1f}%")
            self.list_ctrl.SetItem(idx, 3, str(app["users_count"]))
            top_desc = f"{app['top_user_name']} ({_format_ram(app['top_user_ram'])})"
            self.list_ctrl.SetItem(idx, 4, top_desc)

        self._adjust_column_widths()

        if set_focus:
            if self.filtered_apps:
                self.list_ctrl.Select(0)
                self.list_ctrl.Focus(0)
            self.list_ctrl.SetFocus()

    def show_users_view(self, app):
        """Builds and displays the User Drill-Down level for a specific application."""
        self.current_view = self.VIEW_USERS
        self.selected_app = app
        self.search_ctrl.Enable(False)

        self.action_btn1.SetLabel(_("&End Process for User"))
        self.action_btn1.Enable(True)
        self.details_btn.Enable(False)
        self.switch_mode_btn.SetLabel(_("&All Sessions (F6)"))
        self.action_btn2.SetLabel(_("&Back to Apps (Backspace)"))
        self.action_btn2.Enable(True)

        self.status_label.SetLabel(
            _("Application: {app} | Total RAM: {ram} | CPU: {cpu:.1f}% | Active across {count} users").format(
                app=app["app_name"], ram=_format_ram(app["total_ram"]), cpu=app["total_cpu"], count=len(app["users"])
            )
        )

        self.list_ctrl.ClearAll()
        self.list_ctrl.InsertColumn(0, _("User Account"))
        self.list_ctrl.InsertColumn(1, _("Session ID"))
        self.list_ctrl.InsertColumn(2, _("Session State"))
        self.list_ctrl.InsertColumn(3, _("User RAM"))

        for idx, u in enumerate(app["users"]):
            self.list_ctrl.InsertItem(idx, u["user_name"])
            self.list_ctrl.SetItem(idx, 1, str(u["session_id"]))
            self.list_ctrl.SetItem(idx, 2, u["session_state"])
            self.list_ctrl.SetItem(idx, 3, _format_ram(u["ram_mb"]))

        self._adjust_column_widths()

        if app["users"]:
            self.list_ctrl.Select(0)
            self.list_ctrl.Focus(0)
        self.list_ctrl.SetFocus()

    def show_sessions_view(self, set_focus=True):
        """Builds and displays the Global Sessions Management Dashboard."""
        self.current_view = self.VIEW_SESSIONS
        self.search_ctrl.Enable(False)

        self.action_btn1.SetLabel(_("&Logoff Session"))
        self.action_btn1.Enable(True)
        self.details_btn.Enable(False)
        self.switch_mode_btn.SetLabel(_("&View Apps (F6)"))
        self.action_btn2.SetLabel(_("&Disconnect Session"))
        self.action_btn2.Enable(True)

        active_s = sum(1 for s in self.sessions_list if s["state"] == _("Active"))
        disc_s = sum(1 for s in self.sessions_list if s["state"] == _("Disconnected"))
        total_session_ram = sum(s["ram_mb"] for s in self.sessions_list)

        self.status_label.SetLabel(
            _("All Server Sessions: {total} Sessions ({act} Active, {disc} Disconnected) | RAM: {ram}").format(
                total=len(self.sessions_list), act=active_s, disc=disc_s, ram=_format_ram(total_session_ram)
            )
        )

        self.list_ctrl.ClearAll()
        self.list_ctrl.InsertColumn(0, _("User Account"))
        self.list_ctrl.InsertColumn(1, _("Session ID"))
        self.list_ctrl.InsertColumn(2, _("Session State"))
        self.list_ctrl.InsertColumn(3, _("Client IP / Machine"))
        self.list_ctrl.InsertColumn(4, _("Total Session RAM"))

        for idx, s in enumerate(self.sessions_list):
            self.list_ctrl.InsertItem(idx, s["user"])
            self.list_ctrl.SetItem(idx, 1, str(s["session_id"]))
            self.list_ctrl.SetItem(idx, 2, s["state"])
            self.list_ctrl.SetItem(idx, 3, s["client"])
            self.list_ctrl.SetItem(idx, 4, _format_ram(s["ram_mb"]))

        self._adjust_column_widths()

        if set_focus:
            if self.sessions_list:
                self.list_ctrl.Select(0)
                self.list_ctrl.Focus(0)
            self.list_ctrl.SetFocus()

    def on_toggle_sessions_mode(self, event):
        """Toggles between Applications View and Global Sessions View (F6)."""
        if self.current_view == self.VIEW_SESSIONS:
            self.show_apps_view(set_focus=True)
        else:
            self.show_sessions_view(set_focus=True)

    def get_selected_item_data(self):
        idx = self.list_ctrl.GetFirstSelected()
        if idx == wx.NOT_FOUND:
            return None
        if self.current_view == self.VIEW_APPS:
            return self.filtered_apps[idx] if idx < len(self.filtered_apps) else None
        elif self.current_view == self.VIEW_USERS:
            return self.selected_app["users"][idx] if (self.selected_app and idx < len(self.selected_app["users"])) else None
        else:
            return self.sessions_list[idx] if idx < len(self.sessions_list) else None

    def on_filter_changed(self, event):
        """Filters list in real-time while strictly keeping keyboard focus inside the text box."""
        if self.current_view == self.VIEW_APPS:
            self.show_apps_view(set_focus=False)

    def on_item_activated(self, event):
        if self.current_view == self.VIEW_APPS:
            app = self.get_selected_item_data()
            if app:
                self.show_users_view(app)
        elif self.current_view == self.VIEW_USERS:
            self.on_kill_user_process()
        else:
            self.on_logoff_session()

    def on_primary_action(self, event):
        if self.current_view == self.VIEW_APPS:
            app = self.get_selected_item_data()
            if app:
                self.show_users_view(app)
        elif self.current_view == self.VIEW_USERS:
            self.on_kill_user_process()
        else:
            self.on_logoff_session()

    def on_show_details(self, event):
        app = self.get_selected_item_data()
        if not app or self.current_view != self.VIEW_APPS:
            return
        gui_parent = getattr(gui, "mainFrame", None)
        if gui_parent:
            gui_parent.prePopup()
        try:
            dlg = AppDetailsDialog(self, app)
            dlg.ShowModal()
            dlg.Destroy()
        finally:
            if gui_parent:
                gui_parent.postPopup()

    def on_secondary_action(self, event):
        if self.current_view == self.VIEW_APPS:
            self.on_kill_all_app_instances()
        elif self.current_view == self.VIEW_USERS:
            self.show_apps_view(set_focus=True)
        else:
            self.on_disconnect_session()

    def on_refresh(self, event=None):
        self.start_async_data_load()

    def on_kill_user_process(self):
        user_data = self.get_selected_item_data()
        if not user_data:
            return

        user_name = user_data["user_name"]
        app_name = self.selected_app["app_name"]
        pids = user_data["pids"]

        msg = _("Are you sure you want to end {app} for user {user} ({count} instances)?").format(
            app=app_name, user=user_name, count=len(pids)
        )
        if gui.messageBox(msg, _("Confirm Terminate Application"), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, self) != wx.YES:
            return

        success_count = sum(1 for pid in pids if _kill_process_pid(pid))
        res_msg = _("Terminated {s} of {t} instances for {user}").format(s=success_count, t=len(pids), user=user_name)

        # Allow focus to settle after modal dialog dismisses before announcing feedback
        def notify_and_refresh():
            _trigger_hub_feedback(res_msg, is_success=(success_count > 0))
            self.on_refresh()

        wx.CallLater(350, notify_and_refresh)

    def on_kill_all_app_instances(self):
        app = self.get_selected_item_data()
        if not app:
            return

        app_name = app["app_name"]
        total_pids = app["all_pids"]

        msg = _("Are you sure you want to terminate ALL {count} instances of {app} across ALL users?").format(
            count=len(total_pids), app=app_name
        )
        if gui.messageBox(msg, _("Confirm Server-Wide Termination"), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_EXCLAMATION, self) != wx.YES:
            return

        success_count = sum(1 for pid in total_pids if _kill_process_pid(pid))
        res_msg = _("Terminated {s} of {t} instances of {app}").format(s=success_count, t=len(total_pids), app=app_name)

        def notify_and_refresh():
            _trigger_hub_feedback(res_msg, is_success=(success_count > 0))
            self.on_refresh()

        wx.CallLater(350, notify_and_refresh)

    def on_disconnect_session(self):
        item_data = self.get_selected_item_data()
        if not item_data:
            return
        sid = item_data["session_id"]
        user = item_data.get("user", item_data.get("user_name", _("User")))
        success = WTSDisconnectSession(WTS_CURRENT_SERVER_HANDLE, sid, False)
        res_msg = _("Session {id} ({user}) disconnected").format(id=sid, user=user) if success else _("Failed to disconnect session")

        def notify_and_refresh():
            _trigger_hub_feedback(res_msg, is_success=success)
            self.on_refresh()

        wx.CallLater(350, notify_and_refresh)

    def on_logoff_session(self):
        item_data = self.get_selected_item_data()
        if not item_data:
            return
        sid = item_data["session_id"]
        user = item_data.get("user", item_data.get("user_name", _("User")))

        msg = _("Are you sure you want to log off session {id} ({user})? Any unsaved work will be lost.").format(
            id=sid, user=user
        )
        if gui.messageBox(msg, _("Confirm Logoff Session"), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, self) != wx.YES:
            return

        success = WTSLogoffSession(WTS_CURRENT_SERVER_HANDLE, sid, False)
        res_msg = _("Session {id} ({user}) logged off").format(id=sid, user=user) if success else _("Failed to log off session")

        def notify_and_refresh():
            _trigger_hub_feedback(res_msg, is_success=success)
            self.on_refresh()

        wx.CallLater(350, notify_and_refresh)

    def on_copy_action(self, event):
        if self.current_view == self.VIEW_APPS:
            lines = [
                _("PowerBox - Server Applications Report"),
                "======================================\n"
            ]
            for a in self.filtered_apps:
                lines.append(f"{a['app_name']}: {_format_ram(a['total_ram'])}, CPU {a['total_cpu']:.1f}%, {a['users_count']} Users | Top: {a['top_user_name']}")
            text = "\n".join(lines)
            api.copyToClip(text)
            _trigger_hub_feedback(_("Server applications report copied to clipboard"), is_success=True)
        elif self.current_view == self.VIEW_USERS:
            u = self.get_selected_item_data()
            if u:
                line = f"{self.selected_app['app_name']} | User: {u['user_name']} | Session: {u['session_id']} ({u['session_state']}) | RAM: {_format_ram(u['ram_mb'])}"
                api.copyToClip(line)
                _trigger_hub_feedback(_("User application details copied to clipboard"), is_success=True)
        else:
            s = self.get_selected_item_data()
            if s:
                line = f"Session: {s['session_id']} | User: {s['user']} | State: {s['state']} | Client: {s['client']} | RAM: {_format_ram(s['ram_mb'])}"
                api.copyToClip(line)
                _trigger_hub_feedback(_("Session details copied to clipboard"), is_success=True)

    def on_context_menu(self, event):
        item = self.get_selected_item_data()
        if not item:
            return

        menu = wx.Menu()
        if self.current_view == self.VIEW_APPS:
            m_view = menu.Append(wx.ID_ANY, _("&View Users Running this App"))
            m_details = menu.Append(wx.ID_ANY, _("View &Detailed Information..."))
            m_copy = menu.Append(wx.ID_ANY, _("&Copy App Summary"))
            menu.AppendSeparator()
            m_kill_all = menu.Append(wx.ID_ANY, _("&End Application for ALL Users"))

            self.Bind(wx.EVT_MENU, lambda evt: self.show_users_view(item), m_view)
            self.Bind(wx.EVT_MENU, lambda evt: self.on_show_details(None), m_details)
            self.Bind(wx.EVT_MENU, self.on_copy_action, m_copy)
            self.Bind(wx.EVT_MENU, lambda evt: self.on_kill_all_app_instances(), m_kill_all)
        elif self.current_view == self.VIEW_USERS:
            m_kill = menu.Append(wx.ID_ANY, _("&End Process for this User"))
            m_copy = menu.Append(wx.ID_ANY, _("&Copy User Details"))
            menu.AppendSeparator()
            m_disc = menu.Append(wx.ID_ANY, _("&Disconnect Session"))
            m_logoff = menu.Append(wx.ID_ANY, _("&Logoff Session"))

            self.Bind(wx.EVT_MENU, lambda evt: self.on_kill_user_process(), m_kill)
            self.Bind(wx.EVT_MENU, self.on_copy_action, m_copy)
            self.Bind(wx.EVT_MENU, lambda evt: self.on_disconnect_session(), m_disc)
            self.Bind(wx.EVT_MENU, lambda evt: self.on_logoff_session(), m_logoff)
        else:
            m_logoff = menu.Append(wx.ID_ANY, _("&Logoff Session"))
            m_disc = menu.Append(wx.ID_ANY, _("&Disconnect Session"))
            menu.AppendSeparator()
            m_copy = menu.Append(wx.ID_ANY, _("&Copy Session Details"))

            self.Bind(wx.EVT_MENU, lambda evt: self.on_logoff_session(), m_logoff)
            self.Bind(wx.EVT_MENU, lambda evt: self.on_disconnect_session(), m_disc)
            self.Bind(wx.EVT_MENU, self.on_copy_action, m_copy)

        self.PopupMenu(menu)
        menu.Destroy()


def show_server_process_hub_dialog():
    """Entry point to display the Server Process Hub safely on the UI thread."""
    gui_parent = getattr(gui, "mainFrame", None)
    if gui_parent:
        gui_parent.prePopup()
    try:
        dlg = ServerProcessHubDialog(gui_parent)
        dlg.ShowModal()
        dlg.Destroy()
    finally:
        if gui_parent:
            gui_parent.postPopup()