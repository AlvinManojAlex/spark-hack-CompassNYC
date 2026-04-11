# Compass NYC

**A fully local, privacy-first AI that helps New Yorkers navigate social services.**

Built for the NYC Open Data Hackathon 2025 — Human Impact Track

---

## 🎯 What It Does

Compass NYC uses **local AI** to help anyone understand their eligibility for NYC social services and find where to apply. No cloud, no data exfiltration, just helpful guidance running entirely on the Acer Veriton GN100.

### Key Features

- **Conversational eligibility reasoning** — Not just search. The LLM understands context and explains WHY you qualify or don't.
- **Location-aware** — Automatically filters service centers by borough.
- **Privacy-first** — Everything runs locally. No API calls to OpenAI/Claude. Your data never leaves the machine.
- **Extensible** — Adding a new benefit takes ~5 minutes (see below).

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  USER QUERY                                                  │
│  "I make $2,200/month with 2 kids in Brooklyn. Do I         │
│   qualify for SNAP?"                                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
       ┌───────────────┴───────────────┐
       │                               │
       ▼                               ▼
┌─────────────────┐          ┌──────────────────┐
│ ELIGIBILITY     │          │ LOCATION         │
│ ENGINE          │          │ MANAGER          │
│                 │          │                  │
│ • RAG over      │          │ • Detect borough │
│   eligibility   │          │ • Filter by area │
│   rules         │          │ • Structured SQL │
│ • Vector search │          │                  │
│   (semantic)    │          │                  │
└────────┬────────┘          └────────┬─────────┘
         │                            │
         └──────────┬─────────────────┘
                    │
                    ▼
         ┌────────────────────┐
         │ LLM INTERFACE      │
         │                    │
         │ • Build prompt     │
         │ • Call Ollama      │
         │ • Return answer    │
         └──────────┬─────────┘
                    │
                    ▼
         ┌────────────────────┐
         │ RESPONSE           │
         │                    │
         │ • Eligibility      │
         │ • Action steps     │
         │ • Locations        │
         │ • Map data (JSON)  │
         └────────────────────┘
```

### Why This Architecture?

**Hybrid Approach:**
- **Eligibility** → Vector embeddings (RAG) because rules are complex and semantic
- **Locations** → Structured filtering (SQL) because it's deterministic and fast

**Database-First:**
- Embeddings computed **once** at setup, not every query
- Sub-second retrieval from SQLite
- Easy to add new benefits without recomputing everything

**Modular:**
- Each component (eligibility, locations, LLM) is independent
- Swap Ollama for a different backend? Just change `llm_interface.py`
- Want Postgres instead of SQLite? Just change `database.py`

---

## 📁 File Structure

```
compass-nyc/
├── config.py               # Central configuration - add benefits here
├── database.py             # Database manager (vector + location storage)
├── eligibility_engine.py   # RAG retrieval for eligibility rules
├── location_manager.py     # Structured filtering for service locations
├── llm_interface.py        # Ollama API wrapper with prompt engineering
├── main.py                 # Main orchestrator - run queries here
├── setup.py                # One-time setup script
├── requirements.txt        # Python dependencies
│
├── data/
│   ├── embeddings.db       # Vector DB (auto-generated)
│   ├── locations.db        # Location DB (auto-generated)
│   │
│   ├── eligibility/        # Eligibility text files (you create these)
│   │   ├── snap_eligibility.txt
│   │   ├── hra_cash_eligibility.txt
│   │   └── ...
│   │
│   └── locations/          # Location CSV files (from NYC Open Data)
│       ├── snap_locations.csv
│       ├── hra_centers.csv
│       └── ...
│
└── README.md               # This file
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install and Start Ollama

```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama
ollama serve

# Pull a model (in another terminal)
ollama pull nemotron-mini

# For better reasoning (recommended for demo):
# ollama pull llama3.1:70b
# Then update config.py: OLLAMA_MODEL = "llama3.1:70b"
```

### 3. Prepare Data Files

You need two types of files for each benefit:

**Eligibility file** (`.txt`):
- Scraped/copied from official websites
- Plain text, any length
- Example: `data/eligibility/snap_eligibility.txt`

