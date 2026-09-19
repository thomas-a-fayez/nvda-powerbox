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
import wx
import addonHandler
import config
import ui
import tones

# Initialize translation support for this module
addonHandler.initTranslation()


def get_current_explorer_path():
    """
    Attempts to retrieve the physical file system path of the currently
    focused Windows Explorer window or tab using Shell COM automation.
    """
    try:
        foreground_hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not foreground_hwnd:
            return None

        # GA_ROOT = 2: Retrieves the root window handle (Windows 11 Tabs support)
        root_hwnd = ctypes.windll.user32.GetAncestor(foreground_hwnd, 2)
        valid_hwnds = {foreground_hwnd, root_hwnd}

        shell = comtypes.client.CreateObject("Shell.Application", dynamic=True)
        windows = shell.Windows()

        for window in windows:
            try:
                if getattr(window, "HWND", None) in valid_hwnds:
                    doc = getattr(window, "Document", None)
                    folder = getattr(doc, "Folder", None)
                    self_item = getattr(folder, "Self", None)
                    path = getattr(self_item, "Path", None)

                    if path and os.path.isdir(path):
                        return path
            except Exception:
                continue
    except Exception:
        pass

    return None


def launch_terminal(terminal_type="powershell", as_admin=False):
    """
    Launches the requested terminal targeted at the current Explorer path.
    Returns:
        tuple: (success_status (bool), target_path_or_error_message (str))
    """
    target_path = get_current_explorer_path()

    if not target_path or not os.path.isdir(target_path):
        target_path = os.path.expanduser("~")

    try:
        if as_admin:
            if terminal_type == "powershell":
                exe = "powershell.exe"
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

            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", exe, args, target_path, 1
            )
            if result <= 32:
                return False, _("Elevation was canceled or operation failed")
        else:
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


def open_terminal(terminal_type="powershell", as_admin=False):
    """
    High-level orchestrator: Launches terminal and applies unified feedbackMode.
    """
    success, result = launch_terminal(terminal_type, as_admin=as_admin)
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")

    if success:
        folder_name = os.path.basename(result.rstrip("\\/")) or result
        if terminal_type == "powershell":
            name = _("PowerShell Admin") if as_admin else _("PowerShell")
        elif terminal_type == "cmd":
            name = _("Command Prompt Admin") if as_admin else _("Command Prompt")
        elif terminal_type == "wsl":
            name = _("WSL")
        else:
            name = terminal_type

        msg = _("{terminal} opened in {folder}").format(terminal=name, folder=folder_name)

        if mode in ("beep", "both"):
            tones.beep(500, 50)
        if mode in ("speech", "both"):
            wx.CallLater(1000, ui.message, msg)
    else:
        err_msg = result if result else _("Failed to open terminal")
        if mode in ("beep", "both"):
            tones.beep(200, 80)
        if mode in ("speech", "both"):
            ui.message(err_msg)