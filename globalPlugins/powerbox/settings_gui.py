# -*- coding: utf-8 -*-
# settings_gui.py - GUI settings for PowerBox

import wx
import config
import gui
from gui.settingsDialogs import SettingsPanel

class PowerBoxSettingsPanel(SettingsPanel):
    title = _("PowerBox")

    def makeSettings(self, settingsSizer):
        sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        
        self.feedbackModes = [
            ("none", _("No feedback (Silent)")),
            ("beep", _("Beep only")),
            ("speech", _("Speak action name")),
            ("both", _("Beep and speak"))
        ]
        
        self.feedbackChoice = sHelper.addLabeledControl(
            _("Action feedback mode:"),
            wx.Choice,
            choices=[name for val, name in self.feedbackModes]
        )
        
        current_mode = config.conf["powerBox"]["feedbackMode"]
        try:
            idx = [val for val, name in self.feedbackModes].index(current_mode)
        except ValueError:
            idx = 1
            
        self.feedbackChoice.SetSelection(idx)

    def onSave(self):
        idx = self.feedbackChoice.GetSelection()
        config.conf["powerBox"]["feedbackMode"] = self.feedbackModes[idx][0]