"""
Compass NYC — Database Manager
────────────────────────────────────────────────────────────
Persistent storage for:
  - Vector embeddings (eligibility chunks)
  - Location data (SNAP centers, etc.)

SQLite is used for simplicity. Can upgrade to PostgreSQL + pgvector
for production scale, but SQLite + numpy is fine for hackathon.
"""

import sqlite3
import numpy as np
import json
import csv
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
from benchmark import Benchmark

from config import VECTOR_DB_PATH, LOCATIONS_DB_PATH, BENEFITS


class DatabaseManager:
    """
    Manages both vector embeddings and location data.
    Embeddings are computed once and cached.
    """
    
    def __init__(self):
        self.vector_db_path = VECTOR_DB_PATH
        self.locations_db_path = LOCATIONS_DB_PATH
        self._ensure_db_directories()
        self._init_vector_db()
        self._init_locations_db()
    
    def _ensure_db_directories(self):
        """Create data directory if it doesn't exist."""
        Path(self.vector_db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.locations_db_path).parent.mkdir(parents=True, exist_ok=True)
    
    # ── VECTOR DATABASE (ELIGIBILITY EMBEDDINGS) ──────────────────────────────
    
    def _init_vector_db(self):
        """Create tables for storing eligibility chunk embeddings."""
        conn = sqlite3.connect(self.vector_db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                benefit_type TEXT NOT NULL,
                chunk_text TEXT NOT NULL,
                embedding BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_benefit_type 
            ON embeddings(benefit_type)
        """)
        conn.commit()
        conn.close()
    
    def store_embeddings(self, benefit_type: str, chunks: List[str], 
                        embeddings: np.ndarray):
        """
        Store embeddings for a benefit type.
        Deletes old embeddings for that benefit first (allows updates).
        """
        conn = sqlite3.connect(self.vector_db_path)
        
        # Clear old embeddings for this benefit
        conn.execute("DELETE FROM embeddings WHERE benefit_type = ?", (benefit_type,))
        
        # Insert new embeddings
        for chunk, embedding in zip(chunks, embeddings):
            embedding_blob = embedding.tobytes()  # numpy array → binary
            conn.execute(
                "INSERT INTO embeddings (benefit_type, chunk_text, embedding) VALUES (?, ?, ?)",
                (benefit_type, chunk, embedding_blob)
            )
        
        conn.commit()
        conn.close()
        print(f"[DB] Stored {len(chunks)} embeddings for '{benefit_type}'")
    
    def load_embeddings(self, benefit_type: str, benchmark = None) -> Tuple[List[str], np.ndarray]:
        """
        Load all embeddings for a benefit type.
        Returns: (chunks, embeddings_matrix)
        """
        start_time = time.time()

        conn = sqlite3.connect(self.vector_db_path)
        cursor = conn.execute(
            "SELECT chunk_text, embedding FROM embeddings WHERE benefit_type = ? ORDER BY id",
            (benefit_type,)
        )
        
        chunks = []
        embedding_list = []
        
        for row in cursor:
            chunk_text, embedding_blob = row
            chunks.append(chunk_text)
            
            # Binary → numpy array
            # We need to know the dimension - MiniLM-L6-v2 is 384-dim
            embedding = np.frombuffer(embedding_blob, dtype=np.float32)
            embedding_list.append(embedding)
        
        conn.close()
        
        if not chunks:
            return [], np.array([])
        
        embeddings_matrix = np.vstack(embedding_list)  # shape: (num_chunks, dim)

        load_time = time.time() - start_time
        
        if benchmark:
            benchmark.log("num_embeddings", len(chunks))
            benchmark.log("db_load_time", load_time)
        
        print(f"[DB] Loaded {len(chunks)} embeddings for '{benefit_type}' in {load_time:.4f}s")

        return chunks, embeddings_matrix
    
    def has_embeddings(self, benefit_type: str) -> bool:
        """Check if embeddings exist for a benefit type."""
        conn = sqlite3.connect(self.vector_db_path)
        cursor = conn.execute(
            "SELECT COUNT(*) FROM embeddings WHERE benefit_type = ?",
            (benefit_type,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    
    # ── LOCATIONS DATABASE ────────────────────────────────────────────────────
    
    def _init_locations_db(self):
        """Create table for storing location data."""
        conn = sqlite3.connect(self.locations_db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                benefit_type TEXT NOT NULL,
                name TEXT NOT NULL,
                address TEXT,
                borough TEXT,
                zip TEXT,
                phone TEXT,
                hours TEXT,
                walk_in TEXT,
                languages TEXT,
                latitude REAL,
                longitude REAL,
                metadata TEXT,  -- JSON for any extra fields
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_location_benefit 
            ON locations(benefit_type)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_location_borough 
            ON locations(borough)
        """)
        conn.commit()
        conn.close()
    
    def store_locations(self, benefit_type: str, locations_file: str):
        """
        Load locations from CSV and store in database.
        Deletes old locations for that benefit first.
        """
        conn = sqlite3.connect(self.locations_db_path)
        
        # Clear old locations
        conn.execute("DELETE FROM locations WHERE benefit_type = ?", (benefit_type,))
        
        # Load CSV
        with open(locations_file, 'r') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                # Extract standard fields, put the rest in metadata
                standard_fields = {
                    'name', 'address', 'borough', 'zip', 'phone', 
                    'hours', 'walk_in', 'languages', 'latitude', 'longitude'
                }
                
                metadata = {k: v for k, v in row.items() if k not in standard_fields}
                
                conn.execute("""
                    INSERT INTO locations 
                    (benefit_type, name, address, borough, zip, phone, hours, 
                     walk_in, languages, latitude, longitude, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    benefit_type,
                    row.get('name', ''),
                    row.get('address', ''),
                    row.get('borough', ''),
                    row.get('zip', ''),
                    row.get('phone', ''),
                    row.get('hours', ''),
                    row.get('walk_in', ''),
                    row.get('languages', ''),
                    float(row['latitude']) if row.get('latitude') else None,
                    float(row['longitude']) if row.get('longitude') else None,
                    json.dumps(metadata)
                ))
                count += 1
        
        conn.commit()
        conn.close()
        print(f"[DB] Stored {count} locations for '{benefit_type}'")
    
    def load_locations(self, benefit_type: str, borough: str = None, benchmark = None) -> List[Dict[str, Any]]:
        """
        Load locations for a benefit type, optionally filtered by borough.
        """
        start_time = time.time()

        conn = sqlite3.connect(self.locations_db_path)
        
        if borough:
            cursor = conn.execute("""
                SELECT name, address, borough, zip, phone, hours, walk_in, 
                       languages, latitude, longitude, metadata
                FROM locations 
                WHERE benefit_type = ? AND LOWER(borough) = LOWER(?)
                ORDER BY name
            """, (benefit_type, borough))
        else:
            cursor = conn.execute("""
                SELECT name, address, borough, zip, phone, hours, walk_in, 
                       languages, latitude, longitude, metadata
                FROM locations 
                WHERE benefit_type = ?
                ORDER BY borough, name
            """, (benefit_type,))
        
        locations = []
        for row in cursor:
            loc = {
                'name': row[0],
                'address': row[1],
                'borough': row[2],
                'zip': row[3],
                'phone': row[4],
                'hours': row[5],
                'walk_in': row[6],
                'languages': row[7],
                'latitude': row[8],
                'longitude': row[9],
            }
            # Merge metadata
            if row[10]:
                metadata = json.loads(row[10])
                loc.update(metadata)
            
            locations.append(loc)
        
        conn.close()

        elapsed = time.time() - start_time

        if benchmark:
            benchmark.log("location_query_time", elapsed)
            benchmark.log("num_locations_returned", len(locations))

        return locations
    
    def has_locations(self, benefit_type: str) -> bool:
        """Check if locations exist for a benefit type."""
        conn = sqlite3.connect(self.locations_db_path)
        cursor = conn.execute(
            "SELECT COUNT(*) FROM locations WHERE benefit_type = ?",
            (benefit_type,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0


# ── INITIALIZATION HELPER ─────────────────────────────────────────────────────

def initialize_database(force_rebuild: bool = False):
    """
    Initialize database with all benefits from config.
    If embeddings/locations already exist and force_rebuild=False, skip.
    
    Run this once at setup or when adding new benefits.
    """
    from eligibility_engine import chunk_text
    from sentence_transformers import SentenceTransformer
    from config import EMBED_MODEL_NAME, CHUNK_SIZE, CHUNK_OVERLAP
    
    db = DatabaseManager()
    embed_model = SentenceTransformer(EMBED_MODEL_NAME)
    
    print("\n" + "="*70)
    print(" INITIALIZING COMPASS NYC DATABASE")
    print("="*70 + "\n")
    
    for benefit_type, config in BENEFITS.items():
        print(f"\n── Processing: {config['name']} ──")
        
        # ── Embeddings ────────────────────────────────────────────────────────
        if force_rebuild or not db.has_embeddings(benefit_type):
            print(f"[{benefit_type}] Building embeddings from {config['eligibility_file']}...")
            
            # Load and chunk text
            with open(config['eligibility_file'], 'r') as f:
                text = f.read()
            
            chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
            
            # Generate embeddings
            embeddings = embed_model.encode(chunks, convert_to_numpy=True, show_progress_bar=False)
            
            # Store
            db.store_embeddings(benefit_type, chunks, embeddings)
        else:
            print(f"[{benefit_type}] Embeddings already exist (use force_rebuild=True to recreate)")
        
        # ── Locations ─────────────────────────────────────────────────────────
        if force_rebuild or not db.has_locations(benefit_type):
            print(f"[{benefit_type}] Loading locations from {config['locations_file']}...")
            db.store_locations(benefit_type, config['locations_file'])
        else:
            print(f"[{benefit_type}] Locations already exist (use force_rebuild=True to recreate)")
    
    print("\n" + "="*70)
    print(" DATABASE INITIALIZATION COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    # Run this to build the database for the first time
    initialize_database(force_rebuild=False)