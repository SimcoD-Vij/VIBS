# VIBS Project Audit Report
*Debate Analyzer — Full Code Review vs Master Build Prompt*

---

## Summary Verdict

The project is **~85% complete and correctly structured**. The full pipeline from audio capture → diarization → NLP → knowledge graph → UI renders successfully. There are **4 real bugs** that need immediate fixes, plus **3 missing/incomplete features** from the master prompt. Everything else matches spec.

---

## Part 1 — Architecture Overview (What Was Built)

```
debate-analyzer/
├── backend/                     FastAPI + Celery workers
│   ├── app/
│   │   ├── main.py              ✅ Correct — 4 routers registered
│   │   ├── config.py            ✅ All settings present incl. OLLAMA_MODEL (added vs master)
│   │   ├── database.py          ✅ Async SQLAlchemy engine + sync engine for Celery
│   │   ├── models/db_models.py  ✅ All 5 tables: Session, Segment, Speaker, GraphData, TopicShift
│   │   ├── routers/
│   │   │   ├── ws_router.py     ✅ WebSocket audio streaming — ⚠️ VAD MOCKED (see bugs)
│   │   │   ├── upload_router.py ✅ File upload — NOT in master prompt, added as bonus feature
│   │   │   ├── session_router.py ✅ Status/result/rename APIs
│   │   │   └── export_router.py ⚠️ PDF export — missing `markdown` pip dependency
│   │   ├── services/
│   │   │   ├── audio_service.py ✅ Duration via ffprobe, overlap detection, color assignment
│   │   │   ├── nlp_service.py   ✅ LLM factory (openai/anthropic/ollama), summarize, extract_topics
│   │   │   ├── graph_service.py ✅ LLM graph call, networkx build, eval, explain, save
│   │   │   └── vad_service.py   ✅ SilenceTracker class + score_chunk — but not wired in WS handler
│   │   └── workers/tasks.py     ✅ Full 3-task pipeline: process_audio → analyze_session → build_graph
│   ├── prompts/graph_prompt_v1.txt ✅ Well-structured, correct format placeholders
│   ├── templates/pdf_report.html   ✅ Exists
│   └── requirements.txt            ⚠️ Missing: `markdown`, `langchain-anthropic`
├── frontend/
│   ├── src/
│   │   ├── App.jsx              ✅ Two routes: / and /session/:id
│   │   ├── pages/
│   │   │   ├── RecordPage.jsx   ✅ Mic button + waveform + FileUploader bonus feature
│   │   │   └── SessionPage.jsx  ✅ 4 tabs + polling + progress bar + rename + PDF download
│   │   ├── components/
│   │   │   ├── FileUploader.jsx ✅ Drag-and-drop style file upload (bonus, not in master prompt)
│   │   │   ├── MindMap.jsx      ✅ react-force-graph-2d with correct node/edge mapping
│   │   │   ├── SpeakerCard.jsx  ✅ exists
│   │   │   ├── TopicTimeline.jsx ✅ exists
│   │   │   ├── TranscriptView.jsx ✅ exists
│   │   │   └── Waveform.jsx     ✅ exists
│   │   ├── hooks/useAudioCapture.js ✅ Full lifecycle, WS streaming, silence handler
│   │   └── utils/api.js         ✅ All 4 API calls correct
│   └── package.json             ✅ All deps present + react-markdown (bonus for graph explanation)
└── docker-compose.yml           ✅ 4 services correct, --pool=solo for Celery (good choice)
```

---

## Part 2 — What's Working End-to-End

| Feature | Status | Notes |
|---------|--------|-------|
| File upload workflow | ✅ Complete | POST /api/upload → session created → process_audio queued |
| WebSocket microphone recording | ✅ Complete | Binary chunks → .webm → ffmpeg → .wav |
| WhisperX transcription | ✅ Complete | With URL monkey-patch fix for 301 redirect bug |
| Speaker diarization | ✅ Complete | Falls back to SPEAKER_00 if pyannote fails |
| Overlap detection | ✅ Complete | Marks segments with is_overlap=True |
| Per-speaker summarization | ✅ Complete | LangChain with retry logic |
| spaCy topic extraction | ✅ Complete | Entities + noun chunks, fallback auto-download |
| Knowledge graph generation | ✅ Complete | LLM → JSON → NetworkX + eval + explain |
| Force graph UI | ✅ Complete | react-force-graph-2d, weighted nodes, typed edges |
| Graph explanation in UI | ✅ Complete | ReactMarkdown renders explanation + conclusion |
| 4-tab results page | ✅ Complete | Speakers, Mind Map, Timeline, Transcript |
| Speaker renaming | ✅ Complete | PATCH endpoint + live state update |
| Progress bar polling | ✅ Complete | 3s interval, stops at complete/failed |
| PDF export | ⚠️ Almost | Weasyprint is wired up but `markdown` package missing |
| VAD auto-stop | ❌ Broken | Score hardcoded to 1.0 — will never trigger |
| Prompt improvement loop | ❌ Stub | `run_improvement_check()` is `pass` |

