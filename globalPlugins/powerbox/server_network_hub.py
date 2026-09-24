# -*- coding: utf-8 -*-
# server_network_hub.py - Enterprise Multi-User Server Network Console for PowerBox

# Acknowledgment:
# - Low-level TCP/UDP socket enumeration utilizes Microsoft IP Helper APIs (GetExtendedTcpTable, GetExtendedUdpTable).
# - Individual socket termination utilizes native SetTcpEntry with MIB_TCP_STATE_DELETE_TCB.
# - Multi-session user and domain mapping utilizes Windows Terminal Services (wtsapi32.dll) and Security Accounts (advapi32.dll).
# - Uses isolated WinDLL instances to eliminate ctypes prototype collisions.
# - High-speed socket probing and latency measurement use native Python non-blocking sockets.
# - In-place accessible list updates ensure zero focus stealing or speech interruption for NVDA.

import ctypes
from ctypes import wintypes
import socket
import struct
import threading
import time
import os
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
iphlpapi = ctypes.WinDLL("iphlpapi", use_last_error=True)
ws2_32 = ctypes.WinDLL("ws2_32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
wtsapi32 = ctypes.WinDLL("wtsapi32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

WTS_CURRENT_SERVER_HANDLE = wintypes.HANDLE(0).value

# Win32 Constants & Access Rights
AF_INET = 2
TCP_TABLE_OWNER_PID_ALL = 5
UDP_TABLE_OWNER_PID = 1
PROCESS_TERMINATE = 0x0001
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

# TCP State Constants
MIB_TCP_STATE_CLOSED = 1
MIB_TCP_STATE_LISTEN = 2
MIB_TCP_STATE_SYN_SENT = 3
MIB_TCP_STATE_SYN_RCVD = 4
MIB_TCP_STATE_ESTAB = 5
MIB_TCP_STATE_FIN_WAIT1 = 6
MIB_TCP_STATE_FIN_WAIT2 = 7
MIB_TCP_STATE_CLOSE_WAIT = 8
MIB_TCP_STATE_CLOSING = 9
MIB_TCP_STATE_LAST_ACK = 10
MIB_TCP_STATE_TIME_WAIT = 11
MIB_TCP_STATE_DELETE_TCB = 12

TCP_STATE_STRINGS = {
    MIB_TCP_STATE_CLOSED: _("Closed"),
    MIB_TCP_STATE_LISTEN: _("Listening"),
    MIB_TCP_STATE_SYN_SENT: _("Syn_Sent"),
    MIB_TCP_STATE_SYN_RCVD: _("Syn_Received"),
    MIB_TCP_STATE_ESTAB: _("Established"),
    MIB_TCP_STATE_FIN_WAIT1: _("Fin_Wait1"),
    MIB_TCP_STATE_FIN_WAIT2: _("Fin_Wait2"),
    MIB_TCP_STATE_CLOSE_WAIT: _("Close_Wait"),
    MIB_TCP_STATE_CLOSING: _("Closing"),
    MIB_TCP_STATE_LAST_ACK: _("Last_Ack"),
    MIB_TCP_STATE_TIME_WAIT: _("Time_Wait"),
    MIB_TCP_STATE_DELETE_TCB: _("Deleting"),
}

# Curated Well-Known Service Ports Dictionary
COMMON_SERVICE_PORTS = {
    80: "HTTP", 443: "HTTPS", 53: "DNS", 21: "FTP", 22: "SSH",
    23: "Telnet", 25: "SMTP", 110: "POP3", 143: "IMAP", 3389: "RDP",
    8080: "HTTP-Alt", 8443: "HTTPS-Alt", 5228: "Google Play/FCM",
    5222: "XMPP/WhatsApp", 1433: "MSSQL", 3306: "MySQL", 5432: "PostgreSQL",
    27017: "MongoDB", 6379: "Redis", 8000: "Dev-Server", 3000: "NodeJS-Dev",
    5000: "Flask-Dev"
}

# In-memory reverse DNS cache to prevent redundant network lookups
_REVERSE_DNS_CACHE = {}


# Win32 Structures
class WTS_PROCESS_INFO(ctypes.Structure):
    _fields_ = [
        ("SessionId", wintypes.DWORD),
        ("ProcessId", wintypes.DWORD),
        ("pProcessName", wintypes.LPWSTR),
        ("pUserSid", ctypes.c_void_p),
    ]


class MIB_TCPROW_OWNER_PID(ctypes.Structure):
    _fields_ = [
        ("dwState", wintypes.DWORD),
        ("dwLocalAddr", wintypes.DWORD),
        ("dwLocalPort", wintypes.DWORD),
        ("dwRemoteAddr", wintypes.DWORD),
        ("dwRemotePort", wintypes.DWORD),
        ("dwOwningPid", wintypes.DWORD),
    ]


class MIB_UDPROW_OWNER_PID(ctypes.Structure):
    _fields_ = [
        ("dwLocalAddr", wintypes.DWORD),
        ("dwLocalPort", wintypes.DWORD),
        ("dwOwningPid", wintypes.DWORD),
    ]


class MIB_TCPROW(ctypes.Structure):
    _fields_ = [
        ("dwState", wintypes.DWORD),
        ("dwLocalAddr", wintypes.DWORD),
        ("dwLocalPort", wintypes.DWORD),
        ("dwRemoteAddr", wintypes.DWORD),
        ("dwRemotePort", wintypes.DWORD),
    ]


# Function Bindings using generic c_void_p for cross-module immunity
WTSEnumerateProcesses = wtsapi32.WTSEnumerateProcessesW
WTSEnumerateProcesses.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
    ctypes.POINTER(ctypes.POINTER(WTS_PROCESS_INFO)),
    ctypes.POINTER(wintypes.DWORD)
]
WTSEnumerateProcesses.restype = wintypes.BOOL

WTSFreeMemory = wtsapi32.WTSFreeMemory
WTSFreeMemory.argtypes = [ctypes.c_void_p]
WTSFreeMemory.restype = None

LookupAccountSid = advapi32.LookupAccountSidW
LookupAccountSid.argtypes = [
    wintypes.LPCWSTR, ctypes.c_void_p,
    wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
    wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
    ctypes.POINTER(wintypes.DWORD)
]
LookupAccountSid.restype = wintypes.BOOL

iphlpapi.GetExtendedTcpTable.argtypes = [
    ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), wintypes.BOOL,
    wintypes.ULONG, ctypes.c_int, wintypes.DWORD
]
iphlpapi.GetExtendedTcpTable.restype = wintypes.DWORD

