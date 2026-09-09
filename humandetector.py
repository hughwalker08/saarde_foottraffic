from ultralytics import YOLO
import cv2
import numpy as np
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# ── Configuration — only these values need changing for your CCTV setup ───────
VIDEO_SOURCE = SCRIPT_DIR / "test_video.mp4"  # file path, 0 for webcam, or "rtsp://..." for CCTV
LINE_START   = (600,  540)        # left end of door threshold line  (x, y)
LINE_END     = (1440, 540)        # right end of door threshold line (x, y)
# Crossing convention (for a horizontal line):
#   person moves from ABOVE the line (smaller y) → BELOW (larger y)  = OUT
#   person moves from BELOW the line             → ABOVE              = IN
# ──────────────────────────────────────────────────────────────────────────────

MODEL_PATH   = "yolov8n.pt"
PERSON_CLASS = 0

count_in  = 0
prev_side: dict[int, int] = {}  # track_id → side of line last frame (+1 or -1)


def _side(pt: tuple, p1: tuple, p2: tuple) -> int:
    val = (p2[0] - p1[0]) * (pt[1] - p1[1]) - (p2[1] - p1[1]) * (pt[0] - p1[0])
    return 1 if val >= 0 else -1


def process_frame(frame: np.ndarray, results) -> np.ndarray:
    global count_in

    cv2.line(frame, LINE_START, LINE_END, (0, 255, 255), 2)
    cv2.putText(frame, "DOOR", (LINE_START[0] + 8, LINE_START[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    boxes = results[0].boxes
    if boxes.id is not None:
        for xyxy, track_id, cls in zip(boxes.xyxy.cpu().numpy(),
                                       boxes.id.cpu().numpy(),
                                       boxes.cls.cpu().numpy()):
            if int(cls) != PERSON_CLASS:
                continue

            tid             = int(track_id)
            x1, y1, x2, y2 = map(int, xyxy)
            cx, cy          = (x1 + x2) // 2, (y1 + y2) // 2
            curr_side       = _side((cx, cy), LINE_START, LINE_END)

            if tid in prev_side and prev_side[tid] != curr_side:
                if prev_side[tid] == 1 and curr_side == -1:
                    count_in += 1

            prev_side[tid] = curr_side

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 0), 2)
            cv2.circle(frame, (cx, cy), 5, (0, 200, 0), -1)
            cv2.putText(frame, f"ID {tid}", (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 0), 1)

    # Counter overlay — top right
    _, w = frame.shape[:2]
    bx1, by1, bx2, by2 = w - 260, 16, w - 16, 80
    overlay = frame.copy()
    cv2.rectangle(overlay, (bx1, by1), (bx2, by2), (20, 20, 20), -1, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    cv2.rectangle(frame, (bx1, by1), (bx2, by2), (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(frame, "FOOT TRAFFIC", (bx1 + 12, by1 + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1, cv2.LINE_AA)
    cv2.putText(frame, str(count_in), (bx1 + 12, by1 + 54),
                cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 180), 2, cv2.LINE_AA)

    return frame


def main():
    model = YOLO(MODEL_PATH)
    cap   = cv2.VideoCapture(str(VIDEO_SOURCE))

    if not cap.isOpened():
        print(f"Cannot open video source: {str(VIDEO_SOURCE)!r}")
        return

    print("Running — press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model.track(frame, persist=True, classes=[PERSON_CLASS], verbose=False)
        frame   = process_frame(frame, results)

        cv2.imshow("Foot Traffic Counter", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"\nFoot traffic count: {count_in}")


if __name__ == "__main__":
    main()
