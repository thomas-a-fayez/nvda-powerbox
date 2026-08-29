# -*- coding: utf-8 -*-
# smart_path.py - Smart path execution for PowerBox

import os
import subprocess
import ctypes
import comtypes.client

def get_current_explorer_path():
    """Attempts to retrieve the path of the currently active Windows Explorer window instantly."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        
        # Use NVDA's built-in comtypes with dynamic dispatch instead of win32com
        shell = comtypes.client.CreateObject("Shell.Application", dynamic=True)
        
        for window in shell.Windows():
            if window.HWND == hwnd:
                path = window.Document.Folder.Self.Path
                if path and os.path.isdir(path):
                    return path
    except Exception:
        pass
    return None

def launch_terminal(terminal_type="powershell", as_admin=False):
    """Launches the requested terminal in the current Explorer path or user home directory."""
    path = get_current_explorer_path()
    
    if not path or not os.path.isdir(path):
        path = os.path.expanduser("~")
        
    try:
        if as_admin:
            # Pass explicit startup arguments to force navigation to target directory
            if terminal_type == "powershell":
                exe = "powershell.exe"
                args = f'-NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath \'{path}\'"'
            elif terminal_type == "cmd":
                exe = "cmd.exe"
                args = f'/k cd /d "{path}"'
            else:
                exe = "wsl.exe"
                args = None
            
            # SW_SHOWNORMAL = 1
            result = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, args, None, 1)
            
            # ShellExecuteW returns a value > 32 if successful
            if result <= 32:
                return False, "User canceled elevation or execution failed"
        else:
            # CREATE_NEW_CONSOLE ensures the terminal opens in a fresh standalone window
            flags = subprocess.CREATE_NEW_CONSOLE
            
            if terminal_type == "cmd":
                subprocess.Popen(['cmd.exe'], cwd=path, creationflags=flags)
            elif terminal_type == "powershell":
                subprocess.Popen(['powershell.exe'], cwd=path, creationflags=flags)
            elif terminal_type == "wsl":
                subprocess.Popen(['wsl.exe'], cwd=path, creationflags=flags)
                
        return True, path
    except Exception as e:
        return False, str(e)