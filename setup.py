"""
Compass NYC — Setup Script
────────────────────────────────────────────────────────────
Run this ONCE to:
1. Install dependencies
2. Initialize the database with embeddings and locations
3. Verify everything works

Then you can run main.py to query the system.
"""

import os
import sys
from pathlib import Path


def check_dependencies():
    """Check if required packages are installed."""
    print("\n" + "="*70)
    print(" CHECKING DEPENDENCIES")
    print("="*70 + "\n")
    
    required = [
        "numpy",
        "requests",
        "sentence-transformers",
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package.replace("-", "_"))
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} — MISSING")
            missing.append(package)
    
    if missing:
        print("\n" + "!"*70)
        print(" MISSING DEPENDENCIES")
        print("!"*70)
        print("\nInstall them with:")
        print(f"  pip install {' '.join(missing)}")
        print("\nOr install all at once:")
        print("  pip install numpy requests sentence-transformers")
        return False
    
    print("\n✓ All dependencies installed")
    return True


def check_ollama():
    """Check if Ollama is running."""
    import requests
    from config import OLLAMA_URL, OLLAMA_MODEL
    
    print("\n" + "="*70)
    print(" CHECKING OLLAMA")
    print("="*70 + "\n")
    
    try:
        response = requests.get(OLLAMA_URL.replace("/api/generate", "/api/tags"), timeout=5)
        models = response.json().get("models", [])
        model_names = [m["name"] for m in models]
        
        print(f"✓ Ollama is running at {OLLAMA_URL}")
        print(f"  Available models: {', '.join(model_names)}")
        
        if OLLAMA_MODEL in model_names or any(OLLAMA_MODEL in m for m in model_names):
            print(f"✓ Model '{OLLAMA_MODEL}' is available")
            return True
        else:
            print(f"\n⚠ Model '{OLLAMA_MODEL}' not found")
            print(f"  Pull it with: ollama pull {OLLAMA_MODEL}")
            return False
            
    except Exception as e:
        print(f"✗ Ollama is not running or not accessible")
        print(f"  Error: {e}")
        print("\nStart Ollama with: ollama serve")
        print(f"Then pull the model: ollama pull {OLLAMA_MODEL}")
        return False


def check_data_files():
    """Check if required data files exist."""
    from config import BENEFITS
    
    print("\n" + "="*70)
    print(" CHECKING DATA FILES")
    print("="*70 + "\n")
    
    missing_files = []
    
    for benefit_type, config in BENEFITS.items():
        eligibility_file = config["eligibility_file"]
        locations_file = config["locations_file"]
        
        print(f"\n{benefit_type}:")
        
        if Path(eligibility_file).exists():
            print(f"  ✓ {eligibility_file}")
        else:
            print(f"  ✗ {eligibility_file} — MISSING")
            missing_files.append(eligibility_file)
        
        if Path(locations_file).exists():
            print(f"  ✓ {locations_file}")
        else:
            print(f"  ✗ {locations_file} — MISSING")
            missing_files.append(locations_file)
    
    if missing_files:
        print("\n" + "!"*70)
        print(" MISSING DATA FILES")
        print("!"*70)
        print("\nThe following files are missing:")
        for f in missing_files:
            print(f"  - {f}")
        print("\nCreate these files before proceeding.")
        print("See README.md for expected file formats.")
        return False
    
    print("\n✓ All data files present")
    return True


def initialize_database():
    """Run database initialization."""
    from database import initialize_database as init_db
    
    print("\n" + "="*70)
    print(" INITIALIZING DATABASE")
    print("="*70 + "\n")
    
    print("This will:")
    print("  1. Create vector embeddings for all eligibility rules")
    print("  2. Load all location data into the database")
    print("  3. Save everything for fast retrieval later")
    print()
    
    response = input("Continue? [y/N]: ").strip().lower()
    
    if response != 'y':
        print("Skipped database initialization")
        return False
    
    init_db(force_rebuild=False)
    return True


def run_test_query():
    """Run a test query to verify everything works."""
    print("\n" + "="*70)
    print(" RUNNING TEST QUERY")
    print("="*70 + "\n")
    
    response = input("Run a test query? [y/N]: ").strip().lower()
    
    if response != 'y':
        print("Skipped test query")
        return
    
    from main import run_query
    
    test_query = (
        "I live in Brooklyn with my two kids. "
        "We are a family of 3 and I make about $2,200 a month. "
        "Do I qualify for SNAP?"
    )
    
    print(f"\nTest query: {test_query}\n")
    
    try:
        run_query(test_query, benefit_type="snap")
        print("\n✓ Test query successful!")
    except Exception as e:
        print(f"\n✗ Test query failed: {e}")
        print("\nDebug the error above before proceeding.")


def main():
    """Run full setup process."""
    print("\n" + "█"*70)
    print(" COMPASS NYC — SETUP")
    print("█"*70)
    
    # Step 1: Dependencies
    if not check_dependencies():
        print("\n⚠ Setup incomplete: missing dependencies")
        sys.exit(1)
    
    # Step 2: Ollama
    ollama_ok = check_ollama()
    if not ollama_ok:
        print("\n⚠ Ollama check failed - you can continue but LLM queries won't work")
    
    # Step 3: Data files
    if not check_data_files():
        print("\n⚠ Setup incomplete: missing data files")
        sys.exit(1)
    
    # Step 4: Initialize database
    if not initialize_database():
        print("\n⚠ Setup incomplete: database not initialized")
        sys.exit(1)
    
    # Step 5: Test
    if ollama_ok:
        run_test_query()
    
    # Done
    print("\n" + "█"*70)
    print(" SETUP COMPLETE")
    print("█"*70)
    print("\nYou can now run queries with:")
    print("  python main.py")
    print("\nOr in Python:")
    print("  from main import run_query")
    print("  run_query('your question here', benefit_type='snap')")
    print()


if __name__ == "__main__":
    main()
