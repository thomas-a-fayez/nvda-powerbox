# -*- coding: utf-8 -*-
# smart_path.py - Smart path execution for PowerBox

# Acknowledgment:
# Windows Explorer path retrieval via Shell.Application COM interface 
# is based on standard Windows Shell automation patterns shared within 
# the NVDA add-on development community.

import os
import subprocess
import ctypes
import comtypes.client
import addonHandler

# Initialize translation support for this module
addonHandler.initTranslation()


def get_current_explorer_path():
    """
    Attempts to retrieve the physical file system path of the currently
    focused Windows Explorer window or tab using Shell COM automation.
    Returns:
        str: Absolute directory path if found and valid, otherwise None.
    """
    try:
        foreground_hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not foreground_hwnd:
            return None

        # GA_ROOT = 2: Retrieves the root window handle (crucial for Windows 11 tabbed Explorer)
        root_hwnd = ctypes.windll.user32.GetAncestor(foreground_hwnd, 2)
        valid_hwnds = {foreground_hwnd, root_hwnd}

        # Instantiate Shell.Application using dynamic dispatch via NVDA's comtypes
        shell = comtypes.client.CreateObject("Shell.Application", dynamic=True)
        windows = shell.Windows()

        for window in windows:
            try:
                # Match the active foreground window handle with the Explorer instance
                if getattr(window, "HWND", None) in valid_hwnds:
                    doc = getattr(window, "Document", None)
                    folder = getattr(doc, "Folder", None)
                    self_item = getattr(folder, "Self", None)
                    path = getattr(self_item, "Path", None)

                    if path and os.path.isdir(path):
                        return path
            except Exception:
                # Skip invalid, busy, or non-file Explorer windows (e.g. control panel items)
                continue
    except Exception:
        pass

    return None


def launch_terminal(terminal_type="powershell", as_admin=False):
    """
    Launches the requested terminal application (PowerShell, CMD, or WSL)
    targeted at the current Explorer path, falling back to the user profile directory.

    Args:
        terminal_type (str): "powershell", "cmd", or "wsl".
        as_admin (bool): Whether to request elevated (Administrator) privileges.

    Returns:
        tuple: (success_status (bool), target_path_or_error_message (str))
    """
    target_path = get_current_explorer_path()

    # Fallback to current user's home folder if not in an Explorer folder
    if not target_path or not os.path.isdir(target_path):
        target_path = os.path.expanduser("~")

    try:
        if as_admin:
            # Escape paths appropriately to prevent argument injection or syntax breaks
            if terminal_type == "powershell":
                exe = "powershell.exe"
                # PowerShell escapes single quotes by doubling them (' -> '')
                escaped_path = target_path.replace("'", "''")
                args = f'-NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath \'{escaped_path}\'"'
            elif terminal_type == "cmd":
                exe = "cmd.exe"
                escaped_path = target_path.replace('"', '""')
                args = f'/k cd /d "{escaped_path}"'
            elif terminal_type == "wsl":
                exe = "wsl.exe"
                args = None
            else:
                return False, _("Unsupported terminal type")

            # SW_SHOWNORMAL = 1; 'runas' verb triggers UAC elevation prompt
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", exe, args, target_path, 1
            )

            # ShellExecuteW returns an instance handle > 32 on success
            if result <= 32:
                return False, _("Elevation was canceled or operation failed")
        else:
            # CREATE_NEW_CONSOLE (0x00000010) guarantees a dedicated console window
            flags = subprocess.CREATE_NEW_CONSOLE

            if terminal_type == "cmd":
                cmd_args = ["cmd.exe"]
            elif terminal_type == "powershell":
                cmd_args = ["powershell.exe", "-NoExit"]
            elif terminal_type == "wsl":
                cmd_args = ["wsl.exe"]
            else:
                return False, _("Unsupported terminal type")

            subprocess.Popen(cmd_args, cwd=target_path, creationflags=flags)

        return True, target_path

    except FileNotFoundError:
        return False, _("Terminal executable was not found on this system")
    except Exception as e:
        return False, str(e)