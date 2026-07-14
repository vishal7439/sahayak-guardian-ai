
# Sahayak — IrisBot GuardianAI 🤖



> An offline-first, voice-controlled autonomous guardian robot built on the D-Robotics RDK X5.

> It **sees, listens, thinks, moves, and speaks** — running real-time BPU-accelerated AI on-device, with an optional cloud brain for richer reasoning.



**Author:** Vishal Bharti (Irisrobonium)

**Competition:** D-Robotics RDK X5 Dream Keeper Challenge 2026

**Version:** 1.0 · **Date:** 2026-07-07



---



## Demo Video



▶️ **Watch the full demo:** https://youtu.be/oQaQGBd4iME



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

| 🧭 Explore mode | Rotate, scan, announce objects one-by-one with distance | Offline |

| 📏 Distance fusion | Ultrasonic + YOLO → "person, 0.6 m ahead" | Offline |

| 💬 Conversational chat | Warm companion replies (Gemma 3 1B persona) | Offline |

| 🙌 Hands-free mode | Continuous wake-word listening ("IrisBot") | Offline |

| 🔌 EMI auto-reconnect | Recovers dropped Pico USB without restart | Offline |

| 🔗 ROS 2 nodes | BPU detections published on /sahayak/detections | Offline |

| 💡 Home automation | ESP32-S3 relays — "hey robot, turn on red bulb" | Offline |

| 🎤 Phone-mic + VAD listening | Speak anytime — voice-activated capture, no fixed windows | Offline |

| 🤖 Gemini action agent | "it's too dark in here" → Gemini decides → light on | Online |



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

| Model | YOLOv8n (640×640, NV12) |

| Hardware | RDK X5 BPU (10 TOPS) |

| Avg latency | **174 ms** |

| Avg FPS | **5.7** |



See `docs/` for full architecture, BOM, roadmap, risks, and benchmarks.



## Safety & Emergency Stop

- **Emergency Stop button** on the web remote immediately halts all motion (`POST /api/stop`).

- **Firmware dead-man's switch:** the Pico auto-stops motors within 0.6 s if it

  stops receiving commands (covers crashes, network loss, EMI USB drops).

- **Server-side auto-reconnect:** if motor EMI drops the Pico USB link, the server

  detects the dead handle and re-opens the port — recovering without a restart.

- **Safe shutdown:** leaving any autonomous mode calls `stop_mode()`, which stops

  the motors before exiting. Stopping `sahayak.service` also halts all motion.

- Home-appliance control demonstrated with low-voltage loads only.



## License

MIT — see LICENSE.




## Deployment (systemd services)



For always-on operation, the robot server and the offline Gemma LLM run as

systemd services — auto-start on boot, auto-restart on failure:



    sudo systemctl enable --now sahayak.service   # Flask robot server (port 5000)

    sudo systemctl enable --now gemma.service     # Gemma 3 1B llama-server (port 8081)



## ROS 2 detection nodes (ROS 2 Humble)



Sahayak includes real ROS 2 nodes that publish BPU YOLO detections:



    source /opt/ros/humble/setup.bash

    python3 ros2/detection_publisher.py    # publishes BPU detections

    python3 ros2/detection_subscriber.py   # subscribes and logs

    ros2 topic echo /sahayak/detections    # verify live



See `docs/ROS2_HYBRID.md` for the architecture rationale and `ros2/ROS2_EVIDENCE.txt`

for verified live output.

