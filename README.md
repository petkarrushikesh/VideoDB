<img width="720" height="1640" alt="WhatsApp Image 2026-07-03 at 10 27 04 PM" src="https://github.com/user-attachments/assets/a29ff95f-1db5-4133-b8dc-b035648b82d8" />
<img width="720" height="1640" alt="WhatsApp Image 2026-07-03 at 10 27 04 PM" src="https://github.com/user-attachments/assets/fa28239b-a054-46ac-beaf-b13034fe46bb" />
# FocusLens Lite

A minimal, production-quality Flask backend that analyzes study session videos
using **VideoDB** and returns a structured focus/distraction timeline.

---

## Architecture

```
focuslens-lite/
├── app.py                    # Flask factory & entry point
├── config.py                 # All settings from environment variables
├── requirements.txt
├── .env.example
├── routes/
│   └── session_routes.py     # POST /upload-session, GET /health
├── services/
│   ├── videodb_service.py    # Upload, index, fetch — all VideoDB calls
│   └── analyzer.py           # Raw scenes → classified FocusEvent list
└── utils/
    └── summary.py            # Aggregate metrics & response serialization
```

---

## Setup

### 1. Clone & install

```bash
cd focuslens-lite
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and set VIDEODB_API_KEY (get yours at https://videodb.io)
```

### 3. Run

```bash
python app.py
# Server starts at http://localhost:5000
```

---

## API

### `GET /health`

```json
{ "status": "ok", "service": "FocusLens Lite" }
```

---

### `POST /upload-session`

Upload a study session video and receive a focus performance report.

**Request** — `multipart/form-data`

| Field           | Type   | Required | Description                                          |
|----------------|--------|----------|------------------------------------------------------|
| `file`          | File   | ✅       | Video file (mp4, mov, avi, mkv, webm, ≤500 MB)      |
| `index_audio`   | string | ❌       | `"true"` to also run spoken word indexing            |
| `language_code` | string | ❌       | BCP-47 code for audio (`"en"`, `"hi"`, `"ja"`, …)   |

**cURL example**

```bash
curl -X POST http://localhost:5000/upload-session \
  -F "file=@/path/to/study_session.mp4"
```

**Success response — 200**

```json
{
  "video_id": "m-abc123",
  "scene_index_id": "si-xyz456",
  "summary": {
    "total_duration_seconds": 3600.0,
    "focus_time_seconds": 2700.0,
    "distraction_time_seconds": 720.0,
    "idle_time_seconds": 180.0,
    "focus_percentage": 75.0,
    "distraction_percentage": 20.0,
    "idle_percentage": 5.0,
    "focus_score": "Good",
    "event_count": 14
  },
  "events": [
    { "type": "focus",       "start": 0,    "end": 1200, "duration": 1200, "description": "Person is typing and focused on screen." },
    { "type": "distraction", "start": 1200, "end": 1320, "duration": 120,  "description": "Person is looking at phone." },
    { "type": "focus",       "start": 1320, "end": 2700, "duration": 1380, "description": "Person is reading and taking notes." }
  ]
}
```

**Error responses**

| Status | Meaning                                       |
|--------|-----------------------------------------------|
| 400    | Missing file or unsupported format            |
| 422    | Video too short / empty index                 |
| 502    | VideoDB API error                             |
| 500    | Unexpected internal error                     |

---

## Configuration reference

| Variable               | Default                          | Description                                  |
|------------------------|----------------------------------|----------------------------------------------|
| `VIDEODB_API_KEY`      | *(required)*                     | Your VideoDB API key                         |
| `VIDEODB_COLLECTION_ID`| *(uses default collection)*      | Target collection (leave blank = default)    |
| `FLASK_ENV`            | `production`                     | Flask environment                            |
| `DEBUG`                | `false`                          | Enable debug logging                         |
| `MAX_UPLOAD_MB`        | `500`                            | Max upload size in megabytes                 |
| `SCENE_EXTRACTION_TYPE`| `time`                           | `time` (interval) or `shot` (transitions)   |
| `SCENE_INTERVAL_SECONDS`| `10`                            | Seconds between frames (time-based only)     |
| `SCENE_FRAME_COUNT`    | `2`                              | Frames sampled per interval                  |
| `SCENE_PROMPT`         | *(built-in focus/distraction prompt)* | Custom vision model prompt              |

---

## How it works

1. **Upload** — video is saved to a temp file and sent to VideoDB.
2. **Scene index** — VideoDB samples frames every `SCENE_INTERVAL_SECONDS` seconds and uses a vision model to annotate each segment with the configured prompt.
3. **Classify** — `analyzer.py` applies keyword matching on each description to label it `focus`, `distraction`, or `idle`.
4. **Merge** — consecutive segments of the same type are merged to reduce noise.
5. **Summarize** — `summary.py` totals durations and computes percentages.
6. **Respond** — structured JSON is returned to the caller.

## Focus Score legend

| Score              | Focus %  |
|--------------------|----------|
| Excellent          | ≥ 80%    |
| Good               | 60–79%   |
| Fair               | 40–59%   |
| Needs Improvement  | < 40%    |
