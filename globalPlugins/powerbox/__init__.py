# -*- coding: utf-8 -*-
# PowerBox add-on for NVDA - Main Plugin File

# Acknowledgment: 
# The layer command routing logic (getScript and script_error overrides) 
# is inspired by and derived from the original work of Tyler Spivey and Joseph Lee.

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

# Initialize translation support for this module
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

        # Smart Mouse mappings
        "kb:NVDA+windows+c": "smartLeftClick",
        "kb:NVDA+windows+x": "smartRightClick",
        "kb:NVDA+windows+z": "smartDoubleClick",

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


    # --- Layered Gestures Logic ---
    def getScript(self, gesture):
        # If not in any active layer, fallback to standard NVDA gesture routing
        if not self.inTerminalLayer and not self.inAppLayer:
            return super(GlobalPlugin, self).getScript(gesture)

        # Inside a layer: intercept the next pressed key
        script = super(GlobalPlugin, self).getScript(gesture)
        if not script:
            script = self.script_error

        # Ensure the layer is dismissed after script invocation
        def wrapped_script(gesture):
            try:
                script(gesture)
            finally:
                self.finishLayer()
        return wrapped_script

    def finishLayer(self):
        # Reset layer flags and restore default global gesture bindings
        self.inTerminalLayer = False
        self.inAppLayer = False
        self.clearGestureBindings()
        self.bindGestures(self.__gestures)

    def script_error(self, gesture):
        # Audible cue when an unmapped key is pressed inside a layer
        tones.beep(120, 100)

    # --- Terminal Scripts ---
    @scriptHandler.script(description=_("Terminal Layer: Press p, shift+p, c, shift+c, or w next"))
    def script_terminalLayer(self, gesture):
        if self.inTerminalLayer:
            self.script_error(gesture)
            return

        # Bind temporary layer sub-gestures
        self.bindGestures({
            "kb:p": "openPowerShell",
            "kb:shift+p": "openPowerShellAdmin",
            "kb:c": "openCMD",
            "kb:shift+c": "openCMDAdmin",
            "kb:w": "openWSL",
            "kb:h": "layerHelp",
        })
        self.inTerminalLayer = True
        tones.beep(500, 50)

    @scriptHandler.script(description=_("Opens PowerShell in the current Explorer directory"))
    def script_openPowerShell(self, gesture):
        success, result = smart_path.launch_terminal("powershell", as_admin=False)
        if success:
            msg = _("PowerShell opened in {folder}").format(folder=os.path.basename(result))
            wx.CallLater(1000, ui.message, msg)
        else:
            # Speak failure immediately with the exact returned error reason
            ui.message(result if result else _("Failed to open PowerShell"))

    @scriptHandler.script(description=_("Opens PowerShell as Administrator in the current Explorer directory"))
    def script_openPowerShellAdmin(self, gesture):
        success, result = smart_path.launch_terminal("powershell", as_admin=True)
        if success:
            msg = _("PowerShell Admin opened in {folder}").format(folder=os.path.basename(result))
            wx.CallLater(1000, ui.message, msg)
        else:
            # Speak failure immediately with the exact returned error reason
            ui.message(result if result else _("Failed to open PowerShell as Administrator"))

    @scriptHandler.script(description=_("Opens Command Prompt in the current Explorer directory"))
    def script_openCMD(self, gesture):
        success, result = smart_path.launch_terminal("cmd", as_admin=False)
        if success:
            msg = _("Command Prompt opened in {folder}").format(folder=os.path.basename(result))
            wx.CallLater(1000, ui.message, msg)
        else:
            # Speak failure immediately with the exact returned error reason
            ui.message(result if result else _("Failed to open Command Prompt"))

    @scriptHandler.script(description=_("Opens Command Prompt as Administrator in the current Explorer directory"))
    def script_openCMDAdmin(self, gesture):
        success, result = smart_path.launch_terminal("cmd", as_admin=True)
        if success:
            msg = _("Command Prompt Admin opened in {folder}").format(folder=os.path.basename(result))
            wx.CallLater(1000, ui.message, msg)
        else:
            # Speak failure immediately with the exact returned error reason
            ui.message(result if result else _("Failed to open Command Prompt as Administrator"))

    @scriptHandler.script(description=_("Opens WSL in the current Explorer directory"))
    def script_openWSL(self, gesture):
        success, result = smart_path.launch_terminal("wsl", as_admin=False)
        if success:
            msg = _("WSL opened in {folder}").format(folder=os.path.basename(result))
            wx.CallLater(1000, ui.message, msg)
        else:
            # Speak failure immediately with the exact returned error reason
            ui.message(result if result else _("Failed to open WSL"))

    # --- Smart Mouse Scripts ---
    @scriptHandler.script(description=_("Routes mouse pointer to current object center and left clicks"))
    def script_smartLeftClick(self, gesture):
        actions.perform_smart_click("left", _("Smart Left Click"))

    @scriptHandler.script(description=_("Routes mouse pointer to current object center and right clicks"))
    def script_smartRightClick(self, gesture):
        actions.perform_smart_click("right", _("Smart Right Click"))

    @scriptHandler.script(description=_("Routes mouse pointer to current object center and double clicks"))
    def script_smartDoubleClick(self, gesture):
        actions.perform_smart_click("double", _("Smart Double Click"))

    # --- Keyboard Scripts ---
    @scriptHandler.script(description=_("Applications menu"))
    def script_pressApplications(self, gesture):
        actions.perform_action(actions.VK_APPS, _("Applications menu"), extended=True)

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
        if self.inAppLayer or self.inTerminalLayer:
            self.script_error(gesture)
            return

        self.bindGestures({
            "kb:c": "launchCalculator",
            "kb:m": "launchMail",
            "kb:b": "launchBrowserHome",
            "kb:e": "launchExplorer",
            "kb:p": "launchMediaPlayer",
            "kb:h": "layerHelp",
        })
        self.inAppLayer = True
        tones.beep(400, 60)

    @scriptHandler.script(description=_("Launches the default Calculator"))
    def script_launchCalculator(self, gesture):
        wx.CallLater(100, actions.perform_action, actions.VK_LAUNCH_APP2, _("Calculator"), extended=True)

    @scriptHandler.script(description=_("Launches the default Mail application"))
    def script_launchMail(self, gesture):
        wx.CallLater(100, actions.perform_action, actions.VK_LAUNCH_MAIL, _("Mail"), extended=True)

    @scriptHandler.script(description=_("Launches the default Browser homepage"))
    def script_launchBrowserHome(self, gesture):
        wx.CallLater(100, actions.perform_action, actions.VK_BROWSER_HOME, _("Browser Home"), extended=True)

    @scriptHandler.script(description=_("Launches File Explorer / This PC"))
    def script_launchExplorer(self, gesture):
        wx.CallLater(100, actions.perform_action, actions.VK_LAUNCH_APP1, _("File Explorer"), extended=True)

    @scriptHandler.script(description=_("Launches the default Media Player"))
    def script_launchMediaPlayer(self, gesture):
        wx.CallLater(100, actions.perform_action, actions.VK_LAUNCH_MEDIA_SELECT, _("Media Player"), extended=True)

    # --- Network Scripts ---
    @scriptHandler.script(description=_("Speaks the Local IP. Press twice quickly to copy to clipboard."))
    def script_getLocalIP(self, gesture):
        ip = network_info.get_local_ip()
        if scriptHandler.getLastScriptRepeatCount() == 1:
            api.copyToClip(ip)
            ui.message(_("Local IP {ip} copied to clipboard").format(ip=ip))
        else:
            ui.message(_("Local IP: {ip}").format(ip=ip))

    @scriptHandler.script(description=_("Speaks the Public IP. Press twice quickly to copy to clipboard."))
    def script_getPublicIP(self, gesture):
        import threading

        # Detect double tap before dispatching the background worker
        is_double_press = (scriptHandler.getLastScriptRepeatCount() == 1)

        def worker():
            success, result = network_info.get_public_ip()
            if not success:
                wx.CallAfter(ui.message, result)
                return

            if is_double_press:
                wx.CallAfter(api.copyToClip, result)
                wx.CallAfter(ui.message, _("Public IP {ip} copied to clipboard").format(ip=result))
            else:
                wx.CallAfter(ui.message, _("Public IP: {ip}").format(ip=result))

        # Run network call asynchronously to prevent NVDA UI freeze
        threading.Thread(target=worker, daemon=True).start()

    # --- Global Help Script ---
    @scriptHandler.script(description=_("Shows PowerBox Global Help"))
    def script_globalHelp(self, gesture):
        help_manager.show_global_help(self)

    # --- Contextual Layer Help Script ---
    @scriptHandler.script(description=_("Shows help for the currently active layer"))
    def script_layerHelp(self, gesture):
        if self.inAppLayer:
            layer_title = _("Quick Apps Layer")
            keys_dict = {
                "c": _("Launch Calculator"),
                "m": _("Launch Mail"),
                "b": _("Launch Browser Home"),
                "e": _("Launch File Explorer (This PC)"),
                "p": _("Launch Media Player"),
                "h": _("Show this help message"),
            }
        elif self.inTerminalLayer:
            layer_title = _("Terminal Layer")
            keys_dict = {
                "c": _("Command Prompt"),
                "shift+c": _("Command Prompt (Admin)"),
                "p": _("PowerShell"),
                "shift+p": _("PowerShell (Admin)"),
                "w": _("WSL"),
                "h": _("Show this help message"),
            }
        else:
            self.finishLayer()
            return

        # Critical: Finish the layer prior to displaying the UI to prevent focus lockups
        self.finishLayer()
        help_manager.show_layer_help(layer_title, keys_dict)