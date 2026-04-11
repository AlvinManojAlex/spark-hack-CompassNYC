"""
Compass NYC — FastAPI Backend
────────────────────────────────────────────────────────────
Full-featured conversational API with:
- Multi-benefit auto-detection
- Streaming responses
- Conversation management
- New chat support

Run with: uvicorn api:app --host 0.0.0.0 --port 8000 --reload
"""

import sys
import os

# ── Make sure Python can find your project modules ────────────────────────────
PROJECT_DIR = os.path.expanduser("~/Documents/test")
sys.path.insert(0, PROJECT_DIR)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import json
import uuid

from config import BENEFITS, OLLAMA_URL, OLLAMA_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS
from conversational_agent import ConversationalAgent

# ── APP SETUP ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Compass NYC API",
    description="Local AI for NYC social services navigation",
    version="2.0.0"
)

# Allow the React frontend to call this API (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Fine for hackathon
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active conversations (in production, use Redis or DB)
conversations: Dict[str, ConversationalAgent] = {}

@app.on_event("startup")
async def startup_event():
    print("[API] Compass NYC FastAPI backend ready")
    print(f"[API] Available benefits: {len(BENEFITS)}")


# ── REQUEST/RESPONSE MODELS ───────────────────────────────────────────────────

class NewConversationResponse(BaseModel):
    conversation_id: str
    message: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    benefit_types: Optional[List[str]] = None  # Optional: auto-detect if None


class ChatResponse(BaseModel):
    answer: str
    locations_by_benefit: Dict[str, List[dict]]
    benefit_types: List[str]
    conversation_id: str
    detected_borough: Optional[str] = None


class BenefitInfo(BaseModel):
    id: str
    name: str
    category: str
    color: str
    description: str


class ConversationHistory(BaseModel):
    history: List[Dict[str, str]]


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "status": "Compass NYC API is running",
        "version": "2.0.0",
        "endpoints": {
            "new_conversation": "POST /api/conversations/new",
            "chat": "POST /api/chat",
            "chat_stream": "POST /api/chat/stream",
            "benefits": "GET /api/benefits",
            "health": "GET /api/health"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model": OLLAMA_MODEL,
        "benefits_count": len(BENEFITS),
        "active_conversations": len(conversations)
    }


@app.get("/api/benefits", response_model=List[BenefitInfo])
async def get_benefits():
    """Return list of available benefit programs."""
    return [
        BenefitInfo(
            id=key,
            name=cfg["name"],
            category=cfg["category"],
            color=cfg["color"],
            description=cfg["description"]
        )
        for key, cfg in BENEFITS.items()
    ]


