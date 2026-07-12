
# Sahayak — Risk Analysis

Version 1.0 · 2026-07-07



| # | Risk | Mitigation | Pivot trigger |

|---|------|-----------|---------------|

| 1 | Motor EMI disconnects Pico from USB | Firmware watchdog auto-stops < 0.6 s; drive keepalive every 0.3 s; **server-side auto-reconnect** detects the dead serial handle and re-opens the port (handles ttyACM re-enumeration) — recovers without restart | Persistent disconnects → separate motor power + ferrite, or powered USB hub |

| 2 | 4 GB RAM can't fit local VLM | Keep heavy reasoning off-device (Gemini); run only YOLO+Whisper+Piper+Gemma locally | Offline VLM needed → load-on-demand or 8 GB board |

| 3 | 1B model inconsistent tool-calling | Keyword-first router; Gemma as fallback | Accuracy < 90% → expand keywords or route to Gemini |

| 4 | No localization/mapping hardware | Scope to rotate-and-scan (Check Room), not room navigation | Navigation required → add LiDAR/depth + SLAM |

| 5 | WiFi/hotspot dependency | Core features work offline; Pico port auto-reconnect | Unreliable network → onboard camera, local-only |



Safety: appliance control demonstrated at low voltage only.


## Calibration & Setup Notes

- **Camera:** OPPO F27 IP Webcam serves frames at `http://<phone-ip>:8090/shot.jpg`.
  The phone IP is set via `PHONE_IP` in server.py; if the network changes, update it.
- **Ultrasonic (HC-SR04):** distance read over Pico serial (`CMD:SONAR` → `DIST:`);
  values ≥ 0 accepted, forward-cone nearest-obstacle only.
- **CPU affinity (RDK X5, 8× A55):** Flask cores 0-3, motor/keepalive core 5,
  BPU vision cores 6-7, Gemma llama-server cores 0-4 (via gemma.service). Verified.
- **Gemma llama-server:** 5 threads gives ~5 s replies (vs ~21 s single-thread);
  client timeouts set to 20 s to absorb cold-start.
- **Wake word:** Whisper tiny.en mis-hears uncommon names; wake-word lists include
  common phonetic variants. Tune the WAKE list if recognition is unreliable.
- **Detection threshold:** YOLO detections filtered at confidence ≥ 0.4.

## Failure Recovery Summary
- Pico USB drop → firmware watchdog stops motors + server auto-reconnects.
- Camera unreachable → vision returns empty, robot reports "nothing recognized".
- Network down → Gemini unavailable, system falls back to offline Gemma/YOLO.
- Gemma service crash → systemd `Restart=on-failure` relaunches it.
