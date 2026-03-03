# video-scte35-platform

AI-powered SCTE-35 marker insertion for video streaming with YOLOv8 detection, ABR encoding, and multi-protocol output (HLS, DASH, RTMP, WebRTC).

## Architecture Overview

```
┌──────────────┐     Redis pub/sub     ┌───────────────────────────────────┐
│  FastAPI API │◄─────────────────────►│  Worker (per-channel pipeline)    │
│  (api:8000)  │                       │  FFmpeg ABR → HLS segments        │
└──────┬───────┘                       │  Frame sampler → Detector         │
       │ REST/WS                       │  Decision engine → SCTE-35 gen   │
       ▼                               │  HLS manifest patcher             │
┌──────────────┐                       └───────────────────────────────────┘
│  React UI    │  WebSocket              ▲
│  (nginx:80)  │◄────────────────────────┘
└──────────────┘
       │
       ▼
┌──────────────┐   ┌──────────────┐
│  PostgreSQL  │   │    Redis     │
└──────────────┘   └──────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose v2
- (Optional) Node.js 18+ for local frontend development

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env if needed (defaults work for local dev)
```

### 2. Start all services

```bash
docker compose up --build
```

This starts:
- **api** → http://localhost:8000 (FastAPI + OpenAPI docs at `/docs`)
- **nginx** → http://localhost:80 (React dashboard + HLS serving)
- **postgres** → localhost:5432
- **redis** → localhost:6379
- **worker** → background service

### 3. Open the dashboard

Navigate to http://localhost:80

### 4. Create a channel

```bash
curl -X POST http://localhost:8000/api/v1/channels/ \
  -H "Content-Type: application/json" \
  -d '{"name":"test","input_protocol":"file","input_url":"/data/test.mp4"}'
```

Then start it:
```bash
curl -X POST http://localhost:8000/api/v1/channels/<id>/start
```

### 5. Run tests

```bash
pip install pytest
pytest tests/ -v
```

---

## SCTE-35 Payload Generation

### How it works

SCTE-35 (ANSI/SCTE 35) is the standard for digital program insertion cueing in cable TV and streaming. This platform generates SCTE-35 cue messages automatically when the AI detector identifies splice opportunities (scene changes, black frames, or custom events).

#### Pipeline

```
Frame Sample (2fps) → Baseline/YOLO Detector → Decision Engine → SCTE-35 Generator → HLS Manifest Patcher
```

1. **Frame sampling**: FFmpeg extracts frames at 2fps (configurable) and feeds them to the detector.
2. **Detection**: The `BaselineDetector` uses heuristics (black frame threshold, frame diff) to identify potential ad break opportunities. No ML model required for the baseline.
3. **Decision engine**: Applies cooldowns (default 30s) and confidence thresholds before triggering a splice.
4. **SCTE-35 encoding**: `worker/worker/scte35/generator.py` implements:
   - `splice_insert` command (ad avail start/end)
   - `time_signal` command
   - MPEG-2 CRC-32 checksum per spec
   - Outputs: `binary`, `hex`, `base64`

#### Where SCTE-35 appears in HLS playlists

Tags are injected as `EXT-X-DATERANGE` in the **child (rendition) manifests** (`stream_0.m3u8`, etc.):

```m3u8
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:42
#EXT-X-DATERANGE:ID="scte35-1",CLASS="com.scte35",START-DATE="2024-01-01T12:00:00.000Z",DURATION=30.000,SCTE35-OUT=0xfc301400000000000000fff01405000000017feffe09c4f63500000000,X-SCTE35-OUT="/DAMAAAAAAAAA..."
#EXTINF:6.000,
stream_0_042.ts
```

- `SCTE35-OUT` — hex-encoded SCTE-35 binary payload
- `X-SCTE35-OUT` — base64-encoded version (for HLS players that prefer it)
- `DURATION` — break duration in seconds

#### SCTE-35 Packet Structure

```
SpliceInfoSection {
  table_id          = 0xFC
  section_length    = variable
  protocol_version  = 0
  pts_adjustment    = 0
  splice_command_type = 0x05 (splice_insert) or 0x06 (time_signal)
  splice_command()
  descriptor_loop_length = 0
  CRC_32            = MPEG-2 CRC
}
```

---

## GPU Enablement

The platform is CPU-first by default. To enable GPU acceleration:

### 1. Enable CUDA in FFmpeg (hardware encoding)

In `worker/worker/pipeline/ffmpeg_runner.py`, change the encoder:

