# -*- coding: utf-8 -*-
# network_scanner.py - High-speed, non-blocking LAN device scanner for PowerBox

# Acknowledgment:
# - Low-level ARP discovery uses Microsoft Windows IP Helper API (iphlpapi.dll).
# - MAC address randomization detection complies with IEEE 802 Locally Administered Address (LAA) specifications.
# - Multi-tier web interface probing covers standard (80, 443) and alternate (8080, 8443) service ports.
# - Manufacturer resolution incorporates a curated IEEE OUI table and maclookup.app API fallback.
# - GUI dialog accessibility and modal lifecycle patterns follow NV Access add-on development standards.

import ctypes
import socket
import ipaddress
import threading
import time
import os
import urllib.request
import json
from concurrent.futures import ThreadPoolExecutor
import wx
import addonHandler
import api
import config
import gui
import ui
import tones
from . import network_info

# Initialize translation support for this module
addonHandler.initTranslation()

# Global state tracking to allow non-blocking toggle and safe cancellation
_is_scanning = False
_cancel_event = threading.Event()

# Common web interface ports prioritized for automated browser routing
COMMON_WEB_PORTS = [
    (80, "http"),
    (443, "https"),
    (8080, "http"),
    (8443, "https"),
]

# --- Embedded Curated OUI Vendor Table (Top Consumer & Networking Vendors) ---
OUI_VENDORS = {
    # Networking Equipment
    "A842A1": "TP-Link", "50C7BF": "TP-Link", "E848B8": "TP-Link", "000AEB": "TP-Link",
    "984827": "TP-Link", "0018E7": "D-Link", "C0A0BB": "D-Link", "001E2A": "Netgear",
    "A00460": "Netgear", "00000C": "Cisco", "001F6C": "Cisco",
    # Motherboards & PC Manufacturers
    "B42E99": "Giga-Byte", "001B21": "Intel", "DCF756": "Intel", "00E04C": "Realtek",
    "482AE3": "Realtek", "281878": "Microsoft", "DC5360": "Microsoft", "001422": "Dell",
    "B8AC6F": "Dell", "001E0B": "HP", "3CD92B": "HP", "00262D": "Lenovo", "AC3870": "Lenovo",
    # Apple Devices
    "F01898": "Apple", "ACBC32": "Apple", "F4F5DB": "Apple", "80E650": "Apple",
    "BC9FEF": "Apple", "3C15C2": "Apple", "149877": "Apple", "A4C3F0": "Apple",
    # Samsung Devices
    "A82BB9": "Samsung", "508569": "Samsung", "E4E0C5": "Samsung", "94652D": "Samsung",
    "002454": "Samsung", "54880E": "Samsung", "D0176A": "Samsung",
    # IoT, Smart Home & Mobile
    "B827EB": "Raspberry Pi", "D83ADD": "Raspberry Pi", "E45F01": "Raspberry Pi",
    "240AC4": "Espressif (Smart IoT)", "30AEA4": "Espressif (Smart IoT)",
    "84F3EB": "Espressif (Smart IoT)", "A4CF12": "Espressif (Smart IoT)",
    "64A2F9": "Xiaomi", "742344": "Xiaomi", "00E0FC": "Huawei", "4846FB": "Huawei",
    "F4F5D8": "Google", "48D6D5": "Google", "FC65DE": "Amazon", "40B4CD": "Amazon",
}


def is_randomized_mac(clean_mac):
    """
    Checks IEEE 802 Locally Administered bit (Bit 1 of first octet).
    Mathematically guarantees detection of private randomized MACs (phones/tablets).
    """
    try:
        first_byte = int(clean_mac[:2], 16)
        return bool(first_byte & 0x02)
    except Exception:
        return False


