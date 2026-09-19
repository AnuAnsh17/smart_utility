# Smart Utility (Urja) — AI Electricity Utility Assistant

**Smart Utility** (Urja) turns a raw electricity bill into actionable consumption
insights, forecasts, and conversational guidance. Next.js frontend, local
FastAPI backend.

Everything runs on your own machine. Uploaded bills, OCR text and analysis
results are written to `backend/data/` and are never sent to an external
service — no cloud OCR, no third-party LLM, no telemetry.

---

## Overview

Smart Utility lets a household upload a monthly electricity bill — a PDF or a
photo, in English or an Indian language — and get back a structured breakdown of
what it actually says. A local pipeline rasterises the document, runs OCR,
detects the language, normalises Indian-language numerals and month names,
extracts the billing fields, validates them against each other, and produces
consumption trends, a forecast, and efficiency recommendations.

**Extracted values are reported as found.** A field the pipeline cannot read
stays `null` and is listed as missing; a value that looks wrong is flagged
rather than corrected. Every figure on the dashboard is traceable to a page in
the uploaded document.

---

## Product Concept

Most utility bills are confusing and static documents that hide actionable insights. Smart Utility solves this by offering:
- **Instant Bill Analysis**: Multi-format OCR & AI extraction for Indian electricity utilities (e.g., MSEDCL, TATA Power, BESCOM, BSES, Adani Electricity).
- **Consumption Analytics**: Trend breakdown across appliances and historical billing cycles.
- **Predictive Forecasting**: Weather-adjusted next-month bill ranges and kWh estimations.
- **Weather Impact Correlation**: Live weather context matching high consumption periods with temperature spikes.
- **AI Energy Assistant**: Interactive assistant capable of explaining bill increases, offering custom saving tips, and detailing tariff structures.

---

## Core User Flow

```
Landing Page (Upload / Sample Bill)
        ↓
File Validation & Preparation
        ↓
Animated Processing Pipeline (Multi-stage AI Analysis)
        ↓
Analysis Completion & Metrics Summary
        ↓
Interactive Analytics Dashboard (Insights, Forecasts, Assistant)
```

---

## Technology Stack

**Frontend**
- **Framework**: Next.js 15 (App Router, TypeScript)
- **Styling**: Tailwind CSS, PostCSS, Autoprefixer
- **Animations & Motion**: Framer Motion
- **Data Visualization**: Recharts
- **Icons**: Lucide React
- **Type Safety**: TypeScript 5.7+
- **Code Quality**: ESLint, PostCSS

**Backend**
- **API**: FastAPI + Uvicorn
- **Database**: SQLite via SQLAlchemy 2.0 (WAL mode)
- **Validation**: Pydantic v2
- **OCR**: Tesseract 5 + PyMuPDF (PDF rasterisation) + pytesseract + Pillow
- **Async**: in-process `BackgroundTasks` with an asyncio event bus for SSE

---

## Architecture