iphlpapi.GetExtendedUdpTable.argtypes = [
    ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), wintypes.BOOL,
    wintypes.ULONG, ctypes.c_int, wintypes.DWORD
]
iphlpapi.GetExtendedUdpTable.restype = wintypes.DWORD

iphlpapi.SetTcpEntry.argtypes = [ctypes.c_void_p]
iphlpapi.SetTcpEntry.restype = wintypes.DWORD

OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE

TerminateProcess = kernel32.TerminateProcess
TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
TerminateProcess.restype = wintypes.BOOL

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL


def _trigger_hub_feedback(msg, is_success=True, is_copy=False):
    """Provides user feedback strictly respecting configured feedbackMode."""
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")

    if mode in ("beep", "both"):
        if not is_success:
            tones.beep(250, 60)
        elif is_copy:
            tones.beep(950, 40)
        else:
            tones.beep(850, 40)

    if is_copy and mode in ("speech", "both"):
        ui.message(f"{msg} {_('(Copied)')}")
    else:
        ui.message(msg)


def _format_ip_address(dwAddr):
    """Converts a network byte order uint32 IP into clean dotted string."""
    return socket.inet_ntoa(struct.pack("<I", dwAddr))


def _format_port_number(dwPort):
    """Converts a network byte order port into host uint16 integer."""
    return socket.ntohs(dwPort & 0xFFFF)


def _get_port_display(port):
    """Translates well-known service ports or returns raw port number directly."""
    service = COMMON_SERVICE_PORTS.get(port)
    if service:
        return f"{port} ({service})"
    return str(port)


def _classify_ip(ip_str):
    """Classifies an IP into 'internet', 'lan', or 'local' domain."""
    if not ip_str or ip_str in ("*", "0.0.0.0"):
        return "local"
    if ip_str.startswith("127."):
        return "local"
    if ip_str.startswith(("192.168.", "10.", "172.16.", "172.17.", "172.18.", "172.19.",
                          "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
                          "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
                          "169.254.")):
        return "lan"
    return "internet"


def _drop_tcp_connection(raw_local_addr, raw_local_port, raw_remote_addr, raw_remote_port):
    """Severs an individual active TCP socket cleanly using native SetTcpEntry."""
    row = MIB_TCPROW()
    row.dwState = MIB_TCP_STATE_DELETE_TCB
    row.dwLocalAddr = raw_local_addr
    row.dwLocalPort = raw_local_port
    row.dwRemoteAddr = raw_remote_addr
    row.dwRemotePort = raw_remote_port
    status = iphlpapi.SetTcpEntry(ctypes.byref(row))
    return status == 0


def _kill_process_pid(pid):
    """Emergency process termination for rogue or suspicious network activity."""
    h_proc = OpenProcess(PROCESS_TERMINATE, False, pid)
    if not h_proc or h_proc == INVALID_HANDLE_VALUE:
        return False
    try:
        return bool(TerminateProcess(h_proc, 1))
    finally:
        CloseHandle(h_proc)


