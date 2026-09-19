# -*- coding: utf-8 -*-
# network_info.py - Network utility functions for PowerBox

# Acknowledgment:
# - Local IP detection using the UDP socket routable interface trick is derived 
#   from standard Python community practices.
# - Public IP retrieval uses the free and open API provided by ipify (https://www.ipify.org).
# - Default Gateway detection queries the Windows routing table using GetBestRoute (iphlpapi.dll).

import ctypes
import socket
import struct
import threading
import urllib.request
import urllib.error
import wx
import addonHandler
import api
import config
import ui
import tones

# Initialize translation support for this module
addonHandler.initTranslation()


class _MIB_IPFORWARDROW(ctypes.Structure):
    """Structure representing a route entry in the Windows IPv4 routing table."""
    _fields_ = [
        ("dwForwardDest", ctypes.c_ulong),
        ("dwForwardMask", ctypes.c_ulong),
        ("dwForwardPolicy", ctypes.c_ulong),
        ("dwForwardNextHop", ctypes.c_ulong),
        ("dwForwardIfIndex", ctypes.c_ulong),
        ("dwForwardType", ctypes.c_ulong),
        ("dwForwardProto", ctypes.c_ulong),
        ("dwForwardAge", ctypes.c_ulong),
        ("dwForwardNextHopAS", ctypes.c_ulong),
        ("dwForwardMetric1", ctypes.c_ulong),
        ("dwForwardMetric2", ctypes.c_ulong),
        ("dwForwardMetric3", ctypes.c_ulong),
        ("dwForwardMetric4", ctypes.c_ulong),
        ("dwForwardMetric5", ctypes.c_ulong),
    ]


def get_local_ip():
    """Retrieves the local IPv4 address of the active network adapter."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except Exception:
        return _("127.0.0.1 (Offline)")


def get_default_gateway():
    """Retrieves the IPv4 address of the local network default gateway (router)."""
    try:
        dest_ip = struct.unpack("<I", socket.inet_aton("8.8.8.8"))[0]
        row = _MIB_IPFORWARDROW()
        status = ctypes.windll.iphlpapi.GetBestRoute(dest_ip, 0, ctypes.byref(row))

        if status == 0:
            gateway_ip = socket.inet_ntoa(struct.pack("<I", row.dwForwardNextHop))
            if gateway_ip and gateway_ip != "0.0.0.0":
                return gateway_ip
    except Exception:
        pass
    return None


def get_public_ip():
    """Fetches external IPv4 address via ipify API."""
    try:
        request = urllib.request.Request(
            "https://api.ipify.org",
            headers={"User-Agent": "PowerBox-NVDA-Addon"}
        )
        with urllib.request.urlopen(request, timeout=2.5) as response:
            public_ip = response.read().decode("utf-8").strip()
            return True, public_ip
    except (urllib.error.URLError, socket.timeout):
        return False, _("No internet connection")
    except Exception:
        return False, _("Error retrieving public IP")


# --- High-level User Actions with Unified Feedback Handling ---
def trigger_copy_data(data_str, copy_msg, info_msg, beep_pitch=800):
    """Copies data to clipboard and ensures information is spoken/confirmed cleanly."""
    api.copyToClip(data_str)
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")

    if mode in ("beep", "both"):
        tones.beep(beep_pitch, 40)

    if mode in ("speech", "both"):
        ui.message(copy_msg)
    else:
        ui.message(info_msg)


def speak_local_ip():
    ip = get_local_ip()
    ui.message(_("Local IP: {ip}").format(ip=ip))


def copy_local_ip():
    ip = get_local_ip()
    trigger_copy_data(
        ip,
        _("Local IP {ip} copied to clipboard").format(ip=ip),
        _("Local IP: {ip}").format(ip=ip)
    )


def speak_default_gateway():
    gw = get_default_gateway()
    if gw:
        ui.message(_("Default Gateway: {gw}").format(gw=gw))
    else:
        ui.message(_("Default Gateway unavailable"))


def copy_default_gateway():
    gw = get_default_gateway()
    if gw:
        trigger_copy_data(
            gw,
            _("Default Gateway {gw} copied to clipboard").format(gw=gw),
            _("Default Gateway: {gw}").format(gw=gw)
        )
    else:
        ui.message(_("Default Gateway unavailable"))


def speak_public_ip():
    def worker():
        success, result = get_public_ip()
        if not success:
            wx.CallAfter(ui.message, result)
            return
        wx.CallAfter(ui.message, _("Public IP: {ip}").format(ip=result))
    threading.Thread(target=worker, daemon=True).start()


def copy_public_ip():
    def worker():
        success, result = get_public_ip()
        if not success:
            wx.CallAfter(ui.message, result)
            return
        wx.CallAfter(
            trigger_copy_data,
            result,
            _("Public IP {ip} copied to clipboard").format(ip=result),
            _("Public IP: {ip}").format(ip=result)
        )
    threading.Thread(target=worker, daemon=True).start()