@app.post("/api/conversations/new", response_model=NewConversationResponse)
async def new_conversation():
    """
    Start a new conversation.
    Returns a conversation_id to use in subsequent chat requests.
    """
    conversation_id = str(uuid.uuid4())
    agent = ConversationalAgent()
    conversations[conversation_id] = agent
    
    return NewConversationResponse(
        conversation_id=conversation_id,
        message="New conversation started"
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Non-streaming chat endpoint.
    Processes message and returns complete response.
    """
    # Get or create conversation
    if request.conversation_id and request.conversation_id in conversations:
        agent = conversations[request.conversation_id]
        conversation_id = request.conversation_id
    else:
        # Auto-create conversation if not provided
        conversation_id = str(uuid.uuid4())
        agent = ConversationalAgent()
        conversations[conversation_id] = agent
    
    if not request.message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    try:
        # Process message with agent
        result = agent.chat(request.message, benefit_types=request.benefit_types)
        
        return ChatResponse(
            answer=result["answer"],
            locations_by_benefit=result["locations_by_benefit"],
            benefit_types=result["benefit_types"],
            conversation_id=conversation_id,
            detected_borough=result.get("detected_borough")
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint (Server-Sent Events).
    Sends tokens as they're generated for real-time display.
    
    Events:
    - benefit_detected: {"type": "benefit_detected", "benefit_types": [...]}
    - locations: {"type": "locations", "locations_by_benefit": {...}}
    - token: {"type": "token", "token": "word"}
    - done: {"type": "done", "answer": "full text", "conversation_id": "..."}
    - error: {"type": "error", "error": "message"}
    """
    # Get or create conversation
    if request.conversation_id and request.conversation_id in conversations:
        agent = conversations[request.conversation_id]
        conversation_id = request.conversation_id
    else:
        # Auto-create conversation
        conversation_id = str(uuid.uuid4())
        agent = ConversationalAgent()
        conversations[conversation_id] = agent
    
    if not request.message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    async def generate():
        """Generate streaming response."""
        import requests as req
        
        try:
            # Step 1: Detect benefits
            if request.benefit_types is None:
                detected_benefits = agent.detect_relevant_benefits(request.message)
            else:
                detected_benefits = request.benefit_types
            
            yield f"data: {json.dumps({'type': 'benefit_detected', 'benefit_types': detected_benefits})}\n\n"
            
            # Step 2: Gather context and locations
            benefit_contexts = {}
            all_locations = {}
            detected_borough = None
            
            for benefit_type in detected_benefits:
                if benefit_type not in BENEFITS:
                    continue
                
                # Eligibility
                eligibility_chunks = agent.eligibility_engine.retrieve(benefit_type, request.message, top_k=3)
                eligibility_context = agent.eligibility_engine.format_for_prompt(eligibility_chunks)
                
                # Locations
                borough = agent.location_manager.detect_borough(request.message)
                if borough:
                    detected_borough = borough
                locations = agent.location_manager.get_locations(benefit_type, borough)
                location_context = agent.location_manager.format_for_prompt(locations, max_locations=5)
                
                benefit_contexts[benefit_type] = {
                    'eligibility': eligibility_context,
                    'locations': location_context
                }
                all_locations[benefit_type] = locations
            
            # Send locations
            yield f"data: {json.dumps({'type': 'locations', 'locations_by_benefit': all_locations, 'detected_borough': detected_borough})}\n\n"
            
            # Step 3: Build prompt
            agent.history.append({"role": "user", "content": request.message})
            prompt = agent._build_conversational_prompt(request.message, benefit_contexts, detected_benefits)
            
            # Step 4: Stream LLM response
            full_response = ""
            
            response = req.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": LLM_TEMPERATURE,
                        "num_predict": LLM_MAX_TOKENS,
                    }
                },
                stream=True,
                timeout=300
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        if "response" in chunk:
                            token = chunk["response"]
                            full_response += token
                            yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
                        
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
            
            # Step 5: Save to history and send done event
            agent.history.append({"role": "assistant", "content": full_response})
            
            yield f"data: {json.dumps({'type': 'done', 'answer': full_response, 'conversation_id': conversation_id})}\n\n"
        
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete/reset a conversation (clear history).
    """
    if conversation_id in conversations:
        conversations[conversation_id].reset_conversation()
        return {"status": "reset"}
    
    raise HTTPException(status_code=404, detail="Conversation not found")


@app.get("/api/conversations/{conversation_id}/history", response_model=ConversationHistory)
async def get_history(conversation_id: str):
    """
    Get conversation history.
    """
    if conversation_id in conversations:
        history = conversations[conversation_id].get_history()
        return ConversationHistory(history=history)
    
    raise HTTPException(status_code=404, detail="Conversation not found")


# ── LEGACY ENDPOINTS (for backwards compatibility) ────────────────────────────

class QueryRequest(BaseModel):
    query: str
    benefit_type: str = "snap"


class QueryResponse(BaseModel):
    answer: str
    locations: List[dict]
    benefit_type: str
    benefit_name: str


@app.post("/query", response_model=QueryResponse)
async def run_query(request: QueryRequest):
    """
    Legacy endpoint for single-benefit queries.
    Maintained for backwards compatibility.
    """
    if request.benefit_type not in BENEFITS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown benefit type: {request.benefit_type}. Available: {list(BENEFITS.keys())}"
        )
    
    try:
        # Create temporary agent for this query
        agent = ConversationalAgent()
        result = agent.chat(request.query, benefit_types=[request.benefit_type])
        
        return QueryResponse(
            answer=result["answer"],
            locations=result["locations_by_benefit"].get(request.benefit_type, []),
            benefit_type=request.benefit_type,
            benefit_name=BENEFITS[request.benefit_type]["name"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/benefits", response_model=List[BenefitInfo])
async def get_benefits_legacy():
    """Legacy benefits endpoint (without /api prefix)."""
    return await get_benefits()


# ── RUN ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print(" COMPASS NYC — FastAPI Backend")
    print("="*70)
    print(f" Model: {OLLAMA_MODEL}")
    print(f" Benefits: {len(BENEFITS)}")
    print("="*70)
    print(" Endpoints:")
    print("   POST   /api/conversations/new    - Start new conversation")
    print("   POST   /api/chat                 - Non-streaming chat")
    print("   POST   /api/chat/stream          - Streaming chat (SSE)")
    print("   GET    /api/benefits             - List all benefits")
    print("   DELETE /api/conversations/{id}   - Reset conversation")
    print("   GET    /api/conversations/{id}/history - Get chat history")
    print("   GET    /api/health               - Health check")
    print("="*70)
    print(" Legacy:")
    print("   POST   /query                    - Single-benefit query")
    print("   GET    /benefits                 - List benefits")
    print("="*70 + "\n")
    
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)



# """
# Compass NYC — FastAPI Backend
# ────────────────────────────────────────────────────────────
# Thin HTTP wrapper around the existing CompassNYC pipeline.
# Run with: uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# The React frontend talks to this.
# """

# import sys
# import os

# # ── Make sure Python can find your project modules ────────────────────────────
# # Update this path to wherever your compass_nyc project lives
# PROJECT_DIR = os.path.expanduser("~/Documents/test")
# sys.path.insert(0, PROJECT_DIR)

# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import StreamingResponse
# from pydantic import BaseModel
# from typing import Optional, List
# import json
# import asyncio

