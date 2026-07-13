
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



def record(seconds=4):

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