---

## Part 3 — Bugs That Need Fixing Now

### BUG 1 — VAD Score Hardcoded (Auto-stop Never Fires)
**File:** `backend/app/routers/ws_router.py`, line ~60

**Problem:** The VAD score is always set to `1.0` (mock speech), so silence is never detected and the auto-stop feature is completely broken.

```python
# CURRENT — broken:
score = 1.0 # Mock speech

# FIX — replace with actual VAD scoring:
```

**Fix to apply in `ws_router.py`:**

Add these imports at the top:
```python
import io
import tempfile
import subprocess
import numpy as np
```

Replace the mock score block with:
```python
# Decode the webm chunk to raw PCM for VAD scoring
# We write to a temp file and use ffmpeg to extract raw audio
try:
    with tempfile.NamedTemporaryFile(suffix='.webm', delete=True) as tmp_in:
        tmp_in.write(data['bytes'])
        tmp_in.flush()
        # Convert to raw f32le mono 16kHz for silero
        cmd = [
            'ffmpeg', '-y', '-i', tmp_in.name,
            '-ar', '16000', '-ac', '1', '-f', 'f32le', '-'
        ]
        proc = subprocess.run(cmd, capture_output=True)
        if proc.returncode == 0 and len(proc.stdout) >= 512 * 4:
            score = score_chunk(proc.stdout)
        else:
            score = 1.0  # Can't decode, assume speech
except Exception:
    score = 1.0

chunk_duration = len(data['bytes']) / (16000 * 2)  # rough estimate
tracker.update(score, chunk_duration)
```

---

### BUG 2 — Missing `markdown` Package in requirements.txt
**File:** `backend/requirements.txt`

**Problem:** `export_router.py` does `import markdown` but `markdown` is not in `requirements.txt`. The PDF export endpoint will crash with `ImportError` the first time it's called.

**Fix:** Add these two lines to `backend/requirements.txt`:
```
markdown==3.6
langchain-anthropic==0.1.23
```

`langchain-anthropic` is also used in `nlp_service.py` (`from langchain_anthropic import ChatAnthropic`) but absent from requirements.

---

### BUG 3 — FastAPI 202 Response Returns Tuple (Not Standard)
**File:** `backend/app/routers/session_router.py`, line ~45

**Problem:**
```python
return {"status": "processing"}, 202
```
FastAPI does not support tuple returns for HTTP status codes. This will either return a 200 with a list `[{...}, 202]` or raise an error depending on the FastAPI version.

**Fix:**
```python
from fastapi.responses import JSONResponse

# Replace the tuple return with:
return JSONResponse(content={"status": "processing"}, status_code=202)
```

---

### BUG 4 — MindMap Fixed Width 800px (Not Responsive)
**File:** `frontend/src/components/MindMap.jsx`

**Problem:** `width={800}` hardcoded means it overflows on mobile/tablet and doesn't use the full space on large screens.

**Fix:** Make it responsive using a ref:
```jsx
import { useRef, useCallback, useEffect, useState } from 'react';

// Inside the component, add:
const containerRef = useRef();
const [dimensions, setDimensions] = useState({ width: 800, height: 500 });

useEffect(() => {
  if (!containerRef.current) return;
  const ro = new ResizeObserver(entries => {
    const { width } = entries[0].contentRect;
    setDimensions({ width, height: Math.min(600, Math.max(400, width * 0.6)) });
  });
  ro.observe(containerRef.current);
  return () => ro.disconnect();
}, []);

// Wrap the ForceGraph2D in:
<div ref={containerRef} className="...">
  <ForceGraph2D
    width={dimensions.width}
    height={dimensions.height}
    ...
  />
</div>
```

---

## Part 4 — Features from Master Prompt Not Yet Implemented

### MISSING 1 — Topic Shift Timestamps Are All Zero
**File:** `backend/app/services/graph_service.py`, `detect_topic_shifts()`

The function sets `time_seconds: 0.0` for every shift. The TopicTimeline UI will show all shifts stacked at position 0. The master prompt specified using segment timestamps to find the actual time a topic shift occurred.

**Prompt to fix it:**

```
In backend/app/services/graph_service.py, the detect_topic_shifts function
currently sets time_seconds=0.0 for all shifts.

Fix this by updating the function signature to also accept the segments list:
  def detect_topic_shifts(graph_json: dict, segments: list) -> list

For each "shifts_to" edge in the graph:
  - The edge.source is a topic node ID
  - Find the first segment whose text contains keywords from that topic label
  - Use that segment's start_time as time_seconds
  - If no match found, estimate by position in the node list

Also update build_graph task in tasks.py to pass segments to detect_topic_shifts:
  segments = db.query(Segment).filter(Segment.session_id == session_id).all()
  segments_data = [{"text": s.text, "start": s.start_time, "speaker_label": s.speaker_label} 
                   for s in segments]
  shifts = detect_topic_shifts(graph_json, segments_data)
```

