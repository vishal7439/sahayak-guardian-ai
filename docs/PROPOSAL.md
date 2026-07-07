
# Sahayak — Design Proposal

Version 1.0 · 2026-07-07 · Vishal Bharti



## Challenge 1 — Concept & Application Design



**Scenario:** Indoor home/office, normal lighting. Fully offline core, optional online mode. Target < 200 ms detection latency.



**User:** Home occupants and elderly people. Primary interaction is voice ("check the room", "find my bottle", "follow me"); web remote is the secondary manual interface. No technical skill required.



**Core AI capabilities:**

- Perception: YOLOv8 on RDK X5 BPU (80 classes, ~174 ms, ~5.7 FPS)

- Hearing: Whisper tiny.en offline STT

- Decision: keyword-first router backed by local Gemma 3 1B; optional Gemini Flash-Lite for open-ended visual questions

- Actuation: Pico 2W over CMD:key:value serial, with firmware safety watchdog

- Speech: Piper TTS offline



**Innovation:** A complete perception-action loop on a 4 GB board — hear, understand, move, see, and report by voice. Hybrid brain (offline reflexes + optional cloud reasoning), a firmware dead-man's-switch against real EMI-induced disconnects, and voice object-search (rotate-scan-announce).



**Measurable goals:**

| Goal | Target | Achieved |

|---|---|---|

| Detection latency | < 200 ms | 174 ms |

| Throughput | > 5 FPS | 5.7 FPS |

| Person confidence | > 0.9 | ~0.95 |

| Motor auto-stop | < 1 s | 0.6 s |

| Offline voice→action | no internet | yes |