```
src/
├── app/                  # Next.js App Router routes & layouts
│   ├── layout.tsx        # Global font, styles, metadata
│   ├── page.tsx          # Main single-page application orchestrator
│   └── globals.css       # Global CSS & Tailwind directives
├── components/           # Reusable UI components by domain
│   ├── brand/            # Logo, branding badges, header markers
│   ├── layout/           # Sidebar, Topbar, Main Shell
│   ├── upload/           # Landing page upload zone & file validation
│   ├── processing/       # Animated AI processing pipeline steps
│   ├── dashboard/        # Dashboard overview, top metric cards, breakdown
│   ├── forecast/         # Predictive forecasting visualization
│   ├── weather/          # Weather impact cards & climate widgets
│   ├── insights/         # AI insights & recommendation cards
│   ├── assistant/        # Conversational AI assistant panel
│   ├── documents/        # Historical bills table & document viewer
│   └── ui/               # Reusable buttons, cards, tooltips, badges
├── services/             # Client for the local backend
│   ├── apiClient.ts      # fetch/SSE transport, upload, polling, chat
│   ├── analysisService.ts# Job submission + result mapping
│   ├── assistantService.ts# Conversational query processor
│   └── documentService.ts# User bill document management
├── lib/                  # Shared formatting helpers
├── types/                # TypeScript interface & type definitions
│   ├── bill.ts           # Bill data model
│   ├── analysis.ts       # Analysis pipeline states
│   ├── forecast.ts       # Forecast models
│   ├── weather.ts        # Weather data structures
│   └── assistant.ts     # Chat message & context models
└── config/               # Design tokens, sample bill constants

backend/
├── app/
│   ├── main.py           # FastAPI app, CORS, router wiring, startup
│   ├── config.py         # Settings (env-overridable), paths, languages
│   ├── db.py             # SQLAlchemy engine/session, SQLite in WAL mode
│   ├── models.py         # documents, jobs, bill_analysis, forecast_results,
│   │                     #   user_profiles, chat_sessions, chat_messages
│   ├── schemas.py        # Canonical* models + frontend projection
│   ├── api/              # health.py, bills.py, assistant.py
│   ├── core/             # logging, error shapes, upload security
│   ├── services/         # ocr, language, extraction, validation, analysis,
│   │                     #   forecast, tariff, weather, storage, agent
│   ├── validators/       # Per-field plausibility + cross-field consistency
│   └── workers/pipeline.py # Background job orchestration
├── samples/              # Synthetic bills for testing (no real documents)
├── scripts/              # generate_sample_bills.py
├── requirements.txt
└── data/                 # Runtime state — gitignored, never leaves the machine
    ├── uploads/<job_id>/ #   original uploads, stored as received
    ├── processed/        #   per-page OCR text
    ├── results/          #   analysis JSON per job
    ├── db/               #   smart_utility.db
    └── logs/             #   job-scoped logs (IDs, stages, timings only)
```

---

## Local Backend

The services above are now thin clients over a FastAPI backend that runs on the
same machine. **The normal upload path performs real processing** — a real file
is stored, real OCR runs, real fields are extracted, and the dashboard renders
whatever came out. Nothing is fabricated end to end.

```
Browser  ──POST /bills/upload──▶  FastAPI
                                   │  store original (data/uploads/<job_id>/)
                                   │  create job row
                                   └─ BackgroundTask ─▶ pipeline
                                          ├─ OCR        PyMuPDF raster → Tesseract
                                          ├─ Language   script + stopword detection
                                          ├─ Extract    regex/keyword field extraction
                                          ├─ Validate   plausibility + cross-field
                                          ├─ Analyse    consumption, forecast, tariff
                                          └─ Persist    data/results/<job_id>.json
Browser  ──SSE /bills/{id}/events, plus a 400 ms status poll──▶  done
```

### Pipeline stages

| Stage | What actually happens |
| --- | --- |
| Store | File written to `data/uploads/<job_id>/` under a generated name; original filename kept in the DB only |
| OCR | PDFs rasterised with PyMuPDF at 300 DPI (max 12 pages); images read directly. Tesseract runs with the detected script's language packs |
| Language | Unicode script ranges plus Devanagari/Tamil/Telugu/etc. stopword hits → `detected_language` |
| Normalise | Indian-language digits, lakh/crore grouping and month names mapped to canonical form before extraction |
| Extract | Label-anchored matching for consumer number, meter readings, units, amounts, dates, tariff category, sanctioned load. Every field carries `{value, source, page, confidence}` |
| Validate | Per-field plausibility (units vs. amount, dates in range) and cross-field consistency. **Suspicious values are flagged, never silently corrected.** Values that could not be read stay `null` — they are never guessed |
| Analyse | Consumption trend, weighted-moving-average forecast, slab-based tariff estimate |
| Weather | Optional. With no provider configured it degrades to `weather_status = "unavailable"` and says so in the UI |
| Persist | Canonical bundle written to `data/results/<job_id>.json` and mirrored into `bill_analysis` / `forecast_results` |