---

### MISSING 2 — Prompt Improvement / Self-Learning Loop
**File:** `backend/app/services/graph_service.py`, `run_improvement_check()`

The function is `pass` — no implementation. The master prompt described a loop that: every 50 sessions, fetches the top and bottom eval_score graphs, asks an LLM to rewrite the prompt, and saves it as `graph_prompt_v2.txt`.

**Prompt to implement it:**

```
In backend/app/services/graph_service.py, implement run_improvement_check(db).

Steps:
1. Count total sessions in DB with status="complete"
2. If count % 50 != 0, return immediately (only run every 50 sessions)
3. Query GraphData ordered by eval_score DESC, limit 5 — these are top performers
4. Query GraphData ordered by eval_score ASC, limit 5 — these are worst performers
5. Load the current prompt from prompts/graph_prompt_{settings.PROMPT_VERSION}.txt
6. Build this improvement prompt and call the LLM:

   "You are improving a prompt that generates knowledge graphs from debate transcripts.
    Current prompt:
    {current_prompt}
    
    Best-scoring graph examples (eval >= 4.0):
    {top_examples_nodes_edges}
    
    Worst-scoring graph examples (eval <= 2.0):
    {worst_examples_nodes_edges}
    
    Rewrite the prompt to produce graphs more like the top examples.
    Keep the JSON schema identical. Return only the new prompt text."

7. Parse the new version number: if current is "v1", new is "v2"
8. Save to prompts/graph_prompt_v2.txt
9. Update settings.PROMPT_VERSION = "v2" (or write to .env)
10. Log: "Prompt upgraded to v2"

Call run_improvement_check(db) at the end of save_graph_to_db().
```

---

### MISSING 3 — Session Page Missing "Back to Record" Navigation
**File:** `frontend/src/pages/SessionPage.jsx`

There is no way to start a new session from the results page. The user must manually navigate back or reload. This is a UX gap.

**Fix:** Add a button to the header:
```jsx
import { useNavigate } from 'react-router-dom';
const navigate = useNavigate();

// In the header:
<button onClick={() => navigate('/')} className="text-slate-400 hover:text-slate-200 text-sm flex items-center gap-1">
  ← New Session
</button>
```

---

## Part 5 — What to Do Next (Priority Order)

1. **Fix BUG 2 first** (add `markdown` and `langchain-anthropic` to requirements.txt) — otherwise PDF export and Anthropic LLM both crash on startup/first use. Rebuild the Docker image after this.

2. **Fix BUG 3** (202 response tuple) — quick 2-line fix, prevents backend from returning malformed responses.

3. **Fix BUG 1** (VAD hardcoded score) — required for the auto-stop feature to work at all.

4. **Fix BUG 4** (MindMap width) — important for mobile users.

5. **Implement MISSING 1** (topic shift timestamps) — makes the TopicTimeline tab actually meaningful.

6. **Add MISSING 3** (back button) — small UX fix, 3 lines of code.

7. **Implement MISSING 2** (prompt improvement loop) — this is the "system gets better over time" feature. Lower priority but important for the long-term goal.

---

## Part 6 — Features Added Beyond the Master Prompt (Verify These Are Working)

The builder added these features that weren't in the original prompt — they look correctly implemented but should be verified:

| Addition | File | Status |
|----------|------|--------|
| File upload endpoint | `upload_router.py` + `FileUploader.jsx` | ✅ Looks correct |
| Ollama model name config (`OLLAMA_MODEL`) | `config.py`, `nlp_service.py` | ✅ Correct |
| Graph explanation + conclusion fields | `GraphData` model + `explain_graph()` | ✅ Correct |
| ReactMarkdown rendering of explanation | `SessionPage.jsx` | ✅ Correct |
| Custom diarization model fallback | `tasks.py` uses `fatymatariq/speaker-diarization-3.1` instead of gated pyannote | ✅ Smart workaround for HF auth issues |
| WhisperX 301 redirect monkey-patch | `tasks.py` | ✅ Production-quality hotfix |
| Worker `--pool=solo` | `docker-compose.yml` | ✅ Correct for torch/whisperx |

---

## Part 7 — Security Note

The `.env` file contains a real HuggingFace token:
```
HF_TOKEN=<REDACTED>
```
This is committed to git. **Rotate this token immediately** at https://huggingface.co/settings/tokens and add `.env` to `.gitignore` (it should already be there — check that it's actually being ignored with `git check-ignore backend/.env`).

---

*End of audit. Total: 4 bugs, 3 missing features, 7 bonus additions, 1 security note.*