```python
# CPU (default)
f"-c:v:{i}", "libx264",

# GPU (NVENC)
f"-c:v:{i}", "h264_nvenc",
```

Also add the Docker runtime in `docker-compose.yml`:
```yaml
worker:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

### 2. Enable GPU for YOLOv8

In `worker/worker/detection/base.py`, replace `YOLOv8DetectorStub` with a real implementation:

```python
# Install: pip install ultralytics torch torchvision --index-url https://download.pytorch.org/whl/cu121
from ultralytics import YOLO

class YOLOv8Detector(BaseDetector):
    def __init__(self, model_path: str = "yolov8n.pt", device: str = "cuda"):
        self.model = YOLO(model_path)
        self.device = device

    def detect_frame(self, frame: np.ndarray, pts: float) -> list[DetectionResult]:
        results = self.model(frame, device=self.device, verbose=False)
        detections = []
        for r in results:
            for box in r.boxes:
                detections.append(DetectionResult(
                    event_type=r.names[int(box.cls)],
                    confidence=float(box.conf),
                    pts=pts,
                    metadata={"bbox": box.xyxy.tolist()},
                ))
        return detections
```

Then in `channel_runner.py`, replace `BaselineDetector()` with `YOLOv8Detector()`.

### 3. Use nvidia-docker

Ensure you have:
- NVIDIA Container Toolkit installed
- `nvidia-smi` working inside Docker

---

## API Reference

The full OpenAPI spec is available at http://localhost:8000/docs when running locally.

### Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/channels/` | Create channel |
| GET | `/api/v1/channels/` | List channels |
| GET | `/api/v1/channels/{id}` | Get channel |
| PATCH | `/api/v1/channels/{id}` | Update channel |
| DELETE | `/api/v1/channels/{id}` | Delete channel |
| POST | `/api/v1/channels/{id}/start` | Start channel pipeline |
| POST | `/api/v1/channels/{id}/stop` | Stop channel pipeline |
| POST | `/api/v1/channels/{id}/restart` | Restart channel pipeline |
| WS | `/ws/{channel_id}` | Real-time events (detection/marker/status/metrics) |

### WebSocket Message Types

```json
// Detection event
{"type": "detection", "channel_id": "...", "event_type": "scene_change", "confidence": 0.87, "pts": 42.5}

// SCTE-35 marker
{"type": "marker", "channel_id": "...", "splice_type": "splice_insert", "pts": 42.5, "payload_hex": "fc30...", "payload_base64": "/DAM..."}

// Status update
{"type": "status", "channel_id": "...", "status": "running"}
```

---

## Project Structure

```
.
├── api/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py         # App factory, lifespan
│   │   ├── config.py       # Settings (pydantic-settings)
│   │   ├── database.py     # SQLAlchemy async engine
│   │   ├── models.py       # ORM: Channel, DetectionEvent, SCTEMarker
│   │   ├── schemas.py      # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── channels.py # Channel CRUD + control endpoints
│   │   │   └── websocket.py# WebSocket fan-out endpoint
│   │   └── services/
│   │       ├── redis_service.py
│   │       └── channel_service.py
│   └── alembic/            # Database migrations
│
├── worker/                 # Per-channel pipeline worker
│   └── worker/
│       ├── config.py
│       ├── main.py         # WorkerDaemon entry point
│       ├── scte35/
│       │   └── generator.py # SCTE-35 splice_insert/time_signal encoder
│       ├── hls/
│       │   └── manifest_patcher.py # EXT-X-DATERANGE injector
│       ├── detection/
│       │   └── base.py     # BaselineDetector + YOLOv8Stub
│       └── pipeline/
│           ├── ffmpeg_runner.py   # ABR HLS encoding subprocess
│           ├── frame_sampler.py   # Frame extraction for detection
│           ├── decision_engine.py # Detection → splice opportunity
│           └── channel_runner.py  # Per-channel orchestrator
│
├── dashboard/              # React frontend
│   └── src/
│       ├── pages/          # ChannelListPage, ChannelDetailPage
│       ├── components/     # HLSPlayer, EventLog, MetricsChart, etc.
│       ├── store/          # Redux Toolkit slices
│       ├── hooks/          # useChannelWebSocket
│       └── api/            # Axios client
│
├── nginx/
│   └── nginx.conf          # Reverse proxy + HLS serving + SPA fallback
│
├── tests/
│   ├── test_scte35_generator.py  # SCTE-35 encoding tests
│   └── test_manifest_patcher.py  # HLS manifest injection tests
│
└── docker-compose.yml
```

## License

MIT
