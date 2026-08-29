# -*- coding: utf-8 -*-
# PowerBox - Help Manager Module

import ui
import inputCore

def get_current_gesture(plugin_obj, script_name, default_gesture):
    """
    Attempts to dynamically retrieve the current keyboard gesture assigned 
    to a specific script in NVDA. If the user changed it in NVDA settings, 
    this will fetch the new one.
    
    :param plugin_obj: The instance of the GlobalPlugin.
    :param script_name: The name of the script (e.g., 'terminalLayer' without 'script_').
    :param default_gesture: The default string to return if lookup fails.
    :return: String representing the gesture.
    """
    try:
        # Query NVDA's input manager for gestures bound to this command
        gestures = inputCore.manager.getGesturesForCommand(plugin_obj, script_name)
        if gestures:
            # Return the display name of the first found gesture (e.g., 'NVDA+windows+t')
            return gestures[0].displayName
    except Exception:
        # Fallback to the default gesture safely if the API call fails or changes
        pass
    
    return default_gesture


def show_global_help(plugin_obj):
    """
    Builds and displays a browseable message window containing all global shortcuts,
    dynamically categorized.
    """
    # Build the help text dynamically with all global scripts
    help_lines = [
        "PowerBox - Global Shortcuts Help",
        "================================\n",
        
        "--- Layer Modifiers (Prefix Keys) ---",
        f"Terminal Layer: {get_current_gesture(plugin_obj, 'terminalLayer', 'NVDA+Windows+T')}",
        f"Quick Apps Layer: {get_current_gesture(plugin_obj, 'appLayer', 'NVDA+Windows+Q')}",
        f"Global Help: {get_current_gesture(plugin_obj, 'globalHelp', 'NVDA+Windows+H')}\n",
        
        "--- Media & Audio ---",
        f"Play/Pause: {get_current_gesture(plugin_obj, 'playPause', 'NVDA+Windows+P')}",
        f"Next Track: {get_current_gesture(plugin_obj, 'nextTrack', 'NVDA+Windows+Right arrow')}",
        f"Previous Track: {get_current_gesture(plugin_obj, 'prevTrack', 'NVDA+Windows+Left arrow')}",
        f"Volume Up: {get_current_gesture(plugin_obj, 'volumeUp', 'NVDA+Windows+Up arrow')}",
        f"Volume Down: {get_current_gesture(plugin_obj, 'volumeDown', 'NVDA+Windows+Down arrow')}",
        f"Volume Mute: {get_current_gesture(plugin_obj, 'volumeMute', 'NVDA+Windows+M')}\n",
        
        "--- Browser Navigation ---",
        f"Browser Back: {get_current_gesture(plugin_obj, 'browserBack', 'NVDA+Windows+Backspace')}",
        f"Browser Forward: {get_current_gesture(plugin_obj, 'browserForward', 'NVDA+Windows+Enter')}",
        f"Browser Refresh: {get_current_gesture(plugin_obj, 'browserRefresh', 'NVDA+Windows+R')}\n",

        "--- Mouse & Keyboard ---",
        f"Left Click: {get_current_gesture(plugin_obj, 'leftClick', 'NVDA+Windows+C')}",
        f"Right Click: {get_current_gesture(plugin_obj, 'rightClick', 'NVDA+Windows+X')}",
        f"Double Click: {get_current_gesture(plugin_obj, 'doubleClick', 'NVDA+Windows+Z')}",
        f"Applications Menu: {get_current_gesture(plugin_obj, 'pressApplications', 'NVDA+Windows+A')}\n",

        "--- Network Info ---",
        f"Get Local IP: {get_current_gesture(plugin_obj, 'getLocalIP', 'NVDA+Windows+I')}",
        f"Get Public IP: {get_current_gesture(plugin_obj, 'getPublicIP', 'NVDA+Windows+Shift+I')}\n",
    ]
    
    # Join the list into a single multi-line string
    final_text = "\n".join(help_lines)
    
    # Display it in NVDA's readable text window
    ui.browseableMessage(final_text, "PowerBox Global Help")


def show_layer_help(layer_name, keys_dict):
    """
    Displays a contextual help window for a specific layer.
    
    :param layer_name: String representing the layer name (e.g., 'Terminal Layer').
    :param keys_dict: Dictionary mapping keys to their descriptions.
    """
    help_lines = [
        f"PowerBox - {layer_name} Help",
        "================================\n",
        "Press the layer shortcut, followed by one of these keys:\n"
    ]
    
    for key, description in keys_dict.items():
        # Clean up NVDA's 'kb:' prefix for a cleaner display
        clean_key = key.replace("kb:", "").upper()
        help_lines.append(f"{clean_key} : {description}")
        
    final_text = "\n".join(help_lines)
    
    # Open the UI message window
    ui.browseableMessage(final_text, f"{layer_name} Help")