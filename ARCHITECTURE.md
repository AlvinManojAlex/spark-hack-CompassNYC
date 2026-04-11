# Compass NYC — System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE                                  │
│  ┌──────────────────────────┐    ┌──────────────────────────────────┐  │
│  │   CHAT PANEL             │    │   MAP PANEL                       │  │
│  │                          │    │                                   │  │
│  │  > I make $2,200/month   │    │   ┌─────────────────────────┐   │  │
│  │    with 2 kids in        │    │   │      📍 Brooklyn         │   │  │
│  │    Brooklyn. Do I        │    │   │  • SNAP Center           │   │  │
│  │    qualify for SNAP?     │    │   │  • HRA Office            │   │  │
│  │                          │    │   │  • Food Pantry           │   │  │
│  │  [AI Response Here]      │    │   └─────────────────────────┘   │  │
│  └──────────────────────────┘    └──────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────────────────┘
                       │
                       ▼ HTTP API
┌─────────────────────────────────────────────────────────────────────────┐
│                        MAIN APPLICATION                                  │
│                         (main.py)                                        │
│                                                                          │
│  Orchestrates:                                                           │
│    1. Query understanding                                               │
│    2. Eligibility retrieval (RAG)                                       │
│    3. Location filtering (Structured)                                   │
│    4. LLM reasoning                                                     │
│    5. Response formatting                                               │
└──────────┬─────────────────────┬─────────────────────┬─────────────────┘
           │                     │                     │
           ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  ELIGIBILITY     │  │  LOCATION        │  │  LLM             │
│  ENGINE          │  │  MANAGER         │  │  INTERFACE       │
│                  │  │                  │  │                  │
│  • RAG retrieval │  │  • Borough       │  │  • Prompt        │
│  • Vector search │  │    detection     │  │    engineering   │
│  • Top-K chunks  │  │  • SQL filtering │  │  • Ollama calls  │
│  • Semantic      │  │  • Deterministic │  │  • NeMo/NIMs     │
│    similarity    │  │    logic         │  │  • Local LLM     │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                     │
         ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      DATABASE LAYER                                      │
│                     (database.py)                                        │
│                                                                          │
│  ┌─────────────────────────┐      ┌─────────────────────────────────┐  │
│  │  VECTOR DB              │      │  LOCATION DB                     │  │
│  │  (embeddings.db)        │      │  (locations.db)                  │  │
│  │                         │      │                                  │  │
│  │  • Benefit type         │      │  • Benefit type                  │  │
│  │  • Chunk text           │      │  • Name, address, borough        │  │
│  │  • Embedding vector     │      │  • Phone, hours, languages       │  │
│  │    (384-dim float32)    │      │  • Latitude, longitude           │  │
│  │                         │      │  • Walk-in status                │  │
│  │  SQLite + numpy         │      │  SQLite + JSON metadata          │  │
│  └─────────────────────────┘      └─────────────────────────────────┘  │
└───────────────┬───────────────────────────────────┬─────────────────────┘
                │                                   │
                ▼                                   ▼
┌────────────────────────────────┐   ┌────────────────────────────────────┐
│  DATA SOURCES                   │   │  DATA SOURCES                      │
│                                 │   │                                    │
│  • snap_eligibility.txt         │   │  • snap_locations.csv              │
│  • hra_cash_eligibility.txt     │   │  • hra_centers.csv                 │
│  • medicaid_eligibility.txt     │   │  • medicaid_offices.csv            │
│  • ...                          │   │  • ...                             │
│                                 │   │                                    │
│  Scraped from NYC.gov           │   │  Downloaded from NYC Open Data     │
└────────────────────────────────┘   └────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════

DATA FLOW (EXAMPLE QUERY)