### OCR engine

**Tesseract 5** (`/usr/bin/tesseract`) driven through `pytesseract`, with
**PyMuPDF** for PDF rasterisation. Chosen because it is fully offline, has
mature Indian-language packs, and needs no model download or API key — the
"everything stays local" requirement rules out a cloud vision API.

Installed language packs on the reference machine: `asm, ben, eng, guj, hin,
kan, mal, mar, ori, osd, pan, tam, tel`. The requested set is `eng, hin, mar`;
anything missing is reported in `GET /api/v1/health` under `ocr.missing_languages`
rather than failing the job.

### API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/health` | `{status, ocr, agent, database, weather}` |
| `POST` | `/api/v1/bills/upload` | Multipart upload → `{job_id, document_id, ...}` |
| `GET` | `/api/v1/bills` | Analysed documents for the Documents tab |
| `GET` | `/api/v1/bills/{job_id}` | Job status, stage, progress, timings |
| `GET` | `/api/v1/bills/{job_id}/events` | Server-sent events for the same payload |
| `GET` | `/api/v1/bills/{job_id}/analysis` | Structured analysis result |
| `GET` | `/api/v1/bills/{job_id}/debug/ocr` | Per-page OCR text, for debugging a bad read |
| `GET` | `/api/v1/storage` | Counts and disk usage under `data/` |
| `POST` | `/api/v1/assistant/chat` | Electricity-only assistant |

### Assistant scope controls

The assistant is constrained by **five layers**, not a single system prompt:
input classification → allowed-topic check → structured context retrieval →
response validation → output scope check. Answers are assembled from the stored
analysis, so every number it states is one that was actually extracted. A reply
containing a figure absent from the analysis is discarded. Off-topic questions
get a fixed refusal; questions the bill cannot answer get a fixed
"not enough information" reply.

The optional `agent_service.py` boundary is disabled by default (`agent.enabled
= false`). When enabled it runs a fixed, allowlisted CLI with no tools, in a
scratch sandbox, and is used only for field disambiguation — never as the
numerical source of truth.

### Privacy

Documents, OCR text, the database and result files all live under
`backend/data/`, which is gitignored. Logs record job ID, stage, timings and
errors only — never bill images, consumer numbers, or full OCR text. Numeric
identifiers are redacted from assistant output.

---

## Development Setup

**Prerequisites**: Node 20+, Python 3.11+, and Tesseract 5 with the language
packs you need.

```bash
# Debian/Ubuntu — the language packs are separate packages
sudo apt install tesseract-ocr tesseract-ocr-hin tesseract-ocr-mar \
                 tesseract-ocr-tam tesseract-ocr-tel tesseract-ocr-kan \
                 tesseract-ocr-mal tesseract-ocr-guj tesseract-ocr-ben \
                 tesseract-ocr-pan tesseract-ocr-ori
```

1. **Clone & install both halves**:
   ```bash
   git clone https://github.com/AnuAnsh17/smart_utility.git
   cd smart_utility

   npm install

   python3 -m venv backend/.venv
   backend/.venv/bin/pip install -r backend/requirements.txt
   ```

