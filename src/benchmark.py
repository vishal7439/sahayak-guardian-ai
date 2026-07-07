
import sys, time

sys.path.insert(0, "/app/pydev_demo/02_detection_sample/03_ultralytics_yolov8")

import sahayak_vision as v



print("=" * 50)

print("Sahayak BPU Benchmark — YOLOv8 on RDK X5")

print("=" * 50)



# Warm up (loads model)

print("\nLoading model (warm-up)...")

t0 = time.time()

v.detect()

print(f"Model load + first inference: {time.time()-t0:.2f}s")



# Measure steady-state detection over N runs

N = 20

print(f"\nMeasuring {N} inferences...")

times = []

for i in range(N):

    t = time.time()

    v.detect()

    dt = time.time() - t

    times.append(dt)



times.sort()

avg = sum(times) / len(times)

best = times[0]

worst = times[-1]

median = times[len(times)//2]



print("\n" + "=" * 50)

print("RESULTS")

print("=" * 50)

print(f"Model:        YOLOv8 (yolov8x_detect_bayese_640x640_nv12)")

print(f"Hardware:     RDK X5 BPU (10 TOPS)")

print(f"Resolution:   640x640 (NV12)")

print(f"Runs:         {N}")

print(f"Avg latency:  {avg*1000:.1f} ms")

print(f"Median:       {median*1000:.1f} ms")

print(f"Best:         {best*1000:.1f} ms")

print(f"Worst:        {worst*1000:.1f} ms")

print(f"Avg FPS:      {1/avg:.1f}")

print(f"Peak FPS:     {1/best:.1f}")

print("=" * 50)

