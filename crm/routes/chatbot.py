"""
Alessia chatbot module for aLEXy legal intake.
Replicates the Alessia behavior from the standalone chatbot service.
"""
import json
import random
from flask import Blueprint, request, jsonify

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/chatbot')

# Alessia response templates
GREETINGS = [
    "Hello! Welcome to LexFlow, I'm Alessia, your legal intake assistant. I'm here to help you organize your thoughts and get started on finding the right help for your legal issue. Can you tell me, in a few words, what's been going on that's led you to reach out for legal assistance?",
    "Hi there! I'm Alessia from LexFlow. What legal matter can I help you with today?",
    "Welcome! I'm Alessia, your legal intake assistant. How can I help you today?"
]

INTAKE_PROMPTS = {
    "contract": "Welcome to LexFlow. We're here to help organize your legal intake and get you connected with the right resources. To better understand your situation, can you tell me what happened with the contract that's causing the dispute?",
    "employment": "I understand you're reaching out about an employment matter. Can you tell me more about what happened with your employer? This helps us connect you with the right legal resources.",
    "family": "I'm here to help with your family legal matter. Can you share a bit more about your situation so we can find you the right assistance?",
    "criminal": "Thank you for reaching out. For criminal matters, it's important we understand the situation clearly. Can you tell me what happened?",
    "real_estate": "I understand you have a real estate matter. Can you share more details about the property issue you're facing?",
    "debt": "I'm here to help with your debt collection matter. Can you tell me more about the debt you're dealing with?",
    "default": "Thank you for reaching out to LexFlow. To help you better, can you tell me a bit more about your legal situation? The more details you share, the better we can connect you with the right resources."
}


@chatbot_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"ok": True})


@chatbot_bp.route('/chat', methods=['POST'])
def chat():
    """
    Chat endpoint that replicates Alessia's behavior.
    Accepts: {"message": "...", "user_id": "..."}
    Returns: {"reply": "..."}
    """
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "Missing 'message' field"}), 400
    
    message = data['message'].lower()
    user_id = data.get('user_id', 'anonymous')
    
    # Determine intent category from message keywords
    category = "default"
    keywords = [
        ("contract", ["contract", "agreement", "breach", "terms", "clause"]),
        ("employment", ["employment", "job", "work", "employer", "layoff", "fired", "hr"]),
        ("family", ["family", "divorce", "custody", "child", "marriage", "separation"]),
        ("criminal", ["criminal", "arrest", "charge", "court", "police", "bail"]),
        ("real_estate", ["real estate", "property", "landlord", "tenant", "mortgage", "rent", "home"]),
        ("debt", ["debt", "collection", "loan", "bankruptcy", "creditor", "default"])
    ]
    
    for cat, words in keywords:
        for word in words:
            if word in message:
                category = cat
                break
    
    # Select response based on category
    if "hello" in message or "hi" in message or "hey" in message:
        reply = random.choice(GREETINGS)
    elif category == "default":
        reply = random.choice(list(INTAKE_PROMPTS.values()))
    else:
        reply = random.choice(INTAKE_PROMPTS.get(category, [INTAKE_PROMPTS["default"]]))
    
    return jsonify({"reply": reply})
