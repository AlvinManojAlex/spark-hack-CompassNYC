"""
Compass NYC — Configuration
────────────────────────────────────────────────────────────
Central config for all benefit programs.
Adding a new benefit = add one entry to BENEFITS dict.
"""

# ── MODEL CONFIGURATION ───────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:72b"  # Upgrade to "llama3.1:70b" or "nemotron-51b-instruct" for better reasoning
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

# RAG settings
TOP_K_CHUNKS = 5
CHUNK_SIZE = 200  # words
CHUNK_OVERLAP = 50  # words

# LLM generation settings
LLM_TEMPERATURE = 0.3  # Lower = more factual
LLM_MAX_TOKENS = 600

# ── DATABASE PATHS ────────────────────────────────────────────────────────────

VECTOR_DB_PATH = "data/embeddings.db"  # SQLite for vector storage
LOCATIONS_DB_PATH = "data/locations.db"  # SQLite for structured location data

# ── BENEFIT PROGRAMS ──────────────────────────────────────────────────────────
# This is where you register new benefits. Each benefit needs:
#   - eligibility_file: path to scraped/written eligibility rules (txt)
#   - locations_file: path to CSV with location data
#   - category: for color-coding on map UI later

BENEFITS = {
    "snap": {
        "name": "SNAP (Food Stamps)",
        "eligibility_file": "data/eligibility/snap_eligibility.txt",
        "locations_file": "data/locations/snap_locations.csv",
        "category": "food",
        "color": "#4CAF50",  # green
        "description": "Supplemental Nutrition Assistance Program"
    },
    
    # ── ADD MORE BENEFITS HERE ────────────────────────────────────────────────
    # Uncomment and populate as you add them:
    
    # "hra_cash": {
    #     "name": "HRA Cash Assistance",
    #     "eligibility_file": "data/eligibility/hra_cash_eligibility.txt",
    #     "locations_file": "data/locations/hra_centers.csv",
    #     "category": "financial",
    #     "color": "#2196F3",  # blue
    #     "description": "Temporary cash assistance for basic needs"
    # },
    
    # "dhs_shelter": {
    #     "name": "DHS Emergency Shelter",
    #     "eligibility_file": "data/eligibility/dhs_shelter_eligibility.txt",
    #     "locations_file": "data/locations/dhs_shelters.csv",
    #     "category": "housing",
    #     "color": "#FF9800",  # orange
    #     "description": "Emergency housing for individuals and families"
    # },
    
    # "medicaid": {
    #     "name": "Medicaid",
    #     "eligibility_file": "data/eligibility/medicaid_eligibility.txt",
    #     "locations_file": "data/locations/medicaid_offices.csv",
    #     "category": "health",
    #     "color": "#E91E63",  # pink
    #     "description": "Free or low-cost health coverage"
    # },
    
    # "fair_fares": {
    #     "name": "Fair Fares NYC",
    #     "eligibility_file": "data/eligibility/fair_fares_eligibility.txt",
    #     "locations_file": "data/locations/fair_fares_locations.csv",
    #     "category": "transportation",
    #     "color": "#9C27B0",  # purple
    #     "description": "Half-price MetroCard for low-income residents"
    # },
}

# ── BOROUGH DETECTION ─────────────────────────────────────────────────────────

BOROUGHS = ["manhattan", "brooklyn", "queens", "bronx", "staten island"]
