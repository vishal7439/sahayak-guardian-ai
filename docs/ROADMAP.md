
# Sahayak — Project Roadmap



**Version:** 1.0 · **Date:** 2026-07-08

**Target:** D-Robotics RDK X5 Dream Keeper Challenge 2026



Week numbers; anchor Week 1 to your real start date.



## Stage 2 — Build (design & docs)



### Week 1 — Design & measurable goals

- Design brief (scenario, user, AI capabilities, innovation)

- Measure real metrics: YOLOv8 FPS/latency, STT/TTS round-trip, e-stop reaction

- Milestone M1: PROPOSAL.md with real numbers



### Week 2 — Architecture

- System flow diagram (Mermaid), module design, compute allocation

- ROS 2 node graph design, CPU affinity / real-time table

- Milestone M2: architecture artifacts render on GitHub



### Week 3 — Engineering plan & submit

- BOM, risk analysis (5 risks + mitigation + trigger), repo structure

- Public GitHub repo + showcase PR

- Milestone M3 (Stage 2 complete): showcase PR opened



## Stage 3 — Launch (integrate & demo)



### Week 4 — Prototype integration

- Full stack integrated (BPU vision + STT + TTS + motors + safety)

- README quick start; safe shutdown / e-stop documented

- Milestone M4: fresh clone builds and launches



### Week 5 — Real-time inference & benchmarks

- BPU acceleration proof; two concurrent workloads

- Benchmark table (resolution, FPS/latency, model, tool versions)

- Milestone M5: benchmark + overlay evidence



### Week 6 — Safety, tuning

- ROS 2 performance tuning; thermal/power check under load

- Milestone M6: 30s+ continuous run without failure



### Week 7 — Demo video & packaging

- Demo video (3-7 min, 1080p); tag repo v1.0-demo

- Technical docs; community post; showcase PR update

- Milestone M7 (Stage 3 complete): full bundle submitted



## Milestone summary



| ID | Milestone | Stage |

|----|-----------|-------|

| M1 | Design brief w/ metrics | 2 |

| M2 | Architecture artifacts | 2 |

| M3 | Stage 2 submission | 2 |

| M4 | Integration lock | 3 |

| M5 | Inference + benchmarks | 3 |

| M6 | Safety + stability | 3 |

| M7 | Demo + packaging | 3 |

