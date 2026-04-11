"""
Compass NYC — Conversational Agent
────────────────────────────────────────────────────────────
Handles multi-turn conversations with context.
Auto-detects which benefits are relevant to user's query.
"""

from typing import List, Dict, Optional
import re

from config import BENEFITS, BENEFIT_DETECTION_MODE
from eligibility_engine import EligibilityEngine
from location_manager import LocationManager
from llm_interface import LLMInterface
from benefit_detector import BenefitDetector


class ConversationalAgent:
    """
    Stateful conversational agent that maintains chat history.
    """
    
    def __init__(self, fast_mode: bool = False):
        self.eligibility_engine = EligibilityEngine()
        self.location_manager = LocationManager()
        self.llm = LLMInterface()
        self.benefit_detector = BenefitDetector()
        self.history: List[Dict[str, str]] = []  # Chat history
        self.fast_mode = fast_mode  # If True, use faster but less comprehensive responses
        
        print("\n" + "="*70)
        print(" COMPASS NYC — Conversational Agent Initialized")
        print("="*70)
        print(f" Available benefits: {', '.join(BENEFITS.keys())}")
        print("="*70 + "\n")
    
    def detect_relevant_benefits(self, query: str) -> List[str]:
        """
        Auto-detect which benefits are relevant to user's query.
        Uses LLM or heuristics based on BENEFIT_DETECTION_MODE config.
        
        Returns:
            List of benefit_type keys (e.g., ["snap", "medicaid"])
        """
        # Use config setting to determine detection mode
        use_llm = (BENEFIT_DETECTION_MODE == "llm")
        
        # Use the smart detector with conversation history for context
        return self.benefit_detector.detect(
            query, 
            chat_history=self.history,
            use_llm=use_llm
        )
    
    def chat(self, user_message: str, benefit_types: Optional[List[str]] = None) -> Dict:
        """
        Process a conversational message.
        
        Args:
            user_message: User's message
            benefit_types: Specific benefits to check (None = auto-detect)
        
        Returns:
            Dict with answer, locations, and metadata
        """
        print(f"\n{'='*70}")
        print(f" USER: {user_message}")
        print(f"{'='*70}\n")
        
        # Auto-detect benefits if not specified
        if benefit_types is None:
            benefit_types = self.detect_relevant_benefits(user_message)
        
        # Add user message to history
        self.history.append({"role": "user", "content": user_message})
        
        # Gather context for each benefit
        benefit_contexts = {}
        all_locations = {}
        
        for benefit_type in benefit_types:
            if benefit_type not in BENEFITS:
                print(f"[Agent] WARNING: Unknown benefit '{benefit_type}', skipping")
                continue
            
            print(f"\n── Processing {BENEFITS[benefit_type]['name']} ──")
            
            # Eligibility context (RAG)
            eligibility_chunks = self.eligibility_engine.retrieve(benefit_type, user_message, top_k=3)
            eligibility_context = self.eligibility_engine.format_for_prompt(eligibility_chunks)
            
            # Location context
            borough = self.location_manager.detect_borough(user_message)
            locations = self.location_manager.get_locations(benefit_type, borough)
            location_context = self.location_manager.format_for_prompt(locations, max_locations=5)
            
            benefit_contexts[benefit_type] = {
                'eligibility': eligibility_context,
                'locations': location_context
            }
            all_locations[benefit_type] = locations
        
        # Build conversational prompt
        prompt = self._build_conversational_prompt(
            user_message,
            benefit_contexts,
            benefit_types
        )
        
        # Generate response (with streaming)
        print("\n[Agent] Generating response...")
        answer = self.llm.generate(prompt, stream=True)
        
        # Add assistant response to history
        self.history.append({"role": "assistant", "content": answer})
        
        # Package result
        result = {
            "answer": answer,
            "locations_by_benefit": all_locations,
            "benefit_types": benefit_types,
            "history": self.history.copy(),
            "detected_borough": self.location_manager.detect_borough(user_message)
        }
        
        return result
    
    def _build_conversational_prompt(self,
                                    user_message: str,
                                    benefit_contexts: Dict[str, Dict[str, str]],
                                    benefit_types: List[str]) -> str:
        """
        Build a conversational prompt with chat history.
        """
        # Build benefit sections
        sections = []
        for benefit_type in benefit_types:
            if benefit_type not in benefit_contexts:
                continue
            
            benefit_name = BENEFITS[benefit_type]["name"]
            contexts = benefit_contexts[benefit_type]
            
            sections.append(f"""
═══════════════════════════════════════════════════════════════
{benefit_name.upper()}
═══════════════════════════════════════════════════════════════

ELIGIBILITY RULES:
{contexts['eligibility']}

SERVICE LOCATIONS:
{contexts['locations']}
""")
        
        all_benefits = ", ".join([BENEFITS[bt]["name"] for bt in benefit_types])
        
        # Build chat history context
        history_context = ""
        if len(self.history) > 1:  # More than just current message
            history_context = "\n\nPREVIOUS CONVERSATION:\n"
            for msg in self.history[:-1]:  # Exclude current message
                role = "User" if msg["role"] == "user" else "You"
                history_context += f"{role}: {msg['content']}\n"
            history_context += "\n"
        
        prompt = f"""You are Compass NYC, a warm and helpful AI assistant that guides New Yorkers to social services.

You are having a conversation with someone who needs help. Based on their question, you have information about: {all_benefits}.

INSTRUCTIONS:
1. Answer their specific question directly and conversationally
2. For each relevant program:
   - Determine if they likely qualify based on the rules provided
   - Explain eligibility clearly, referencing their specific situation
   - If they qualify, tell them where to go and what documents to bring
   - If unclear, ask clarifying questions
3. Be warm, conversational, and remember the context of your conversation
4. Prioritize the programs that best fit their needs
5. Use clear headings to organize information about different programs
6. Never make up rules - only use information from the context below

{history_context}
{"".join(sections)}

──────────────────────────────────────────────────────────────────────
CURRENT QUESTION:
──────────────────────────────────────────────────────────────────────
{user_message}

YOUR RESPONSE (be conversational and helpful):"""

        return prompt
    
    def reset_conversation(self):
        """Clear chat history."""
        self.history = []
        print("[Agent] Conversation reset")
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get chat history."""
        return self.history.copy()


# ── CONVENIENCE FUNCTIONS ─────────────────────────────────────────────────────

def start_conversation() -> ConversationalAgent:
    """
    Start a new conversation.
    Returns an agent instance that maintains state.
    """
    return ConversationalAgent()


if __name__ == "__main__":
    # Test conversational flow
    agent = ConversationalAgent()
    
    # First message
    print("\n" + "█"*70)
    print(" TEST CONVERSATION")
    print("█"*70)
    
    result1 = agent.chat("I'm struggling to afford food and healthcare. I make about $2,000/month.")
    
    print("\n\n" + "="*70)
    print(" COMPASS NYC RESPONSE")
    print("="*70)
    print(result1["answer"])
    print("="*70)
    
    # Follow-up message (has context!)
    result2 = agent.chat("What documents do I need to bring for SNAP?")
    
    print("\n\n" + "="*70)
    print(" COMPASS NYC RESPONSE (Follow-up)")
    print("="*70)
    print(result2["answer"])
    print("="*70)