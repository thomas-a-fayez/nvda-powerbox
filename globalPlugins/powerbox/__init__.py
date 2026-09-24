# -*- coding: utf-8 -*-
# PowerBox add-on for NVDA - Main Plugin File

# Acknowledgment: 
# The layer command routing logic (getScript and script_error overrides) 
# is inspired by and derived from the original work of Tyler Spivey and Joseph Lee.

import wx
import globalPluginHandler
import scriptHandler
import addonHandler
import config
import gui
import ui
import tones
from . import actions
from . import smart_path
from . import network_info
from . import network_scanner
from . import power_manager
from . import audio_manager
from . import process_inspector
from . import server_process_hub
from . import process_network_tracker
from . import file_manager
from .settings_gui import PowerBoxSettingsPanel
from . import help_manager

# Initialize translation support for this module
addonHandler.initTranslation()

# --- Configuration Settings Specification ---
confspec = {
    "feedbackMode": "string(default='beep')",
    "powerConfirmStyle": "string(default='dialog')",
    "fileSizeUnit": "string(default='auto')",
    "driveSizeUnit": "string(default='auto')",
    "hashAlgorithm": "string(default='sha256')",
}
config.conf.spec["powerBox"] = confspec


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = _("PowerBox")

    __gestures = {
        # Context Menu mappings
        "kb:NVDA+windows+a": "pressApplications",
        "kb:NVDA+windows+shift+a": "pressClassicApplications",

        # Master Audio mappings
        "kb:NVDA+windows+m": "masterVolumeMute",
        "kb:NVDA+windows+downArrow": "masterVolumeDown",
        "kb:NVDA+windows+upArrow": "masterVolumeUp",

        # Per-App Audio mappings (Active Window)
        "kb:NVDA+windows+shift+m": "appVolumeMute",
        "kb:NVDA+windows+shift+downArrow": "appVolumeDown",
        "kb:NVDA+windows+shift+upArrow": "appVolumeUp",

        # Media Player / Browser Track mappings
        "kb:NVDA+windows+p": "playPause",
        "kb:NVDA+windows+rightArrow": "nextTrack",
        "kb:NVDA+windows+leftArrow": "prevTrack",
        "kb:NVDA+windows+backspace": "browserBack",
        "kb:NVDA+windows+enter": "browserForward",
        "kb:NVDA+windows+r": "browserRefresh",

        # Layer Prefix mappings
        "kb:NVDA+windows+q": "appLayer",
        "kb:NVDA+windows+t": "terminalLayer",
        "kb:NVDA+windows+n": "networkLayer",
        "kb:NVDA+windows+s": "systemLayer",
        "kb:NVDA+windows+f": "filesLayer",

        # Smart Mouse mappings
        "kb:NVDA+windows+c": "smartLeftClick",
        "kb:NVDA+windows+x": "smartRightClick",
        "kb:NVDA+windows+z": "smartDoubleClick",

        # Direct Network mappings (Quick access)
        "kb:NVDA+windows+i": "getLocalIP",
        "kb:NVDA+windows+shift+i": "getPublicIP",

        # Global Help mapping
        "kb:NVDA+windows+h": "globalHelp",
    }

    def __init__(self, *args, **kwargs):
        super(GlobalPlugin, self).__init__(*args, **kwargs)
        gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(PowerBoxSettingsPanel)

        # Unified single-state layer tracker (None, 'app', 'terminal', 'network', 'system')
        self.activeLayer = None
        self._double_press_timer = None
        self.keepLayerActive = False

    def terminate(self):
        self._cancel_double_press_timer()
        try:
            gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(PowerBoxSettingsPanel)
        except ValueError:
            pass
        super(GlobalPlugin, self).terminate()

    # --- Double-Press Timeout Handlers ---
    def _cancel_double_press_timer(self):
        """Cancels any pending auto-expiration timer for double-press confirmations."""
        timer = getattr(self, "_double_press_timer", None)
        if timer and timer.IsRunning():
            timer.Stop()
        self._double_press_timer = None

    def _on_double_press_expired(self):
        """Automatically dismisses the layer if the second confirmation key was not pressed."""
        self._double_press_timer = None
        power_manager.reset_press_tracking()
        if self.activeLayer:
            self.finishLayer()

    # --- Layer Feedback Helpers ---
    def trigger_layer_entry_feedback(self, layer_name, beep_pitch=500, beep_duration=50):
        """Provides layer activation feedback respecting user feedbackMode."""
        mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
        if mode in ("beep", "both"):
            tones.beep(beep_pitch, beep_duration)
        if mode in ("speech", "both"):
            ui.message(layer_name)

    # --- Layered Gestures Core Routing Logic ---
    def getScript(self, gesture):
        if not self.activeLayer:
            return super(GlobalPlugin, self).getScript(gesture)

        script = super(GlobalPlugin, self).getScript(gesture)
        if not script:
            script = self.script_error

        def wrapped_script(gesture):
            try:
                script(gesture)
            finally:
                if not getattr(self, "keepLayerActive", False):
                    self.finishLayer()
                self.keepLayerActive = False
        return wrapped_script

    def finishLayer(self):
        """Resets layer state, clears pending timers, and restores global shortcuts."""
        self._cancel_double_press_timer()
        self.activeLayer = None
        self.clearGestureBindings()
        self.bindGestures(self.__gestures)

    def script_error(self, gesture):
        """Provides feedback when an unmapped key is pressed inside an active layer."""
        mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
        if mode in ("beep", "both"):
            tones.beep(120, 100)
        if mode in ("speech", "both"):
            ui.message(_("Invalid key"))

    # --- System Layer Scripts ---
    @scriptHandler.script(description=_("System Layer: Press t, shift+t, c, d, r, s, b, l, or h next"))
    def script_systemLayer(self, gesture):
        if self.activeLayer:
            self.script_error(gesture)
            return

        self.bindGestures({
            "kb:t": "layerPowerTimer",
            "kb:shift+t": "layerPowerTimerStatus",
            "kb:c": "layerCancelTimer",
            "kb:d": "layerShutdown",
            "kb:r": "layerRestart",
            "kb:s": "layerSleep",
            "kb:b": "layerHibernate",
            "kb:l": "layerLock",
            "kb:p": "layerProcessInspector",
            "kb:shift+p": "layerCopyProcessInspector",
            "kb:control+p": "layerServerProcessHub",
            "kb:control+e": "layerRestartExplorer",
            "kb:h": "layerHelp",
        })
        self.activeLayer = "system"
        self.trigger_layer_entry_feedback(_("System Layer"), 600, 50)

    @scriptHandler.script(description=_("Opens the shutdown timer setup dialog"))
    def script_layerPowerTimer(self, gesture):
        wx.CallAfter(power_manager.show_timer_dialog)

    @scriptHandler.script(description=_("Announces the remaining time on the shutdown timer"))
    def script_layerPowerTimerStatus(self, gesture):
        power_manager.get_timer_status()

    @scriptHandler.script(description=_("Cancels any active shutdown timer"))
    def script_layerCancelTimer(self, gesture):
        power_manager.cancel_timer()

    @scriptHandler.script(description=_("Shuts down the computer with confirmation"))
    def script_layerShutdown(self, gesture):
        confirm_style = config.conf.get("powerBox", {}).get("powerConfirmStyle", "dialog")
        if confirm_style == "doublePress":
            if not power_manager.is_second_press("shutdown"):
                self.keepLayerActive = True
                self._cancel_double_press_timer()
                self._double_press_timer = wx.CallLater(2100, self._on_double_press_expired)
            else:
                self._cancel_double_press_timer()
        power_manager.request_confirmed_action("shutdown")

    @scriptHandler.script(description=_("Restarts the computer with confirmation"))
    def script_layerRestart(self, gesture):
        confirm_style = config.conf.get("powerBox", {}).get("powerConfirmStyle", "dialog")
        if confirm_style == "doublePress":
            if not power_manager.is_second_press("restart"):
                self.keepLayerActive = True
                self._cancel_double_press_timer()
                self._double_press_timer = wx.CallLater(2100, self._on_double_press_expired)
            else:
                self._cancel_double_press_timer()
        power_manager.request_confirmed_action("restart")

    @scriptHandler.script(description=_("Puts the computer into sleep mode"))
    def script_layerSleep(self, gesture):
        power_manager.sleep_system()

    @scriptHandler.script(description=_("Hibernates the computer"))
    def script_layerHibernate(self, gesture):
        power_manager.hibernate_system()

    @scriptHandler.script(description=_("Locks the Windows workstation"))
    def script_layerLock(self, gesture):
        power_manager.lock_workstation()

    @scriptHandler.script(description=_("Inspects CPU and RAM usage of the active application"))
    def script_layerProcessInspector(self, gesture):
        process_inspector.inspect_active_process(copy_to_clip=False)

    @scriptHandler.script(description=_("Copies and speaks CPU and RAM usage of the active application"))
    def script_layerCopyProcessInspector(self, gesture):
        process_inspector.inspect_active_process(copy_to_clip=True)

    @scriptHandler.script(description=_("Opens Server Process Hub and Session Manager"))
    def script_layerServerProcessHub(self, gesture):
        wx.CallAfter(server_process_hub.show_server_process_hub_dialog)

    @scriptHandler.script(description=_("Restarts or starts Windows Explorer"))
    def script_layerRestartExplorer(self, gesture):
        power_manager.restart_explorer()

    # --- Terminal Layer Scripts ---
    @scriptHandler.script(description=_("Terminal Layer: Press p, shift+p, c, shift+c, or w next"))
    def script_terminalLayer(self, gesture):
        if self.activeLayer:
            self.script_error(gesture)
            return

        self.bindGestures({
            "kb:p": "openPowerShell",
            "kb:shift+p": "openPowerShellAdmin",
            "kb:c": "openCMD",
            "kb:shift+c": "openCMDAdmin",
            "kb:w": "openWSL",
            "kb:h": "layerHelp",
        })
        self.activeLayer = "terminal"
        self.trigger_layer_entry_feedback(_("Terminal Layer"), 500, 50)

    @scriptHandler.script(description=_("Opens PowerShell in the current Explorer directory"))
    def script_openPowerShell(self, gesture):
        smart_path.open_terminal("powershell", as_admin=False)

    @scriptHandler.script(description=_("Opens PowerShell as Administrator in the current Explorer directory"))
    def script_openPowerShellAdmin(self, gesture):
        smart_path.open_terminal("powershell", as_admin=True)

    @scriptHandler.script(description=_("Opens Command Prompt in the current Explorer directory"))
    def script_openCMD(self, gesture):
        smart_path.open_terminal("cmd", as_admin=False)

    @scriptHandler.script(description=_("Opens Command Prompt as Administrator in the current Explorer directory"))
    def script_openCMDAdmin(self, gesture):
        smart_path.open_terminal("cmd", as_admin=True)

    @scriptHandler.script(description=_("Opens WSL in the current Explorer directory"))
    def script_openWSL(self, gesture):
        smart_path.open_terminal("wsl", as_admin=False)

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

    # --- Context Menu Scripts ---
    @scriptHandler.script(description=_("Applications menu (Modern Context Menu)"))
    def script_pressApplications(self, gesture):
        import threading
        threading.Thread(
            target=actions.perform_applications,
            args=(_("Applications menu"),),
            daemon=True
        ).start()

    @scriptHandler.script(description=_("Opens the classic context menu (Shift+F10)"))
    def script_pressClassicApplications(self, gesture):
        import threading
        threading.Thread(
            target=actions.perform_classic_applications,
            args=(_("Classic context menu"),),
            daemon=True
        ).start()

    # --- Master Audio Scripts ---
    @scriptHandler.script(description=_("Master Volume Mute Toggle"))
    def script_masterVolumeMute(self, gesture):
        audio_manager.toggle_master_mute()

    @scriptHandler.script(description=_("Master Volume Down"))
    def script_masterVolumeDown(self, gesture):
        audio_manager.change_master_volume(up=False)

    @scriptHandler.script(description=_("Master Volume Up"))
    def script_masterVolumeUp(self, gesture):
        audio_manager.change_master_volume(up=True)

    # --- Per-App Audio Scripts (Active Window) ---
    @scriptHandler.script(description=_("Mutes or unmutes the active application"))
    def script_appVolumeMute(self, gesture):
        audio_manager.toggle_app_mute()

    @scriptHandler.script(description=_("Decreases the volume of the active application"))
    def script_appVolumeDown(self, gesture):
        audio_manager.change_app_volume(up=False)

    @scriptHandler.script(description=_("Increases the volume of the active application"))
    def script_appVolumeUp(self, gesture):
        audio_manager.change_app_volume(up=True)

    # --- Media Player / Browser Track Scripts ---
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
        if self.activeLayer:
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
        self.activeLayer = "app"
        self.trigger_layer_entry_feedback(_("Quick Apps Layer"), 400, 60)

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

    # --- Network Layer Scripts ---
    @scriptHandler.script(description=_("Network Layer: Press s, l, shift+l, p, shift+p, g, shift+g, or h next"))
    def script_networkLayer(self, gesture):
        if self.activeLayer:
            self.script_error(gesture)
            return

        self.bindGestures({
            "kb:s": "layerScanNetwork",
            "kb:c": "layerTrackConnections",
            "kb:l": "layerLocalIP",
            "kb:shift+l": "layerCopyLocalIP",
            "kb:p": "layerPublicIP",
            "kb:shift+p": "layerCopyPublicIP",
            "kb:g": "layerGatewayIP",
            "kb:shift+g": "layerCopyGatewayIP",
            "kb:h": "layerHelp",
        })
        self.activeLayer = "network"
        self.trigger_layer_entry_feedback(_("Network Layer"), 550, 50)

    @scriptHandler.script(description=_("Scans local network for connected devices"))
    def script_layerScanNetwork(self, gesture):
        network_scanner.start_async_network_scan()

    @scriptHandler.script(description=_("Tracks real-time network connections of the active application"))
    def script_layerTrackConnections(self, gesture):
        process_network_tracker.track_active_app_network()

    @scriptHandler.script(description=_("Speaks the Local IP"))
    def script_layerLocalIP(self, gesture):
        network_info.speak_local_ip()

    @scriptHandler.script(description=_("Copies and speaks the Local IP"))
    def script_layerCopyLocalIP(self, gesture):
        network_info.copy_local_ip()

    @scriptHandler.script(description=_("Speaks the Public IP"))
    def script_layerPublicIP(self, gesture):
        network_info.speak_public_ip()

    @scriptHandler.script(description=_("Copies and speaks the Public IP"))
    def script_layerCopyPublicIP(self, gesture):
        network_info.copy_public_ip()

    @scriptHandler.script(description=_("Speaks the Default Gateway (Router IP)"))
    def script_layerGatewayIP(self, gesture):
        network_info.speak_default_gateway()

    @scriptHandler.script(description=_("Copies and speaks the Default Gateway (Router IP)"))
    def script_layerCopyGatewayIP(self, gesture):
        network_info.copy_default_gateway()

    # --- Direct Network Scripts (Global shortcuts) ---
    @scriptHandler.script(description=_("Speaks the Local IP. Press twice quickly to copy to clipboard."))
    def script_getLocalIP(self, gesture):
        if scriptHandler.getLastScriptRepeatCount() == 1:
            network_info.copy_local_ip()
        else:
            network_info.speak_local_ip()

    @scriptHandler.script(description=_("Speaks the Public IP. Press twice quickly to copy to clipboard."))
    def script_getPublicIP(self, gesture):
        if scriptHandler.getLastScriptRepeatCount() == 1:
            network_info.copy_public_ip()
        else:
            network_info.speak_public_ip()

    # --- Files & Storage Layer Scripts ---
    @scriptHandler.script(description=_("Files Layer: Press s, shift+s, d, shift+d, l, shift+l, c, shift+c, n, p, shift+p, or h next"))
    def script_filesLayer(self, gesture):
        if self.activeLayer:
            self.script_error(gesture)
            return

        self.bindGestures({
            "kb:s": "layerItemSize",
            "kb:shift+s": "layerCopyItemSize",
            "kb:d": "layerDrivesPulse",
            "kb:shift+d": "layerCopyDrivesPulse",
            "kb:l": "layerFileLock",
            "kb:shift+l": "layerCopyFileLock",
            "kb:c": "layerFileChecksum",
            "kb:shift+c": "layerCopyFileChecksum",
            "kb:n": "layerCreateNewFile",
            "kb:p": "layerCopyPathWindows",
            "kb:shift+p": "layerCopyPathWSL",
            "kb:h": "layerHelp",
        })
        self.activeLayer = "files"
        self.trigger_layer_entry_feedback(_("Files Layer"), 520, 50)

    @scriptHandler.script(description=_("Speaks size of focused file, folder, or drive"))
    def script_layerItemSize(self, gesture):
        file_manager.calculate_size(copy_to_clip=False)

    @scriptHandler.script(description=_("Copies and speaks size of focused file, folder, or drive"))
    def script_layerCopyItemSize(self, gesture):
        file_manager.calculate_size(copy_to_clip=True)

    @scriptHandler.script(description=_("Announces free space across all system drives"))
    def script_layerDrivesPulse(self, gesture):
        file_manager.check_drives_pulse(copy_to_clip=False)

    @scriptHandler.script(description=_("Copies and speaks free space across all system drives"))
    def script_layerCopyDrivesPulse(self, gesture):
        file_manager.check_drives_pulse(copy_to_clip=True)

    @scriptHandler.script(description=_("Inspects applications locking the focused file or folder"))
    def script_layerFileLock(self, gesture):
        file_manager.inspect_file_lock(copy_to_clip=False)

    @scriptHandler.script(description=_("Copies locking application details to clipboard"))
    def script_layerCopyFileLock(self, gesture):
        file_manager.inspect_file_lock(copy_to_clip=True)

    @scriptHandler.script(description=_("Computes file checksum and matches against clipboard"))
    def script_layerFileChecksum(self, gesture):
        file_manager.calculate_file_checksum(copy_to_clip=False)

    @scriptHandler.script(description=_("Copies file checksum directly to clipboard"))
    def script_layerCopyFileChecksum(self, gesture):
        file_manager.calculate_file_checksum(copy_to_clip=True)

    @scriptHandler.script(description=_("Instantly creates a new file in current directory"))
    def script_layerCreateNewFile(self, gesture):
        file_manager.create_new_file()

    @scriptHandler.script(description=_("Copies Windows path of focused item or current folder"))
    def script_layerCopyPathWindows(self, gesture):
        file_manager.copy_path(wsl=False)

    @scriptHandler.script(description=_("Copies WSL Linux path of focused item or current folder"))
    def script_layerCopyPathWSL(self, gesture):
        file_manager.copy_path(wsl=True)

    # --- Global Help Script ---
    @scriptHandler.script(description=_("Shows PowerBox Global Help"))
    def script_globalHelp(self, gesture):
        help_manager.show_global_help(self)

    # --- Contextual Layer Help Script ---
    @scriptHandler.script(description=_("Shows help for the currently active layer"))
    def script_layerHelp(self, gesture):
        layer = self.activeLayer
        self.finishLayer()

        if layer == "app":
            layer_title = _("Quick Apps Layer")
            keys_dict = {
                "c": _("Launch Calculator"),
                "m": _("Launch Mail"),
                "b": _("Launch Browser Home"),
                "e": _("Launch File Explorer (This PC)"),
                "p": _("Launch Media Player"),
                "h": _("Show this help message"),
            }
        elif layer == "terminal":
            layer_title = _("Terminal Layer")
            keys_dict = {
                "c": _("Command Prompt"),
                "shift+c": _("Command Prompt (Admin)"),
                "p": _("PowerShell"),
                "shift+p": _("PowerShell (Admin)"),
                "w": _("WSL"),
                "h": _("Show this help message"),
            }
        elif layer == "network":
            layer_title = _("Network Layer")
            keys_dict = {
                "s": _("Scan local network devices"),
                "c": _("Track active application network connections"),
                "l": _("Speak Local IP"),
                "shift+l": _("Copy and speak Local IP"),
                "p": _("Speak Public IP"),
                "shift+p": _("Copy and speak Public IP"),
                "g": _("Speak Default Gateway (Router IP)"),
                "shift+g": _("Copy and speak Default Gateway"),
                "h": _("Show this help message"),
            }
        elif layer == "system":
            layer_title = _("System Layer")
            keys_dict = {
                "t": _("Set shutdown timer"),
                "shift+t": _("Check shutdown timer remaining time"),
                "c": _("Cancel shutdown timer"),
                "d": _("Shut down computer"),
                "r": _("Restart computer"),
                "s": _("Sleep"),
                "b": _("Hibernate"),
                "l": _("Lock workstation"),
                "p": _("Inspect active application CPU and RAM usage"),
                "shift+p": _("Copy and speak active application CPU and RAM usage"),
                "control+p": _("Open Server Process Hub (Enterprise Manager)"),
                "control+e": _("Restart or start Windows Explorer"),
                "h": _("Show this help message"),
            }
        elif layer == "files":
            layer_title = _("Files Layer")
            keys_dict = {
                "s": _("Calculate size of focused file, folder, or drive"),
                "shift+s": _("Copy size of focused file, folder, or drive"),
                "d": _("Check free space across all drives"),
                "shift+d": _("Copy drives free space report"),
                "l": _("Inspect and unlock file locking processes"),
                "shift+l": _("Copy locking process details"),
                "c": _("Compute checksum and match with clipboard"),
                "shift+c": _("Copy file checksum to clipboard"),
                "n": _("Create new file in current folder"),
                "p": _("Copy Windows path"),
                "shift+p": _("Copy WSL Linux path"),
                "h": _("Show this help message"),
            }
        else:
            return

        help_manager.show_layer_help(layer_title, keys_dict)