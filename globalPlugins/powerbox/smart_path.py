# -*- coding: utf-8 -*-
# smart_path.py - Smart path execution for PowerBox

# Acknowledgment:
# - Windows Explorer active tab path resolution uses native window title and focus inspection
#   paired with safe Shell.Application COM querying, eliminating C++ assertion crashes.
# - Detached terminal process spawning via Win32 ShellExecuteW prevents child process handle lockups.

import os
import ctypes
import comtypes.client
import wx
import addonHandler
import api
import config
import ui
import tones
import winUser

# Initialize translation support for this module
addonHandler.initTranslation()


def get_current_explorer_path():
    """
    Intelligently retrieves the physical path of the active Explorer window/tab.
    Language-independent: Detects virtual shell locations (Home, This PC, etc.)
    using Windows Shell path characteristics, gracefully defaulting to user home.
    """
    try:
        focus = api.getFocusObject()
        if not focus:
            return os.path.expanduser("~")

        # 1. Verify that the active application is Windows Explorer
        app_name = getattr(getattr(focus, "appModule", None), "appName", "").lower()
        if app_name != "explorer":
            return os.path.expanduser("~")

        foreground_hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not foreground_hwnd:
            return os.path.expanduser("~")

        root_hwnd = ctypes.windll.user32.GetAncestor(foreground_hwnd, 2)
        if not root_hwnd:
            root_hwnd = foreground_hwnd

        # In all Windows languages, the window title equals the active tab's LocationName
        window_title = winUser.getWindowText(root_hwnd).strip().lower()
        focus_name = getattr(focus, "name", "").strip().lower()

        # Check for Desktop (Progman / WorkerW)
        class_buf = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetClassNameW(root_hwnd, class_buf, 256)
        if class_buf.value in ("Progman", "WorkerW"):
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            if os.path.isdir(desktop_path):
                return desktop_path

        shell = comtypes.client.CreateObject("Shell.Application", dynamic=True)
        windows = shell.Windows()

        matched_physical_path = None
        active_tab_is_virtual = False

        for window in windows:
            try:
                w_hwnd = getattr(window, "HWND", None)
                if w_hwnd == root_hwnd:
                    doc = getattr(window, "Document", None)
                    folder = getattr(doc, "Folder", None)
                    self_item = getattr(folder, "Self", None)
                    path = getattr(self_item, "Path", None)
                    loc_name = getattr(window, "LocationName", "").strip().lower()

                    # Language-agnostic active tab matching
                    is_active_tab = bool(
                        loc_name and (loc_name == window_title or loc_name in window_title or window_title in loc_name)
                    )

                    # Identify Virtual Shell Folders (Path starts with '::' or is not a filesystem directory)
                    is_virtual_path = (
                        not path 
                        or not isinstance(path, str) 
                        or path.startswith("::") 
                        or not os.path.isdir(path)
                    )

                    if is_active_tab:
                        if is_virtual_path:
                            # The active tab is a virtual location (Home, This PC, etc.) in ANY language!
                            active_tab_is_virtual = True
                            break
                        else:
                            # The active tab is a valid physical filesystem folder
                            matched_physical_path = path
                            break

                    # Secondary check: If focused item explicitly belongs to this physical folder view
                    if not is_virtual_path:
                        try:
                            focused_item = getattr(doc, "FocusedItem", None)
                            if focused_item and getattr(focused_item, "Name", "").strip().lower() == focus_name:
                                matched_physical_path = path
                        except Exception:
                            pass
            except Exception:
                continue

        # If the active tab was positively identified as a virtual folder, default to home directory
        if active_tab_is_virtual:
            return os.path.expanduser("~")

        if matched_physical_path and os.path.isdir(matched_physical_path):
            return matched_physical_path

    except Exception:
        pass

    return os.path.expanduser("~")


def launch_terminal(terminal_type="powershell", as_admin=False):
    """
    Launches the requested terminal targeted at the discovered path.
    Spawns an entirely detached OS process using ShellExecuteW.
    """
    target_path = get_current_explorer_path()
    if not target_path or not os.path.isdir(target_path):
        target_path = os.path.expanduser("~")

    try:
        verb = "runas" if as_admin else "open"

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

        # SW_SHOWNORMAL = 1; Detached process execution
        result = ctypes.windll.shell32.ShellExecuteW(
            None, verb, exe, args, target_path, 1
        )

        if result <= 32:
            return False, _("Elevation was canceled or operation failed")

        return True, target_path

    except FileNotFoundError:
        return False, _("Terminal executable was not found on this system")
    except Exception as e:
        return False, str(e)


def open_terminal(terminal_type="powershell", as_admin=False):
    """
    Executes terminal launch on the main thread safely.
    Uses wx.CallLater on the main thread, strictly avoiding C++ assertion crashes.
    """
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
    success, result = launch_terminal(terminal_type, as_admin=as_admin)

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
            # Safe execution on the main UI thread (Zero C++ assertion errors)
            wx.CallLater(1000, ui.message, msg)
    else:
        err_msg = result if result else _("Failed to open terminal")
        if mode in ("beep", "both"):
            tones.beep(200, 80)
        if mode in ("speech", "both"):
            ui.message(err_msg)