**Locations file** (`.csv`):
- From NYC Open Data
- Must have columns: `name, address, borough, zip, phone, hours, walk_in, languages`
- Optional: `latitude, longitude` (for map display)
- Example: `data/locations/snap_locations.csv`

See `data/README.md` for detailed format specs.

### 4. Run Setup

```bash
python setup.py
```

This will:
- Check dependencies
- Verify Ollama is running
- Check data files exist
- Build vector embeddings (takes 1-2 minutes for SNAP)
- Load location data
- Run a test query

### 5. Run Queries

```python
from main import run_query

query = "I make $2,200/month with 2 kids in Brooklyn. Do I qualify for SNAP?"
result = run_query(query, benefit_type="snap")

# Result contains:
# - answer: LLM response text
# - locations: List of service centers (for map)
# - eligibility_chunks: Retrieved rules (for debugging)
```

Or just run the demo:

```bash
python main.py
```

---

## 🔧 Adding a New Benefit

It's **dead simple**:

### Step 1: Add data files

```
data/eligibility/medicaid_eligibility.txt    # Scraped from NYC.gov
data/locations/medicaid_offices.csv          # From NYC Open Data
```

### Step 2: Register in `config.py`

```python
BENEFITS = {
    "snap": { ... },  # existing
    
    "medicaid": {
        "name": "Medicaid",
        "eligibility_file": "data/eligibility/medicaid_eligibility.txt",
        "locations_file": "data/locations/medicaid_offices.csv",
        "category": "health",
        "color": "#E91E63",
        "description": "Free or low-cost health coverage"
    },
}
```

### Step 3: Rebuild database

```bash
python -c "from database import initialize_database; initialize_database(force_rebuild=False)"
```

### Step 4: Query it

```python
from main import run_query
run_query("Do I qualify for Medicaid?", benefit_type="medicaid")
```

**That's it.** No code changes needed.

---

## 🧠 Model Recommendations

### Current: `nemotron-mini`
- ✓ Fast (good for initial development)
- ✗ Limited reasoning on complex rules

### Recommended for Demo: `llama3.1:70b` or `nemotron-51b-instruct`
- ✓ Much better reasoning
- ✓ Understands edge cases
- ✓ Still runs locally on Acer Veriton GN100
- ✓ **Better "Spark Story"** for judges

To switch:

```python
# In config.py
OLLAMA_MODEL = "llama3.1:70b"
```

```bash
ollama pull llama3.1:70b
```

---

## 📊 The "Spark Story" (For Hackathon Judges)

**Why does this need the Acer Veriton GN100?**

1. **Local Inference** — We run a 70B parameter LLM locally using NVIDIA NIMs. No cloud dependency means:
   - Zero PII exfiltration risk
   - Works offline (critical for community centers in low-connectivity areas)
   - Sub-second latency (no API round-trip)

2. **Vector Search** — Semantic similarity computed on GPU-accelerated embeddings
   - 384-dimensional vectors for every eligibility rule chunk
   - Thousands of comparisons per query, instant results

3. **Privacy-First Design** — A Medicaid caseworker can use this in a community center without worrying about HIPAA violations

4. **Future: RAPIDS Integration** (if time permits)
   - Process 311 demand data with cuDF
   - Cross-reference service requests with supply
   - Show: "This SNAP center has 3x normal demand on Fridays"

---

## 🗺️ Map Display (Frontend Integration)

The `locations` field in query results is JSON-ready:

```json
[
  {
    "name": "SNAP Center - Downtown Brooklyn",
    "address": "350 Jay Street",
    "borough": "Brooklyn",
    "latitude": 40.6928,
    "longitude": -73.9874,
    "phone": "718-555-1234",
    "hours": "Mon-Fri 9am-5pm",
    "category": "food",
    "color": "#4CAF50"
  },
  ...
]
```

Feed this to Leaflet.js, Google Maps, or Mapbox:

```javascript
// Example: Leaflet
locations.forEach(loc => {
  L.marker([loc.latitude, loc.longitude], {
    icon: L.divIcon({ className: 'custom-pin', html: `<div style="background:${loc.color}"></div>` })
  })
  .bindPopup(`<b>${loc.name}</b><br>${loc.address}`)
  .addTo(map);
});
```

