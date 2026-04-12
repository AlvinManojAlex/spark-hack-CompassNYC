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

- Hardware: NVIDIA GB100 (128GB unified memory, ARM Grace CPU, integrated GPU)
- Backend: FastAPI, Python 3.10+
- AI: Ollama (local LLM), sentence-transformers (embeddings), RAG
- Data: SQLite (embeddings + locations), NYC Open Data
- Frontend: React

## Quick Start

Prerequisites

- NVIDIA GB100 or compatible system
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
pip install -r requirements.txt
```

Install Ollama model

```
ollama pull qwen2.5:32b
```

Initialize database (embeds eligibility rules, loads locations)

```
python setup.py
```

Running
Backend:

```
uvicorn api:app --host 0.0.0.0 --port 8000
```

Terminal Interface (for testing):

```
python terminal_chat.py
```
