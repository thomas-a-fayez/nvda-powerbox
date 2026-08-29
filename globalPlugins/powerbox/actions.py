# -*- coding: utf-8 -*-
# actions.py - Handles Windows API interactions and feedback for PowerBox

import ctypes
import config
import tones
import ui
import core

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
VK_LAUNCH_APP1 = 0xB6 # Usually mapped to My Computer / File Explorer
VK_LAUNCH_APP2 = 0xB7 # Usually mapped to Calculator

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
    _fields_ = (("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.c_void_p))

class MOUSEINPUT(ctypes.Structure):
    _fields_ = (("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.c_void_p))

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = (("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_ushort),
                ("wParamH", ctypes.c_ushort))

class INPUT_UNION(ctypes.Union):
    _fields_ = (("ki", KEYBDINPUT),
                ("mi", MOUSEINPUT),
                ("hi", HARDWAREINPUT))

class INPUT(ctypes.Structure):
    _fields_ = (("type", ctypes.c_ulong),
                ("union", INPUT_UNION))

def send_key(vk_code, extended=False):
    flags_down = KEYEVENTF_EXTENDEDKEY if extended else 0
    flags_up = KEYEVENTF_KEYUP | (KEYEVENTF_EXTENDEDKEY if extended else 0)

    input_down = INPUT(
        type=INPUT_KEYBOARD, 
        union=INPUT_UNION(ki=KEYBDINPUT(wVk=vk_code, wScan=0, dwFlags=flags_down, time=0, dwExtraInfo=None))
    )
    
    input_up = INPUT(
        type=INPUT_KEYBOARD, 
        union=INPUT_UNION(ki=KEYBDINPUT(wVk=vk_code, wScan=0, dwFlags=flags_up, time=0, dwExtraInfo=None))
    )

    inputs = (INPUT * 2)(input_down, input_up)
    ctypes.windll.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))

def send_mouse_click(button="left"):
    if button in ("left", "double"):
        down_flag = MOUSEEVENTF_LEFTDOWN
        up_flag = MOUSEEVENTF_LEFTUP
    elif button == "right":
        down_flag = MOUSEEVENTF_RIGHTDOWN
        up_flag = MOUSEEVENTF_RIGHTUP
    else:
        return

    input_down = INPUT(
        type=INPUT_MOUSE,
        union=INPUT_UNION(mi=MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=down_flag, time=0, dwExtraInfo=None))
    )
    input_up = INPUT(
        type=INPUT_MOUSE,
        union=INPUT_UNION(mi=MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=up_flag, time=0, dwExtraInfo=None))
    )

    if button == "double":
        inputs = (INPUT * 4)(input_down, input_up, input_down, input_up)
        ctypes.windll.user32.SendInput(4, ctypes.byref(inputs), ctypes.sizeof(INPUT))
    else:
        inputs = (INPUT * 2)(input_down, input_up)
        ctypes.windll.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))

def trigger_feedback(action_name):
    mode = config.conf["powerBox"]["feedbackMode"]
    
    if mode in ("beep", "both"):
        tones.beep(500, 50)
        
    if mode in ("speech", "both"):
        core.callLater(100, ui.message, action_name)

def perform_action(vk_code, action_name, extended=False):
    send_key(vk_code, extended=extended)
    trigger_feedback(action_name)

def perform_mouse_action(button, action_name):
    send_mouse_click(button)
    trigger_feedback(action_name)