---

## 🎨 Extensibility Ideas

### Adding More Benefits (Immediate)
- ✅ HRA Cash Assistance
- ✅ DHS Emergency Shelter
- ✅ Medicaid
- ✅ Fair Fares (half-price MetroCard)
- ✅ DYCD After-School Programs
- ✅ Food Pantries

### Advanced Features (If Time Permits)
1. **Multi-benefit queries**
   - Already supported! See `run_multi_query()` in `main.py`
   - User: "I need help with food and housing in Brooklyn"
   - System: Checks SNAP + DHS simultaneously

2. **Demand analysis with RAPIDS**
   - Process 311 Service Requests
   - Show which centers are overwhelmed
   - Suggest less-busy alternatives

3. **Document OCR with NVIDIA NIM Vision**
   - Upload a pay stub → auto-extract income
   - Upload ID → auto-extract household size
   - Pre-fill eligibility check

4. **Routing with cuOpt**
   - "Get SNAP + Medicaid enrolled in one trip"
   - Optimize for walking/transit time

---

## 🧪 Testing & Debugging

### Test individual components:

```bash
# Test eligibility retrieval
python eligibility_engine.py

# Test location filtering
python location_manager.py

# Test LLM prompt building (won't call model)
python llm_interface.py

# Test database operations
python database.py
```

### Enable verbose logging:

```python
# In main.py, add:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect the database:

```bash
sqlite3 data/embeddings.db "SELECT benefit_type, COUNT(*) FROM embeddings GROUP BY benefit_type"
sqlite3 data/locations.db "SELECT benefit_type, COUNT(*) FROM locations GROUP BY benefit_type"
```

---

## 📝 License & Acknowledgments

Built for NYC Open Data Hackathon 2025.

Data sources:
- NYC Open Data Portal
- NYC Human Resources Administration (HRA)
- NYC Department of Homeless Services (DHS)
- NYC.gov

Tech stack:
- **Ollama** for local LLM inference
- **sentence-transformers** for embeddings
- **SQLite** for persistence (easily upgradable to Postgres + pgvector)
- **NVIDIA NIMs** (via Ollama) for privacy-first inference

---

## 🐛 Common Issues

**"Ollama not running"**
```bash
ollama serve  # In one terminal
ollama pull nemotron-mini  # In another
```

**"Model not found"**
```bash
ollama list  # See what you have
ollama pull <model-name>
```

**"No embeddings found"**
```bash
python setup.py  # Re-run setup
# Or force rebuild:
python -c "from database import initialize_database; initialize_database(force_rebuild=True)"
```

**"Missing data files"**
- Check `data/eligibility/` and `data/locations/` exist
- Verify file paths in `config.py` match actual files

---

## 🚀 Next Steps

1. **Get SNAP working** ← You are here
2. **Add 2-3 more benefits** (HRA, DHS, Medicaid)
3. **Build the map UI** (React + Leaflet)
4. **Add RAPIDS demand analysis** (if time)
5. **Polish the pitch** (practice "Spark Story")

Good luck! 🎉


## What each file does

config.py

- Central settings (model names, DB paths, chunk sizes)
- BENEFITS dict - where you register each benefit (SNAP, Medicaid, etc.)
- Add new benefits here in 8 lines


database.py

- Stores & loads embeddings (vector DB)
- Stores & loads locations (structured DB)
- SQLite operations
- Knows CSV columns - see below ⬇️


eligibility_engine.py

- RAG retrieval: takes user query → finds relevant eligibility chunks
- Vector similarity search
- Returns top K chunks


location_manager.py

- Filters locations by borough
- Formats location data for prompts & maps
- Detects borough names in queries


llm_interface.py

- Calls Ollama API
- Builds prompts with eligibility + location context
- Returns LLM responses


main.py

- Main orchestrator - ties everything together
- Run queries here: run_query("Do I qualify?", "snap")
- Coordinates: retrieval → filtering → LLM → response


setup.py

- One-time initialization
- Checks dependencies, Ollama, data files
- Builds embeddings database
- Loads location CSVs into DB


requirements.txt

- Python dependencies list