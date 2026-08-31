# -*- coding: utf-8 -*-
# PowerBox add-on for NVDA - Main Plugin File

import os
import wx
import globalPluginHandler
import scriptHandler
import addonHandler
import config
import gui
import ui
import api
import tones
from . import actions
from . import smart_path
from . import network_info
from .settings_gui import PowerBoxSettingsPanel
from . import help_manager

addonHandler.initTranslation()

# --- Configuration Settings ---
confspec = {
    "feedbackMode": "string(default='beep')",
}
config.conf.spec["powerBox"] = confspec


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = _("PowerBox")

    __gestures = {
        # Keyboard Media/Browser mappings
        "kb:NVDA+windows+a": "pressApplications",
        "kb:NVDA+windows+m": "volumeMute",
        "kb:NVDA+windows+downArrow": "volumeDown",
        "kb:NVDA+windows+upArrow": "volumeUp",
        "kb:NVDA+windows+p": "playPause",
        "kb:NVDA+windows+rightArrow": "nextTrack",
        "kb:NVDA+windows+leftArrow": "prevTrack",
        "kb:NVDA+windows+backspace": "browserBack",
        "kb:NVDA+windows+enter": "browserForward",
        "kb:NVDA+windows+r": "browserRefresh",
        
        # Quick Application mappings
        "kb:NVDA+windows+q": "appLayer",

        # Mouse mappings
        "kb:NVDA+windows+c": "leftClick",
        "kb:NVDA+windows+x": "rightClick",
        "kb:NVDA+windows+z": "doubleClick",

        # Terminal paths mappings
        "kb:NVDA+windows+t": "terminalLayer",

        # Network mappings
        "kb:NVDA+windows+i": "getLocalIP",
        "kb:NVDA+windows+shift+i": "getPublicIP",

        # Global Help mapping
        "kb:NVDA+windows+h": "globalHelp",
    }

    def __init__(self, *args, **kwargs):
        super(GlobalPlugin, self).__init__(*args, **kwargs)
        gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(PowerBoxSettingsPanel)

        # Track active layers
        self.inTerminalLayer = False 
        self.inAppLayer = False

    def terminate(self):
        try:
            gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(PowerBoxSettingsPanel)
        except ValueError:
            pass
        super(GlobalPlugin, self).terminate()

    # Acknowledgment: 
    # The layer command routing logic (getScript and script_error overrides) 
    # is inspired by and derived from the original work of Tyler Spivey and Joseph Lee.

    # --- Layered Gestures Logic ---
    def getScript(self, gesture):
        # If not in ANY layer, use normal NVDA behavior
        if not self.inTerminalLayer and not self.inAppLayer:
            return super(GlobalPlugin, self).getScript(gesture)
        
        # We are inside a layer, catch the next key pressed
        script = super(GlobalPlugin, self).getScript(gesture)
        if not script:
            script = self.script_error

        # Wrap the script to ensure we exit the layer after execution
        def wrapped_script(gesture):
            try:
                script(gesture)
            finally:
                self.finishLayer()  # Unified finish function
        return wrapped_script

    def finishLayer(self):
        # Reset ALL layer states and restore original normal gestures
        self.inTerminalLayer = False
        self.inAppLayer = False
        self.clearGestureBindings()
        self.bindGestures(self.__gestures)

    def script_error(self, gesture):
        # Low beep if user presses an unassigned key inside any layer
        tones.beep(120, 100)

    # --- Terminal Scripts ---
    @scriptHandler.script(description=_("Terminal Layer: Press p, shift+p, c, shift+c, or w next"))
    def script_terminalLayer(self, gesture):
        if self.inTerminalLayer:
            self.script_error(gesture)
            return
        
        # Bind the temporary sub-keys
        # Note: You can change "kb:p" to "kb:shift+p" if you prefer
        self.bindGestures({
            "kb:p": "openPowerShell",
            "kb:shift+p": "openPowerShellAdmin",
            "kb:c": "openCMD",
            "kb:shift+c": "openCMDAdmin",
            "kb:w": "openWSL",
            "kb:h": "layerHelp",
        })
        self.inTerminalLayer = True
        tones.beep(500, 50)  # High beep for entering the layer successfully

    @scriptHandler.script(description=_("Opens PowerShell in the current Explorer directory"))
    def script_openPowerShell(self, gesture):
        # Execute terminal launch and fetch path/status
        success, path = smart_path.launch_terminal("powershell", as_admin=False)
        if success:
            msg = _("PowerShell opened in {folder}").format(folder=os.path.basename(path))
        else:
            msg = _("Failed to open PowerShell")

        # Speak after window takes focus
        wx.CallLater(1000, ui.message, msg)

    @scriptHandler.script(description=_("Opens PowerShell as Administrator in the current Explorer directory"))
    def script_openPowerShellAdmin(self, gesture):
        # Execute terminal launch with admin privileges
        success, path = smart_path.launch_terminal("powershell", as_admin=True)
        if success:
            msg = _("PowerShell Admin opened in {folder}").format(folder=os.path.basename(path))
        else:
            msg = _("Failed to open PowerShell as Administrator")

        # Speak after window takes focus
        wx.CallLater(1000, ui.message, msg)

    @scriptHandler.script(description=_("Opens Command Prompt in the current Explorer directory"))
    def script_openCMD(self, gesture):
        # Execute CMD launch and fetch path/status
        success, path = smart_path.launch_terminal("cmd", as_admin=False)
        if success:
            msg = _("Command Prompt opened in {folder}").format(folder=os.path.basename(path))
        else:
            msg = _("Failed to open Command Prompt")

        # Speak after window takes focus
        wx.CallLater(1000, ui.message, msg)

    @scriptHandler.script(description=_("Opens Command Prompt as Administrator in the current Explorer directory"))
    def script_openCMDAdmin(self, gesture):
        # Execute CMD launch with admin privileges
        success, path = smart_path.launch_terminal("cmd", as_admin=True)
        if success:
            msg = _("Command Prompt Admin opened in {folder}").format(folder=os.path.basename(path))
        else:
            msg = _("Failed to open Command Prompt as Administrator")

        # Speak after window takes focus
        wx.CallLater(1000, ui.message, msg)

    @scriptHandler.script(description=_("Opens WSL in the current Explorer directory"))
    def script_openWSL(self, gesture):
        # Execute WSL launch and fetch path/status
        success, path = smart_path.launch_terminal("wsl", as_admin=False)
        if success:
            msg = _("WSL opened in {folder}").format(folder=os.path.basename(path))
        else:
            msg = _("Failed to open WSL")

        # Speak after window takes focus
        wx.CallLater(1000, ui.message, msg)

    # --- Mouse Scripts ---
    @scriptHandler.script(description=_("Simulates a Left Mouse Click"))
    def script_leftClick(self, gesture):
        actions.perform_mouse_action("left", _("Left Click"))

    @scriptHandler.script(description=_("Simulates a Right Mouse Click"))
    def script_rightClick(self, gesture):
        actions.perform_mouse_action("right", _("Right Click"))

    @scriptHandler.script(description=_("Simulates a Double Mouse Click"))
    def script_doubleClick(self, gesture):
        actions.perform_mouse_action("double", _("Double Click"))

    # --- Keyboard Scripts ---
    @scriptHandler.script(description=_("Applications menu"))
    def script_pressApplications(self, gesture):
        actions.perform_action(actions.VK_APPS, _("Applications menu"))

    @scriptHandler.script(description=_("Volume Mute"))
    def script_volumeMute(self, gesture):
        actions.perform_action(actions.VK_VOLUME_MUTE, _("Volume Mute"), extended=True)

    @scriptHandler.script(description=_("Volume Down"))
    def script_volumeDown(self, gesture):
        actions.perform_action(actions.VK_VOLUME_DOWN, _("Volume Down"), extended=True)

    @scriptHandler.script(description=_("Volume Up"))
    def script_volumeUp(self, gesture):
        actions.perform_action(actions.VK_VOLUME_UP, _("Volume Up"), extended=True)

    @scriptHandler.script(description=_("Play/Pause"))
    def script_playPause(self, gesture):
        actions.perform_action(actions.VK_MEDIA_PLAY_PAUSE, _("Play Pause"), extended=True)

    @scriptHandler.script(description=_("Next Track"))
    def script_nextTrack(self, gesture):
        actions.perform_action(actions.VK_MEDIA_NEXT_TRACK, _("Next Track"), extended=True)

    @scriptHandler.script(description=_("Previous Track"))
    def script_prevTrack(self, gesture):
        actions.perform_action(actions.VK_MEDIA_PREV_TRACK, _("Previous Track"), extended=True)

    @scriptHandler.script(description=_("Browser Back"))
    def script_browserBack(self, gesture):
        actions.perform_action(actions.VK_BROWSER_BACK, _("Browser Back"), extended=True)

    @scriptHandler.script(description=_("Browser Forward"))
    def script_browserForward(self, gesture):
        actions.perform_action(actions.VK_BROWSER_FORWARD, _("Browser Forward"), extended=True)

    @scriptHandler.script(description=_("Browser Refresh"))
    def script_browserRefresh(self, gesture):
        actions.perform_action(actions.VK_BROWSER_REFRESH, _("Browser Refresh"), extended=True)

    # --- Quick Application Scripts ---
    @scriptHandler.script(description=_("Quick Apps Layer: Press c, m, b, e, or p next"))
    def script_appLayer(self, gesture):
        # Prevent activating a layer if another one is already active
        if self.inAppLayer or self.inTerminalLayer:
            self.script_error(gesture)
            return
        
        # Bind the temporary sub-keys for applications
        self.bindGestures({
            "kb:c": "launchCalculator",
            "kb:m": "launchMail",
            "kb:b": "launchBrowserHome",
            "kb:e": "launchExplorer",
            "kb:p": "launchMediaPlayer",
            "kb:h": "layerHelp",
        })
        self.inAppLayer = True
        
        # Unique beep for App Layer (slightly lower pitch than Terminal layer) to distinguish them
        tones.beep(400, 60)

    @scriptHandler.script(description=_("Launches the default Calculator"))
    def script_launchCalculator(self, gesture):
        # Delay the simulated key press by 100ms to allow finishLayer() to clean up the keyboard hooks
        wx.CallLater(100, actions.perform_action, actions.VK_LAUNCH_APP2, _("Calculator"), extended=True)

    @scriptHandler.script(description=_("Launches the default Mail application"))
    def script_launchMail(self, gesture):
        wx.CallLater(100, actions.perform_action, actions.VK_LAUNCH_MAIL, _("Mail"), extended=True)

    @scriptHandler.script(description=_("Launches the default Browser homepage"))
    def script_launchBrowserHome(self, gesture):
        wx.CallLater(100, actions.perform_action, actions.VK_BROWSER_HOME, _("Browser Home"), extended=True)

    @scriptHandler.script(description=_("Launches My Computer / File Explorer"))
    def script_launchExplorer(self, gesture):
        wx.CallLater(100, actions.perform_action, actions.VK_LAUNCH_APP1, _("Explorer"), extended=True)

    @scriptHandler.script(description=_("Launches the default Media Player"))
    def script_launchMediaPlayer(self, gesture):
        wx.CallLater(100, actions.perform_action, actions.VK_LAUNCH_MEDIA_SELECT, _("Media Player"), extended=True)

    # --- Network Scripts ---
    @scriptHandler.script(description=_("Speaks the Local IP. Press twice quickly to copy to clipboard."))
    def script_getLocalIP(self, gesture):
        ip = network_info.get_local_ip()
        
        # Check if the user double-tapped the shortcut
        if scriptHandler.getLastScriptRepeatCount() == 1:
            api.copyToClip(ip)
            ui.message(_("Local IP {ip} copied to clipboard").format(ip=ip))
        else:
            ui.message(_("Local IP: {ip}").format(ip=ip))

    @scriptHandler.script(description=_("Speaks the Public IP. Press twice quickly to copy to clipboard."))
    def script_getPublicIP(self, gesture):
        success, result = network_info.get_public_ip()
        
        if not success:
            # If no internet, just speak the error
            ui.message(result)
            return
            
        # Check if the user double-tapped the shortcut
        if scriptHandler.getLastScriptRepeatCount() == 1:
            api.copyToClip(result)
            ui.message(_("Public IP {ip} copied to clipboard").format(ip=result))
        else:
            ui.message(_("Public IP: {ip}").format(ip=result))

    # --- Global Help Script ---
    @scriptHandler.script(description=_("Shows PowerBox Global Help"))
    def script_globalHelp(self, gesture):
        # Call the external help manager to display global shortcuts
        help_manager.show_global_help(self)

    # --- Contextual Layer Help Script ---
    @scriptHandler.script(description=_("Shows help for the currently active layer"))
    def script_layerHelp(self, gesture):
        # Determine which layer is active and build the corresponding dictionary
        if self.inAppLayer:
            layer_title = "Quick Apps Layer"
            keys_dict = {
                "c": _("Launch Calculator"),
                "m": _("Launch Mail"),
                "b": _("Launch Browser Home"),
                "e": _("Launch Explorer"),
                "p": _("Launch Media Player"),
                "h": _("Show this help message")
            }
        elif self.inTerminalLayer:
            layer_title = "Terminal Layer"
            keys_dict = {
                "c": _("Command Prompt"),
                "shift+c": _("Command Prompt (Admin)"),  # تم تصحيح هذا
                "p": _("PowerShell"),
                "shift+p": _("PowerShell (Admin)"),      # تمت إضافة هذا
                "w": _("WSL"),
                "h": _("Show this help message")
            }
        else:
            # If no layer is active for some reason, just exit safely
            self.finishLayer()
            return
            
        # CRITICAL: We must finish the layer BEFORE showing the UI message
        # This removes the keyboard hooks and prevents NVDA/Windows from freezing
        self.finishLayer()
        
        # Send the gathered data to the help manager to display
        help_manager.show_layer_help(layer_title, keys_dict)