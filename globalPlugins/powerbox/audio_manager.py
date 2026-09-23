# -*- coding: utf-8 -*-
# audio_manager.py - Comprehensive Windows Master & Per-App Audio Manager for PowerBox

# Acknowledgment:
# - Master audio volume & mute queries utilize Win32 Core Audio COM VTable (IAudioEndpointVolume).
# - Per-application session enumeration & volume control utilize IAudioSessionManager2 and ISimpleAudioVolume via ctypes.
# - Utilizes isolated WinDLL ole32 instances to prevent cross-add-on COM initialization collisions.

import ctypes
from ctypes import wintypes
import time
import wx
import addonHandler
import api
import config
import core
import tones
import ui
import winUser

# Initialize translation support for this module
addonHandler.initTranslation()

# Isolated ole32 instance preventing cross-module ctypes prototype collisions
ole32 = ctypes.WinDLL("ole32", use_last_error=True)

# Global state tracker for master mute state reliability
_last_known_master_mute = False

# --- Virtual Key Codes for System Sound Simulation ---
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF

# --- Pure Win32 Core Audio COM Definitions ---
class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]

_CLSID_MMDeviceEnumerator = _GUID(0xBCDE0395, 0xE52F, 0x467C, (ctypes.c_ubyte * 8)(0x8E, 0x3D, 0xC4, 0x57, 0x92, 0x91, 0x69, 0x2E))
_IID_IMMDeviceEnumerator = _GUID(0xA95664D2, 0x9614, 0x4F35, (ctypes.c_ubyte * 8)(0xA7, 0x46, 0xDE, 0x8D, 0xB6, 0x36, 0x17, 0xE6))
_IID_IAudioEndpointVolume = _GUID(0x5CDF2C82, 0x841E, 0x4546, (ctypes.c_ubyte * 8)(0x97, 0x22, 0x0C, 0xF7, 0x40, 0x78, 0x22, 0x9A))
_IID_IAudioSessionManager2 = _GUID(0x77AA99A0, 0x1BD6, 0x484F, (ctypes.c_ubyte * 8)(0x8B, 0xC7, 0x2C, 0x65, 0x4C, 0x9A, 0x9B, 0x6F))
_IID_IAudioSessionControl2 = _GUID(0xBFB7FF88, 0x7239, 0x4FC9, (ctypes.c_ubyte * 8)(0x8F, 0xA2, 0x07, 0xC9, 0x50, 0xBE, 0x9C, 0x6D))
_IID_ISimpleAudioVolume = _GUID(0x87CE5498, 0x68D6, 0x44E5, (ctypes.c_ubyte * 8)(0x92, 0x15, 0x6D, 0xA4, 0x7E, 0xF8, 0x83, 0xD8))

# Define CoCreateInstance prototype using c_void_p to ensure universal immunity
ole32.CoCreateInstance.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p
]
ole32.CoCreateInstance.restype = ctypes.c_long


def _get_default_audio_device():
    """Helper to instantiate and return the default audio playback endpoint device."""
    try:
        ole32.CoInitialize(None)
    except Exception:
        pass

    try:
        Release_Proto = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
        pEnum = ctypes.c_void_p()
        hr = ole32.CoCreateInstance(
            ctypes.byref(_CLSID_MMDeviceEnumerator),
            None,
            1,  # CLSCTX_INPROC_SERVER
            ctypes.byref(_IID_IMMDeviceEnumerator),
            ctypes.byref(pEnum)
        )
        if hr != 0 or not pEnum.value:
            return None

        vtbl_enum = ctypes.cast(pEnum.value, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        GetDefaultAudioEndpoint_Proto = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)
        )
        pDevice = ctypes.c_void_p()
        hr = GetDefaultAudioEndpoint_Proto(vtbl_enum[4])(pEnum, 0, 1, ctypes.byref(pDevice))  # 0=eRender, 1=eMultimedia
        Release_Proto(vtbl_enum[2])(pEnum)

        if hr != 0 or not pDevice.value:
            return None

        return pDevice
    except Exception:
        return None


# ==========================================
# PART 1: MASTER SYSTEM AUDIO MANAGEMENT
# ==========================================

def _get_audio_endpoint_volume_pointer():
    """Helper to instantiate and return the native IAudioEndpointVolume COM pointer."""
    pDevice = _get_default_audio_device()
    if not pDevice:
        return None

    try:
        Release_Proto = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
        vtbl_dev = ctypes.cast(pDevice.value, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        Activate_Proto = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
        )
        pVolume = ctypes.c_void_p()
        hr = Activate_Proto(vtbl_dev[3])(pDevice, ctypes.byref(_IID_IAudioEndpointVolume), 1, None, ctypes.byref(pVolume))
        Release_Proto(vtbl_dev[2])(pDevice)

        if hr != 0 or not pVolume.value:
            return None

        return pVolume
    except Exception:
        return None