┌─ USER QUERY ─────────────────────────────────────────────────────────────┐
│ "I make $2,200/month with 2 kids in Brooklyn. Do I qualify for SNAP?"   │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─ ELIGIBILITY ENGINE ─────────────────────────────────────────────────────┐
│ 1. Embed query → 384-dim vector                                         │
│ 2. Search embeddings.db for benefit_type='snap'                         │
│ 3. Compute cosine similarity with all SNAP eligibility chunks           │
│ 4. Return top 3 chunks:                                                  │
│    • "For household of 3: gross limit $2,694..."                        │
│    • "Net income is gross minus deductions..."                          │
│    • "You need: proof of income, proof of address..."                   │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─ LOCATION MANAGER ───────────────────────────────────────────────────────┐
│ 1. Detect borough → "brooklyn"                                          │
│ 2. Query locations.db:                                                  │
│    SELECT * FROM locations                                              │
│    WHERE benefit_type='snap' AND borough='brooklyn'                     │
│ 3. Return 5 locations:                                                  │
│    • SNAP Center - Downtown Brooklyn (350 Jay St)                      │
│    • HRA Center - East New York (2885 Linden Blvd)                     │
│    • ...                                                                │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─ LLM INTERFACE ──────────────────────────────────────────────────────────┐
│ 1. Build prompt:                                                         │
│    ┌─────────────────────────────────────────────────────────────────┐  │
│    │ You are Compass NYC...                                          │  │
│    │                                                                 │  │
│    │ ELIGIBILITY RULES:                                              │  │
│    │ [3 retrieved chunks here]                                       │  │
│    │                                                                 │  │
│    │ SERVICE LOCATIONS:                                              │  │
│    │ [5 Brooklyn SNAP centers here]                                 │  │
│    │                                                                 │  │
│    │ USER'S QUESTION:                                                │  │
│    │ I make $2,200/month with 2 kids in Brooklyn...                 │  │
│    └─────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│ 2. Call Ollama (llama3.1:70b running locally via NVIDIA NIM)            │
│ 3. Stream response                                                       │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─ LLM RESPONSE ───────────────────────────────────────────────────────────┐
│ "Good news! You likely qualify for SNAP. Here's why:                    │
│                                                                          │
│ • Your household of 3 has a gross income limit of $2,694/month          │
│ • Your $2,200 is below this limit                                       │
│ • You'll also qualify based on net income after deductions              │
│                                                                          │
│ WHAT TO BRING:                                                           │
│ • Proof of income (pay stubs from last 30 days)                         │
│ • Proof of address (lease or utility bill)                              │
│ • Social Security cards for all household members                       │
│ • Photo ID                                                               │
│                                                                          │
│ WHERE TO GO:                                                             │
│ • SNAP Center - Downtown Brooklyn (350 Jay St)                          │
│   Hours: Mon-Fri 9am-5pm | Walk-in: Yes                                 │
│   Languages: English, Spanish, Chinese, Russian                         │
│                                                                          │
│ They'll interview you and give a decision within 30 days."              │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─ FORMATTED OUTPUT ───────────────────────────────────────────────────────┐
│ {                                                                        │
│   "answer": "Good news! You likely qualify...",                         │
│   "locations": [                                                         │
│     {                                                                    │
│       "name": "SNAP Center - Downtown Brooklyn",                        │
│       "address": "350 Jay Street",                                      │
│       "latitude": 40.6928,                                              │
│       "longitude": -73.9874,                                            │
│       "phone": "718-555-0100",                                          │
│       "category": "food",                                               │
│       "color": "#4CAF50"                                                │
│     },                                                                   │
│     ...                                                                  │
│   ],                                                                     │
│   "eligibility_chunks": [...]                                           │
│ }                                                                        │
└──────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════

NVIDIA INTEGRATION POINTS

┌──────────────────────────────────────────────────────────────────────────┐
│  🟢 ACTIVE (Current Implementation)                                      │
├──────────────────────────────────────────────────────────────────────────┤
│  • NVIDIA NIM (via Ollama) for local LLM inference                       │
│  • sentence-transformers (can use GPU acceleration)                      │
│  • Local privacy (no cloud API calls)                                    │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  🟡 PLANNED (High-Impact Additions)                                      │
├──────────────────────────────────────────────────────────────────────────┤
│  • RAPIDS cuDF for 311 demand analysis                                   │
│    - Process 50M 311 service requests on GPU                             │
│    - "This SNAP center has 3x demand on Fridays - go Tuesday"            │
│                                                                           │
│  • cuOpt for route optimization                                          │
│    - "Get SNAP + Medicaid in one trip: here's the fastest route"         │
│                                                                           │
│  • NVIDIA NIM Vision for document OCR                                    │
│    - Upload pay stub → auto-extract income                               │
│    - Upload ID → auto-extract household size                             │
└──────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════

KEY DESIGN DECISIONS

✓ HYBRID RETRIEVAL
  • Eligibility → RAG (semantic, handles complexity)
  • Locations → SQL (deterministic, fast)
  
✓ DATABASE-FIRST
  • Embeddings computed once, cached forever
  • No re-computation on each query
  • Sub-second retrieval
  
✓ MODULAR ARCHITECTURE
  • Easy to swap components
  • Each benefit is self-contained
  • Adding benefits = config change only
  
✓ LOCAL-FIRST
  • No API keys needed
  • No cloud dependency
  • Complete privacy
  • Works offline

✓ PRODUCTION-READY
  • Error handling
  • Logging
  • Type hints
  • Documentation
  • Extensible design
```
