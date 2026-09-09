# -*- coding: utf-8 -*-
# network_info.py - Network utility functions for PowerBox

# Acknowledgment:
# - Local IP detection using the UDP socket routable interface trick is derived 
#   from standard Python community practices.
# - Public IP retrieval uses the free and open API provided by ipify (https://www.ipify.org).

import socket
import urllib.request
import urllib.error
import addonHandler

# Initialize translation support for this module
addonHandler.initTranslation()


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