def get_master_volume_info():
    """Returns (is_muted: bool, volume_percent: int) for the master audio mixer."""
    pVolume = _get_audio_endpoint_volume_pointer()
    if not pVolume:
        return None, None

    try:
        Release_Proto = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
        vtbl_vol = ctypes.cast(pVolume.value, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents

        GetMasterVolumeLevelScalar_Proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(ctypes.c_float))
        GetMute_Proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(wintypes.BOOL))

        level = ctypes.c_float()
        is_muted = wintypes.BOOL()

        hr_vol = GetMasterVolumeLevelScalar_Proto(vtbl_vol[9])(pVolume, ctypes.byref(level))
        hr_mute = GetMute_Proto(vtbl_vol[15])(pVolume, ctypes.byref(is_muted))
        Release_Proto(vtbl_vol[2])(pVolume)

        if hr_vol == 0 and hr_mute == 0:
            return bool(is_muted.value), int(round(level.value * 100))

        return None, None
    except Exception:
        return None, None


def set_master_mute(b_mute):
    """Sets master mute state directly in the Windows kernel mixer."""
    pVolume = _get_audio_endpoint_volume_pointer()
    if not pVolume:
        return False

    try:
        Release_Proto = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
        vtbl_vol = ctypes.cast(pVolume.value, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        SetMute_Proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, wintypes.BOOL, ctypes.c_void_p)
        hr = SetMute_Proto(vtbl_vol[14])(pVolume, wintypes.BOOL(b_mute), None)
        Release_Proto(vtbl_vol[2])(pVolume)
        return hr == 0
    except Exception:
        return False


def change_master_volume(up=True):
    """Adjusts master system volume up or down and announces updated percentage."""
    from . import actions
    vk = VK_VOLUME_UP if up else VK_VOLUME_DOWN
    actions.send_key(vk, extended=True)

    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")
    if mode in ("beep", "both"):
        tones.beep(500, 50)

    if mode in ("speech", "both"):
        def announce_vol():
            is_muted, vol_level = get_master_volume_info()
            if vol_level is not None:
                if is_muted:
                    msg = _("Muted ({vol}%)").format(vol=vol_level)
                else:
                    msg = _("Volume: {vol}%").format(vol=vol_level)
            else:
                msg = _("Volume Up") if up else _("Volume Down")
            ui.message(msg)

        core.callLater(80, announce_vol)


def toggle_master_mute():
    """Toggles master system mute with instant speech/chime feedback."""
    global _last_known_master_mute
    from . import actions
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")

    is_muted, vol = get_master_volume_info()
    currently_muted = is_muted if is_muted is not None else _last_known_master_mute

    if not currently_muted:
        _last_known_master_mute = True
        def do_mute():
            if not set_master_mute(True):
                actions.send_key(VK_VOLUME_MUTE, extended=True)

        if mode in ("beep", "both"):
            tones.beep(400, 50)
        if mode in ("speech", "both"):
            ui.message(_("Muted"))
            core.callLater(350, do_mute)
        elif mode == "beep":
            core.callLater(70, do_mute)
        else:
            do_mute()
    else:
        _last_known_master_mute = False
        if not set_master_mute(False):
            actions.send_key(VK_VOLUME_MUTE, extended=True)

        unmuted_state, new_vol = get_master_volume_info()
        val = new_vol if new_vol is not None else (vol if vol is not None else "")

        if mode in ("beep", "both"):
            tones.beep(550, 50)
        if mode in ("speech", "both"):
            msg = _("Unmuted: {vol}%").format(vol=val) if val != "" else _("Unmuted")
            core.callLater(50, ui.message, msg)


# ==========================================
# PART 2: PER-APPLICATION AUDIO SESSIONS
# ==========================================

def _get_active_app_info():
    """Retrieves target Process ID and friendly name for the currently focused window."""
    focus_obj = api.getFocusObject()
    target_pid = None
    app_name = _("Current App")

    if focus_obj:
        target_pid = getattr(focus_obj, "processID", None)
        if getattr(focus_obj, "appModule", None):
            raw_name = getattr(focus_obj.appModule, "appName", "")
            if raw_name:
                app_name = raw_name.capitalize()

    if not target_pid:
        hwnd = winUser.getForegroundWindow()
        if hwnd:
            target_pid = winUser.getWindowThreadProcessId(hwnd)[0]

    return target_pid, app_name


