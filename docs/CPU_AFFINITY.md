
# Sahayak — CPU Affinity & Real-Time Table



**Version:** 1.1 · **Date:** 2026-07-08

**Hardware:** RDK X5 — 8x Cortex-A55 (cores 0-7), 10 TOPS BPU, 4 GB RAM



All three CPU-affinity pins are implemented with os.sched_setaffinity in server.py and verified from live runtime logs.



## Thread / process / affinity / real-time table



| Module | Thread / process | CPU core(s) | Verified | Real-time constraint |

|---|---|---|---|---|

| Flask web server | main process | 0-3 | YES (logged) | Soft: web response < 100 ms |

| Vision (YOLOv8 BPU) | detection call | 6-7 | YES (logged) | ~174 ms per inference; isolated |

| Motor + drive keepalive | keepalive thread | 5 | YES (logged) | Hard: re-send drive faster than Pico 0.6 s watchdog |

| Autonomous mode loops | mode thread | shares 0-3 | - | Soft: ~1 Hz (Guard) to fast (Follow) |

| STT / TTS / Gemma | subprocess / thread | scheduler-managed | - | Burst, not latency-critical |



## Design rationale



- Vision on isolated cores 6-7: heaviest recurring workload; pinning away from web cores keeps detection stable and remote responsive.

- Web serving on cores 0-3: general request handling has spare capacity.

- Motor keepalive on core 5: the drive-keepalive to Pico-watchdog path is the hard-real-time constraint; a dedicated core prevents stutter.



## Evidence (journalctl -u sahayak)



    [affinity] keepalive/motor pinned to cores [5]

    [affinity] flask-main pinned to cores [0, 1, 2, 3]

    [affinity] vision pinned to cores [6, 7]



All three pins confirmed active at runtime.

