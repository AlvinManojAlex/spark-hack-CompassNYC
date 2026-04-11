"""
Compass NYC — LLM Interface
────────────────────────────────────────────────────────────
Handles all LLM calls to Ollama.
Builds prompts and manages generation.
"""

import requests
import time
from typing import Dict, List, Optional
from config import OLLAMA_URL, OLLAMA_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, BENEFITS
from benchmark import Benchmark

class LLMInterface:
    """
    Wrapper for Ollama API calls with prompt engineering.
    """
    
    def __init__(self, model: str = OLLAMA_MODEL):
        self.model = model
        self.url = OLLAMA_URL
        print(f"[LLM] Initialized with model: {self.model}")
    
    def generate(
            self,
            prompt: str,
            temperature: float = LLM_TEMPERATURE,
            max_tokens: int = LLM_MAX_TOKENS,
            stream: bool = False,
            benchmark=None,
        ) -> str:
        """
        Call Ollama to generate a response.
        """
        print(f"[LLM] Generating with {self.model}...")

        if benchmark:
            benchmark.start("llm_api_call")

        start_time = time.time()
        full_response = ""  # Ensure it's always defined

        try:
            response = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": stream,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
                stream=stream,
                timeout=300,
            )
            response.raise_for_status()

            if stream:
                import json

                print()  # New line before streaming output

                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                token = chunk["response"]
                                full_response += token
                                print(token, end="", flush=True)
                        except json.JSONDecodeError:
                            continue

                print()  # New line after streaming

            else:
                result = response.json()
                full_response = result.get("response", "")

            # ---- Timing & Metrics (NOW ALWAYS RUNS) ----
            latency = time.time() - start_time

            input_chars = len(prompt)
            output_chars = len(full_response)

            # Rough token estimate
            input_tokens = input_chars / 4
            output_tokens = output_chars / 4

            if benchmark:
                benchmark.stop("llm_api_call")
                benchmark.log("llm_latency", latency)
                benchmark.log("input_tokens", int(input_tokens))
                benchmark.log("output_tokens", int(output_tokens))
                benchmark.log(
                    "tokens_per_sec",
                    output_tokens / latency if latency > 0 else 0,
                )

            print(f"[LLM] Generated {output_chars} characters in {latency:.2f}s")

            return full_response

        except requests.RequestException as e:
            print(f"[LLM ERROR] {e}")
            return ""
    
    def build_eligibility_prompt(self, 
                                 benefit_type: str,
                                 user_query: str,
                                 eligibility_context: str,
                                 location_context: str) -> str:
        """
        Build a prompt for eligibility reasoning.
        
        This is the core prompt engineering - make it clear and structured.
        """
        benefit_name = BENEFITS[benefit_type]["name"]
        
        prompt = f"""You are Compass NYC, a helpful AI assistant that guides New Yorkers to social services.

Your job is to help someone understand if they qualify for {benefit_name} and where to apply.

INSTRUCTIONS:
1. Based on the ELIGIBILITY RULES below, determine if the user likely qualifies
2. Explain WHY in plain language, referencing their specific situation
3. If they qualify:
   - Tell them what documents to bring
   - Point them to the nearest office from the list below
   - Give clear next steps
4. If they don't qualify or you're unsure:
   - Explain what's missing or unclear
   - Suggest what they'd need to qualify OR point them to another service
5. Be warm, specific, and honest - never guess about rules not in the context

──────────────────────────────────────────────────────────────────────
ELIGIBILITY RULES FOR {benefit_name.upper()}:
──────────────────────────────────────────────────────────────────────
{eligibility_context}

──────────────────────────────────────────────────────────────────────
SERVICE LOCATIONS:
──────────────────────────────────────────────────────────────────────
{location_context}

──────────────────────────────────────────────────────────────────────
USER'S SITUATION:
──────────────────────────────────────────────────────────────────────
{user_query}

YOUR RESPONSE:"""

        return prompt
    
    def build_multi_benefit_prompt(self,
                                  user_query: str,
                                  benefit_contexts: Dict[str, Dict[str, str]]) -> str:
        """
        Build a prompt when checking multiple benefits at once.
        
        Args:
            user_query: User's question
            benefit_contexts: Dict mapping benefit_type to dict with keys:
                - 'eligibility': eligibility context text
                - 'locations': location context text
        """
        # Build sections for each benefit
        sections = []
        for benefit_type, contexts in benefit_contexts.items():
            benefit_name = BENEFITS[benefit_type]["name"]
            sections.append(f"""
═══════════════════════════════════════════════════════════════
{benefit_name.upper()}
═══════════════════════════════════════════════════════════════

ELIGIBILITY RULES:
{contexts['eligibility']}

LOCATIONS:
{contexts['locations']}
""")
        
        all_benefits = ", ".join([BENEFITS[bt]["name"] for bt in benefit_contexts.keys()])
        
        prompt = f"""You are Compass NYC, a helpful AI assistant that guides New Yorkers to social services.

The user is asking about their eligibility for multiple programs. You have information about: {all_benefits}.

INSTRUCTIONS:
1. For EACH program, determine if the user likely qualifies based on the rules provided
2. Explain eligibility for each program separately and clearly
3. Prioritize the programs that are the best fit for their situation
4. Point them to specific offices and tell them what documents to bring
5. Be warm, specific, and organized - use clear headings for each program

{"".join(sections)}

──────────────────────────────────────────────────────────────────────
USER'S SITUATION:
──────────────────────────────────────────────────────────────────────
{user_query}

YOUR RESPONSE (organize by program):"""

        return prompt
    
    def answer_eligibility_query(self,
                                benefit_type: str,
                                user_query: str,
                                eligibility_context: str,
                                location_context: str,
                                benchmark = None) -> str:
        """
        Convenience method: build prompt + generate answer for single benefit.
        """
        prompt = self.build_eligibility_prompt(
            benefit_type, user_query, eligibility_context, location_context
        )

        if benchmark:
            benchmark.log("prompt_length_chars", len(prompt))

        return self.generate(prompt, benchmark = benchmark)
    
    def answer_multi_benefit_query(self,
                                   user_query: str,
                                   benefit_contexts: Dict[str, Dict[str, str]],
                                   benchmark = None) -> str:
        """
        Convenience method: build prompt + generate answer for multiple benefits.
        """
        prompt = self.build_multi_benefit_prompt(user_query, benefit_contexts)

        if benchmark:
            benchmark.log("prompt_length_chars", len(prompt))

        return self.generate(prompt, benchmark = benchmark)


if __name__ == "__main__":
    # Test prompt building (won't actually call LLM unless Ollama is running)
    llm = LLMInterface()
    
    test_query = "I make $2,200/month with 2 kids in Brooklyn, do I qualify for SNAP?"
    test_eligibility = "Example eligibility rule text here..."
    test_locations = "Example location list here..."
    
    prompt = llm.build_eligibility_prompt(
        "snap", test_query, test_eligibility, test_locations
    )
    
    print("\n" + "="*70)
    print(" GENERATED PROMPT")
    print("="*70)
    print(prompt)
    print("="*70)