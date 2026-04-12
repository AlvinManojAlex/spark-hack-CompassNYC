"""
Compass NYC — Eligibility Engine
────────────────────────────────────────────────────────────
RAG-based eligibility reasoning.
Retrieves relevant chunks from vector DB and reasons over them.
"""

import numpy as np
import time
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer

from config import EMBED_MODEL_NAME, TOP_K_CHUNKS
from database import DatabaseManager
from benchmark import Benchmark

# ── TEXT CHUNKING ─────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Split text into overlapping chunks (by word count).
    Overlap prevents rules that span chunk boundaries from being lost.
    """
    words = text.split()
    chunks = []
    step = chunk_size - overlap
    
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    
    return chunks


# ── ELIGIBILITY ENGINE ────────────────────────────────────────────────────────

class EligibilityEngine:
    """
    Retrieves relevant eligibility rules using vector similarity (RAG).
    Works across all benefit types.
    """
    
    def __init__(self):
        self.db = DatabaseManager()
        self.embed_model = SentenceTransformer(EMBED_MODEL_NAME)
        print(f"[Eligibility] Initialized with model: {EMBED_MODEL_NAME}")
    
    def retrieve(self, benefit_type: str, query: str, top_k: int = TOP_K_CHUNKS, benchmark = None) -> List[Dict]:
        """
        Retrieve the most relevant eligibility chunks for a query.
        
        Args:
            benefit_type: e.g., "snap", "hra_cash"
            query: User's question (natural language)
            top_k: Number of chunks to return
        
        Returns:
            List of dicts with keys: chunk (text), score (similarity)
        """

        total_start = time.time()

        # Load stored embeddings
        load_start = time.time()
        chunks, embeddings = self.db.load_embeddings(benefit_type, benchmark = benchmark)
        load_time = time.time() - load_start
        
        if len(chunks) == 0:
            print(f"[Eligibility] WARNING: No embeddings found for '{benefit_type}'")
            return []
        
        if benchmark:
            benchmark.log("retrieval_db_load_time", load_time)
            benchmark.log("num_chunks_in_db", len(chunks))
        
        # Embed query
        embed_start = time.time()
        query_embedding = self.embed_model.encode([query], convert_to_numpy=True)
        embed_time = time.time() - embed_start

        if benchmark:
            benchmark.log("query_embedding_time", embed_time)
        
        # Cosine similarity (embeddings are already normalized)
        sim_start = time.time()
        scores = np.dot(embeddings, query_embedding.T).flatten()
        sim_time = time.time() - sim_start

        if benchmark:
            benchmark.log("similarity_compute_time", sim_time)
        
        # Get top K
        topk_start = time.time()
        top_indices = scores.argsort()[-top_k:][::-1]
        topk_time = time.time() - topk_start

        if benchmark:
            benchmark.log("topk_selection_time", topk_time)
        
        results = []
        for idx in top_indices:
            results.append({
                "chunk": chunks[idx],
                "score": float(scores[idx])
            })
            print(f"[RAG] Retrieved chunk #{idx} for '{benefit_type}' "
                  f"(score: {scores[idx]:.3f}): {chunks[idx][:60]}...")
        
        total_time = time.time() - total_start

        if benchmark:
            benchmark.log("retrieval_total_time", total_time)
        
        return results
    
    def retrieve_multi_benefit(self, benefit_types: List[str], query: str, 
                               top_k_per_benefit: int = 2) -> Dict[str, List[Dict]]:
        """
        Retrieve eligibility chunks across multiple benefits.
        Useful when user doesn't specify which benefit they need.
        
        Returns:
            Dict mapping benefit_type → list of retrieved chunks
        """
        results = {}
        for benefit_type in benefit_types:
            results[benefit_type] = self.retrieve(benefit_type, query, top_k_per_benefit)
        return results
    
    def format_for_prompt(self, retrieved_chunks: List[Dict]) -> str:
        """
        Format retrieved chunks as clean text for LLM prompt.
        """
        if not retrieved_chunks:
            return "No eligibility information available."
        
        formatted = []
        for i, item in enumerate(retrieved_chunks, 1):
            formatted.append(f"Rule {i}:\n{item['chunk']}")
        
        return "\n\n---\n\n".join(formatted)


# ── CONVENIENCE FUNCTION ──────────────────────────────────────────────────────

def get_eligibility_context(benefit_type: str, query: str) -> str:
    """
    One-liner to get formatted eligibility context for a prompt.
    """
    engine = EligibilityEngine()
    chunks = engine.retrieve(benefit_type, query)
    return engine.format_for_prompt(chunks)


if __name__ == "__main__":
    # Test retrieval
    engine = EligibilityEngine()
    
    test_query = "I make $2,200 per month with 2 kids, do I qualify for SNAP?"
    
    chunks = engine.retrieve("snap", test_query, top_k=3)
    
    print("\n" + "="*70)
    print(" RETRIEVED ELIGIBILITY CHUNKS")
    print("="*70)
    print(engine.format_for_prompt(chunks))
    print("="*70)