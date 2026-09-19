# -*- coding: utf-8 -*-
# settings_gui.py - GUI settings panel for PowerBox

# Acknowledgment:
# Settings panel layout and controls follow standard NVDA Preferences dialog patterns.

import wx
import addonHandler
import config
import gui
from gui.settingsDialogs import SettingsPanel

# Initialize translation support for this module
addonHandler.initTranslation()


class PowerBoxSettingsPanel(SettingsPanel):
    """Configuration panel integrated within NVDA's Preferences dialog."""
    
    title = _("PowerBox")

    def makeSettings(self, settingsSizer):
        helper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

        # 1. Configurable feedback modes
        self.feedbackModes = [
            ("none", _("No feedback (Silent)")),
            ("beep", _("Beep only")),
            ("speech", _("Speak action name")),
            ("both", _("Beep and speak")),
        ]

        mode_choices = [name for _, name in self.feedbackModes]
        self.feedbackChoice = helper.addLabeledControl(
            _("Action feedback mode:"),
            wx.Choice,
            choices=mode_choices
        )

        # Safely retrieve current feedback mode configuration with default fallback
        current_mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
        mode_keys = [val for val, _ in self.feedbackModes]
        try:
            selection_index = mode_keys.index(current_mode)
        except ValueError:
            selection_index = 1  # Default to 'beep'

        self.feedbackChoice.SetSelection(selection_index)

        # 2. Configurable power confirmation styles
        self.confirmStyles = [
            ("dialog", _("Confirmation dialog (Recommended)")),
            ("doublePress", _("Press key twice within 2 seconds")),
        ]

        style_choices = [name for _, name in self.confirmStyles]
        self.confirmChoice = helper.addLabeledControl(
            _("Shutdown and restart confirmation style:"),
            wx.Choice,
            choices=style_choices
        )

        # Safely retrieve current confirmation style with default fallback
        current_style = config.conf.get("powerBox", {}).get("powerConfirmStyle", "dialog")
        style_keys = [val for val, _ in self.confirmStyles]
        try:
            style_index = style_keys.index(current_style)
        except ValueError:
            style_index = 0  # Default to 'dialog'

        self.confirmChoice.SetSelection(style_index)

    def onSave(self):
        # Save feedback mode
        selected_fb = self.feedbackChoice.GetSelection()
        if selected_fb != wx.NOT_FOUND:
            config.conf["powerBox"]["feedbackMode"] = self.feedbackModes[selected_fb][0]

        # Save power actions confirmation style
        selected_cs = self.confirmChoice.GetSelection()
        if selected_cs != wx.NOT_FOUND:
            config.conf["powerBox"]["powerConfirmStyle"] = self.confirmStyles[selected_cs][0]