def _query_extended_tcp_table():
    """Retrieves all IPv4 TCP table entries with owning PIDs."""
    buf_size = wintypes.DWORD(0)
    iphlpapi.GetExtendedTcpTable(None, ctypes.byref(buf_size), True, AF_INET, TCP_TABLE_OWNER_PID_ALL, 0)
    if buf_size.value == 0:
        return []

    buffer = (ctypes.c_byte * buf_size.value)()
    if iphlpapi.GetExtendedTcpTable(ctypes.byref(buffer), ctypes.byref(buf_size), True, AF_INET, TCP_TABLE_OWNER_PID_ALL, 0) != 0:
        return []

    num_entries = struct.unpack_from("<I", buffer, 0)[0]
    row_size = ctypes.sizeof(MIB_TCPROW_OWNER_PID)
    offset = 4

    rows = []
    for _ in range(num_entries):
        row = MIB_TCPROW_OWNER_PID.from_buffer_copy(buffer, offset)
        offset += row_size
        rows.append(row)

    return rows


def _query_extended_udp_table():
    """Retrieves all IPv4 UDP listeners with owning PIDs."""
    buf_size = wintypes.DWORD(0)
    iphlpapi.GetExtendedUdpTable(None, ctypes.byref(buf_size), True, AF_INET, UDP_TABLE_OWNER_PID, 0)
    if buf_size.value == 0:
        return []

    buffer = (ctypes.c_byte * buf_size.value)()
    if iphlpapi.GetExtendedUdpTable(ctypes.byref(buffer), ctypes.byref(buf_size), True, AF_INET, UDP_TABLE_OWNER_PID, 0) != 0:
        return []

    num_entries = struct.unpack_from("<I", buffer, 0)[0]
    row_size = ctypes.sizeof(MIB_UDPROW_OWNER_PID)
    offset = 4

    rows = []
    for _ in range(num_entries):
        row = MIB_UDPROW_OWNER_PID.from_buffer_copy(buffer, offset)
        offset += row_size
        rows.append(row)

    return rows


def _resolve_reverse_dns(ip_str):
    """Asynchronously resolves public IPs only, avoiding DNS timeouts on private networks."""
    domain_type = _classify_ip(ip_str)
    if domain_type == "local":
        return _("Local Device")
    if domain_type == "lan":
        return _("Local LAN")

    if ip_str in _REVERSE_DNS_CACHE:
        return _REVERSE_DNS_CACHE[ip_str]

    try:
        host = socket.gethostbyaddr(ip_str)[0]
        _REVERSE_DNS_CACHE[ip_str] = host
        return host
    except Exception:
        _REVERSE_DNS_CACHE[ip_str] = ip_str
        return ip_str


def _probe_socket_latency(ip_str, port, timeout_sec=1.5):
    """Direct non-blocking socket test returning (is_open: bool, latency_ms: float)."""
    if not ip_str or ip_str in ("0.0.0.0", "*"):
        return False, 0.0

    t0 = time.perf_counter()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_sec)
            res = s.connect_ex((ip_str, port))
            latency = (time.perf_counter() - t0) * 1000.0
            return (res == 0), latency
    except Exception:
        return False, 0.0


