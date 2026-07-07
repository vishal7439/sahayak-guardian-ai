
# Sahayak — System Architecture

Version 1.0 · 2026-07-07



## Challenge 2 — AI System Architecture



### System flow

```mermaid

flowchart TD

    MIC["Mic"] --> STT["Whisper tiny.en (CPU)"]

    WEB["Web Remote"] --> SRV

    STT --> ROUTER["Command Router: keywords + Gemma 3 1B"]

    ROUTER --> SRV["Flask Server (RDK X5)"]

    CAM["OPPO F27 IP cam"] --> YOLO["YOLOv8 (BPU)"]

    YOLO --> SRV

    SRV --> VLM["Gemini Flash-Lite (cloud, optional)"]

    SRV -->|serial| PICO["Pico 2W"]

    PICO --> MOTOR["L298N motors"]

    PICO --> SONAR["HC-SR04"]

    PICO -->|watchdog auto-stop| MOTOR

    SRV --> TTS["Piper TTS"] --> SPK["Speaker"]

    SRV -->|WiFi HTTP| ESP["ESP32-S3 lights"]

```



### Module design

| Module | Responsibility | Failure handling |

|---|---|---|

| Flask server | orchestrates features, serves remote | auto-restart via systemd |

| Vision | YOLOv8 BPU inference | empty list on camera fail |

| STT | Whisper transcription | "did not hear" on empty |

| Router | map command to action | keyword fallback if Gemma unsure |

| Motor bridge (Pico) | drive + sensors | watchdog auto-stop < 0.6 s |

| TTS | speak responses | log error, continue |

| Home control (ESP32) | switch lights | independent node |



### Compute allocation

| Workload | Runs on | Utilisation |

|---|---|---|

| YOLOv8 | BPU | ~1 inference / 174 ms |

| Whisper / Piper | CPU | burst |

| Gemma 3 1B | CPU | ~3 s per routed command |

| Flask + I/O | CPU | continuous, light |

| Gemini | cloud | only on online request |



### Real-time note

The drive-keepalive (re-send every 0.3 s) must stay under the Pico's 0.6 s watchdog timeout: smooth motion when connected, guaranteed stop when not.

