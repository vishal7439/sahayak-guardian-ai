#!/usr/bin/env python3

"""Sahayak robot backend — offline-first. Online (Claude) agent optional."""

import os, re, json, time, logging, threading

from pathlib import Path

from flask import Flask, request, jsonify



# ---------------- CONFIG ----------------

PHONE_IP            = "192.0.0.4"

CAMERA_PORT         = 8090

CAMERA_MJPEG_URL    = f"http://{PHONE_IP}:{CAMERA_PORT}/video"

CAMERA_SNAPSHOT_URL = f"http://{PHONE_IP}:{CAMERA_PORT}/shot.jpg"

import glob as _glob

def _find_pico():

    ports = sorted(_glob.glob("/dev/ttyACM*"))

    return ports[0] if ports else "/dev/ttyACM0"

PICO_PORT   = _find_pico()

PICO_BAUD   = 115200

CLAUDE_MODEL = "claude-haiku-4-5-20251001"

MAX_TOKENS   = 400

SESSION_CAP  = 50

HTML_FILE    = Path(__file__).with_name("remote.html")

MAX_MOVE_MS  = 2000



logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s  %(message)s")

log = logging.getLogger("sahayak")


# ---------------- CPU core affinity (RDK X5: 8x Cortex-A55) ----------------

def pin_to_cores(cores, label=""):

    """Pin the CURRENT thread/process to the given CPU cores, if supported."""

    try:

        if hasattr(os, "sched_setaffinity"):

            os.sched_setaffinity(0, set(cores))

            log.info("[affinity] %s pinned to cores %s", label, cores)

    except Exception as e:

        log.warning("[affinity] %s pin failed: %s", label, e)



# Core plan for the RDK X5 (8 cores, 0-7):

CORES_MOTOR   = [5]        # real-time critical: motor + watchdog keepalive

CORES_VISION  = [6, 7]     # BPU vision work, isolated for smooth detection

CORES_GENERAL = [0, 1, 2, 3]  # Flask web serving + general





try:

    import serial

except Exception:

    serial = None; log.warning("pyserial missing — Pico commands logged only.")

try:

    import requests

except Exception:

    requests = None; log.warning("requests missing — camera disabled.")



# ---------------- Pico link ----------------

_pico = None

def pico():

    global _pico, PICO_PORT

    if serial is None: return None

    if _pico is not None: return _pico

    # re-detect port in case EMI reconnect re-enumerated it (ttyACM0 -> ttyACM1)

    PICO_PORT = _find_pico()

    try:

        _pico = serial.Serial(PICO_PORT, PICO_BAUD, timeout=0.3)

        time.sleep(1.5); log.info("Pico connected on %s", PICO_PORT)

    except Exception as e:

        log.warning("Pico not connected (%s) — logging only.", e); _pico = None

    return _pico



def pico_write(line):

    global _pico

    p = pico()

    if p is None: log.info("[pico-sim] %s", line); return False

    try:

        p.write((line + "\n").encode()); return True

    except Exception as e:

        log.error("Pico write failed (%s) — dropping handle, will reconnect.", e)

        try: p.close()

        except Exception: pass

        _pico = None   # clear dead handle so next call reconnects

        return False



def pico_query(cmd, prefix, timeout=0.5):

    p = pico()

    if p is None: return None

    try:

        p.reset_input_buffer(); p.write((cmd + "\n").encode())

        deadline = time.time() + timeout

        while time.time() < deadline:

            raw = p.readline().decode(errors="ignore").strip()

            if raw.startswith(prefix): return raw

        return None

    except Exception as e:

        log.warning("pico_query(%s) failed: %s", cmd, e); return None



DIRECTIONS = {"FORWARD", "BACKWARD", "LEFT", "RIGHT"}

def do_drive(direction, speed=150):

    direction = str(direction).upper()

    if direction == "STOP": return pico_write("CMD:STOP")

    if direction in DIRECTIONS: return pico_write(f"CMD:{direction}:{int(speed)}")

    return False



def do_estop():

    ok = False

    for _ in range(3): ok = pico_write("CMD:STOP") or ok

    return ok



def pico_read_sensors():

    out = {"distance_cm": None, "temp_c": None, "humidity_pct": None}

    d = pico_query("CMD:SONAR", "DIST:")

    if d:

        try:

            v = float(d.split(":", 1)[1]); out["distance_cm"] = v if v >= 0 else None

        except Exception: pass

    t = pico_query("CMD:DHT", "DHT:")

    if t:

        try:

            _, tc, hum = t.split(":"); out["temp_c"] = float(tc); out["humidity_pct"] = float(hum)

        except Exception: pass

    return out



# ---------------- Speech (Piper) ----------------

