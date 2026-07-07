
# Sahayak — IrisBot GuardianAI 🤖



> An offline-first, voice-controlled autonomous guardian robot built on the D-Robotics RDK X5.

> It **sees, listens, thinks, moves, and speaks** — running real-time BPU-accelerated AI on-device, with an optional cloud brain for richer reasoning.



**Author:** Vishal Bharti (Irisrobonium)

**Competition:** D-Robotics RDK X5 Dream Keeper Challenge 2026

**Version:** 1.0 · **Date:** 2026-07-07



---



## What it does



You talk to it, and it acts — all core intelligence runs **offline on the RDK X5's BPU**.



| Capability | How | Runs |

|---|---|---|

| 👁️ See & identify objects | YOLOv8 on BPU (80 classes) | Offline |

| 🎤 Listen to commands | Whisper (tiny.en) STT | Offline |

| 🧠 Understand commands | Keyword router + Gemma 3 1B | Offline |

| 🗣️ Speak responses | Piper TTS | Offline |

| 🚗 Move | Pico 2W + L298N motors | Offline |

| 🛡️ Guard mode | Detect person → alert | Offline |

| 🧭 Patrol mode | Drive + ultrasonic avoidance | Offline |

| 🏃 Follow mode | Track & follow a person | Offline |

| 🔍 Find object | "Find my bottle" → rotate, scan, announce | Offline |

| 🔎 Check room | 360° sweep → report everything seen | Offline |

| 💬 Describe scene | Rich natural-language description | Online (Gemini) |



## Quick Start



```bash

git clone https://github.com/vishal7439/sahayak-guardian-ai.git

cd sahayak-guardian-ai

pip3 install flask google-genai requests pyserial

python3 src/server.py

# open http://<RDK-X5-IP>:5000

```



## Benchmarks (measured)



| Metric | Value |

|---|---|

| Model | YOLOv8x (640×640, NV12) |

| Hardware | RDK X5 BPU (10 TOPS) |

| Avg latency | **174 ms** |

| Avg FPS | **5.7** |



See `docs/` for full architecture, BOM, roadmap, risks, and benchmarks.



## Safety

The Pico firmware auto-stops motors within 0.6 s if commands stop (dead-man's switch). Home-control demonstrated with low-voltage LEDs only.



## License

MIT — see LICENSE.

