
# Sahayak — Bill of Materials

Version 2.0 · 2026-07-17 (Stage 3 final build)



| # | Part (exact) | Qty | Power / Interface | Source / supplier | Est. cost (INR) |

|---|---|---|---|---|---|

| 1 | D-Robotics RDK X5, 4 GB RAM, 10 TOPS BPU | 1 | 5 V USB-C supply | D-Robotics (challenge kit) | 7,000 |

| 2 | Raspberry Pi Pico 2 W (RP2350, WiFi) | 1 | 5 V over USB from RDK; USB-CDC serial | Local electronics / robu.in | 800 |

| 3 | L298N dual H-bridge motor driver | 1 | Motor V+ from battery pack; IN1–IN4 from Pico GPIO | Local electronics | 150 |

| 4 | BO DC gear motors (6 V) + wheels | 2 | 6 V from L298N outputs | Local electronics | 300 |

| 5 | HC-SR04 ultrasonic sensor | 1 | 5 V from Pico VBUS; TRIG/ECHO on GPIO | Local electronics | 80 |

| 6 | DHT22 (AM2302) temp/humidity sensor | 1 | 3.3 V from Pico; single-wire DATA on GPIO | Local electronics | 150 |

| 7 | OPPO F27 phone + IP Webcam app | 1 | Own battery; WiFi hotspot; serves camera + mic at :8090 | Owned | owned |

| 8 | ESP32-S3 dev board | 1 | 5 V USB adapter; WiFi web server | Local electronics / robu.in | 500 |

| 9 | 2-channel relay module (SRD-05VDC-SL-C, 10 A 250 VAC, opto-isolated) | 1 | 5 V + IN1/IN2 from ESP32 GPIO | Local electronics | 120 |

| 10 | Bulbs — red + white CFL, with holders | 2 | 230 V mains, LIVE switched via relay COM→NO | Local hardware store | 150 |

| 11 | 3.5 mm mini speaker | 1 | RDK 3.5 mm jack (Piper TTS output) | Local electronics | 150 |

| 12 | 3.5 mm microphone (fallback ears) | 1 | RDK 3.5 mm jack | Local electronics | 100 |

| 13 | Battery pack (motor supply) | 1 | Feeds L298N motor V+; common GND with Pico | Local electronics | 400 |

| 14 | Wooden chassis, mounts, jumper wires | 1 | — | Self-made / local | 200 |



**Est. build cost (excluding owned phone): ~10,100 INR (~$120).**



## Power summary

- RDK X5: dedicated 5 V USB-C supply (always on; runs systemd services)

- Pico 2W: powered over the same USB cable that carries serial commands

- Motors: separate battery pack via L298N — logic and motor power never share a rail

- ESP32-S3 + relay: independent 5 V USB adapter — home side stays on if the robot is off

- Bulbs: 230 V mains, LIVE wire switched through relay COM/NO, NEUTRAL direct



## Mains safety note

Home-appliance switching uses the opto-isolated relay with outputs in an insulated

enclosure. All mains wiring done unplugged and under supervision. For replication,

low-voltage LED loads on the relay give identical demo behaviour with zero risk.

