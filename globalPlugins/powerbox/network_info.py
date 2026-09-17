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
import urllib.request
import urllib.error
import addonHandler

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
    """
    Retrieves the local IPv4 address of the active network adapter.
    Uses a lightweight UDP connection check that does not send actual network packets.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            # Route check against a known external IP to determine the local interface
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except Exception:
        # Fallback message when offline or no network adapter is active
        return _("127.0.0.1 (Offline)")


def get_default_gateway():
    """
    Retrieves the IPv4 address of the local network default gateway (router).
    Directly queries the Windows routing table via GetBestRoute without network latency.

    Returns:
        str: Gateway IP address if connected to a network, otherwise None.
    """
    try:
        # Lookup the best route towards an external address to find the active gateway
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
    """
    Fetches the machine's external IPv4 address via a lightweight HTTP API.
    Returns:
        tuple: (success_status (bool), ip_address_or_localized_error (str))
    """
    try:
        # Keep the timeout short (2.5s) to avoid noticeable UI lag in NVDA
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