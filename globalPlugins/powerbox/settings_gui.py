# -*- coding: utf-8 -*-
# settings_gui.py - GUI settings panel for PowerBox

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

        # Configurable feedback modes
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

        # Safely retrieve current configuration with default fallback
        current_mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
        mode_keys = [val for val, _ in self.feedbackModes]
        try:
            selection_index = mode_keys.index(current_mode)
        except ValueError:
            selection_index = 1  # Default to 'beep'

        self.feedbackChoice.SetSelection(selection_index)

    def onSave(self):
        selected_index = self.feedbackChoice.GetSelection()
        if selected_index != wx.NOT_FOUND:
            config.conf["powerBox"]["feedbackMode"] = self.feedbackModes[selected_index][0]