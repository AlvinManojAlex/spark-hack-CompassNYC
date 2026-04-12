# Compass NYC

**A fully local, privacy-first AI that helps New Yorkers navigate social services.**

Compass NYC is a locally-deployed AI system running on the Acer GN100 that determines eligibility for NYC social services without cloud exposure. The system analyzes user situations against eligibility criteria for SNAP, Medicaid, and HRA Cash Assistance, providing precise benefit amounts, office locations, required documentation, and actionable next steps.

Built using a hybrid RAG architecture combining semantic search of embedded policy documents with structured queries of NYC Open Data, the system runs Qwen 2.5 7B entirely locally with zero external dependencies. This enables vulnerable populations, including undocumented immigrants and domestic violence survivors, to safely access benefit information without data transmission to external servers.

## Architecture:

Hybrid RAG System:

- Semantic search via vector embeddings
- Structured queries against NYC Open Data (benefit office locations)
- Local LLM synthesis (Qwen 2.5 7B via Ollama)

Stack:

- Hardware: Acer GN100 (128GB unified memory, ARM Grace CPU, integrated GPU)
- Backend: FastAPI, Python 3.10+
- AI: Ollama (local LLM), sentence-transformers (embeddings), RAG
- Data: SQLite (embeddings + locations), NYC Open Data
- Frontend: React + Leaflet 

## Quick Start

Prerequisites

- Acer GN100 or compatible system
- Python 3.10+
- Ollama installed
- Node.js 16+ (for frontend)

Installation

```
git clone git@github.com:MeenakshiMadhu/spark-hack-CompassNYC.git

cd spark-hack-CompassNYC
```

Install Python dependencies

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install Ollama model

```
ollama pull qwen2.5:7b
```

Initialize database (embeds eligibility rules, loads locations)

```
python setup.py
```

## Running the App

**Terminal 1 - Ollama (LLM server):**
```bash
ollama serve
```

**Terminal 2 - FastAPI backend:**
```bash
source .venv/bin/activate
uvicorn api:app --host 0.0.0.0 --port 8000
```

**Terminal 3 - Frontend file server:**
```bash
cd frontend
python3 -m http.server 3000
```

## Accessing the Frontend

### Step 1 - Find the GN100's IP

### Step 2 - Configure the frontend
 
Open `frontend/index.html` and update line 31 with the GN100's IP:
 
```js
const API_BASE = "http://YOUR_GN100_IP:8000";
```

### Step 3 - Open in browser
 
On your laptop, navigate to:
 
```
http://YOUR_GN100_IP:3000/frontend/index.html
```
 
The chat interface and map should load. All AI inference happens on the GN100 - nothing leaves the machine.

## Current Limitations

1. Manual integration of benefit programs into the system
2. Sparse available data from NYC Open data (Missing values for fields like walk-in hours etc)
3. Current bottleneck - only a single instance of the application is running. If it crashes, then the current conversation would be lost since it is stored in RAM.

## Next Steps...

1. Speech-to-text and Text-to-speech options for better accessibility
2. Multi-language support
3. Additional benefit programs can be integrated 