def query_online_vendor(mac_prefix):
    """Queries an online lightweight API for unknown hardware MAC vendors."""
    try:
        url = f"https://api.maclookup.app/v2/macs/{mac_prefix}"
        req = urllib.request.Request(url, headers={"User-Agent": "PowerBox-NVDA"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("success") and data.get("company"):
                return data["company"]
    except Exception:
        pass
    return None


def get_mac_vendor(mac_address):
    """Resolves device vendor safely and accurately."""
    if not mac_address:
        return _("Unknown")

    clean_mac = mac_address.replace(":", "").replace("-", "").upper()

    if is_randomized_mac(clean_mac):
        return _("Randomized MAC (Phone / Mobile)")

    prefix = clean_mac[:6]
    local_vendor = OUI_VENDORS.get(prefix)
    if local_vendor:
        return local_vendor

    online_vendor = query_online_vendor(prefix)
    if online_vendor:
        OUI_VENDORS[prefix] = online_vendor
        return online_vendor

    return _("Hardware Device")


def send_arp_probe(ip_str):
    """Sends a fast single-pass Win32 ARP request using SendARP from iphlpapi.dll."""
    try:
        dest_ip = ctypes.windll.ws2_32.inet_addr(ip_str.encode("ascii"))
        if dest_ip == 0xFFFFFFFF:
            return None

        mac_buffer = (ctypes.c_ubyte * 6)()
        mac_len = ctypes.c_ulong(6)

        status = ctypes.windll.iphlpapi.SendARP(
            dest_ip, 0, ctypes.byref(mac_buffer), ctypes.byref(mac_len)
        )
        if status == 0 and mac_len.value == 6:
            return ":".join(f"{b:02X}" for b in mac_buffer)
    except Exception:
        pass
    return None


def resolve_hostname(ip_str):
    """Attempts to resolve the local hostname safely."""
    try:
        host_info = socket.gethostbyaddr(ip_str)
        return host_info[0]
    except Exception:
        return _("Unknown")


def enrich_device_info(dev):
    """
    Enriches an active host with metadata.
    Distinguishes the current host machine, default gateway, and mobile devices.
    """
    ip_str = dev["ip"]
    mac_str = dev["mac"]
    clean_mac = mac_str.replace(":", "").replace("-", "").upper()

    local_ip = network_info.get_local_ip()
    gateway_ip = network_info.get_default_gateway()

    # Fast-path 1: The current PC running this add-on (instant kernel query)
    if local_ip and ip_str == local_ip:
        base_name = socket.gethostname() or resolve_hostname(ip_str)
        hostname = f"{base_name} ({_('This PC')})"
    # Fast-path 2: Default gateway (Router)
    elif gateway_ip and ip_str == gateway_ip:
        hostname = _("Router / Default Gateway")
    # Fast-path 3: Mobile devices with private MACs (skip NetBIOS delay)
    elif is_randomized_mac(clean_mac):
        hostname = _("Mobile Device")
    else:
        hostname = resolve_hostname(ip_str)

    vendor = get_mac_vendor(mac_str)

    return {
        "ip": ip_str,
        "name": hostname,
        "vendor": vendor,
        "mac": mac_str,
    }


def execute_network_scan(cancel_event):
    """Full concurrent 254-thread ARP sweep in ~2 to 3 seconds."""
    local_ip = network_info.get_local_ip()
    if not local_ip or local_ip.startswith("127.") or "Offline" in local_ip:
        return None

    try:
        subnet = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
        targets = [str(ip) for ip in subnet.hosts()]
    except Exception:
        return None

    discovered_raw = []

    def probe_worker(ip):
        if cancel_event.is_set():
            return None
        mac = send_arp_probe(ip)
        if mac:
            return {"ip": ip, "mac": mac}
        return None

    with ThreadPoolExecutor(max_workers=180) as executor:
        for res in executor.map(probe_worker, targets):
            if cancel_event.is_set():
                return None
            if res:
                discovered_raw.append(res)

    if cancel_event.is_set() or not discovered_raw:
        return []

    with ThreadPoolExecutor(max_workers=len(discovered_raw)) as executor:
        active_devices = list(executor.map(enrich_device_info, discovered_raw))

    active_devices.sort(key=lambda d: socket.inet_aton(d["ip"]))
    return active_devices


def probe_single_port(ip, port):
    """Probes a single TCP port with a fast 200ms timeout."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex((ip, port)) == 0:
                return port
    except Exception:
        pass
    return None


def detect_best_web_url(ip):
    """
    Checks common web ports (80, 443, 8080, 8443) concurrently in ~200ms.
    Returns the most specific URL scheme and port, or None if no standard port is open.
    """
    open_ports = set()
    with ThreadPoolExecutor(max_workers=len(COMMON_WEB_PORTS)) as executor:
        futures = [executor.submit(probe_single_port, ip, port) for port, _ in COMMON_WEB_PORTS]
        for f in futures:
            p = f.result()
            if p:
                open_ports.add(p)

    if 443 in open_ports and 80 not in open_ports:
        return f"https://{ip}"
    if 80 in open_ports:
        return f"http://{ip}"
    if 8443 in open_ports:
        return f"https://{ip}:8443"
    if 8080 in open_ports:
        return f"http://{ip}:8080"
    if 443 in open_ports:
        return f"https://{ip}"

    return None


# --- Accessible Results Dialog ---
class NetworkScannerDialog(wx.Dialog):
    """An accessible, beautifully centered modal dialog presenting discovered network devices."""

    def __init__(self, parent, devices):
        super(NetworkScannerDialog, self).__init__(
            parent,
            title=_("Network Scanner - Discovered Devices ({count})").format(count=len(devices)),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(780, 490),
        )
        self.devices = devices

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        info_label = wx.StaticText(
            self,
            label=_("Active devices on your local network. Press Enter on any item to copy its IP:"),
        )
        main_sizer.Add(info_label, 0, wx.ALL, 12)

        # High-accessibility List View
        self.list_ctrl = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN
        )
        self.list_ctrl.InsertColumn(0, _("IP Address"), width=140)
        self.list_ctrl.InsertColumn(1, _("Device Name"), width=220)
        self.list_ctrl.InsertColumn(2, _("Manufacturer"), width=210)
        self.list_ctrl.InsertColumn(3, _("MAC Address"), width=160)

        for idx, dev in enumerate(self.devices):
            self.list_ctrl.InsertItem(idx, dev["ip"])
            self.list_ctrl.SetItem(idx, 1, dev["name"])
            self.list_ctrl.SetItem(idx, 2, dev["vendor"])
            self.list_ctrl.SetItem(idx, 3, dev["mac"])

        main_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        # Action Buttons Sizer with Accelerators
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.copy_ip_btn = wx.Button(self, label=_("Copy &IP"))
        self.copy_mac_btn = wx.Button(self, label=_("Copy &MAC"))
        self.open_web_btn = wx.Button(self, label=_("&Open in Browser"))
        self.rescan_btn = wx.Button(self, label=_("&Rescan"))
        self.copy_all_btn = wx.Button(self, label=_("Copy &All Details"))
        self.close_btn = wx.Button(self, wx.ID_CANCEL, label=_("&Close"))

        btn_sizer.Add(self.copy_ip_btn, 0, wx.RIGHT, 6)
        btn_sizer.Add(self.copy_mac_btn, 0, wx.RIGHT, 6)
        btn_sizer.Add(self.open_web_btn, 0, wx.RIGHT, 6)
        btn_sizer.Add(self.rescan_btn, 0, wx.RIGHT, 6)
        btn_sizer.Add(self.copy_all_btn, 0, wx.RIGHT, 6)
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(self.close_btn, 0)

        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 12)
        self.SetSizer(main_sizer)

        # Event Bindings
        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_copy_ip)
        self.list_ctrl.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        self.copy_ip_btn.Bind(wx.EVT_BUTTON, self.on_copy_ip)
        self.copy_mac_btn.Bind(wx.EVT_BUTTON, self.on_copy_mac)
        self.open_web_btn.Bind(wx.EVT_BUTTON, self.on_open_browser)
        self.rescan_btn.Bind(wx.EVT_BUTTON, self.on_rescan)
        self.copy_all_btn.Bind(wx.EVT_BUTTON, self.on_copy_all)

        # Initial selection and focus
        if self.devices:
            self.list_ctrl.Select(0)
            self.list_ctrl.Focus(0)
        self.list_ctrl.SetFocus()

        # Center strictly on active monitor work area
        self.CenterOnScreen()

    def get_selected_device(self):
        idx = self.list_ctrl.GetFirstSelected()
        if idx != wx.NOT_FOUND:
            return self.devices[idx]
        return None

    def trigger_feedback_message(self, msg, beep_pitch=800):
        """Helper to respect user feedbackMode for dialog clipboard operations."""
        mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
        if mode in ("beep", "both"):
            tones.beep(beep_pitch, 30)
        if mode in ("speech", "both"):
            ui.message(msg)

    def on_copy_ip(self, event):
        dev = self.get_selected_device()
        if dev:
            api.copyToClip(dev["ip"])
            self.trigger_feedback_message(_("IP {ip} copied to clipboard").format(ip=dev["ip"]))

    def on_copy_mac(self, event):
        dev = self.get_selected_device()
        if dev:
            api.copyToClip(dev["mac"])
            self.trigger_feedback_message(_("MAC {mac} copied to clipboard").format(mac=dev["mac"]))

    def on_open_browser(self, event):
        dev = self.get_selected_device()
        if not dev:
            return

        ip = dev["ip"]
        mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")

        def probe_and_open():
            target_url = detect_best_web_url(ip)
            is_fallback = False

            if target_url:
                msg = _("Opening {url} in web browser").format(url=target_url)
            else:
                target_url = f"http://{ip}"
                msg = _("No standard web port detected. Opening default address...")
                is_fallback = True

            if mode in ("speech", "both"):
                wx.CallAfter(ui.message, msg)
                speech_delay = 1.6 if is_fallback else 0.9
                time.sleep(speech_delay)

            if mode in ("beep", "both"):
                tones.beep(850, 40)

            def safe_launch(url):
                try:
                    os.startfile(url)
                except Exception:
                    if mode in ("speech", "both"):
                        ui.message(_("Failed to open web browser"))

            wx.CallAfter(safe_launch, target_url)

        threading.Thread(target=probe_and_open, daemon=True).start()

    def on_rescan(self, event):
        self.Destroy()
        wx.CallAfter(start_async_network_scan)

    def on_copy_all(self, event):
        dev = self.get_selected_device()
        if dev:
            details = (
                f"{_('IP')}: {dev['ip']} | "
                f"{_('Name')}: {dev['name']} | "
                f"{_('Vendor')}: {dev['vendor']} | "
                f"{_('MAC')}: {dev['mac']}"
            )
            api.copyToClip(details)
            self.trigger_feedback_message(_("Device details copied to clipboard"))

    def on_context_menu(self, event):
        dev = self.get_selected_device()
        if not dev:
            return
        menu = wx.Menu()
        item_ip = menu.Append(wx.ID_ANY, _("Copy IP Address"))
        item_mac = menu.Append(wx.ID_ANY, _("Copy MAC Address"))
        item_all = menu.Append(wx.ID_ANY, _("Copy All Details"))
        menu.AppendSeparator()
        item_web = menu.Append(wx.ID_ANY, _("Open in Web Browser"))

        self.Bind(wx.EVT_MENU, self.on_copy_ip, item_ip)
        self.Bind(wx.EVT_MENU, self.on_copy_mac, item_mac)
        self.Bind(wx.EVT_MENU, self.on_copy_all, item_all)
        self.Bind(wx.EVT_MENU, self.on_open_browser, item_web)

        self.PopupMenu(menu)
        menu.Destroy()


def show_scanner_dialog(devices):
    """Presents the modal scanner results dialog safely on the UI thread."""
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")

    if devices is None:
        if mode in ("beep", "both"):
            tones.beep(250, 80)
        if mode in ("speech", "both"):
            ui.message(_("Not connected to a local network"))
        return

    if not devices:
        if mode in ("beep", "both"):
            tones.beep(250, 80)
        if mode in ("speech", "both"):
            ui.message(_("No active devices found on the local network"))
        return

    gui_parent = getattr(gui, "mainFrame", None)
    if gui_parent:
        gui_parent.prePopup()
    try:
        dialog = NetworkScannerDialog(gui_parent, devices)
        dialog.CenterOnScreen()
        dialog.ShowModal()
        dialog.Destroy()
    finally:
        if gui_parent:
            gui_parent.postPopup()


def start_async_network_scan():
    """
    Initiates non-blocking LAN scan with interruptible audio pulse ticker.
    Fully respects the user's feedbackMode configuration.
    """
    global _is_scanning, _cancel_event

    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")

    if _is_scanning:
        _cancel_event.set()
        _is_scanning = False
        if mode in ("speech", "both"):
            ui.message(_("Scan canceled"))
        if mode in ("beep", "both"):
            tones.beep(400, 40)
        return

    _cancel_event.clear()
    _is_scanning = True

    if mode in ("speech", "both"):
        ui.message(_("Scanning local network, please wait..."))

    def scan_worker():
        global _is_scanning
        ticker_stop = threading.Event()

        # Emit audible pulse ticks only if beep feedback is enabled
        if mode in ("beep", "both"):
            def ticker_loop():
                while not ticker_stop.is_set() and not _cancel_event.is_set():
                    tones.beep(750, 15)
                    if ticker_stop.wait(0.35) or _cancel_event.is_set():
                        break

            ticker_thread = threading.Thread(target=ticker_loop, daemon=True)
            ticker_thread.start()

        devices = None
        try:
            devices = execute_network_scan(_cancel_event)
        finally:
            ticker_stop.set()
            _is_scanning = False

        if not _cancel_event.is_set():
            if mode in ("beep", "both"):
                tones.beep(950, 60)
            wx.CallAfter(show_scanner_dialog, devices)

    threading.Thread(target=scan_worker, daemon=True).start()