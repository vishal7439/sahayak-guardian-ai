
# ROS 2 Integration — Sahayak / IrisBot GuardianAI



**Version:** 1.0  |  **Date:** 2026-07-12  |  **Platform:** RDK X5, ROS 2 Humble + TogetheROS (tros)



## What runs on ROS 2



Sahayak includes a working ROS 2 node graph demonstrating real inter-node

communication on the RDK X5's BPU perception path:



- **`sahayak_detection_publisher`** — runs BPU-accelerated YOLOv8n inference and

  publishes detections (object name + confidence) on the `/sahayak/detections`

  topic at 1 Hz using `std_msgs/msg/String` (JSON payload).

- **`sahayak_detection_subscriber`** — subscribes to `/sahayak/detections` and

  logs received detections, confirming node-to-node delivery.



Verified live (see `ROS2_EVIDENCE.txt`):

- Topic `/sahayak/detections` active, type `std_msgs/msg/String`

- Publisher count: 1, Subscription count: 1

- Real messages, e.g. `{"objects": [{"name": "person", "score": 0.91}]}`



Reproduce:

```bash

source /opt/ros/humble/setup.bash

python3 ~/sahayak_ros/detection_publisher.py    # terminal 1

python3 ~/sahayak_ros/detection_subscriber.py   # terminal 2

ros2 topic echo /sahayak/detections             # terminal 3 (optional)

```



## Architecture decision — why the rest is Flask + direct serial



The main runtime control system (web remote, autonomous modes, motor control,

voice pipeline) uses a Flask server with direct serial to the Pico 2W, rather

than a full ROS 2 node graph. This is a deliberate engineering tradeoff for

this specific platform:



- **Single-board, latency-sensitive:** motor keepalive and the EMI safety

  watchdog need tight, predictable timing. Direct serial with a firmware

  watchdog gives a shorter, more deterministic control path than DDS

  discovery + serialization across multiple processes.

- **4 GB RAM budget:** the BPU vision stack, Whisper, Piper, and a local Gemma

  LLM already use significant memory. Running the full stack as separate ROS 2

  processes adds overhead without a proportional benefit at this scale.

- **CPU affinity control:** the system pins Flask, motor, and vision work to

  specific cores (verified). A single-process threaded design makes this

  affinity explicit and testable.



## Designed full node graph (future work)



The Stage 2 `ROS2_NODEGRAPH.md` documents the full intended node graph

(vision, motor, sensor, voice, mode-manager, web-bridge nodes). The detection

publisher/subscriber above is the first implemented slice of that design. Full

migration is planned post-competition when the multi-process overhead is

justified by distributed deployment.