def do_speak(text):

    text = (text or "").strip()

    if not text: return False

    try:

        _record_speech(text)   # let the phone browser speak it too

    except Exception:

        pass

    try:

        import subprocess

        piper_dir = str(Path(__file__).with_name("piper"))

        model = piper_dir + "/en_US-lessac-medium.onnx"

        wav = "/tmp/sahayak_say.wav"

        subprocess.run(f'echo {json.dumps(text)} | ./piper --model {model} --output_file {wav}',

                       shell=True, cwd=piper_dir, check=True,

                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        _speaking.set()

        try:

            subprocess.run(["aplay", "-D", "plughw:0,0", wav],

                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        finally:

            _speaking.clear()

        log.info("[speak] %s", text)

        return True

    except Exception as e:

        log.error("speak failed: %s", e); return False

# ---------------- Camera ----------------

def grab_frame_b64():

    if requests is None: return None

    try:

        import base64

        r = requests.get(CAMERA_SNAPSHOT_URL, timeout=3); r.raise_for_status()

        return base64.b64encode(r.content).decode()

    except Exception as e:

        log.warning("frame grab failed: %s", e); return None



# ---------------- Offline vision hook ----------------

def yolo_detections():
    pin_to_cores(CORES_VISION, "vision")

    """Run YOLOv8 on the BPU via the D-Robotics sample. Returns ["person", ...]."""

    try:

        import sys

        VISION_DIR = "/app/pydev_demo/02_detection_sample/03_ultralytics_yolov8"

        if VISION_DIR not in sys.path:

            sys.path.insert(0, VISION_DIR)

        import sahayak_vision

        results = sahayak_vision.detect()   # [(name, score), ...]

        return [name for name, score in results]

    except Exception as e:

        log.error("vision failed: %s", e)

        return []



def fused_detections():

    """ADDITIVE: combine YOLO detections with HC-SR04 nearest-distance.

    NOTE: the ultrasonic sensor reports ONE distance (nearest object in its

    forward cone), not a per-object distance. So distance_cm here means

    'nearest obstacle straight ahead', paired with the full YOLO label set.

    Returns: {"objects": [names...], "nearest_cm": float|None, "phrase": str}."""

    names = yolo_detections()            # existing function, untouched

    try:

        sensors = pico_read_sensors()    # existing function, untouched

        nearest = sensors.get("distance_cm")

    except Exception as e:

        log.warning("[fusion] sensor read failed: %s", e); nearest = None



    if not names:

        phrase = "I don't see anything I recognise right now."

    elif nearest is None:

        phrase = "I can see: " + ", ".join(names) + "."

    else:

        m = nearest / 100.0

        lead = names[0]

        phrase = f"I can see {lead}, and the nearest object is about {m:.1f} meters ahead."

    return {"objects": names, "nearest_cm": nearest, "phrase": phrase}

# ---------------- Claude brain (online, optional) ----------------

_claude_calls = 0

BRAIN_SYSTEM = """You are the brain of "Sahayak", a small guardian robot.

You get a camera image, a list of detected objects, and a user instruction.

Decide what to SAY and how to MOVE. Movement options: forward, backward, left, right, stop, none.

Keep moves short; the robot auto-stops near obstacles.

Reply with ONLY JSON: {"speech":"...","command":"forward|backward|left|right|stop|none","duration_ms":0-2000}"""



def ask_claude(user_text):

    global _claude_calls

    if _claude_calls >= SESSION_CAP:

        return {"speech": "Session thinking limit reached.", "command": "none", "duration_ms": 0}

    from anthropic import Anthropic

    client = Anthropic()

    content = []

    frame = grab_frame_b64()

    if frame:

        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": frame}})

    content.append({"type": "text", "text": f"Detected: {yolo_detections() or 'none'}\nUser said: {user_text}"})

    msg = client.messages.create(model=CLAUDE_MODEL, max_tokens=MAX_TOKENS,

        system=BRAIN_SYSTEM, messages=[{"role": "user", "content": content}])

    _claude_calls += 1

    raw = "".join(b.text for b in msg.content if b.type == "text").strip()

    raw = re.sub(r"^```(?:json)?|```$", "", raw).strip()

    try: return json.loads(raw)

    except Exception: return {"speech": raw[:200] or "I got confused.", "command": "none", "duration_ms": 0}



def execute_brain(data):

    do_speak(data.get("speech", ""))

    cmd = str(data.get("command", "none")).upper()

    if cmd in DIRECTIONS:

        dur = max(0, min(int(data.get("duration_ms", 0) or 0), MAX_MOVE_MS))

        if dur > 0:

            do_drive(cmd, 150); time.sleep(dur / 1000.0); do_drive("STOP")





# ---------------- Drive keepalive (feeds Pico watchdog) ----------------

_drive_cmd = ("STOP", 0)

_drive_lock = threading.Lock()



def set_drive(direction, speed=150):

    """Set the desired drive state; a background thread keeps sending it."""

    global _drive_cmd

    with _drive_lock:

        _drive_cmd = (str(direction).upper(), int(speed))

    do_drive(direction, speed)   # send immediately too



def _keepalive_loop():
    pin_to_cores(CORES_MOTOR, "keepalive/motor")

    while True:

        with _drive_lock:

            d, s = _drive_cmd

        if d != "STOP":

            do_drive(d, s)       # re-feed the watchdog

        time.sleep(0.3)



threading.Thread(target=_keepalive_loop, daemon=True).start()



# ---------------- Autonomous mode engine ----------------

_mode_thread = None

_mode_stop = threading.Event()
_handsfree_stop = threading.Event()
_speaking = threading.Event()
_handsfree_thread = None

_active_mode = None



def _guard_loop():

    """Watch for a person; speak an alert with a cooldown. Speak-only (no driving)."""

    last_alert = 0

    log.info("[guard] loop started, entering watch")

    while not _mode_stop.is_set():

        try:

            names = yolo_detections()

            log.info("[guard] saw: %s", names)

            if "person" in names and (time.time() - last_alert) > 10:

                log.info("[guard] person detected -> speaking")

                do_speak("Attention. A person has been detected.")

                last_alert = time.time()

        except Exception as e:

            log.error("[guard] loop error: %s", e)

        _mode_stop.wait(2.0)

    log.info("[guard] loop stopped")



def _patrol_loop():

    """Drive forward; on close obstacle: stop, back up, turn, continue. Uses HC-SR04."""

    STOP_CM = 30.0

    log.info("[patrol] loop started")

    do_drive("FORWARD", 140)

    while not _mode_stop.is_set():

        try:

            s = pico_read_sensors()

            dist = s.get("distance_cm")

            log.info("[patrol] dist=%s", dist)

            if dist is not None and 0 <= dist < STOP_CM:

                log.info("[patrol] obstacle! avoiding")

                do_drive("STOP");     _mode_stop.wait(0.3)

                do_drive("BACKWARD", 140); _mode_stop.wait(0.6)

                do_drive("STOP");     _mode_stop.wait(0.2)

                do_drive("RIGHT", 150);    _mode_stop.wait(0.6)

                do_drive("STOP");     _mode_stop.wait(0.2)

                if not _mode_stop.is_set():

                    do_drive("FORWARD", 140)

        except Exception as e:

            log.error("[patrol] error: %s", e)

        _mode_stop.wait(0.3)

    do_drive("STOP")

    log.info("[patrol] loop stopped")



def _follow_loop():

    """Track a person: steer to keep them centered; approach if far; stop if close."""

    import sys

    VDIR = "/app/pydev_demo/02_detection_sample/03_ultralytics_yolov8"

    if VDIR not in sys.path:

        sys.path.insert(0, VDIR)

    import sahayak_vision as vision

    log.info("[follow] loop started")

    while not _mode_stop.is_set():

        try:

            p = vision.detect_person_box()

            if p is None:

                log.info("[follow] no person -> stop")

                do_drive("STOP")

            else:

                cx = p["cx"]; area = p["area_frac"]

                log.info("[follow] cx=%.2f area=%.2f", cx, area)

                if cx < 0.40:

                    do_drive("LEFT", 150);  _mode_stop.wait(0.25); do_drive("STOP")

                elif cx > 0.60:

                    do_drive("RIGHT", 150); _mode_stop.wait(0.25); do_drive("STOP")

                elif area < 0.25:

                    do_drive("FORWARD", 140); _mode_stop.wait(0.4); do_drive("STOP")

                else:

                    do_drive("STOP")  # centered and close enough

        except Exception as e:

            log.error("[follow] error: %s", e)

        _mode_stop.wait(0.2)

    do_drive("STOP")

    log.info("[follow] loop stopped")



_MODE_LOOPS = {"guard": _guard_loop, "patrol": _patrol_loop, "follow": _follow_loop}



def start_mode(name):

    global _mode_thread, _active_mode

    stop_mode()  # stop any current mode first

    loop = _MODE_LOOPS.get(name)

    if loop is None:

        return None

    _mode_stop.clear()

    _active_mode = name

    _mode_thread = threading.Thread(target=loop, daemon=True)

    _mode_thread.start()

    return name



def stop_mode():

    global _mode_thread, _active_mode

    if _mode_thread and _mode_thread.is_alive():

        _mode_stop.set()

        _mode_thread.join(timeout=3)

    _mode_thread = None

    _active_mode = None

    do_drive("STOP")  # safety: ensure motors off when leaving any mode



def find_object_search(target):

    """Rotate scanning for `target` COCO class. Announce side when found."""

    import sys

    VDIR = "/app/pydev_demo/02_detection_sample/03_ultralytics_yolov8"

    if VDIR not in sys.path:

        sys.path.insert(0, VDIR)

    import sahayak_vision as vision

    log.info("[find] searching for: %s", target)

    do_speak(f"Looking for the {target}.")

    MAX_STEPS = 12   # ~12 turn steps = roughly a full rotation

    for step in range(MAX_STEPS):

        if _mode_stop.is_set():

            break

        # detect with positions

        try:

            r = requests.get(vision.CAMERA_URL, timeout=5)

            import numpy as np, cv2

            arr = np.frombuffer(r.content, np.uint8)

            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

            h, w = img.shape[:2]

            yolo, names = vision._load()

            boxes, ids, scores = yolo.post_process(yolo.forward(yolo.pre_process(img)), w, h)

            found = None

            for box, cid in zip(boxes, ids):

                if names[cid] == target:

                    cx = ((box[0] + box[2]) / 2.0) / w

                    found = cx

                    break

            if found is not None:

                do_drive("STOP")

                if found < 0.4:

                    side = "on my left"

                elif found > 0.6:

                    side = "on my right"

                else:

                    side = "right in front of me"

                log.info("[find] FOUND %s at cx=%.2f (%s)", target, found, side)

                do_speak(f"I found the {target} {side}!")

                return True

        except Exception as e:

            log.error("[find] error: %s", e)

        # not found this frame -> turn a bit and look again

        do_drive("RIGHT", 150); _mode_stop.wait(0.4); do_drive("STOP"); _mode_stop.wait(0.6)

    do_drive("STOP")

    log.info("[find] not found: %s", target)

    do_speak(f"Sorry, I could not find the {target}.")

    return False



def _find_loop_target(target):

    def loop():

        find_object_search(target)

        global _active_mode

        _active_mode = None

    return loop



# ---------------- Gemini brain (online, vision) ----------------

_gemini_calls = 0

GEMINI_MODEL = "gemini-flash-lite-latest"



def gemini_chat(question):

    """ADDITIVE: text-only conversational Gemini (no camera frame).

    Smarter than offline Gemma chat. Uses same key/model/session cap."""

    global _gemini_calls

    if _gemini_calls >= SESSION_CAP:

        return "I have reached my online question limit for this session."

    from google import genai

    from google.genai import types

    client = genai.Client()   # reads GEMINI_API_KEY from env

    prompt = ("You are Sahayak, a warm and friendly guardian robot who helps at home. "

              "You are having a spoken conversation. Answer helpfully and kindly in 1 to 3 "

              "short sentences that are easy to say out loud. No lists, no emojis. "

              "User says: " + question)

    resp = client.models.generate_content(model=GEMINI_MODEL,

                                           contents=[types.Part.from_text(text=prompt)])

    _gemini_calls += 1

    try:

        return resp.text.strip()

    except Exception:

        return "Sorry, I could not think of a reply just now."



def gemini_describe(question):

    """Send camera frame + question to Gemini Flash-Lite. Returns spoken answer."""

    global _gemini_calls

    if _gemini_calls >= SESSION_CAP:

        return "I have reached my online question limit for this session."

    from google import genai

    from google.genai import types

    client = genai.Client()   # reads GEMINI_API_KEY from env

    frame = grab_frame_b64()

    parts = []

    if frame:

        import base64

        parts.append(types.Part.from_bytes(data=base64.b64decode(frame), mime_type="image/jpeg"))

    prompt = ("You are Sahayak, a friendly guardian robot with a camera. "

              "Answer the user in 1 to 2 short spoken sentences, describing what you see if relevant. "

              "User asks: " + question)

    parts.append(types.Part.from_text(text=prompt))

    resp = client.models.generate_content(model=GEMINI_MODEL, contents=parts)

    _gemini_calls += 1

    return (resp.text or "I could not think of an answer.").strip()



def check_room_scan():

    """Full 360 sweep: rotate in steps, collect all objects seen, speak a report."""

    import sys

    VDIR = "/app/pydev_demo/02_detection_sample/03_ultralytics_yolov8"

    if VDIR not in sys.path:

        sys.path.insert(0, VDIR)

    import sahayak_vision as vision

    from collections import Counter

    log.info("[roomcheck] starting full sweep")

    do_speak("Checking the room. Please wait.")

    STEPS = 10          # ~10 steps for a full rotation

    seen = Counter()

    for step in range(STEPS):

        if _mode_stop.is_set():

            break

        try:

            dets = vision.detect()            # [(name, score), ...]

            # keep the max count of each object seen in any single frame

            frame_counts = Counter(name for name, score in dets if score >= 0.4)

            for obj, c in frame_counts.items():

                seen[obj] = max(seen[obj], c)

            log.info("[roomcheck] step %d saw: %s", step, dict(frame_counts))

        except Exception as e:

            log.error("[roomcheck] %s", e)

        # rotate a step

        do_drive("RIGHT", 150); _mode_stop.wait(0.4); do_drive("STOP"); _mode_stop.wait(0.8)

    do_drive("STOP")

    # build the spoken report

    if not seen:

        do_speak("Room check complete. I did not detect anything I recognize.")

        log.info("[roomcheck] nothing found")

        return

    parts = []

    for obj, c in seen.most_common():

        label = obj + ("s" if c > 1 else "")

        parts.append(f"{c} {label}")

    report = "Room check complete. I found " + ", ".join(parts) + "."

    log.info("[roomcheck] %s", report)

    do_speak(report)



def explore_scan():

    """EXPLORE MODE (additive): rotate a full turn, collect objects + nearest

    distance at the step each was first seen, then announce ONE BY ONE with

    pauses. Reuses check-room rotation style + Day-2 distance fusion. Offline."""

    import sys

    VDIR = "/app/pydev_demo/02_detection_sample/03_ultralytics_yolov8"

    if VDIR not in sys.path:

        sys.path.insert(0, VDIR)

    import sahayak_vision as vision

    log.info("[explore] starting exploration sweep")

    do_speak("Exploring the room. Let me look around.")

    STEPS = 10

    first_seen = {}   # object name -> distance_cm when first spotted (or None)

    for step in range(STEPS):

        if _mode_stop.is_set():

            break

        try:

            dets = vision.detect()

            names = [name for name, score in dets if score >= 0.4]

            dist = None

            try:

                dist = pico_read_sensors().get("distance_cm")

            except Exception:

                pass

            for n in names:

                if n not in first_seen:

                    first_seen[n] = dist

            log.info("[explore] step %d saw: %s (dist=%s)", step, names, dist)

        except Exception as e:

            log.error("[explore] %s", e)

        do_drive("RIGHT", 150); _mode_stop.wait(0.4); do_drive("STOP"); _mode_stop.wait(0.8)

    do_drive("STOP")



    if _mode_stop.is_set():

        do_speak("Exploration stopped."); return

    if not first_seen:

        do_speak("I explored the room but did not find anything I recognize."); return



    do_speak("Here is what I found.")

    _mode_stop.wait(0.8)

    # announce ONE BY ONE with pauses

    for name, dist in first_seen.items():

        if _mode_stop.is_set():

            break

        if dist is not None:

            m = dist / 100.0

            do_speak(f"I see a {name}, about {m:.1f} meters away.")

        else:

            do_speak(f"I see a {name}.")

        _mode_stop.wait(1.5)   # pause between each announcement

    do_speak("That is everything I found.")

    log.info("[explore] done: %s", dict(first_seen))

# register Explore mode now that explore_scan is defined
_MODE_LOOPS["explore"] = explore_scan



def _roomcheck_loop():

    def loop():

        check_room_scan()

        global _active_mode

        _active_mode = None

    return loop



# ---------------- Universal voice command router ----------------

import urllib.request as _urlreq



def gemma_route(text):

    """Ask the local Gemma server to classify the command. Returns a keyword or None."""

    try:

        prompt = ("You are a robot command classifier. Map the user request to EXACTLY ONE label "

                  "from this list: FIND, FOLLOW, GUARD, PATROL, ROOMCHECK, DESCRIBE, STOP, CHAT. "

                  "Use CHAT if the user is just talking, asking a question, or making conversation "

                  "rather than giving a movement or vision command. "

                  "Reply with only the label.\nUser: " + text + "\nLabel:")

        data = json.dumps({"prompt": prompt, "n_predict": 6, "temperature": 0}).encode()

        req = _urlreq.Request("http://127.0.0.1:8081/completion", data=data,

                              headers={"Content-Type": "application/json"})

        with _urlreq.urlopen(req, timeout=20) as r:

            out = json.loads(r.read())["content"].strip().upper()

        if "CHAT" in out:

            return None   # not a command -> triggers conversational fallback

        for label in ["ROOMCHECK","FIND","FOLLOW","GUARD","PATROL","DESCRIBE","STOP"]:

            if label in out:

                return label

    except Exception as e:

        log.warning("gemma_route failed: %s", e)

    return None



GEMMA_PERSONA = (

    "You are Sahayak, a warm and friendly little guardian robot who helps at home. "

    "You speak naturally and kindly, like a caring companion. "

    "Keep replies short: one or two sentences, easy to say out loud. "

    "Never use lists, emojis, or technical jargon. Just talk simply and warmly."

)



def gemma_chat(text):

    """ADDITIVE: warm conversational reply from local Gemma (offline, no tokens).

    Separate from gemma_route() which stays a strict command classifier.

    Returns a friendly sentence string, or None on failure."""

    try:

        prompt = (GEMMA_PERSONA + "\n\nPerson: " + text + "\nSahayak:")

        data = json.dumps({"prompt": prompt, "n_predict": 60,

                           "temperature": 0.7, "stop": ["\nPerson:", "Person:"]}).encode()

        req = _urlreq.Request("http://127.0.0.1:8081/completion", data=data,

                              headers={"Content-Type": "application/json"})

        with _urlreq.urlopen(req, timeout=20) as r:

            out = json.loads(r.read())["content"].strip()

        return out if out else None

    except Exception as e:

        log.warning("gemma_chat failed: %s", e)

        return None



def route_command(text):

    """Keyword-first routing (reliable), Gemma as fallback. Tolerates Whisper mishearings."""

    t = text.lower().strip()



    # --- VISION: what do you see / describe ---

    if any(w in t for w in ["what do you see", "what can you see", "what you see",

                            "describe", "look around", "what is there", "what's there"]):

        return "VISION", None



    # --- ROOM CHECK ---

    if any(w in t for w in ["check the room", "check room", "scan the room",

                            "room check", "scan room", "sweep the room"]):

        return "ROOMCHECK", None



    # --- FOLLOW ---

    if any(w in t for w in ["follow"]):

        return "FOLLOW", None



    # --- GUARD (whisper often hears 'god', 'cod', 'gard') ---

    if any(w in t for w in ["guard", "god the", "god mode", "gaurd", "gard",

                            "watch the room", "watch mode", "keep watch"]):

        return "GUARD", None



    # --- PATROL ---

    # --- EXPLORE ---
    if any(w in t for w in ["explore", "exploration", "look around and tell", "scan and tell"]):
        return "EXPLORE", None
    # --- STATUS report ---

    if any(w in t for w in ["status", "report", "how are things", "sensor reading", "readings"]):

        return "STATUS", None



    # --- HOME AUTOMATION (ESP32 relays: red bulb=1, white bulb=2) ---

    if any(w in t for w in ["bulb", "light", "lights", "lamp", "led", "relay", "red bulb", "white bulb"]):

        st = None

        if any(w in t for w in ["off", "shut", "stop", "turn off", "switch off"]): st = "off"

        elif any(w in t for w in ["on", "start", "turn on", "switch on"]): st = "on"

        if st:

            targets = []

            if any(w in t for w in ["red", "first", "one"]): targets.append(1)

            if any(w in t for w in ["white", "cfl", "second", "two"]): targets.append(2)

            if not targets and any(w in t for w in ["all", "both", "everything", "lights", "bulbs"]):

                targets = [1, 2]

            if not targets:

                targets = [1, 2]

            return "HOME", ",".join("%d:%s" % (n, st) for n in targets)



    if any(w in t for w in ["patrol", "patrole", "go around", "walk around", "petrol"]):

        return "PATROL", None



    # --- STOP ---

    if any(w in t for w in ["stop", "halt", "stand still"]):

        return "STOP", None



    # --- FIND <object> ---

    if any(w in t for w in ["find", "where is", "where's", "look for", "search for"]):

        import sys

        p = os.path.expanduser("~/sahayak")

        if p not in sys.path:

            sys.path.insert(0, p)

        import voice_command as vc

        obj = vc.find_object_in_text(t)

        return "FIND", obj



    # No Gemma classifier here: keyword matches above catch all commands.

    # SPEED: keywords catch all commands above; skip the slow classifier.

    # Unmatched input is conversation -> chat directly (saves ~11s).



    return "CHAT", text


def gemini_find_object(target):

    """Rotate scanning; at each step ask Gemini if the target is visible. Announce when found."""

    global _gemini_calls

    from google import genai

    from google.genai import types

    import base64

    client = genai.Client()

    log.info("[gfind] searching for: %s", target)

    do_speak("Looking for your " + target + ".")

    STEPS = 8

    for step in range(STEPS):

        if _mode_stop.is_set():

            break

        if _gemini_calls >= SESSION_CAP:

            do_speak("I have reached my online limit."); return

        frame = grab_frame_b64()

        if frame:

            try:

                prompt = ("Look at this camera image. Is there a " + target +

                          " visible? If yes, reply exactly: YES followed by its location "

                          "(left, center, or right) and a very short description. "

                          "If no, reply exactly: NO. Keep it under 15 words.")

                parts = [types.Part.from_bytes(data=base64.b64decode(frame), mime_type="image/jpeg"),

                         types.Part.from_text(text=prompt)]

                resp = client.models.generate_content(model=GEMINI_MODEL, contents=parts)

                _gemini_calls += 1

                answer = (resp.text or "").strip()

                log.info("[gfind] step %d: %s", step, answer)

                if answer.upper().startswith("YES"):

                    do_drive("STOP")

                    do_speak("I found your " + target + ". " + answer[3:].strip(" .:"))

                    return

            except Exception as e:

                log.error("[gfind] %s", e)

        do_drive("RIGHT", 150); _mode_stop.wait(0.4); do_drive("STOP"); _mode_stop.wait(0.6)

    do_drive("STOP")

    do_speak("Sorry, I could not find your " + target + ".")

    log.info("[gfind] not found: %s", target)



def _gfind_loop(target):

    def loop():

        gemini_find_object(target)

        global _active_mode

        _active_mode = None

    return loop



# ---------------- Phone speaker support ----------------

_last_speech = {"text": "", "id": 0}



def _record_speech(text):

    """Remember what the robot just said, so the phone browser can speak it too."""

    _last_speech["text"] = text

    _last_speech["id"] += 1



# ---------------- Flask ----------------

app = Flask(__name__)



@app.route("/")

def index():

    if not HTML_FILE.exists(): return "Put remote.html next to server.py.", 500

    html = HTML_FILE.read_text(encoding="utf-8")

    html = re.sub(r'(<img id="cam"[^>]*\bsrc=")[^"]*(")', r"\g<1>" + CAMERA_MJPEG_URL + r"\g<2>", html)

    return html



@app.route("/api/drive", methods=["POST"])

def api_drive():

    d = request.get_json(silent=True) or {}

    return jsonify(ok=set_drive(d.get("direction", "STOP"), d.get("speed", 150)) or True)



@app.route("/api/stop", methods=["POST"])

def api_stop():

    return jsonify(ok=do_estop())



ESP32_IP = "172.18.100.16"



def esp_relay(relay, state):

    """ADDITIVE: call the ESP32-S3 home-automation relay.

    relay = 1 (Red Bulb) or 2 (White Bulb); state = on | off | toggle."""

    try:

        import requests

        r = requests.get("http://%s/set?relay=%s&state=%s" % (ESP32_IP, relay, state), timeout=4)

        return r.json()

    except Exception as e:

        log.warning("esp_relay failed: %s", e)

        return None



@app.route("/api/home/<int:relay>/<state>", methods=["POST", "GET"])

def api_home(relay, state):

    result = esp_relay(relay, state)

    return jsonify(ok=(result is not None), relay=relay, state=state, esp=result)



@app.route("/api/sensors")

def api_sensors():

    return jsonify(ok=True, **pico_read_sensors())



@app.route("/api/scan")

def api_scan():

    """ADDITIVE: fused YOLO + ultrasonic. Returns objects, nearest_cm, phrase.

    Pass ?speak=1 to also speak the phrase via the existing speak path."""

    try:

        r = fused_detections()

        if request.args.get("speak") == "1":

            try: do_speak(r["phrase"])

            except Exception as e: log.warning("[scan] speak failed: %s", e)

        return jsonify(ok=True, **r)

    except Exception as e:

        return jsonify(ok=False, objects=[], nearest_cm=None, phrase="", error=str(e))



@app.route("/api/find", methods=["POST"])

def api_find():

    """Record voice -> transcribe -> extract object -> rotate & search."""

    global _mode_thread, _active_mode

    try:

        import sys

        if os.path.expanduser("~/sahayak") not in sys.path:

            sys.path.insert(0, os.path.expanduser("~/sahayak"))

        import voice_command as vc

        text, obj = vc.listen_for_command(4)

        log.info("[find] heard=%r object=%s", text, obj)

        if obj is None:

            do_speak("Sorry, I did not catch which object to find.")

            return jsonify(ok=False, heard=text, error="no known object recognized")

        # launch the rotate-and-search in a background thread

        stop_mode()

        _mode_stop.clear()

        _active_mode = "find:" + obj

        _mode_thread = threading.Thread(target=_find_loop_target(obj), daemon=True)

        _mode_thread.start()

        return jsonify(ok=True, heard=text, target=obj)

    except Exception as e:

        log.exception("find error")

        return jsonify(ok=False, error=str(e))



@app.route("/api/roomcheck", methods=["POST"])

def api_roomcheck():

    global _mode_thread, _active_mode

    try:

        stop_mode()

        _mode_stop.clear()

        _active_mode = "roomcheck"

        _mode_thread = threading.Thread(target=_roomcheck_loop(), daemon=True)

        _mode_thread.start()

        return jsonify(ok=True, mode="roomcheck")

    except Exception as e:

        log.exception("roomcheck error")

        return jsonify(ok=False, error=str(e))





def _handsfree_loop():

    """HANDS-FREE (additive): greet once, then continuously listen. Only act when

    the wake word 'irisbot' is heard. Reuses route_command + dispatch_action.

    Loops until _handsfree_stop is set (panel Stop button). Offline."""

    WAKE = ["irisbot", "iris bot", "iris board", "eris bot", "iris pot", "iris what",

            "iris bought", "irisbot", "hey iris", "iris", "irispot", "iris but"]

    import sys

    p = os.path.expanduser("~/sahayak")

    if p not in sys.path: sys.path.insert(0, p)

    import voice_command as vc

    do_speak("Hey Vishal, how can I help you today? Say iris bot before your command.")

    log.info("[handsfree] started")

    while not _handsfree_stop.is_set():

        try:

            # TTS-aware: do not record while the robot is speaking
            while _speaking.is_set() and not _handsfree_stop.is_set():
                _handsfree_stop.wait(0.2)
            vc.record(5)

            if _handsfree_stop.is_set():

                break

            text = (vc.transcribe() or "").strip()

            if not text or text == "[BLANK_AUDIO]":

                continue

            low = text.lower()

            hit = next((w for w in WAKE if w in low), None)

            log.info("[handsfree] heard: %r (wake=%s)", text, bool(hit))

            if not hit:

                continue   # no wake word -> stay quiet, keep listening

            # strip the wake word, keep the command/question after it

            idx = low.find(hit) + len(hit)

            cmd = text[idx:].lstrip(" ,.-").strip()

            if not cmd:

                do_speak("Yes Vishal, I am listening.")

                continue

            action, arg = route_command(cmd)

            log.info("[handsfree] routed %r -> %s", cmd, action)

            try:

                dispatch_action(action, arg, cmd)

            except Exception as de:

                log.error("[handsfree] dispatch failed: %s", de)

            log.info("[handsfree] ready for next command")

        except Exception as e:

            log.error("[handsfree] loop error: %s", e)

            _handsfree_stop.wait(1.0)

    do_speak("Hands free mode off.")

    log.info("[handsfree] stopped")



def dispatch_action(action, arg, text=""):
    """Shared action dispatch: used by both api_voice and hands-free loop."""
    global _mode_thread, _active_mode
    if action == "ROOMCHECK":

        stop_mode(); _mode_stop.clear(); _active_mode = "roomcheck"

        _mode_thread = threading.Thread(target=_roomcheck_loop(), daemon=True); _mode_thread.start()

        do_speak("Checking the room now.")

    elif action == "FOLLOW":

        start_mode("follow"); do_speak("Following you now.")

    elif action == "GUARD":

        start_mode("guard"); do_speak("Guard mode on.")

    elif action == "STATUS":

        try:

            sens = pico_read_sensors()

            parts = []

            d = sens.get("distance_cm")

            if d is not None: parts.append("nearest object %.0f centimeters" % d)

            tc = sens.get("temp_c"); hp = sens.get("humidity_pct")

            if tc is not None: parts.append("temperature %.0f degrees" % tc)

            if hp is not None: parts.append("humidity %.0f percent" % hp)

            mode = _active_mode or "idle"

            parts.append("mode " + str(mode))

            do_speak("Status report. " + ", ".join(parts) + ".")

        except Exception as e:

            log.warning("STATUS failed: %s", e)

            do_speak("Sorry, I could not read my sensors.")

    elif action == "HOME":

        names = {1: "red bulb", 2: "white bulb"}

        done = []

        for part in (arg or "").split(","):

            if ":" not in part:

                continue

            n, st = part.split(":", 1)

            try:

                esp_relay(int(n), st)

                done.append("%s %s" % (names.get(int(n), "light"), st))

            except Exception as e:

                log.warning("HOME dispatch failed: %s", e)

        if done:

            do_speak("Okay, " + ", ".join(done) + ".")

        else:

            do_speak("I could not control the lights.")

    elif action == "PATROL":

        start_mode("patrol"); do_speak("Patrolling now.")
    elif action == "EXPLORE":
        start_mode("explore"); do_speak("Starting to explore.")

    elif action == "STOP":

        stop_mode(); do_speak("Stopped.")

    elif action == "FIND":

        if arg:

            stop_mode(); _mode_stop.clear(); _active_mode = "find:" + arg

            _mode_thread = threading.Thread(target=_find_loop_target(arg), daemon=True); _mode_thread.start()

        else:

            do_speak("I could not tell which object to find.")

    elif action == "VISION":

        try:

            import sys

            VDIR = "/app/pydev_demo/02_detection_sample/03_ultralytics_yolov8"

            if VDIR not in sys.path:

                sys.path.insert(0, VDIR)

            import sahayak_vision as vision

            dets = vision.detect()

            if dets:

                from collections import Counter

                c = Counter(n for n, s in dets if s >= 0.4)

                parts = [f"{v} {k}" + ("s" if v > 1 else "") for k, v in c.most_common()]

                do_speak("I can see " + ", ".join(parts) + ".")

            else:

                do_speak("I do not see anything I recognize.")

        except Exception as e:

            log.error("[voice] vision error: %s", e)

            do_speak("Sorry, I could not look right now.")

    elif action == "DESCRIBE":

        try:

            ans = gemini_describe("Describe what you see briefly.")

            do_speak(ans)

        except Exception:

            do_speak("Scene description needs online mode.")

    elif action == "SPEAK":

        do_speak("Hello, I am Sahayak. How can I help?")

    elif action == "CHAT":
        reply = gemma_chat(arg) or "Sorry, I did not quite catch that."
        do_speak(reply)
    else:

        do_speak("Sorry, I did not understand that command.")

@app.route("/api/handsfree/start", methods=["POST"])

def api_handsfree_start():

    """Start hands-free continuous listening loop (offline)."""

    global _handsfree_thread

    if _handsfree_thread and _handsfree_thread.is_alive():

        return jsonify(ok=True, running=True, note="already running")

    _handsfree_stop.clear()

    _handsfree_thread = threading.Thread(target=_handsfree_loop, daemon=True)

    _handsfree_thread.start()

    return jsonify(ok=True, running=True)



@app.route("/api/handsfree/stop", methods=["POST"])

def api_handsfree_stop():

    """Stop the hands-free loop."""

    _handsfree_stop.set()

    return jsonify(ok=True, running=False)



@app.route("/api/voice", methods=["POST"])
def api_voice():

    """Universal voice command: record -> transcribe -> route -> execute -> confirm."""

    global _mode_thread, _active_mode

    try:

        import sys

        if os.path.expanduser("~/sahayak") not in sys.path:

            sys.path.insert(0, os.path.expanduser("~/sahayak"))

        import voice_command as vc

        vc.record(4)

        text = vc.transcribe()

        log.info("[voice] heard: %r", text)

        if not text:

            do_speak("I did not hear a command.")

            return jsonify(ok=False, error="no speech heard")



        action, arg = route_command(text)

        log.info("[voice] routed to: %s (arg=%s)", action, arg)



        # execute the matched action

        dispatch_action(action, arg, text)



        return jsonify(ok=True, heard=text, action=action, arg=arg)

    except Exception as e:

        log.exception("voice error")

        return jsonify(ok=False, error=str(e))



@app.route("/api/detections")

def api_detections():

    """Return raw detections (name + confidence) for the live vision panel."""

    try:

        import sys

        VDIR = "/app/pydev_demo/02_detection_sample/03_ultralytics_yolov8"

        if VDIR not in sys.path:

            sys.path.insert(0, VDIR)

        import sahayak_vision

        results = sahayak_vision.detect()   # [(name, score), ...]

        dets = [{"name": n, "score": round(float(s), 2)} for n, s in results]

        return jsonify(ok=True, detections=dets)

    except Exception as e:

        return jsonify(ok=False, detections=[], error=str(e))



@app.route("/api/gfind", methods=["POST"])

def api_gfind():

    """Gemini find-anything: get target (typed or voice), rotate & search with Gemini vision."""

    global _mode_thread, _active_mode

    d = request.get_json(silent=True) or {}

    target = (d.get("target") or "").strip()

    try:

        if not target:

            # voice: record and transcribe, use whole phrase minus 'find my/the'

            import sys

            if os.path.expanduser("~/sahayak") not in sys.path:

                sys.path.insert(0, os.path.expanduser("~/sahayak"))

            import voice_command as vc

            vc.record(4)

            text = vc.transcribe().lower()

            for w in ["find my ", "find the ", "find a ", "find ", "where is my ", "where is the ", "where is "]:

                if w in text:

                    target = text.split(w,1)[1].strip(" .?!"); break

            if not target:

                target = text.strip(" .?!")

        if not target:

            return jsonify(ok=False, error="no target heard")

        stop_mode(); _mode_stop.clear(); _active_mode = "gfind:" + target

        _mode_thread = threading.Thread(target=_gfind_loop(target), daemon=True); _mode_thread.start()

        return jsonify(ok=True, target=target)

    except Exception as e:

        log.exception("gfind error")

        return jsonify(ok=False, error=str(e))



@app.route("/api/lastspeech")

def api_lastspeech():

    """Browser polls this; if id changed, the phone speaks the text."""

    return jsonify(ok=True, text=_last_speech["text"], id=_last_speech["id"])



@app.route("/api/status")

def api_status():

    return jsonify(pico=pico() is not None, camera=grab_frame_b64() is not None, audio=True)



@app.route("/api/speak", methods=["POST"])

def api_speak():

    d = request.get_json(silent=True) or {}

    return jsonify(ok=do_speak(d.get("text", "")))



@app.route("/api/vision", methods=["POST"])

def api_vision():

    d = request.get_json(silent=True) or {}

    if d.get("mode") == "detect":

        dets = yolo_detections()

        answer = ("I see: " + ", ".join(dets)) if dets else "Nothing detected yet."

        do_speak(answer)          # speak via 3.5mm AND record for phone speaker

        return jsonify(ok=True, answer=answer)

    return jsonify(ok=False, error="Scene description runs online — switch to Online mode.")



_current_mode = None

@app.route("/api/mode/<name>", methods=["POST"])

def api_mode(name):

    if name == "stop":

        stop_mode()

        return jsonify(ok=True, mode=None)

    m = start_mode(name)

    return jsonify(ok=(m is not None), mode=m)



@app.route("/api/mode/status")

def api_mode_status():

    return jsonify(mode=_active_mode)



@app.route("/api/agent", methods=["POST"])

def api_agent():

    d = request.get_json(silent=True) or {}

    text = (d.get("text") or "").strip()

    if not text: return jsonify(ok=False, error="empty question")

    try:

        answer = gemini_describe(text)

        do_speak(answer)

        return jsonify(ok=True, answer=answer, calls=_gemini_calls)

    except Exception as e:

        log.exception("gemini error")

        return jsonify(ok=False, error="Gemini unreachable: " + str(e))



@app.route("/api/agent_voice", methods=["POST"])

def api_agent_voice():

    try:

        import sys

        p = os.path.expanduser("~/sahayak")

        if p not in sys.path: sys.path.insert(0, p)

        import voice_command as vc

        vc.record(4)

        text = vc.transcribe()

        if not text:

            return jsonify(ok=False, error="did not catch the question")

        answer = gemini_describe(text)

        do_speak(answer)

        return jsonify(ok=True, heard=text, answer=answer, calls=_gemini_calls)

    except Exception as e:

        log.exception("gemini voice error")

        return jsonify(ok=False, error=str(e))



@app.route("/api/hey_sahayak", methods=["POST"])

def api_hey_sahayak():

    """WAKE-WORD gate: record + transcribe locally (free). Only call Gemini if

    'hey sahayak' is heard. No wake word -> zero Gemini calls."""

    WAKE = ["hey robot", "hi robot", "ok robot", "okay robot", "a robot",

            "hey robert", "hey robo", "hey robbot", "hey robat", "he robot",

            "hey sahayak", "sahayak", "hey saha"]

    try:

        import sys

        p = os.path.expanduser("~/sahayak")

        if p not in sys.path: sys.path.insert(0, p)

        import voice_command as vc

        vc.record(5)

        text = (vc.transcribe() or "").strip()

        if not text:

            return jsonify(ok=False, error="did not catch anything")

        low = text.lower()

        hit = next((w for w in WAKE if w in low), None)

        if not hit:

            # NO wake word -> do NOT call Gemini (saves the call)

            do_speak("Please say, hey Sahayak, before your question.")

            return jsonify(ok=True, heard=text, woke=False,

                           answer="(no wake word - Gemini not called)", calls=_gemini_calls)

        # strip the wake phrase, keep the actual question

        idx = low.find(hit) + len(hit)

        question = text[idx:].lstrip(" ,.-").strip()

        if not question:

            do_speak("Yes? I am listening. Please ask again with hey Sahayak.")

            return jsonify(ok=True, heard=text, woke=True,

                           answer="(woke but no question)", calls=_gemini_calls)

        answer = gemini_chat(question)   # ONE Gemini call

        do_speak(answer)

        return jsonify(ok=True, heard=text, woke=True, question=question,

                       answer=answer, calls=_gemini_calls)

    except Exception as e:

        log.exception("hey_sahayak error")

        return jsonify(ok=False, error=str(e))



if __name__ == "__main__":

    pin_to_cores(CORES_GENERAL, "flask-main")
    log.info("Sahayak backend starting. Model=%s Camera=%s", CLAUDE_MODEL, PHONE_IP)

    app.run(host="0.0.0.0", port=5000, threaded=True)
