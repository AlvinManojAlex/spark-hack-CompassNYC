"""
Compass NYC — Main Application
────────────────────────────────────────────────────────────
Orchestrates the full pipeline:
  User query → RAG retrieval → Location filtering → LLM reasoning → Response
"""

import textwrap
from typing import List, Dict, Optional

from config import BENEFITS
from database import DatabaseManager
from eligibility_engine import EligibilityEngine
from location_manager import LocationManager
from llm_interface import LLMInterface


class CompassNYC:
    """
    Main application class - coordinates all components.
    """
    
    def __init__(self):
        self.db = DatabaseManager()
        self.eligibility_engine = EligibilityEngine()
        self.location_manager = LocationManager()
        self.llm = LLMInterface()
        
        print("\n" + "="*70)
        print(" COMPASS NYC — Initialized")
        print("="*70)
        print(f" Available benefits: {', '.join(BENEFITS.keys())}")
        print("="*70 + "\n")
    
    def query(self, user_query: str, benefit_type: str = "snap") -> Dict:
        """
        Process a user query for a specific benefit.
        
        Args:
            user_query: Natural language question from user
            benefit_type: Which benefit to check (default: "snap")
        
        Returns:
            Dict with keys:
                - answer: LLM response text
                - locations: List of location dicts (for map display)
                - eligibility_chunks: Retrieved chunks (for debugging)
        """
        print(f"\n{'='*70}")
        print(f" QUERY: {user_query}")
        print(f" BENEFIT: {BENEFITS[benefit_type]['name']}")
        print(f"{'='*70}\n")
        
        # Step 1: Retrieve eligibility context (RAG)
        print("[1/4] Retrieving eligibility rules...")
        eligibility_chunks = self.eligibility_engine.retrieve(benefit_type, user_query)
        eligibility_context = self.eligibility_engine.format_for_prompt(eligibility_chunks)
        
        # Step 2: Get location context (structured filtering)
        print("[2/4] Loading service locations...")
        borough = self.location_manager.detect_borough(user_query)
        if borough:
            print(f"      Borough detected: {borough}")
        locations = self.location_manager.get_locations(benefit_type, borough)
        location_context = self.location_manager.format_for_prompt(locations)
        
        # Step 3: Generate LLM response
        print("[3/4] Generating response...")
        answer = self.llm.answer_eligibility_query(
            benefit_type, user_query, eligibility_context, location_context
        )
        
        # Step 4: Package results
        print("[4/4] Packaging results...")
        
        result = {
            "answer": answer,
            "locations": locations,  # Raw data for map
            "eligibility_chunks": eligibility_chunks,  # For debugging
            "benefit_type": benefit_type,
            "benefit_name": BENEFITS[benefit_type]["name"]
        }
        
        return result
    
    def query_multi_benefit(self, user_query: str, 
                           benefit_types: Optional[List[str]] = None) -> Dict:
        """
        Process a query across multiple benefits.
        Useful when user doesn't specify which benefit they need.
        
        Args:
            user_query: Natural language question
            benefit_types: List of benefits to check (default: all available)
        
        Returns:
            Dict with answer and locations grouped by benefit
        """
        if benefit_types is None:
            benefit_types = list(BENEFITS.keys())
        
        print(f"\n{'='*70}")
        print(f" MULTI-BENEFIT QUERY: {user_query}")
        print(f" Checking: {', '.join([BENEFITS[bt]['name'] for bt in benefit_types])}")
        print(f"{'='*70}\n")
        
        # Gather context for each benefit
        benefit_contexts = {}
        all_locations = {}
        
        for benefit_type in benefit_types:
            print(f"\n── Processing {BENEFITS[benefit_type]['name']} ──")
            
            # Eligibility
            eligibility_chunks = self.eligibility_engine.retrieve(benefit_type, user_query, top_k=2)
            eligibility_context = self.eligibility_engine.format_for_prompt(eligibility_chunks)
            
            # Locations
            borough = self.location_manager.detect_borough(user_query)
            locations = self.location_manager.get_locations(benefit_type, borough)
            location_context = self.location_manager.format_for_prompt(locations)
            
            benefit_contexts[benefit_type] = {
                'eligibility': eligibility_context,
                'locations': location_context
            }
            all_locations[benefit_type] = locations
        
        # Generate response
        print("\n[LLM] Generating multi-benefit response...")
        answer = self.llm.answer_multi_benefit_query(user_query, benefit_contexts)
        
        result = {
            "answer": answer,
            "locations_by_benefit": all_locations,
            "benefit_types": benefit_types
        }
        
        return result
    
    def print_response(self, result: Dict):
        """
        Pretty-print a response to console.
        """
        print("\n" + "="*70)
        print(" COMPASS NYC RESPONSE")
        print("="*70)
        print(textwrap.fill(result["answer"], width=68))
        print("="*70)
        
        if "locations" in result:
            print(f"\n{len(result['locations'])} service locations available for map display")
        
        print()


# ── CONVENIENCE FUNCTIONS ─────────────────────────────────────────────────────

def run_query(user_query: str, benefit_type: str = "snap") -> Dict:
    """
    One-liner to run a query.
    Returns full result dict.
    """
    app = CompassNYC()
    result = app.query(user_query, benefit_type)
    app.print_response(result)
    return result


def run_multi_query(user_query: str, benefit_types: Optional[List[str]] = None) -> Dict:
    """
    One-liner to run a multi-benefit query.
    """
    app = CompassNYC()
    result = app.query_multi_benefit(user_query, benefit_types)
    app.print_response(result)
    return result


# ── DEMO / TESTING ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Example usage
    
    print("\n" + "█"*70)
    print(" COMPASS NYC — DEMO")
    print("█"*70)
    
    # Single benefit query
    query1 = (
        "I live in Brooklyn with my two kids. "
        "We are a family of 3 and I make about $2,200 a month from my job. "
        "I'm a US citizen. Do I qualify for SNAP and where can I apply?"
    )
    
    run_query(query1, benefit_type="snap")
    
    # Uncomment when you have multiple benefits set up:
    # query2 = "I'm homeless and need help with housing and food in Manhattan"
    # run_multi_query(query2, benefit_types=["snap", "dhs_shelter"])
