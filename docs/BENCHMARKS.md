
# Sahayak — Benchmarks

Version 1.0 · 2026-07-07 · 20 inferences after warm-up (benchmark.py)



| Metric | Value |

|---|---|

| Model | YOLOv8x (yolov8x_detect_bayese_640x640_nv12) |

| Hardware | RDK X5 BPU (10 TOPS) |

| Resolution | 640×640 NV12 |

| Runtime | hbm_runtime / HBRT 3.15.55 |

| Avg latency | 174.4 ms |

| Median | 176.8 ms |

| Best | 145.3 ms |

| Worst | 223.9 ms |

| Avg FPS | 5.7 |

| Peak FPS | 6.9 |

| Person confidence | ~0.95 |



Latency is end-to-end (WiFi frame fetch + BPU inference + post-process). Pure BPU is faster.



Reproduce:

    cd /app/pydev_demo/02_detection_sample/03_ultralytics_yolov8/

    python3 ~/sahayak/benchmark.py

