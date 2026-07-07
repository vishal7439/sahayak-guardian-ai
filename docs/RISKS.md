
# Sahayak — Risk Analysis

Version 1.0 · 2026-07-07



| # | Risk | Mitigation | Pivot trigger |

|---|------|-----------|---------------|

| 1 | Motor EMI disconnects Pico from USB | Firmware watchdog auto-stops < 0.6 s; drive keepalive every 0.3 s | Persistent disconnects → separate motor power + ferrite, or powered USB hub |

| 2 | 4 GB RAM can't fit local VLM | Keep heavy reasoning off-device (Gemini); run only YOLO+Whisper+Piper+Gemma locally | Offline VLM needed → load-on-demand or 8 GB board |

| 3 | 1B model inconsistent tool-calling | Keyword-first router; Gemma as fallback | Accuracy < 90% → expand keywords or route to Gemini |

| 4 | No localization/mapping hardware | Scope to rotate-and-scan (Check Room), not room navigation | Navigation required → add LiDAR/depth + SLAM |

| 5 | WiFi/hotspot dependency | Core features work offline; Pico port auto-reconnect | Unreliable network → onboard camera, local-only |



Safety: appliance control demonstrated at low voltage only.