# from config import BENEFITS
# from main import CompassNYC

# # ── APP SETUP ─────────────────────────────────────────────────────────────────

# app = FastAPI(
#     title="Compass NYC API",
#     description="Local AI for NYC social services navigation",
#     version="1.0.0"
# )

# # Allow the React frontend to call this API (CORS)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Fine for hackathon
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Initialize the pipeline once at startup (not per-request)
# compass = None

# @app.on_event("startup")
# async def startup_event():
#     global compass
#     print("[API] Initializing Compass NYC pipeline...")
#     compass = CompassNYC()
#     print("[API] Ready.")


# # ── REQUEST/RESPONSE MODELS ───────────────────────────────────────────────────

# class QueryRequest(BaseModel):
#     query: str
#     benefit_type: str = "snap"


# class Location(BaseModel):
#     name: str
#     address: str
#     borough: str
#     zip: str
#     phone: str
#     hours: str
#     walk_in: str
#     languages: str
#     latitude: Optional[float] = None
#     longitude: Optional[float] = None


# class QueryResponse(BaseModel):
#     answer: str
#     locations: List[dict]
#     benefit_type: str
#     benefit_name: str


# class BenefitInfo(BaseModel):
#     key: str
#     name: str
#     category: str
#     color: str
#     description: str


# # ── ENDPOINTS ─────────────────────────────────────────────────────────────────

# @app.get("/")
# async def root():
#     return {"status": "Compass NYC API is running"}


# @app.get("/benefits", response_model=List[BenefitInfo])
# async def get_benefits():
#     """Return list of available benefit programs."""
#     return [
#         BenefitInfo(
#             key=key,
#             name=cfg["name"],
#             category=cfg["category"],
#             color=cfg["color"],
#             description=cfg["description"]
#         )
#         for key, cfg in BENEFITS.items()
#     ]


# @app.post("/query", response_model=QueryResponse)
# async def run_query(request: QueryRequest):
#     """
#     Main endpoint: process a user query and return answer + locations.
#     """
#     if compass is None:
#         raise HTTPException(status_code=503, detail="Pipeline not initialized")

#     if request.benefit_type not in BENEFITS:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Unknown benefit type: {request.benefit_type}. Available: {list(BENEFITS.keys())}"
#         )

#     try:
#         result = compass.query(request.query, request.benefit_type)
#         return QueryResponse(
#             answer=result["answer"],
#             locations=result["locations"],
#             benefit_type=result["benefit_type"],
#             benefit_name=result["benefit_name"]
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @app.post("/query/stream")
# async def run_query_stream(request: QueryRequest):
#     """
#     Streaming endpoint: sends tokens as they're generated.
#     The frontend can display them word-by-word for a better UX.
#     """
#     if compass is None:
#         raise HTTPException(status_code=503, detail="Pipeline not initialized")

#     async def generate():
#         # First: retrieve eligibility + locations (fast, non-LLM steps)
#         from eligibility_engine import EligibilityEngine
#         from location_manager import LocationManager
#         from llm_interface import LLMInterface
#         import requests as req

#         engine = EligibilityEngine()
#         loc_manager = LocationManager()

#         eligibility_chunks = engine.retrieve(request.benefit_type, request.query)
#         eligibility_context = engine.format_for_prompt(eligibility_chunks)

#         borough = loc_manager.detect_borough(request.query)
#         locations = loc_manager.get_locations(request.benefit_type, borough)
#         location_context = loc_manager.format_for_prompt(locations)

#         # Send locations immediately (before LLM starts)
#         yield f"data: {json.dumps({'type': 'locations', 'locations': locations})}\n\n"

#         # Build prompt
#         llm = LLMInterface()
#         prompt = llm.build_eligibility_prompt(
#             request.benefit_type,
#             request.query,
#             eligibility_context,
#             location_context
#         )

#         # Stream from Ollama
#         from config import OLLAMA_URL, OLLAMA_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS

#         response = req.post(
#             OLLAMA_URL,
#             json={
#                 "model": OLLAMA_MODEL,
#                 "prompt": prompt,
#                 "stream": True,
#                 "options": {
#                     "temperature": LLM_TEMPERATURE,
#                     "num_predict": LLM_MAX_TOKENS,
#                 }
#             },
#             stream=True,
#             timeout=300
#         )

#         for line in response.iter_lines():
#             if line:
#                 try:
#                     chunk = json.loads(line)
#                     if "response" in chunk:
#                         token = chunk["response"]
#                         yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
#                     if chunk.get("done"):
#                         yield f"data: {json.dumps({'type': 'done'})}\n\n"
#                         break
#                 except json.JSONDecodeError:
#                     continue

#     return StreamingResponse(
#         generate(),
#         media_type="text/event-stream",
#         headers={
#             "Cache-Control": "no-cache",
#             "X-Accel-Buffering": "no"
#         }
#     )


# # ── RUN ───────────────────────────────────────────────────────────────────────

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
