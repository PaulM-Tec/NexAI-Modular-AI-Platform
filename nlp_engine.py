# nlp_engine.py
 
import warnings
import logging
import os
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
 
warnings.filterwarnings("ignore")
logging.getLogger("transformers").setLevel(logging.ERROR)
 
os.environ["TOKENIZERS_PARALLELISM"] = "false"
 
# ---------------------------
# INTENT DETECTION
# ---------------------------
def detect_intent(text: str) -> str:
    t = text.lower()
    if "hello" in t or "hi" in t or "hey" in t:
        return "GREETING"
    if "book" in t and "service" in t:
        return "BOOK_SERVICE"
    if "cancel" in t and "service" in t:
        return "CANCEL_SERVICE"
    if "reschedule" in t and "service" in t:
        return "RESCHEDULE_SERVICE"
    return "FALLBACK"
 
 
# ---------------------------
# ENTITY EXTRACTION
# ---------------------------
def extract_entities(text: str):
    t = text.lower()
 
    date_match = re.search(r"\b(tomorrow|today|\d{4}-\d{2}-\d{2})\b", t)
    time_match = re.search(r"\b(\d{1,2}(:\d{2})?\s?(am|pm)?)\b", t)
 
    return {
        "date": date_match.group(0) if date_match else None,
        "time": time_match.group(0) if time_match else None,
    }
 
 
# ---------------------------
# MAIN RESPONSE LOGIC (STABLE)
# ---------------------------
def get_response(user_input: str, max_tokens: int = 80) -> str:
    if not user_input.strip():
        return "Please provide a message."
 
    intent = detect_intent(user_input)
    entities = extract_entities(user_input)
 
    if intent == "GREETING":
        return "Hi! How can I help with your vehicle service today?"
 
    if intent == "BOOK_SERVICE":
        if not entities["date"] or not entities["time"]:
            return "Sure - what date and time would you like the service?"
        return f"Great - booking a service on {entities['date']} at {entities['time']}. Please confirm."
 
    if intent == "CANCEL_SERVICE":
        return "Okay, please provide the booking details to cancel."
 
    if intent == "RESCHEDULE_SERVICE":
        return "Sure, what new date and time would you like to reschedule to?"
 
    # fallback response (no transformers risk)
    return "I'm here to help with bookings, services, or scheduling. What would you like to do?"
 
 
# ---------------------------
# TF-IDF embeddings (UNCHANGED)
# ---------------------------
def vectorize_texts(texts, normalize: bool = True, max_features: int = 1024):
    if not isinstance(texts, list) or len(texts) == 0:
        raise ValueError("texts must be a non-empty list")
 
    vec = TfidfVectorizer(max_features=max_features)
    X = vec.fit_transform(texts).toarray()
 
    if normalize:
        norms = np.linalg.norm(X, axis=1, keepdims=True) + 1e-12
        X = X / norms
 
    return X