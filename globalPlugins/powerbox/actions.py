# -*- coding: utf-8 -*-
# actions.py - Handles Windows API interactions and feedback for PowerBox

# Acknowledgment:
# Low-level Windows input simulation structures are based on Microsoft Win32 API documentation.
# Smart click routing logic is inspired by NVDA core's mouse-to-navigator routing behavior.

import time
import ctypes
import addonHandler
import api
import config
import core
import tones
import ui
import winUser

# Initialize translation support for this module
addonHandler.initTranslation()

# --- Virtual Key (VK) Codes ---
VK_APPS = 0x5D
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_BROWSER_BACK = 0xA6
VK_BROWSER_FORWARD = 0xA7
VK_BROWSER_REFRESH = 0xA8

# --- App Launch Virtual Key Codes ---
VK_BROWSER_HOME = 0xAC
VK_LAUNCH_MAIL = 0xB4
VK_LAUNCH_MEDIA_SELECT = 0xB5
VK_LAUNCH_APP1 = 0xB6  # Usually mapped to File Explorer / This PC
VK_LAUNCH_APP2 = 0xB7  # Usually mapped to Calculator

# --- SendInput Constants and Structures ---
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

# Keyboard Flags
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

# Mouse Flags
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010


class KEYBDINPUT(ctypes.Structure):
    _fields_ = (
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_void_p),
    )


class MOUSEINPUT(ctypes.Structure):
    _fields_ = (
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_void_p),
    )


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = (
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_ushort),
        ("wParamH", ctypes.c_ushort),
    )


class INPUT_UNION(ctypes.Union):
    _fields_ = (
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    )


class INPUT(ctypes.Structure):
    _fields_ = (
        ("type", ctypes.c_ulong),
        ("union", INPUT_UNION),
    )


def send_key(vk_code, extended=False):
    """Simulates a low-level key down and key up sequence via SendInput."""
    flags_down = KEYEVENTF_EXTENDEDKEY if extended else 0
    flags_up = KEYEVENTF_KEYUP | (KEYEVENTF_EXTENDEDKEY if extended else 0)

    input_down = INPUT(
        type=INPUT_KEYBOARD,
        union=INPUT_UNION(
            ki=KEYBDINPUT(
                wVk=vk_code,
                wScan=0,
                dwFlags=flags_down,
                time=0,
                dwExtraInfo=None,
            )
        ),
    )

    input_up = INPUT(
        type=INPUT_KEYBOARD,
        union=INPUT_UNION(
            ki=KEYBDINPUT(
                wVk=vk_code,
                wScan=0,
                dwFlags=flags_up,
                time=0,
                dwExtraInfo=None,
            )
        ),
    )

    inputs = (INPUT * 2)(input_down, input_up)
    ctypes.windll.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))


def send_mouse_click(button="left"):
    """Simulates a physical mouse button click via SendInput."""
    if button == "double":
        # Execute two separate clicks with a realistic double-click delay
        send_mouse_click("left")
        time.sleep(0.05)
        send_mouse_click("left")
        return

    if button == "left":
        down_flag = MOUSEEVENTF_LEFTDOWN
        up_flag = MOUSEEVENTF_LEFTUP
    elif button == "right":
        down_flag = MOUSEEVENTF_RIGHTDOWN
        up_flag = MOUSEEVENTF_RIGHTUP
    else:
        return

    input_down = INPUT(
        type=INPUT_MOUSE,
        union=INPUT_UNION(
            mi=MOUSEINPUT(
                dx=0, dy=0, mouseData=0, dwFlags=down_flag, time=0, dwExtraInfo=None
            )
        ),
    )
    input_up = INPUT(
        type=INPUT_MOUSE,
        union=INPUT_UNION(
            mi=MOUSEINPUT(
                dx=0, dy=0, mouseData=0, dwFlags=up_flag, time=0, dwExtraInfo=None
            )
        ),
    )

    inputs = (INPUT * 2)(input_down, input_up)
    ctypes.windll.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))


def trigger_feedback(action_name):
    """Provides user feedback (speech, tones, or both) according to configuration."""
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")

    if mode in ("beep", "both"):
        tones.beep(500, 50)

    if mode in ("speech", "both"):
        core.callLater(100, ui.message, action_name)


def perform_action(vk_code, action_name, extended=False):
    """Performs a keyboard simulation and triggers corresponding feedback."""
    send_key(vk_code, extended=extended)
    trigger_feedback(action_name)


def perform_smart_click(button, action_name):
    """
    Locates the current navigator object on screen, routes the mouse cursor
    to its exact center, executes the requested click, and provides feedback.
    """
    nav_obj = api.getNavigatorObject()

    # Verify that the navigator object exists and has valid screen bounds
    if not nav_obj or not getattr(nav_obj, "location", None):
        ui.message(_("Object has no location"))
        return

    try:
        left, top, width, height = nav_obj.location
        center_x = left + (width // 2)
        center_y = top + (height // 2)

        # Route the physical mouse cursor to the calculated center
        winUser.setCursorPos(center_x, center_y)
    except Exception:
        ui.message(_("Failed to route mouse to object"))
        return

    # Execute mouse click and provide feedback
    send_mouse_click(button)
    trigger_feedback(action_name)