# Saardé Foot Traffic

Computer-vision foot traffic counter for the Saardé Redfern store, plus tooling to turn the daily counts into a branded PDF report and to pull Shopify sales data for the same period.

## What's in here

| File | Purpose |
|---|---|
| [humandetector.py](humandetector.py) | Runs YOLOv8 person tracking over CCTV/video footage, counts people crossing a virtual "door" line, and logs the daily total. |
| [generate_report.py](generate_report.py) | Reads the logged daily counts and generates a branded PDF summary report. |
| [datafetch.py](datafetch.py) | Pulls order data from the Saardé Shopify store and prints daily revenue totals. |
| `foot_traffic_log.csv` | Running log of `date,count` written by `humandetector.py`, read by `generate_report.py`. Generated locally — not tracked in git except for the sample data included here for testing. |
| `saarde-logo-LIS.png` | Saardé wordmark, used in the generated PDF report. |

## Setup

1. **Install Python** 3.11+.
2. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```
3. **Shopify access** (only needed for `datafetch.py`): create a `.env` file in the project root with:
   ```
   SHOPIFY_TOKEN=your_shopify_access_token
   ```
   This file is gitignored and should never be committed.
4. **Video source**: `humandetector.py` expects a video file (or CCTV/webcam stream) to read from — see Configuration below.

## Usage

### 1. Count foot traffic — `humandetector.py`

```
python humandetector.py
```

- Runs YOLOv8 (`yolov8n.pt`) with tracking over the configured video source, drawing a threshold line across the doorway.
- Every time a tracked person crosses the line from below to above, the running count goes up (see the crossing convention comment in the script for how "in" vs "out" is defined for your camera angle).
- Press `q` at any time to stop early.
- On exit, the final count is written to `foot_traffic_log.csv` under today's date. Running it again on the same day updates that day's row instead of adding a duplicate.

**Configuration** (top of the file):
- `VIDEO_SOURCE` — path to a video file, `0` for a webcam, or an `"rtsp://..."` URL for a live CCTV feed.
- `LINE_START` / `LINE_END` — pixel coordinates of the door threshold line; adjust to match your camera's framing.
- `MODEL_PATH` — YOLOv8 weights file (defaults to the bundled `yolov8n.pt`).

### 2. Generate a PDF report — `generate_report.py`

```
python generate_report.py
```

- Reads the last 7 entries from `foot_traffic_log.csv`.
- Builds a one-page PDF with the Saardé logo, the covered date range, total foot traffic, average daily foot traffic, the highest- and lowest-traffic days, and a full daily breakdown table.
- Saves the PDF into the project folder (named after the date range it covers) and opens it automatically.
- If you don't have footage to test with yet, the sample data already in `foot_traffic_log.csv` is enough to run this on its own.

### 3. Pull Shopify sales data — `datafetch.py`

```
python datafetch.py
```

- Fetches recent orders from the Saardé Shopify store and prints total revenue per day.
- Requires `SHOPIFY_TOKEN` to be set in `.env` (see Setup above).

## Notes

- `test_video.mp4`, `test_video_1.mp4`, and `yolov8n.pt` are local test/model assets and are gitignored — bring your own footage or re-download the YOLOv8 weights (`ultralytics` will fetch them automatically if `yolov8n.pt` isn't present).
- Generated PDF reports are gitignored — each run produces its own file locally rather than being checked into version control.