# --- Enterprise Server Network Hub Console ---
class ServerNetworkHubDialog(wx.Dialog):
    """
    Enterprise real-time network console featuring multi-user Active Directory attribution,
    per-user socket filtering, 3-tier traffic segregation, and socket drop controls.
    """

    def __init__(self, parent, app_name, pids, pid_to_user_map=None, default_user_filter=""):
        super(ServerNetworkHubDialog, self).__init__(
            parent,
            title=_("Server Network Hub - {app} ({count} PIDs)").format(app=app_name, count=len(pids)),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )

        self.app_name = app_name
        self.pids = set(pids)
        self.pid_to_user_map = pid_to_user_map or {}
        self.connection_history = {}

        # Determine multi-user mode
        unique_users = sorted(list(set(self.pid_to_user_map.values())))
        self.is_multi_user = (len(unique_users) > 1)
        self.active_user_filter = default_user_filter or _("All Users")

        # Responsive Dialog Sizing (78% of active display area)
        display_rect = wx.Display().GetClientArea()
        w = max(1000, int(display_rect.width * 0.78))
        h = max(640, int(display_rect.height * 0.78))
        self.SetSize((w, h))
        self.SetMinSize((900, 540))

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 1. Header Pulse Status Label
        self.status_label = wx.StaticText(self, label=_("Connecting to kernel network tables..."))
        font_header = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font_header.SetWeight(wx.FONTWEIGHT_BOLD)
        self.status_label.SetFont(font_header)
        main_sizer.Add(self.status_label, 0, wx.ALL | wx.EXPAND, 12)

        # 2. Multi-User Filter Dropdown (Visible only in Enterprise Server Multi-User Scope)
        if self.is_multi_user:
            filter_box = wx.BoxSizer(wx.HORIZONTAL)
            filter_label = wx.StaticText(self, label=_("&User Filter:"))
            
            choices = [_("All Users ({count})").format(count=len(unique_users))] + unique_users
            self.user_choice = wx.Choice(self, choices=choices)
            
            # Select appropriate initial filter
            if default_user_filter and default_user_filter in unique_users:
                self.user_choice.SetSelection(unique_users.index(default_user_filter) + 1)
                self.active_user_filter = default_user_filter
            else:
                self.user_choice.SetSelection(0)
                self.active_user_filter = _("All Users")

            self.user_choice.Bind(wx.EVT_CHOICE, self.on_user_filter_changed)

            filter_box.Add(filter_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            filter_box.Add(self.user_choice, 1, wx.EXPAND)
            main_sizer.Add(filter_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # 3. Accessible Notebook (Tabs: Internet, Local LAN, Localhost/Listeners)
        self.notebook = wx.Notebook(self)
        self.tab_lists = []

        tab_names = [
            _("Internet Connections"),
            _("Local Network (LAN)"),
            _("Localhost / Listeners")
        ]

        for i, name in enumerate(tab_names):
            panel = wx.Panel(self.notebook)
            panel_sizer = wx.BoxSizer(wx.VERTICAL)

            list_ctrl = wx.ListCtrl(
                panel,
                style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN
            )

            col = 0
            list_ctrl.InsertColumn(col, _("Remote IP")); col += 1
            if self.is_multi_user:
                list_ctrl.InsertColumn(col, _("User Account")); col += 1
            list_ctrl.InsertColumn(col, _("Host / Domain")); col += 1
            list_ctrl.InsertColumn(col, _("Port / Service")); col += 1
            list_ctrl.InsertColumn(col, _("Protocol")); col += 1
            list_ctrl.InsertColumn(col, _("State")); col += 1
            list_ctrl.InsertColumn(col, _("Local Endpoint")); col += 1

            panel_sizer.Add(list_ctrl, 1, wx.EXPAND)
            panel.SetSizer(panel_sizer)

            self.notebook.AddPage(panel, name)
            self.tab_lists.append(list_ctrl)

            list_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_copy_ip)
            list_ctrl.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)

        main_sizer.Add(self.notebook, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # 4. Clean Action Buttons Sizer
        self.btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.test_btn = wx.Button(self, label=_("&Test Port & Latency"))
        self.drop_btn = wx.Button(self, label=_("&Drop Connection"))
        self.clear_btn = wx.Button(self, label=_("Clear &Inactive"))
        self.browser_btn = wx.Button(self, label=_("&Open in Browser"))
        self.threat_btn = wx.Button(self, label=_("Check &VirusTotal"))
        self.kill_btn = wx.Button(self, label=_("&Emergency End App"))
        self.close_btn = wx.Button(self, wx.ID_CANCEL, label=_("&Close"))

        self.test_btn.SetHelpText(_("Tests port latency. Hold Shift while pressing to copy result to clipboard."))

        self.btn_sizer.Add(self.test_btn, 0, wx.RIGHT, 6)
        self.btn_sizer.Add(self.drop_btn, 0, wx.RIGHT, 6)
        self.btn_sizer.Add(self.clear_btn, 0, wx.RIGHT, 6)
        self.btn_sizer.Add(self.browser_btn, 0, wx.RIGHT, 6)
        self.btn_sizer.Add(self.threat_btn, 0, wx.RIGHT, 6)
        self.btn_sizer.Add(self.kill_btn, 0, wx.RIGHT, 6)
        self.btn_sizer.AddStretchSpacer()
        self.btn_sizer.Add(self.close_btn, 0)

        main_sizer.Add(self.btn_sizer, 0, wx.EXPAND | wx.ALL, 12)
        self.SetSizer(main_sizer)

        # Global Event Bindings
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        self.Bind(wx.EVT_SIZE, self.on_dialog_resize)
        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_tab_changed)

        self.test_btn.Bind(wx.EVT_BUTTON, self.on_test_port_action)
        self.drop_btn.Bind(wx.EVT_BUTTON, self.on_drop_connection)
        self.clear_btn.Bind(wx.EVT_BUTTON, self.on_clear_inactive)
        self.browser_btn.Bind(wx.EVT_BUTTON, self.on_open_browser)
        self.threat_btn.Bind(wx.EVT_BUTTON, self.on_check_threat)
        self.kill_btn.Bind(wx.EVT_BUTTON, self.on_emergency_end_app)

        self.CenterOnScreen()

        # Non-blocking Live Polling Timer (2.5 seconds interval)
        self.poll_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_poll_tick, self.poll_timer)
        self.poll_timer.Start(2500)

        self.trigger_async_socket_scan()

    def get_current_list_ctrl(self):
        """Returns the active ListCtrl corresponding to the selected Notebook tab."""
        idx = self.notebook.GetSelection()
        if 0 <= idx < len(self.tab_lists):
            return self.tab_lists[idx]
        return self.tab_lists[0]

    def on_tab_changed(self, event):
        """Adjusts column widths without stealing keyboard focus from tab control."""
        event.Skip()
        wx.CallAfter(self._adjust_column_widths)

    def on_dialog_resize(self, event):
        """Maintains dynamic column proportions across all tab lists on resize."""
        event.Skip()
        wx.CallAfter(self._adjust_column_widths)

    def _adjust_column_widths(self):
        """Calculates dynamic column widths preventing text cramping across all lists."""
        for list_ctrl in self.tab_lists:
            w = list_ctrl.GetClientSize().width - 25
            if w <= 0:
                continue

            col = 0
            if self.is_multi_user:
                list_ctrl.SetColumnWidth(col, int(w * 0.16)); col += 1  # Remote IP
                list_ctrl.SetColumnWidth(col, int(w * 0.20)); col += 1  # User Account
                list_ctrl.SetColumnWidth(col, int(w * 0.20)); col += 1  # Host / Domain
                list_ctrl.SetColumnWidth(col, int(w * 0.14)); col += 1  # Port / Service
                list_ctrl.SetColumnWidth(col, int(w * 0.08)); col += 1  # Protocol
                list_ctrl.SetColumnWidth(col, int(w * 0.10)); col += 1  # State
                list_ctrl.SetColumnWidth(col, int(w * 0.12)); col += 1  # Local Endpoint
            else:
                list_ctrl.SetColumnWidth(col, int(w * 0.18)); col += 1  # Remote IP
                list_ctrl.SetColumnWidth(col, int(w * 0.24)); col += 1  # Host / Domain
                list_ctrl.SetColumnWidth(col, int(w * 0.16)); col += 1  # Port / Service
                list_ctrl.SetColumnWidth(col, int(w * 0.10)); col += 1  # Protocol
                list_ctrl.SetColumnWidth(col, int(w * 0.14)); col += 1  # State
                list_ctrl.SetColumnWidth(col, int(w * 0.18)); col += 1  # Local Endpoint

    def on_char_hook(self, event):
        """Global key interceptors: F5 to refresh, Escape to exit."""
        key = event.GetKeyCode()
        if key == wx.WXK_ESCAPE:
            self.poll_timer.Stop()
            self.EndModal(wx.ID_CANCEL)
            return
        elif key == wx.WXK_F5:
            self.trigger_async_socket_scan()
            return
        event.Skip()

    def on_poll_tick(self, event):
        """Periodic background tick executing non-blocking kernel socket inspection."""
        self.trigger_async_socket_scan()

    def on_user_filter_changed(self, event):
        """Filters active connections by selected user in real time."""
        sel = self.user_choice.GetSelection()
        if sel == 0:
            self.active_user_filter = _("All Users")
        else:
            self.active_user_filter = self.user_choice.GetString(sel)
        
        self._refresh_all_tab_lists()
        _trigger_hub_feedback(_("Filtered by {user}").format(user=self.active_user_filter), is_success=True)

    def trigger_async_socket_scan(self):
        """Dispatches socket snapshot query in a background thread."""
        def worker():
            active_sockets = self._collect_app_sockets()
            wx.CallAfter(self._update_connections_in_place, active_sockets)

        threading.Thread(target=worker, daemon=True).start()

    def _collect_app_sockets(self):
        """Gathers and parses all TCP & UDP sockets matching target PIDs."""
        discovered = {}

        # 1. Query Extended TCP Table
        try:
            tcp_rows = _query_extended_tcp_table()
            for r in tcp_rows:
                if r.dwOwningPid in self.pids:
                    r_ip = _format_ip_address(r.dwRemoteAddr)
                    r_port = _format_port_number(r.dwRemotePort)
                    l_ip = _format_ip_address(r.dwLocalAddr)
                    l_port = _format_port_number(r.dwLocalPort)

                    state_str = TCP_STATE_STRINGS.get(r.dwState, _("Unknown"))
                    if r.dwState == MIB_TCP_STATE_LISTEN:
                        r_ip = "*"
                        r_port = 0

                    user_desc = self.pid_to_user_map.get(r.dwOwningPid, _("User"))

                    key = f"TCP_{l_ip}:{l_port}_{r_ip}:{r_port}_{r.dwOwningPid}"
                    discovered[key] = {
                        "key": key,
                        "proto": "TCP",
                        "remote_ip": r_ip,
                        "remote_port": r_port,
                        "local_endpoint": f"{l_ip}:{l_port}",
                        "state": state_str,
                        "raw_state": r.dwState,
                        "raw_l_addr": r.dwLocalAddr,
                        "raw_l_port": r.dwLocalPort,
                        "raw_r_addr": r.dwRemoteAddr,
                        "raw_r_port": r.dwRemotePort,
                        "pid": r.dwOwningPid,
                        "user": user_desc,
                        "domain_category": _classify_ip(r_ip),
                        "host": _REVERSE_DNS_CACHE.get(r_ip, "")
                    }
        except Exception as e:
            log.debug("Error querying TCP table: %s" % str(e))

        # 2. Query Extended UDP Table
        try:
            udp_rows = _query_extended_udp_table()
            for r in udp_rows:
                if r.dwOwningPid in self.pids:
                    l_ip = _format_ip_address(r.dwLocalAddr)
                    l_port = _format_port_number(r.dwLocalPort)
                    user_desc = self.pid_to_user_map.get(r.dwOwningPid, _("User"))

                    key = f"UDP_{l_ip}:{l_port}_{r.dwOwningPid}"
                    discovered[key] = {
                        "key": key,
                        "proto": "UDP",
                        "remote_ip": "*",
                        "remote_port": 0,
                        "local_endpoint": f"{l_ip}:{l_port}",
                        "state": _("Listening"),
                        "raw_state": MIB_TCP_STATE_LISTEN,
                        "raw_l_addr": r.dwLocalAddr,
                        "raw_l_port": r.dwLocalPort,
                        "raw_r_addr": 0,
                        "raw_r_port": 0,
                        "pid": r.dwOwningPid,
                        "user": user_desc,
                        "domain_category": "local",
                        "host": _("Local Listener")
                    }
        except Exception as e:
            log.debug("Error querying UDP table: %s" % str(e))

        return discovered

    def _update_connections_in_place(self, active_sockets):
        """Smart In-Place Diffing: Never wipes the list or resets cursor."""
        for key, item in self.connection_history.items():
            if key not in active_sockets:
                item["state"] = _("Closed")
                item["is_active"] = False

        for key, item in active_sockets.items():
            item["is_active"] = True
            if key in self.connection_history:
                self.connection_history[key]["state"] = item["state"]
                self.connection_history[key]["is_active"] = True
            else:
                self.connection_history[key] = item
                if item["domain_category"] == "internet":
                    self._dispatch_reverse_dns(item["remote_ip"])

        self._refresh_all_tab_lists()

    def _dispatch_reverse_dns(self, ip_str):
        """Dispatches reverse DNS query without blocking."""
        def dns_worker():
            host = _resolve_reverse_dns(ip_str)
            wx.CallAfter(self._on_dns_resolved, ip_str, host)

        threading.Thread(target=dns_worker, daemon=True).start()

    def _on_dns_resolved(self, ip_str, host):
        """Updates resolved host column in-place across active tab lists."""
        for list_ctrl in self.tab_lists:
            for idx in range(list_ctrl.GetItemCount()):
                if list_ctrl.GetItemText(idx) == ip_str:
                    col_idx = 2 if self.is_multi_user else 1
                    list_ctrl.SetItem(idx, col_idx, host)

    def _refresh_all_tab_lists(self):
        """Synchronizes internal connection dictionary into the three dedicated tabs."""
        buckets = {
            "internet": [],
            "lan": [],
            "local": []
        }

        for item in self.connection_history.values():
            # Apply active user filter if enabled
            if self.is_multi_user and self.active_user_filter != _("All Users"):
                if item.get("user") != self.active_user_filter:
                    continue

            cat = item.get("domain_category", "internet")
            buckets[cat].append(item)

        # Update dynamic Notebook Tab labels with connection counts
        self.notebook.SetPageText(0, _("Internet ({cnt})").format(cnt=len(buckets["internet"])))
        self.notebook.SetPageText(1, _("Local LAN ({cnt})").format(cnt=len(buckets["lan"])))
        self.notebook.SetPageText(2, _("Localhost / Listeners ({cnt})").format(cnt=len(buckets["local"])))

        active_count = sum(1 for item in self.connection_history.values() if item.get("is_active", False))
        closed_count = len(self.connection_history) - active_count

        self.status_label.SetLabel(
            _("Connections Monitor: {act} Active, {cls} Closed/History | App: {app}").format(
                act=active_count, cls=closed_count, app=self.app_name
            )
        )

        self._sync_single_list(self.tab_lists[0], buckets["internet"])
        self._sync_single_list(self.tab_lists[1], buckets["lan"])
        self._sync_single_list(self.tab_lists[2], buckets["local"])

    def _sync_single_list(self, list_ctrl, items):
        """Synchronizes items into a specific ListCtrl using Freeze/Thaw without focus stealing."""
        list_ctrl.Freeze()
        try:
            selected_idx = list_ctrl.GetFirstSelected()
            current_rows = list_ctrl.GetItemCount()

            for idx, item in enumerate(items):
                r_port_display = _get_port_display(item["remote_port"]) if item["remote_port"] > 0 else "*"
                host_display = item["host"] or _REVERSE_DNS_CACHE.get(item["remote_ip"], "")

                col = 0
                if idx < current_rows:
                    list_ctrl.SetItem(idx, col, item["remote_ip"]); col += 1
                    if self.is_multi_user:
                        list_ctrl.SetItem(idx, col, item["user"]); col += 1
                    list_ctrl.SetItem(idx, col, host_display); col += 1
                    list_ctrl.SetItem(idx, col, r_port_display); col += 1
                    list_ctrl.SetItem(idx, col, item["proto"]); col += 1
                    list_ctrl.SetItem(idx, col, item["state"]); col += 1
                    list_ctrl.SetItem(idx, col, item["local_endpoint"]); col += 1
                else:
                    list_ctrl.InsertItem(idx, item["remote_ip"]); col += 1
                    if self.is_multi_user:
                        list_ctrl.SetItem(idx, col, item["user"]); col += 1
                    list_ctrl.SetItem(idx, col, host_display); col += 1
                    list_ctrl.SetItem(idx, col, r_port_display); col += 1
                    list_ctrl.SetItem(idx, col, item["proto"]); col += 1
                    list_ctrl.SetItem(idx, col, item["state"]); col += 1
                    list_ctrl.SetItem(idx, col, item["local_endpoint"]); col += 1

                list_ctrl.SetItemData(idx, idx)

            while list_ctrl.GetItemCount() > len(items):
                list_ctrl.DeleteItem(list_ctrl.GetItemCount() - 1)

            if selected_idx != wx.NOT_FOUND and selected_idx < list_ctrl.GetItemCount():
                list_ctrl.Select(selected_idx)
                list_ctrl.Focus(selected_idx)
            elif items and list_ctrl.GetItemCount() > 0 and list_ctrl == self.get_current_list_ctrl() and list_ctrl.GetFirstSelected() == wx.NOT_FOUND:
                list_ctrl.Select(0)
                list_ctrl.Focus(0)
        finally:
            list_ctrl.Thaw()

    def get_selected_connection(self):
        """Retrieves selected connection dictionary from the active tab list."""
        curr_list = self.get_current_list_ctrl()
        idx = curr_list.GetFirstSelected()
        if idx == wx.NOT_FOUND:
            return None

        tab_idx = self.notebook.GetSelection()
        cat_key = "internet" if tab_idx == 0 else ("lan" if tab_idx == 1 else "local")

        filtered_items = []
        for it in self.connection_history.values():
            if self.is_multi_user and self.active_user_filter != _("All Users"):
                if it.get("user") != self.active_user_filter:
                    continue
            if it.get("domain_category") == cat_key:
                filtered_items.append(it)

        if idx < len(filtered_items):
            return filtered_items[idx]
        return None

    def on_copy_ip(self, event):
        """Copies remote IP or socket endpoint to clipboard respecting feedbackMode."""
        conn = self.get_selected_connection()
        if not conn:
            return
        target = conn["remote_ip"] if conn["remote_ip"] != "*" else conn["local_endpoint"]
        api.copyToClip(target)

        mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
        if mode in ("beep", "both"):
            tones.beep(800, 35)
        if mode in ("speech", "both"):
            ui.message(_("Address {addr} copied to clipboard").format(addr=target))

    def on_test_port_action(self, event=None, force_copy=False):
        """
        Executes ultra-fast socket probe measuring latency in 0.2s.
        Normal press speaks; holding Shift (or force_copy) copies to clipboard and speaks.
        """
        conn = self.get_selected_connection()
        if not conn or conn["remote_ip"] in ("*", "0.0.0.0"):
            _trigger_hub_feedback(_("Cannot test local or listening endpoint"), is_success=False)
            return

        should_copy = force_copy or wx.GetKeyState(wx.WXK_SHIFT)
        remote_ip = conn["remote_ip"]
        port = conn["remote_port"]

        def test_worker():
            is_open, latency = _probe_socket_latency(remote_ip, port)
            if is_open:
                res_msg = _("{ip}:{port} is OPEN (Latency: {ms:.0f} ms)").format(ip=remote_ip, port=port, ms=latency)
            else:
                res_msg = _("{ip}:{port} is UNREACHABLE or Timed Out").format(ip=remote_ip, port=port)

            if should_copy:
                api.copyToClip(res_msg)
                res_msg = f"{res_msg} {_('(Copied)')}"

            wx.CallAfter(_trigger_hub_feedback, res_msg, is_open)

        threading.Thread(target=test_worker, daemon=True).start()

    def on_drop_connection(self, event=None):
        """Severs single active TCP connection immediately without terminating app."""
        conn = self.get_selected_connection()
        if not conn or conn["proto"] != "TCP" or conn["state"] == _("Closed"):
            _trigger_hub_feedback(_("Cannot drop this connection"), is_success=False)
            return

        success = _drop_tcp_connection(
            conn["raw_l_addr"], conn["raw_l_port"],
            conn["raw_r_addr"], conn["raw_r_port"]
        )

        if success:
            conn["state"] = _("Closed")
            conn["is_active"] = False
            self._refresh_all_tab_lists()
            _trigger_hub_feedback(_("Connection severed successfully"), is_success=True)
        else:
            _trigger_hub_feedback(_("Failed to sever connection (Admin privileges recommended)"), is_success=False)

    def on_clear_inactive(self, event):
        """Removes closed connection history rows."""
        self.connection_history = {k: v for k, v in self.connection_history.items() if v.get("is_active", False)}
        self._refresh_all_tab_lists()
        _trigger_hub_feedback(_("Cleared inactive connections"), is_success=True)

    def on_open_browser(self, event):
        """Opens remote server address in default web browser."""
        conn = self.get_selected_connection()
        if not conn or conn["remote_ip"] in ("*", "0.0.0.0", "127.0.0.1"):
            _trigger_hub_feedback(_("Cannot open local or internal address"), is_success=False)
            return

        ip = conn["remote_ip"]
        port = conn["remote_port"]
        scheme = "https" if port in (443, 8443) else "http"
        url = f"{scheme}://{ip}:{port}" if port not in (80, 443) else f"{scheme}://{ip}"

        try:
            os.startfile(url)
            _trigger_hub_feedback(_("Opening {url}").format(url=url), is_success=True)
        except Exception:
            _trigger_hub_feedback(_("Failed to open web browser"), is_success=False)

    def on_check_threat(self, event):
        """Opens VirusTotal threat analysis for the remote IP in browser."""
        conn = self.get_selected_connection()
        if not conn or conn["domain_category"] != "internet":
            _trigger_hub_feedback(_("Threat lookup is available for public internet IPs only"), is_success=False)
            return

        ip = conn["remote_ip"]
        url = f"https://www.virustotal.com/gui/ip-address/{ip}"
        try:
            os.startfile(url)
            _trigger_hub_feedback(_("Checking IP safety on VirusTotal..."), is_success=True)
        except Exception:
            _trigger_hub_feedback(_("Failed to open threat lookup"), is_success=False)

    def on_emergency_end_app(self, event):
        """Emergency kill switch for the entire application across all PIDs."""
        msg = _("Are you sure you want to emergency-terminate {app} across ALL {cnt} PIDs?").format(
            app=self.app_name, cnt=len(self.pids)
        )
        if gui.messageBox(msg, _("Confirm Emergency Termination"), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, self) != wx.YES:
            return

        success_count = sum(1 for p in self.pids if _kill_process_pid(p))
        _trigger_hub_feedback(
            _("Terminated {s} of {t} PIDs for {app}").format(s=success_count, t=len(self.pids), app=self.app_name),
            is_success=(success_count > 0)
        )
        self.poll_timer.Stop()
        self.EndModal(wx.ID_OK)

    def on_context_menu(self, event):
        """Rich accessible context menu."""
        conn = self.get_selected_connection()
        if not conn:
            return

        menu = wx.Menu()
        m_copy_ip = menu.Append(wx.ID_ANY, _("&Copy Remote IP Address (Enter)"))
        m_test = menu.Append(wx.ID_ANY, _("&Test Port & Measure Latency (Alt+T)"))
        m_test_copy = menu.Append(wx.ID_ANY, _("Test Port and &Copy Result"))
        m_drop = menu.Append(wx.ID_ANY, _("&Drop This Connection (Alt+D)"))
        menu.AppendSeparator()
        m_open_web = menu.Append(wx.ID_ANY, _("&Open in Web Browser (Alt+O)"))
        m_threat = menu.Append(wx.ID_ANY, _("Check &Threat Safety (VirusTotal) (Alt+V)"))
        menu.AppendSeparator()
        m_clear = menu.Append(wx.ID_ANY, _("&Clear Inactive Connections (Alt+I)"))
        m_kill = menu.Append(wx.ID_ANY, _("&Emergency Terminate Application (Alt+E)"))

        self.Bind(wx.EVT_MENU, self.on_copy_ip, m_copy_ip)
        self.Bind(wx.EVT_MENU, lambda evt: self.on_test_port_action(None, force_copy=False), m_test)
        self.Bind(wx.EVT_MENU, lambda evt: self.on_test_port_action(None, force_copy=True), m_test_copy)
        self.Bind(wx.EVT_MENU, self.on_drop_connection, m_drop)
        self.Bind(wx.EVT_MENU, self.on_open_browser, m_open_web)
        self.Bind(wx.EVT_MENU, self.on_check_threat, m_threat)
        self.Bind(wx.EVT_MENU, self.on_clear_inactive, m_clear)
        self.Bind(wx.EVT_MENU, self.on_emergency_end_app, m_kill)

        self.PopupMenu(menu)
        menu.Destroy()


def show_server_network_hub_dialog(app_name, pids, pid_to_user_map=None, default_user_filter=""):
    """Entry point safely presenting the Server Network Hub dialog on the main UI thread."""
    if not pids:
        _trigger_hub_feedback(_("No active PIDs to track for {app}").format(app=app_name), is_success=False)
        return

    gui_parent = getattr(gui, "mainFrame", None)
    if gui_parent:
        gui_parent.prePopup()
    try:
        dlg = ServerNetworkHubDialog(gui_parent, app_name, pids, pid_to_user_map, default_user_filter)
        dlg.ShowModal()
        dlg.Destroy()
    finally:
        if gui_parent:
            gui_parent.postPopup()