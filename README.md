
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



## Quick Start — Full Setup



**Platform:** D-Robotics RDK X5 (4 GB), stock RDK Ubuntu 22.04 image (includes the BPU

runtime and Python samples under `/app/pydev_demo`). User in examples: `sunrise`.



### 1. Clone + Python dependencies

```bash

git clone https://github.com/vishal7439/sahayak-guardian-ai.git

cd sahayak-guardian-ai

sudo apt update && sudo apt install -y ffmpeg

pip3 install flask requests pyserial google-genai

```



### 2. BPU vision model (YOLOv8x)

The model file `yolov8x_detect_bayese_640x640_nv12.bin` is the D-Robotics

BPU-quantized YOLOv8x build. It ships **pre-installed** with the RDK X5 image at:
`src/sahayak_vision.py` automatically adds that directory to `sys.path` and

loads the model from it. If your samples live elsewhere, either symlink the

model next to the code or export `PYTHONPATH`:

```bash

# Option A — symlink the model into the repo

ln -s /app/pydev_demo/02_detection_sample/03_ultralytics_yolov8/yolov8x_detect_bayese_640x640_nv12.bin src/



# Option B — point Python at the D-Robotics sample modules

export PYTHONPATH=/app/pydev_demo/02_detection_sample/03_ultralytics_yolov8:$PYTHONPATH

```

(The provided `deploy/sahayak.service` already sets this `PYTHONPATH` for systemd runs.) If your image lacks the

samples, download the model from the D-Robotics RDK Model Zoo

(https://github.com/D-Robotics/rdk_model_zoo) and place the `.bin` in that path.



### 3. Offline voice stack

```bash

# Whisper (speech-to-text)

git clone https://github.com/ggml-org/whisper.cpp ~/whisper.cpp

cd ~/whisper.cpp && cmake -B build && cmake --build build -j4

bash ./models/download-ggml-model.sh base.en



# Piper (text-to-speech, aarch64 binary + voice)

# unpack piper_linux_aarch64.tar.gz into ./piper next to server.py and add

# the en_US-lessac-medium.onnx voice to the same folder



# Gemma 3 1B (offline chat, via llama.cpp)

git clone https://github.com/ggml-org/llama.cpp ~/llama.cpp

cd ~/llama.cpp && cmake -B build && cmake --build build -j4 --target llama-server

# download gemma-3-1b-it-Q4_K_M.gguf (Hugging Face) into ~/llama.cpp/

```



### 4. Pico 2W firmware (motor safety)

Flash MicroPython (v1.2x) on the Pico 2W, then install the firmware:

```bash

pip3 install mpremote

mpremote connect /dev/ttyACM0 cp firmware/pico_main.py :main.py

```

`firmware/pico_main.py` implements the CMD serial protocol and the safety

watchdog (`CMD_TIMEOUT_MS = 600` — motors auto-stop 0.6 s after commands stop).



### 5. Configure your devices

Edit the constants near the top of `src/server.py` for your network:

- `PHONE_IP` — the phone running the IP Webcam app (camera + microphone;

  enable Audio mode in the app settings)

- `ESP32_IP` — the ESP32-S3 home-automation board

- `PHONE_MIC` in `src/voice_command.py` — same phone IP (audio stream)



### 6. Run it

```bash

python3 src/server.py            # manual run

# open http://<RDK-X5-IP>:5000

```

For always-on deployment install the systemd units:

```bash

sudo cp deploy/sahayak.service deploy/gemma.service /etc/systemd/system/

sudo systemctl daemon-reload

sudo systemctl enable --now gemma.service sahayak.service

```

Optional online mode (Gemini): see `deploy/gemini.conf.example`.



## Benchmarks (measured)



| Metric | Value |

|---|---|

| Model | YOLOv8x (640×640, NV12) |

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