def _modify_app_audio_session(target_pid, volume_delta=None, toggle_mute=False):
    """
    Finds the WASAPI audio session corresponding to target_pid,
    adjusts volume scalar or toggles mute directly in the mixer.
    """
    pDevice = _get_default_audio_device()
    if not pDevice:
        return None

    try:
        Release_Proto = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
        QueryInterface_Proto = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
        )

        vtbl_dev = ctypes.cast(pDevice.value, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        Activate_Proto = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
        )

        pMgr = ctypes.c_void_p()
        hr = Activate_Proto(vtbl_dev[3])(pDevice, ctypes.byref(_IID_IAudioSessionManager2), 1, None, ctypes.byref(pMgr))
        Release_Proto(vtbl_dev[2])(pDevice)

        if hr != 0 or not pMgr.value:
            return None

        vtbl_mgr = ctypes.cast(pMgr.value, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        GetSessionEnumerator_Proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))
        pEnum = ctypes.c_void_p()
        hr = GetSessionEnumerator_Proto(vtbl_mgr[5])(pMgr, ctypes.byref(pEnum))
        Release_Proto(vtbl_mgr[2])(pMgr)

        if hr != 0 or not pEnum.value:
            return None

        vtbl_enum = ctypes.cast(pEnum.value, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        GetCount_Proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int))
        GetSession_Proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))

        session_count = ctypes.c_int(0)
        GetCount_Proto(vtbl_enum[3])(pEnum, ctypes.byref(session_count))

        matched_result = None

        for i in range(session_count.value):
            pSession = ctypes.c_void_p()
            if GetSession_Proto(vtbl_enum[4])(pEnum, i, ctypes.byref(pSession)) != 0 or not pSession.value:
                continue

            vtbl_session = ctypes.cast(pSession.value, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
            QI = QueryInterface_Proto(vtbl_session[0])

            # Query IAudioSessionControl2 for Process ID
            pControl2 = ctypes.c_void_p()
            if QI(pSession, ctypes.byref(_IID_IAudioSessionControl2), ctypes.byref(pControl2)) == 0 and pControl2.value:
                vtbl_c2 = ctypes.cast(pControl2.value, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
                GetProcessId_Proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD))
                pid = wintypes.DWORD(0)
                GetProcessId_Proto(vtbl_c2[14])(pControl2, ctypes.byref(pid))
                Release_Proto(vtbl_c2[2])(pControl2)

                if pid.value == target_pid:
                    # Query ISimpleAudioVolume
                    pVolume = ctypes.c_void_p()
                    if QI(pSession, ctypes.byref(_IID_ISimpleAudioVolume), ctypes.byref(pVolume)) == 0 and pVolume.value:
                        vtbl_v = ctypes.cast(pVolume.value, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents

                        SetMasterVolume_Proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_float, ctypes.c_void_p)
                        GetMasterVolume_Proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(ctypes.c_float))
                        SetMute_Proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, wintypes.BOOL, ctypes.c_void_p)
                        GetMute_Proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(wintypes.BOOL))

                        curr_level = ctypes.c_float(0.0)
                        curr_mute = wintypes.BOOL(False)

                        GetMasterVolume_Proto(vtbl_v[4])(pVolume, ctypes.byref(curr_level))
                        GetMute_Proto(vtbl_v[6])(pVolume, ctypes.byref(curr_mute))

                        final_vol = int(round(curr_level.value * 100))
                        final_mute = bool(curr_mute.value)

                        # 1. Adjust Volume Step
                        if volume_delta is not None:
                            new_val = min(1.0, max(0.0, curr_level.value + volume_delta))
                            SetMasterVolume_Proto(vtbl_v[3])(pVolume, ctypes.c_float(new_val), None)
                            final_vol = int(round(new_val * 100))
                            # Setting volume automatically unmutes app in Windows
                            if final_mute:
                                SetMute_Proto(vtbl_v[5])(pVolume, wintypes.BOOL(False), None)
                                final_mute = False

                        # 2. Toggle Mute
                        if toggle_mute:
                            final_mute = not final_mute
                            SetMute_Proto(vtbl_v[5])(pVolume, wintypes.BOOL(final_mute), None)

                        Release_Proto(vtbl_v[2])(pVolume)
                        matched_result = (final_mute, final_vol)

            Release_Proto(vtbl_session[2])(pSession)
            if matched_result:
                break

        Release_Proto(vtbl_enum[2])(pEnum)
        return matched_result

    except Exception:
        return None


def change_app_volume(up=True):
    """Adjusts the volume of the focused application by 5% and announces new percentage."""
    target_pid, app_name = _get_active_app_info()
    if not target_pid:
        ui.message(_("No active application found"))
        return

    delta = 0.05 if up else -0.05
    res = _modify_app_audio_session(target_pid, volume_delta=delta)
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")

    if mode in ("beep", "both"):
        tones.beep(600 if up else 450, 40)

    if mode in ("speech", "both"):
        if res is not None:
            is_muted, vol = res
            if is_muted:
                ui.message(_("{app} muted ({vol}%)").format(app=app_name, vol=vol))
            else:
                ui.message(_("{app}: {vol}%").format(app=app_name, vol=vol))
        else:
            ui.message(_("No audio session for {app}").format(app=app_name))


def toggle_app_mute():
    """Toggles mute state for the currently focused application."""
    target_pid, app_name = _get_active_app_info()
    if not target_pid:
        ui.message(_("No active application found"))
        return

    res = _modify_app_audio_session(target_pid, toggle_mute=True)
    mode = config.conf.get("powerBox", {}).get("feedbackMode", "beep")

    if res is not None:
        is_muted, vol = res
        if is_muted:
            if mode in ("beep", "both"):
                tones.beep(350, 60)
            if mode in ("speech", "both"):
                ui.message(_("{app} muted").format(app=app_name))
        else:
            if mode in ("beep", "both"):
                tones.beep(550, 50)
            if mode in ("speech", "both"):
                ui.message(_("{app} unmuted: {vol}%").format(app=app_name, vol=vol))
    else:
        if mode in ("speech", "both"):
            ui.message(_("No audio session for {app}").format(app=app_name))