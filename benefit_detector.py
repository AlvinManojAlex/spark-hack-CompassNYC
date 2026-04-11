"""
Compass NYC — Smart Benefit Detector
────────────────────────────────────────────────────────────
Uses LLM to intelligently detect relevant benefits from user queries.
Returns structured JSON for reliable parsing.
"""

import json
import requests as req
from typing import List, Dict
from config import BENEFITS, OLLAMA_URL, OLLAMA_MODEL


class BenefitDetector:
    """
    Intelligent benefit detection using LLM with structured output.
    """
    
    def __init__(self):
        self.ollama_url = OLLAMA_URL
        self.ollama_model = OLLAMA_MODEL
    
    def detect(self, query: str, chat_history: List[Dict] = None, use_llm: bool = True) -> List[str]:
        """
        Detect relevant benefits using LLM reasoning or fast heuristics.
        
        Args:
            query: User's question
            chat_history: Previous conversation for context (optional)
            use_llm: If False, use fast keyword heuristics instead of LLM
        
        Returns:
            List of benefit IDs (e.g., ["snap", "medicaid"])
        """
        # Fast path: Use heuristics (skip LLM call)
        if not use_llm:
            print(f"[Detector] Using fast heuristic detection...")
            return self._fallback_detection(query)
        
        print(f"[Detector] Analyzing query for relevant benefits...")
        
        # Build benefits catalog
        benefits_catalog = self._build_benefits_catalog()
        
        # Build context from history
        history_context = ""
        if chat_history:
            history_context = "\n\nPREVIOUS CONVERSATION CONTEXT:\n"
            for msg in chat_history[-4:]:  # Last 4 messages for context
                role = "User" if msg["role"] == "user" else "Assistant"
                history_context += f"{role}: {msg['content'][:100]}...\n"
        
        # Build detection prompt
        prompt = f"""You are a benefits eligibility expert analyzing what NYC social services programs might help someone.

AVAILABLE BENEFITS:
{benefits_catalog}

ANALYSIS TASK:
Read the user's question below and determine which benefits are most relevant to their needs.

RULES:
1. Consider what the user is asking for (food, healthcare, housing, money, transportation, etc.)
2. Include benefits where they might be eligible based on their situation
3. If they mention specific needs (e.g., "food"), prioritize those benefits
4. If the query is general (e.g., "I need help"), include the most common benefits: snap, medicaid
5. If they mention being a student, include student-specific benefits
6. Limit to maximum 4 benefits to avoid overwhelming them
{history_context}

USER'S CURRENT QUESTION:
"{query}"

RESPOND WITH ONLY A JSON OBJECT IN THIS EXACT FORMAT:
{{
  "benefits": ["benefit_id_1", "benefit_id_2"],
  "reasoning": "Brief explanation of why these benefits were selected"
}}

IMPORTANT: 
- Use only benefit IDs from the list above
- Return valid JSON only, no other text
- The "benefits" array must contain at least 1 benefit

JSON RESPONSE:"""

        try:
            # Call Ollama
            response = req.post(
                self.ollama_url,
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,  # Low temp for consistent structured output
                        "num_predict": 200,
                    }
                },
                timeout=30
            )
            response.raise_for_status()
            
            llm_response = response.json()["response"].strip()
            
            # Parse JSON response
            detected = self._parse_llm_response(llm_response, query)
            
            print(f"[Detector] Detected benefits: {detected}")
            return detected
            
        except Exception as e:
            print(f"[Detector] ERROR: {e}")
            print(f"[Detector] Falling back to heuristic detection")
            return self._fallback_detection(query)
    
    def _build_benefits_catalog(self) -> str:
        """Build a formatted catalog of available benefits."""
        catalog = []
        for benefit_id, config in BENEFITS.items():
            catalog.append(
                f"• {benefit_id}: {config['name']}\n"
                f"  Description: {config['description']}\n"
                f"  Category: {config['category']}"
            )
        return "\n\n".join(catalog)
    
    def _parse_llm_response(self, llm_response: str, query: str) -> List[str]:
        """
        Parse LLM response to extract benefit IDs.
        Handles multiple formats and cleans the response.
        """
        # Try to extract JSON from response
        # Sometimes LLM adds text before/after JSON
        
        # Find JSON block
        start = llm_response.find('{')
        end = llm_response.rfind('}') + 1
        
        if start != -1 and end > start:
            json_str = llm_response[start:end]
            
            try:
                parsed = json.loads(json_str)
                benefits = parsed.get("benefits", [])
                reasoning = parsed.get("reasoning", "")
                
                print(f"[Detector] Reasoning: {reasoning}")
                
                # Validate benefit IDs
                valid_benefits = [b for b in benefits if b in BENEFITS]
                
                if valid_benefits:
                    return valid_benefits[:4]  # Max 4
                
            except json.JSONDecodeError as e:
                print(f"[Detector] JSON parse error: {e}")
        
        # Fallback: scan for benefit IDs in response
        print(f"[Detector] Could not parse JSON, scanning for benefit IDs...")
        detected = []
        response_lower = llm_response.lower()
        
        for benefit_id in BENEFITS.keys():
            if benefit_id in response_lower:
                detected.append(benefit_id)
        
        if detected:
            return detected[:4]
        
        # Last resort: heuristic fallback
        return self._fallback_detection(query)
    
    def _fallback_detection(self, query: str) -> List[str]:
        """
        Heuristic fallback when LLM detection fails.
        Simple keyword matching as last resort.
        """
        query_lower = query.lower()
        detected = []
        
        # Category-based detection
        if any(word in query_lower for word in ["food", "hungry", "eat", "meal", "groceries", "snap", "ebt"]):
            if "snap" in BENEFITS:
                detected.append("snap")
            if "food_pantries" in BENEFITS and "student" not in query_lower:
                detected.append("food_pantries")
        
        if any(word in query_lower for word in ["health", "medical", "doctor", "sick", "hospital", "insurance", "medicaid"]):
            if "medicaid" in BENEFITS:
                detected.append("medicaid")
        
        if any(word in query_lower for word in ["cash", "money", "job", "unemployed", "emergency", "financial", "tanf"]):
            if "hra_cash" in BENEFITS:
                detected.append("hra_cash")
        
        # Default to most common if nothing detected
        if not detected:
            detected = []
            if "snap" in BENEFITS:
                detected.append("snap")
            if "medicaid" in BENEFITS:
                detected.append("medicaid")
        
        return detected[:4]  # Max 4


# ── CONVENIENCE FUNCTION ──────────────────────────────────────────────────────

def detect_benefits(query: str, chat_history: List[Dict] = None) -> List[str]:
    """
    One-liner to detect benefits from a query.
    """
    detector = BenefitDetector()
    return detector.detect(query, chat_history)


if __name__ == "__main__":
    # Test the detector
    detector = BenefitDetector()
    
    test_queries = [
        "I need help with food and healthcare",
        "I'm a CUNY student and I'm hungry",
        "I lost my job and need emergency money",
        "Can you help me?",
        "I can't afford the subway",
        "I'm struggling to make ends meet with rent and groceries",
    ]
    
    print("\n" + "="*70)
    print(" BENEFIT DETECTOR TEST")
    print("="*70 + "\n")
    
    for query in test_queries:
        print(f"Query: {query}")
        benefits = detector.detect(query)
        print(f"Detected: {benefits}")
        print("─"*70 + "\n")