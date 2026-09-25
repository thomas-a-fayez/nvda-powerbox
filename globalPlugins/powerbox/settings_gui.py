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

        # 3. Configurable File & Folder size format
        self.fileSizeChoices = [
            ("auto", _("Smart Adaptive (Recommended)")),
            ("mb", _("Always Megabytes (MB)")),
            ("gb", _("Always Gigabytes (GB)")),
        ]
        self.fileSizeChoice = helper.addLabeledControl(
            _("Files and folders size format:"),
            wx.Choice,
            choices=[name for _, name in self.fileSizeChoices]
        )

        # Safely retrieve current file and folder size format with default fallback
        current_fs = config.conf.get("powerBox", {}).get("fileSizeUnit", "auto")
        fs_keys = [val for val, _ in self.fileSizeChoices]
        try:
            fs_index = fs_keys.index(current_fs)
        except ValueError:
            fs_index = 0  # Default to 'auto'

        self.fileSizeChoice.SetSelection(fs_index)

        # 4. Configurable Drives free space format
        self.driveSizeChoices = [
            ("auto", _("Smart Adaptive (Recommended)")),
            ("gb", _("Always Gigabytes (GB)")),
            ("tb", _("Always Terabytes (TB)")),
        ]
        self.driveSizeChoice = helper.addLabeledControl(
            _("Drives storage space format:"),
            wx.Choice,
            choices=[name for _, name in self.driveSizeChoices]
        )

        # Safely retrieve current drive storage space format with default fallback
        current_ds = config.conf.get("powerBox", {}).get("driveSizeUnit", "auto")
        ds_keys = [val for val, _ in self.driveSizeChoices]
        try:
            ds_index = ds_keys.index(current_ds)
        except ValueError:
            ds_index = 0  # Default to 'auto'

        self.driveSizeChoice.SetSelection(ds_index)

        # 5. Configurable Default Hash Algorithm
        self.hashChoices = [
            ("sha256", _("SHA-256 (Standard & Secure)")),
            ("md5", _("MD5 (Fast)")),
            ("sha1", "SHA-1"),
        ]
        self.hashChoice = helper.addLabeledControl(
            _("Default file checksum algorithm:"),
            wx.Choice,
            choices=[name for _, name in self.hashChoices]
        )

        # Safely retrieve current default hash algorithm with default fallback
        current_ha = config.conf.get("powerBox", {}).get("hashAlgorithm", "sha256")
        ha_keys = [val for val, _ in self.hashChoices]
        try:
            ha_index = ha_keys.index(current_ha)
        except ValueError:
            ha_index = 0  # Default to 'sha256'

        self.hashChoice.SetSelection(ha_index)

    def onSave(self):
        # 1. Save user action feedback mode (None, Beep, Speech, or Both)
        selected_fb = self.feedbackChoice.GetSelection()
        if selected_fb != wx.NOT_FOUND:
            config.conf["powerBox"]["feedbackMode"] = self.feedbackModes[selected_fb][0]

        # 2. Save confirmation style for shutdown and restart actions (Dialog or Double-Press)
        selected_cs = self.confirmChoice.GetSelection()
        if selected_cs != wx.NOT_FOUND:
            config.conf["powerBox"]["powerConfirmStyle"] = self.confirmStyles[selected_cs][0]

        # 3. Save preferred display unit for files and folders size (Auto, MB, or GB)
        sel_fs = self.fileSizeChoice.GetSelection()
        if sel_fs != wx.NOT_FOUND:
            config.conf["powerBox"]["fileSizeUnit"] = self.fileSizeChoices[sel_fs][0]

        # 4. Save preferred display unit for storage drives capacity (Auto, GB, or TB)
        sel_ds = self.driveSizeChoice.GetSelection()
        if sel_ds != wx.NOT_FOUND:
            config.conf["powerBox"]["driveSizeUnit"] = self.driveSizeChoices[sel_ds][0]

        # 5. Save default hashing algorithm used for file checksum verification (SHA-256, MD5, or SHA-1)
        sel_ha = self.hashChoice.GetSelection()
        if sel_ha != wx.NOT_FOUND:
            config.conf["powerBox"]["hashAlgorithm"] = self.hashChoices[sel_ha][0]