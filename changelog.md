# PowerBox Changelog

## v2.1.3 - Defense-in-Depth Security Hardening & Input Gestures Protection

This release reinforces PowerBox's security architecture by introducing automated method-level guards against custom gesture remappings on secure desktops.

### 🛡️ Security & Zero-Trust Hardening:
* **Defense-in-Depth Script Wrapping:** Implemented automated runtime security wrapping across all plugin action methods. Even if an end-user maps custom direct shortcuts via NVDA's Input Gestures dialog (bypassing layer routing via `userGestureMap`), command execution is intercepted and strictly rejected on secure screens.
* **UAC Consent UI Isolation:** Hardened kernel-level desktop checks to guarantee that User Account Control (UAC) elevation prompts ("Yes/No" screens) and lock screens strictly block terminal or application launching.
* **Balanced Acoustic Alert Chime:** Refined the 3-stage security alarm pattern (650Hz -> 850Hz -> 280Hz) to provide an authoritative, non-speech auditory warning when restricted actions are attempted.
* **Safe Audio Preservation:** Maintained unhindered master volume controls (mute, volume up, volume down) across all secure screens.