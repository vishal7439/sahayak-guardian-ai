
import subprocess, os



WHISPER = os.path.expanduser("~/whisper.cpp/build/bin/whisper-cli")

MODEL   = os.path.expanduser("~/whisper.cpp/models/ggml-base.en.bin")

WAV     = "/tmp/voice_cmd.wav"



# The 80 COCO classes YOLOv8 knows

COCO = ["person","bicycle","car","motorbike","aeroplane","bus","train","truck","boat",

"traffic light","fire hydrant","stop sign","parking meter","bench","bird","cat","dog",

"horse","sheep","cow","elephant","bear","zebra","giraffe","backpack","umbrella","handbag",

"tie","suitcase","frisbee","skis","snowboard","sports ball","kite","baseball bat",

"baseball glove","skateboard","surfboard","tennis racket","bottle","wine glass","cup",

"fork","knife","spoon","bowl","banana","apple","sandwich","orange","broccoli","carrot",

"hot dog","pizza","donut","cake","chair","sofa","pottedplant","bed","diningtable","toilet",

"tvmonitor","laptop","mouse","remote","keyboard","cell phone","microwave","oven","toaster",

"sink","refrigerator","book","clock","vase","scissors","teddy bear","hair drier","toothbrush"]



PHONE_MIC = "http://192.0.0.4:8090/audio.wav"   # OPPO IP Webcam audio stream



def record(seconds=4):

    """Record from the phone mic (better quality, separate device); fall back

    to the local 3.5mm mic if the phone stream is unreachable."""

    try:

        subprocess.run(["ffmpeg","-y","-loglevel","error",

                        "-i",PHONE_MIC,"-t",str(seconds),

                        

                        "-ar","16000","-ac","1",WAV],

                       check=True, timeout=seconds+6,

                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return

    except Exception:

        pass  # phone unreachable -> fall back to local mic

    subprocess.run(["arecord","-D","plughw:0,0","-f","S16_LE","-r","16000",

                    "-c","1","-d",str(seconds),WAV],

                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)



def transcribe():

    out = subprocess.run([WHISPER,"-m",MODEL,"-f",WAV,"-nt"],

                         capture_output=True, text=True)

    return out.stdout.strip()



def find_object_in_text(text):

    """Return the first COCO class mentioned in the text, or None."""

    t = text.lower()

    # check multi-word classes first (e.g. 'cell phone' before 'phone')

    for cls in sorted(COCO, key=lambda c: -len(c)):

        if cls in t:

            return cls

    # a few friendly synonyms

    synonyms = {"phone":"cell phone","tv":"tvmonitor","television":"tvmonitor",

                "plant":"pottedplant","couch":"sofa","table":"diningtable","glass":"cup"}

    for word, cls in synonyms.items():

        if word in t:

            return cls

    return None



def listen_for_command(seconds=4):

    """Record, transcribe, return (raw_text, matched_object_or_None)."""

    record(seconds)

    text = transcribe()

    obj = find_object_in_text(text)

    return text, obj



if __name__ == "__main__":

    print("Speak now (4s)...")

    text, obj = listen_for_command()

    print("Heard:", repr(text))

    print("Object:", obj)




VAD_THRESHOLD = 700      # RMS above this counts as voice

VAD_CHUNK_SEC = 0.25

VAD_SILENCE_CHUNKS = 3   # ~0.75s of silence ends the capture

VAD_MAX_SEC = 8          # max utterance length



def record_vad(max_wait=15):

    """Listen continuously on the phone stream; start capturing when voice is

    detected, stop after ~0.75s of silence. Returns True if speech was captured,

    False on timeout. Falls back to fixed local recording if the stream fails."""

    import audioop, wave, time

    rate, width = 16000, 2

    chunk_bytes = int(rate * VAD_CHUNK_SEC) * width

    try:

        p = subprocess.Popen(["ffmpeg", "-loglevel", "quiet", "-i", PHONE_MIC,

                              "-f", "s16le", "-ar", str(rate), "-ac", "1", "pipe:1"],

                             stdout=subprocess.PIPE)

    except Exception:

        record(4)

        return True

    pre, buf = [], []

    started, ok, silent = False, False, 0

    t0 = time.time()

    try:

        while True:

            data = p.stdout.read(chunk_bytes)

            if not data or len(data) < chunk_bytes // 2:

                break

            level = audioop.rms(data, width)

            if not started:

                pre.append(data)

                pre = pre[-2:]                      # 0.5s pre-roll so word starts aren't clipped

                if level >= VAD_THRESHOLD:

                    started = True

                    buf = list(pre)

                elif time.time() - t0 > max_wait:

                    break

            else:

                buf.append(data)

                silent = silent + 1 if level < VAD_THRESHOLD else 0

                if silent >= VAD_SILENCE_CHUNKS or len(buf) * VAD_CHUNK_SEC > VAD_MAX_SEC:

                    ok = True

                    break

    finally:

        try:

            p.kill()

        except Exception:

            pass

    if not ok:

        return False

    w = wave.open(WAV, "wb")

    w.setnchannels(1)

    w.setsampwidth(width)

    w.setframerate(rate)

    w.writeframes(b"".join(buf))

    w.close()

    return True