2. **Start everything** (backend on `:8000`, frontend on `:3000`):
   ```bash
   ./scripts/start-dev.sh
   ```
   Open [http://localhost:3000](http://localhost:3000).

   Or run the two processes separately:
   ```bash
   cd backend && .venv/bin/python -m uvicorn app.main:app --port 8000 --reload
   npm run dev
   ```

3. **Confirm the backend is healthy** before uploading:
   ```bash
   curl -s localhost:8000/api/v1/health | python3 -m json.tool
   ```
   Check `ocr.available`, `ocr.missing_languages` and `database.writable`.

4. **Try it without a real bill**. `backend/samples/` holds synthetic bills —
   including a Marathi one and a deliberately sparse one — generated by
   `backend/scripts/generate_sample_bills.py`. Upload one through the landing
   page; the dashboard should show exactly the figures printed on it.

5. **Typecheck & lint**:
   ```bash
   npm run typecheck
   npm run lint
   ```

---

## Environment Variables

**Frontend** — copy `.env.example` to `.env.local` only if the backend is not on
the default loopback address:
```env
NEXT_PUBLIC_API_BASE="http://127.0.0.1:8000/api/v1"
```

**Backend** — copy `backend/.env.example` to `backend/.env`. Every value has a
working default; the file exists so you can change them. Notable ones:

```env
HOST=127.0.0.1                     # loopback only, by design
PORT=8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
DATA_DIR=./data                    # where uploads, OCR text and results go
MAX_UPLOAD_BYTES=10485760          # 10 MB

OCR_ENGINE=tesseract
OCR_LANGUAGES=eng,hin,mar          # requested Tesseract packs
OCR_DPI=300                        # PDF rasterisation resolution
OCR_MAX_PAGES=12
OCR_TIMEOUT_SECONDS=180
OCR_KEEP_PAGE_IMAGES=false

ENABLE_TRANSLATION=false           # normalisation happens without a translation model
AGENT_ENABLED=false                # optional disambiguation CLI, off by default
WEATHER_ENABLED=false              # stays "unavailable" until enabled
WEATHER_API_BASE=https://api.open-meteo.com/v1

LOG_LEVEL=INFO
LOG_REDACT=true                    # keep consumer numbers and OCR text out of logs
```

Leave `WEATHER_ENABLED=false` and `AGENT_ENABLED=false` for a fully offline
run — both are optional enrichment, and the pipeline completes without them.

---

## Roadmap

- [x] Phase 1: Repository initialization & Design system tokens
- [x] Phase 2: Minimal landing page & Drag-and-drop bill uploader
- [x] Phase 3: Multi-stage animated AI processing pipeline
- [x] Phase 4: Analysis completion transition & quick summary cards
- [x] Phase 5: Production Analytics Dashboard shell & metric cards
- [x] Phase 6: Monthly consumption charts & Appliance breakdown donut chart
- [x] Phase 7: Predictive forecast visualization & Weather impact module
- [x] Phase 8: Conversational energy assistant experience
- [x] Phase 9: Document history table & detailed bill view modal
- [x] Phase 10: Real backend OCR & analysis pipeline integration

---

## Current Status

**End-to-end locally**: uploading a bill runs real OCR and real extraction on
this machine, and the dashboard renders the extracted values. The frontend is
unchanged in design — only its service layer was swapped from mocks to the
local backend.

### Known limitations

- **Field extraction is label-anchored, not a trained model.** It handles the
  bill layouts it has seen (Tata Power, MSEDCL-style, Adani, Mescom) well and
  degrades to `null` + a flag on unfamiliar ones. A different DISCOM's layout
  may need another pattern. Unreadable fields are reported, not guessed.
- **Forecasting needs history.** With fewer than three prior bills the forecast
  reports "Not enough historical data to generate a reliable forecast" instead
  of extrapolating from one point.
- **The tariff engine is a slab approximation**, generic across states. It is
  not a substitute for your DISCOM's actual order.
- **Weather is unconfigured by default**, so the weather card reports
  `unavailable` rather than showing invented conditions.
- **Scanned handwritten bills** and heavily skewed photos OCR poorly;
  Tesseract wants clean print. Re-scanning at a higher DPI is the fix.
- **Single-process only** — SQLite, local filesystem, in-process background
  tasks. That is deliberate; it keeps the deployment to one machine.

### Handling your own bills

Uploaded documents are stored under `backend/data/uploads/<job_id>/` with
generated filenames, and the SQLite database is at
`backend/data/db/smart_utility.db`. Both are gitignored. Delete the contents of
`backend/data/uploads/` when you no longer need the originals.
