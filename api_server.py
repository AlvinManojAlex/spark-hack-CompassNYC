"""
Compass NYC — API Server
────────────────────────────────────────────────────────────
Flask API for frontend integration.
Supports streaming responses and multi-benefit queries.
"""

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import json
import requests
from typing import Generator

from conversational_agent import ConversationalAgent
from config import OLLAMA_URL, OLLAMA_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, BENEFITS

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Store active conversations (in production, use Redis or DB)
conversations = {}


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Non-streaming chat endpoint.
    
    Request body:
    {
        "message": "I need help with food and healthcare",
        "conversation_id": "optional-uuid",
        "benefit_types": ["snap", "medicaid"]  // optional, auto-detected if missing
    }
    
    Response:
    {
        "answer": "Here's how I can help...",
        "locations_by_benefit": {
            "snap": [...],
            "medicaid": [...]
        },
        "benefit_types": ["snap", "medicaid"],
        "conversation_id": "uuid",
        "detected_borough": "brooklyn"
    }
    """
    data = request.json
    message = data.get('message', '')
    conversation_id = data.get('conversation_id')
    benefit_types = data.get('benefit_types')  # None = auto-detect
    
    if not message:
        return jsonify({"error": "Message is required"}), 400
    
    # Get or create conversation
    if conversation_id and conversation_id in conversations:
        agent = conversations[conversation_id]
    else:
        agent = ConversationalAgent()
        conversation_id = str(len(conversations))  # Simple ID generation
        conversations[conversation_id] = agent
    
    # Process message
    result = agent.chat(message, benefit_types=benefit_types)
    result['conversation_id'] = conversation_id
    
    return jsonify(result)


@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """
    Streaming chat endpoint (Server-Sent Events).
    
    Request body: Same as /api/chat
    
    Response: Stream of Server-Sent Events
    
    Event types:
    - benefit_detected: {"benefit_types": ["snap", "medicaid"]}
    - locations: {"locations_by_benefit": {...}}
    - token: {"token": "word"}
    - done: {"answer": "full response", "conversation_id": "uuid"}
    """
    data = request.json
    message = data.get('message', '')
    conversation_id = data.get('conversation_id')
    benefit_types = data.get('benefit_types')
    
    if not message:
        return jsonify({"error": "Message is required"}), 400
    
    # Get or create conversation
    if conversation_id and conversation_id in conversations:
        agent = conversations[conversation_id]
    else:
        agent = ConversationalAgent()
        conversation_id = str(len(conversations))
        conversations[conversation_id] = agent
    
    def generate() -> Generator[str, None, None]:
        """Generate streaming response."""
        
        # Step 1: Detect benefits
        if benefit_types is None:
            detected_benefits = agent.detect_relevant_benefits(message)
        else:
            detected_benefits = benefit_types
        
        yield f"data: {json.dumps({'type': 'benefit_detected', 'benefit_types': detected_benefits})}\n\n"
        
        # Step 2: Gather context and locations
        benefit_contexts = {}
        all_locations = {}
        
        for benefit_type in detected_benefits:
            if benefit_type not in BENEFITS:
                continue
            
            # Eligibility
            eligibility_chunks = agent.eligibility_engine.retrieve(benefit_type, message, top_k=3)
            eligibility_context = agent.eligibility_engine.format_for_prompt(eligibility_chunks)
            
            # Locations
            borough = agent.location_manager.detect_borough(message)
            locations = agent.location_manager.get_locations(benefit_type, borough)
            location_context = agent.location_manager.format_for_prompt(locations, max_locations=5)
            
            benefit_contexts[benefit_type] = {
                'eligibility': eligibility_context,
                'locations': location_context
            }
            all_locations[benefit_type] = locations
        
        # Send locations
        yield f"data: {json.dumps({'type': 'locations', 'locations_by_benefit': all_locations, 'detected_borough': borough})}\n\n"
        
        # Step 3: Build prompt
        agent.history.append({"role": "user", "content": message})
        prompt = agent._build_conversational_prompt(message, benefit_contexts, detected_benefits)
        
        # Step 4: Stream LLM response
        full_response = ""
        
        try:
            response = requests.post(
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
                    except json.JSONDecodeError:
                        continue
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            return
        
        # Step 5: Save to history and send done event
        agent.history.append({"role": "assistant", "content": full_response})
        
        yield f"data: {json.dumps({'type': 'done', 'answer': full_response, 'conversation_id': conversation_id})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/api/conversations/new', methods=['POST'])
def new_conversation():
    """
    Start a new conversation.
    
    Response:
    {
        "conversation_id": "uuid",
        "message": "New conversation started"
    }
    """
    agent = ConversationalAgent()
    conversation_id = str(len(conversations))
    conversations[conversation_id] = agent
    
    return jsonify({
        "conversation_id": conversation_id,
        "message": "New conversation started"
    })


@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def reset_conversation(conversation_id):
    """
    Reset a conversation (clear history).
    """
    if conversation_id in conversations:
        conversations[conversation_id].reset_conversation()
        return jsonify({"status": "reset"})
    return jsonify({"error": "Conversation not found"}), 404


@app.route('/api/conversations/<conversation_id>/history', methods=['GET'])
def get_history(conversation_id):
    """
    Get conversation history.
    """
    if conversation_id in conversations:
        history = conversations[conversation_id].get_history()
        return jsonify({"history": history})
    return jsonify({"error": "Conversation not found"}), 404


@app.route('/api/benefits', methods=['GET'])
def list_benefits():
    """
    List all available benefits.
    """
    benefits_list = [
        {
            "id": benefit_id,
            "name": config["name"],
            "category": config["category"],
            "color": config["color"],
            "description": config["description"]
        }
        for benefit_id, config in BENEFITS.items()
    ]
    return jsonify({"benefits": benefits_list})


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "model": OLLAMA_MODEL,
        "benefits_count": len(BENEFITS)
    })


if __name__ == '__main__':
    print("\n" + "="*70)
    print(" COMPASS NYC — API SERVER")
    print("="*70)
    print(f" Model: {OLLAMA_MODEL}")
    print(f" Benefits: {len(BENEFITS)}")
    print("="*70)
    print(" Endpoints:")
    print("   POST   /api/conversations/new  - Start new conversation")
    print("   POST   /api/chat              - Non-streaming chat")
    print("   POST   /api/chat/stream       - Streaming chat (SSE)")
    print("   GET    /api/benefits          - List all benefits")
    print("   GET    /api/health            - Health check")
    print("="*70 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)