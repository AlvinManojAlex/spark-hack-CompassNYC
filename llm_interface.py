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
    
    def generate(self, prompt: str, temperature: float = LLM_TEMPERATURE, 
                 max_tokens: int = LLM_MAX_TOKENS, stream: bool = False, benchmark = None) -> str:
        """
        Call Ollama to generate a response.
        
        Args:
            prompt: Full prompt text
            temperature: Lower = more factual, higher = more creative
            max_tokens: Max length of response
            stream: If True, print tokens as they generate (better UX for large models)
        
        Returns:
            Generated text
        """
        print(f"[LLM] Generating with {self.model}...")

        if benchmark:
            benchmark.start("llm_api_call")
        
        start_time = time.time()
        full_response = ""
        
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
                    }
                },
                stream=stream,  # Enable streaming in requests
                timeout=300  # 5 minutes for large models like Qwen 72B
            )
            response.raise_for_status()
            
            if stream:
                # Stream tokens as they arrive
                import json
                print()  # New line before streaming output
                
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                token = chunk["response"]
                                full_response += token
                                print(token, end="", flush=True)  # Print immediately
                        except json.JSONDecodeError:
                            continue
                
                print()  # New line after streaming
            else:
                # Non-streaming (original behavior)
                result = response.json()["response"]
                full_response = result["response"] if isinstance(result, dict) else result
            
            latency = time.time() - start_time

            # metrics
            input_chars = len(prompt)
            output_chars = len(full_response)

            # Rough token estimate (works fine for benchmarking)
            input_tokens = input_chars / 4
            output_tokens = output_chars / 4

            if benchmark:
                benchmark.stop("llm_api_call")
                benchmark.log("llm_latency", latency)
                benchmark.log("input_tokens", int(input_tokens))
                benchmark.log("output_tokens", int(output_tokens))
                benchmark.log("tokens_per_sec", output_tokens / latency if latency > 0 else 0)
        
            print(f"[LLM] Generated {output_chars} characters in {latency:.2f}s")

            return full_response
            
        except requests.exceptions.RequestException as e:
            if benchmark:
                benchmark.log("llm_error", str(e))
            print(f"[LLM] ERROR: {e}")
            return f"Error calling LLM: {e}"
    
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
        
        prompt = f"""You are Compass NYC, an AI assistant helping New Yorkers access social services.

Goal: Assess whether the user likely qualifies for {benefit_name} and guide them on next steps.

Instructions:
- Use ONLY the eligibility rules below.
- Determine if the user likely qualifies.
- Explain your reasoning clearly using their situation.

If they likely qualify:
- List required documents
- Recommend the nearest service location from the list
- Provide clear next steps

If they don’t or it’s unclear:
- Explain what’s missing or uncertain
- Suggest how they could qualify or alternative services

Style:
- Be warm, clear, and specific
- Do not assume rules not provided

--- ELIGIBILITY RULES ({benefit_name.upper()}) ---
{eligibility_context}

--- SERVICE LOCATIONS ---
{location_context}

--- USER SITUATION ---
{user_query}

Response:"""

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
        --- {benefit_name.upper()} ---

        ELIGIBILITY:
        {contexts['eligibility']}

        LOCATIONS:
        {contexts['locations']}
        """)

        all_benefits = ", ".join(BENEFITS[bt]["name"] for bt in benefit_contexts.keys())

        prompt = f"""You are Compass NYC, an assistant that helps New Yorkers understand social service eligibility and where to apply.

        The user may qualify for: {all_benefits}.

        TASK:
        For EACH program below:
        - Decide if the user likely qualifies using ONLY the provided eligibility rules
        - Explain briefly why/why not, based on their situation
        - If eligible: list required documents + nearest location + next steps
        - If not/unclear: explain what is missing or suggest alternatives

        PRIORITIZATION:
        - Rank programs by best fit for the user

        FORMAT:
        Use clear headings per program (one section per benefit). Be organized and easy to scan.

        PROGRAM DETAILS:
        {"".join(sections)}

        --- USER SITUATION ---
        {user_query}

        RESPONSE:"""

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