# -*- coding: utf-8 -*-
# network_info.py - Network utility functions for PowerBox

import socket
import urllib.request
import urllib.error

def get_local_ip():
    """
    Retrieves the local IPv4 address of the machine.
    Uses a UDP socket to determine the active network interface.
    """
    try:
        # Connect to a dummy external IP to force the OS to use the active local interface
        # No actual data is sent, so it's instantaneous and works offline
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip
    except Exception:
        # Fallback if no network interface is active
        return "127.0.0.1 (Offline)"

def get_public_ip():
    """
    Retrieves the public IPv4 address using an external API.
    Returns a tuple: (success_boolean, ip_or_error_message).
    """
    try:
        # We use a short timeout (2.5 seconds) so NVDA doesn't freeze if there's no internet
        request = urllib.request.Request("https://api.ipify.org")
        with urllib.request.urlopen(request, timeout=2.5) as response:
            public_ip = response.read().decode('utf-8').strip()
        return True, public_ip
    except urllib.error.URLError:
        return False, "No internet connection"
    except Exception as e:
        return False, f"Error retrieving public IP"