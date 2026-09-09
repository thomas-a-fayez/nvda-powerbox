# -*- coding: utf-8 -*-
# PowerBox - Help Manager Module

import addonHandler
import inputCore
import ui

# Initialize translation support for this module
addonHandler.initTranslation()


def format_gesture(gesture_str):
    """
    Normalizes and sorts gesture keys into the intuitive standard order:
    NVDA + Windows + Control + Alt + Shift + Main Key,
    and prettifies special keys (e.g. RIGHTARROW -> Right Arrow).
    """
    if not gesture_str:
        return ""

    # Clean prefix tags
    clean = (
        gesture_str.replace("kb:", "")
        .replace("kb(desktop):", "")
        .replace("kb(laptop):", "")
        .strip()
    )

    parts = [p.strip() for p in clean.split("+") if p.strip()]

    # Mapping of special key names to user-friendly titles
    pretty_names = {
        "nvda": "NVDA",
        "windows": "Windows",
        "win": "Windows",
        "control": "Control",
        "ctrl": "Control",
        "alt": "Alt",
        "shift": "Shift",
        "rightarrow": "Right Arrow",
        "leftarrow": "Left Arrow",
        "uparrow": "Up Arrow",
        "downarrow": "Down Arrow",
        "backspace": "Backspace",
        "enter": "Enter",
        "space": "Space",
        "tab": "Tab",
        "escape": "Escape",
    }

    # Weight hierarchy to guarantee proper ordering
    order_weights = {
        "nvda": 1,
        "windows": 2,
        "win": 2,
        "control": 3,
        "ctrl": 3,
        "alt": 4,
        "shift": 5,
    }

    def key_sorter(key):
        return order_weights.get(key.lower(), 100)

    # Sort modifiers first, then the actual primary key
    sorted_parts = sorted(parts, key=key_sorter)

    formatted_parts = [
        pretty_names.get(k.lower(), k.upper() if len(k) == 1 else k.capitalize())
        for k in sorted_parts
    ]

    return "+".join(formatted_parts)


def get_current_gesture(plugin_obj, script_name, default_gesture):
    """
    Dynamically retrieves the current keyboard gesture assigned to a script.
    Checks NVDA's user remapped gestures first, then plugin bindings,
    falling back safely to the default gesture, and formats it cleanly.
    """
    try:
        # 1. Check if user remapped this shortcut in NVDA's Input Gestures dialog
        user_map = getattr(inputCore.manager, "userGestureMap", None)
        if user_map:
            cls_name = plugin_obj.__class__.__name__
            for gesture_id, scripts in getattr(user_map, "_map", {}).items():
                for cls, s_name in scripts:
                    if cls == cls_name and s_name == script_name:
                        return format_gesture(gesture_id)

        # 2. Check the plugin's internal active gesture map
        gesture_map = getattr(plugin_obj, "_gestureMap", {})
        for gesture, script in gesture_map.items():
            s_func_name = getattr(script, "__name__", "")
            if s_func_name == f"script_{script_name}" or script == script_name:
                gesture_display = getattr(gesture, "displayName", None)
                if gesture_display:
                    return gesture_display
                return format_gesture(str(gesture))
    except Exception:
        pass

    return format_gesture(default_gesture)


def show_global_help(plugin_obj):
    """
    Builds and displays a browseable message window containing all global shortcuts,
    fully localized and dynamically retrieved.
    """
    help_lines = [
        _("PowerBox - Global Shortcuts Help"),
        "================================\n",

        _("--- Layer Modifiers (Prefix Keys) ---"),
        f"{_('Terminal Layer')}: {get_current_gesture(plugin_obj, 'terminalLayer', 'NVDA+Windows+T')}",
        f"{_('Quick Apps Layer')}: {get_current_gesture(plugin_obj, 'appLayer', 'NVDA+Windows+Q')}",
        f"{_('Global Help')}: {get_current_gesture(plugin_obj, 'globalHelp', 'NVDA+Windows+H')}\n",

        _("--- Media & Audio ---"),
        f"{_('Play/Pause')}: {get_current_gesture(plugin_obj, 'playPause', 'NVDA+Windows+P')}",
        f"{_('Next Track')}: {get_current_gesture(plugin_obj, 'nextTrack', 'NVDA+Windows+Right Arrow')}",
        f"{_('Previous Track')}: {get_current_gesture(plugin_obj, 'prevTrack', 'NVDA+Windows+Left Arrow')}",
        f"{_('Volume Up')}: {get_current_gesture(plugin_obj, 'volumeUp', 'NVDA+Windows+Up Arrow')}",
        f"{_('Volume Down')}: {get_current_gesture(plugin_obj, 'volumeDown', 'NVDA+Windows+Down Arrow')}",
        f"{_('Volume Mute')}: {get_current_gesture(plugin_obj, 'volumeMute', 'NVDA+Windows+M')}\n",

        _("--- Browser Navigation ---"),
        f"{_('Browser Back')}: {get_current_gesture(plugin_obj, 'browserBack', 'NVDA+Windows+Backspace')}",
        f"{_('Browser Forward')}: {get_current_gesture(plugin_obj, 'browserForward', 'NVDA+Windows+Enter')}",
        f"{_('Browser Refresh')}: {get_current_gesture(plugin_obj, 'browserRefresh', 'NVDA+Windows+R')}\n",

        _("--- Smart Mouse Routing & Controls ---"),
        f"{_('Smart Left Click')}: {get_current_gesture(plugin_obj, 'smartLeftClick', 'NVDA+Windows+C')}",
        f"{_('Smart Right Click')}: {get_current_gesture(plugin_obj, 'smartRightClick', 'NVDA+Windows+X')}",
        f"{_('Smart Double Click')}: {get_current_gesture(plugin_obj, 'smartDoubleClick', 'NVDA+Windows+Z')}",
        f"{_('Applications Menu')}: {get_current_gesture(plugin_obj, 'pressApplications', 'NVDA+Windows+A')}\n",

        _("--- Network Info ---"),
        f"{_('Get Local IP')}: {get_current_gesture(plugin_obj, 'getLocalIP', 'NVDA+Windows+I')}",
        f"{_('Get Public IP')}: {get_current_gesture(plugin_obj, 'getPublicIP', 'NVDA+Windows+Shift+I')}\n",
    ]

    final_text = "\n".join(help_lines)
    ui.browseableMessage(final_text, _("PowerBox Global Help"))


def show_layer_help(layer_name, keys_dict):
    """Displays a contextual help window for a specific layer."""
    help_lines = [
        _("PowerBox - {name} Help").format(name=layer_name),
        "================================\n",
        _("Press the layer shortcut, followed by one of these keys:\n"),
    ]

    for key, description in keys_dict.items():
        clean_key = key.replace("kb:", "").upper()
        help_lines.append(f"{clean_key} : {description}")

    final_text = "\n".join(help_lines)
    ui.browseableMessage(final_text, _("{name} Help").format(name=layer_name))