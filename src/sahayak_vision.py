import os, sys, cv2, requests, numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))

os.chdir(_HERE)

sys.path.append(os.path.abspath(os.path.join(_HERE, "../..")))

import utils.common_utils as common

from ultralytics_yolov8 import YoloV8



CAMERA_URL = "http://192.0.0.4:8090/shot.jpg"



class _Opt:

    model_path  = os.path.join(_HERE, "yolov8x_detect_bayese_640x640_nv12.bin")

    score_thres = 0.35

    nms_thres   = 0.45



_yolo = None

_names = None



def _load():

    global _yolo, _names

    if _yolo is None:

        _yolo = YoloV8(_Opt())

        _yolo.set_scheduling_params(priority=0, bpu_cores=[0])

        _names = common.load_class_names(os.path.join(_HERE, "coco_classes.names"))

    return _yolo, _names



def detect():

    """Grab one camera frame, run YOLOv8 on the BPU, return list of (name, score)."""

    yolo, names = _load()

    r = requests.get(CAMERA_URL, timeout=5)

    arr = np.frombuffer(r.content, np.uint8)

    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if img is None:

        return []

    h, w = img.shape[:2]

    boxes, ids, scores = yolo.post_process(yolo.forward(yolo.pre_process(img)), w, h)

    return [(names[c], float(s)) for c, s in zip(ids, scores)]



if __name__ == "__main__":

    print(detect())






def detect_person_box():

    """Return the largest person's horizontal center as a fraction 0..1 (0=left,1=right),

    plus box area fraction (how big/close they are), or None if no person."""

    yolo, names = _load()

    r = requests.get(CAMERA_URL, timeout=5)

    arr = np.frombuffer(r.content, np.uint8)

    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if img is None:

        return None

    h, w = img.shape[:2]

    boxes, ids, scores = yolo.post_process(yolo.forward(yolo.pre_process(img)), w, h)

    best = None

    best_area = 0

    for box, cid in zip(boxes, ids):

        if names[cid] != "person":

            continue

        x1, y1, x2, y2 = box

        area = abs((x2 - x1) * (y2 - y1))

        if area > best_area:

            best_area = area

            cx = ((x1 + x2) / 2.0) / w        # 0..1 horizontal center

            best = {"cx": float(cx), "area_frac": float(area / (w * h))}

    return best



if __name__ == "__main__":

    print("detect:", detect())

    print("person box:", detect_person_box())

