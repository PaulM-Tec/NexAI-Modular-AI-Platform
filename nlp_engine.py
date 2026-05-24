# nlp_engine.py
 
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
 
# =========================================================
# 1. INTENT TRAINING DATA (SEMANTIC FOUNDATION)
# =========================================================
intent_data = [
    # BOOKING
    ("book a service", "BOOK_SERVICE"),
    ("schedule my car", "BOOK_SERVICE"),
    ("car needs service", "BOOK_SERVICE"),
    ("fix my brakes", "BOOK_SERVICE"),
    ("repair my vehicle", "BOOK_SERVICE"),
 
    # GREETING
    ("hello", "GREETING"),
    ("hi", "GREETING"),
    ("hey", "GREETING"),
 
    # SMALL TALK
    ("how are you", "SMALL_TALK"),
 
    # IT SUPPORT
    ("email not working", "IT_SUPPORT"),
    ("fix my email", "IT_SUPPORT"),
    ("outlook not opening", "IT_SUPPORT"),
    ("password not working", "IT_SUPPORT"),
    ("cannot login", "IT_SUPPORT"),
 
    # KNOWLEDGE
    ("what is engine", "KNOWLEDGE"),
    ("why does a car overheat", "KNOWLEDGE"),
    ("what are brakes", "KNOWLEDGE"),
    ("what is oil", "KNOWLEDGE"),
]
 
intent_texts = [i[0] for i in intent_data]
intent_labels = [i[1] for i in intent_data]
 
 
# =========================================================
# 2. KNOWLEDGE BASE (DYNAMIC RETRIEVAL)
# =========================================================
knowledge_data = [
    ("what is an engine", "An engine converts fuel into mechanical energy to move a vehicle."),
    ("why does a car overheat", "A car may overheat due to low coolant, radiator issues, or thermostat failure."),
    ("what are brakes", "Brakes slow down a vehicle using friction between brake pads and discs."),
    ("what is engine oil", "Engine oil lubricates moving parts and reduces wear and overheating."),
    ("why is my battery dead", "A dead battery can be caused by leaving lights on or a faulty alternator."),
    ("how to fix a puncture", "A puncture can be fixed using a patch or by replacing the tyre."),
]
 
knowledge_questions = [k[0] for k in knowledge_data]
knowledge_answers = [k[1] for k in knowledge_data]
 
 
# =========================================================
# 3. VECTOR SPACE (SHARED FOR INTENT + KNOWLEDGE)
# =========================================================
vectorizer = TfidfVectorizer()
 
# Combine text for better vocabulary coverage
combined_corpus = intent_texts + knowledge_questions
 
vectorizer.fit(combined_corpus)
 
# Vector representations
intent_vectors = vectorizer.transform(intent_texts)
knowledge_vectors = vectorizer.transform(knowledge_questions)
 
 
# =========================================================
# 4. SEMANTIC INTENT DETECTION
# =========================================================
def detect_intent(text: str) -> str:
    input_vec = vectorizer.transform([text])
    similarities = cosine_similarity(input_vec, intent_vectors)
 
    best_index = similarities.argmax()
    confidence = similarities[0][best_index]
 
    if confidence < 0.3:
        return "FALLBACK"
 
    return intent_labels[best_index]
 
 
# =========================================================
# 5. KNOWLEDGE SEARCH (DYNAMIC AI)
# =========================================================
def search_knowledge(text: str):
    input_vec = vectorizer.transform([text])
    similarities = cosine_similarity(input_vec, knowledge_vectors)
 
    best_index = similarities.argmax()
    confidence = similarities[0][best_index]
 
    if confidence < 0.3:
        return None
 
    return knowledge_answers[best_index]
 
 
# =========================================================
# 6. ENTITY EXTRACTION (FOR BOOKINGS)
# =========================================================
def extract_entities(text: str):
    t = text.lower()
 
    date_match = re.search(r"\b(tomorrow|today|\d{4}-\d{2}-\d{2})\b", t)
    time_match = re.search(r"\b(\d{1,2}(:\d{2})?\s?(am|pm)?)\b", t)
 
    return {
        "date": date_match.group(0) if date_match else None,
        "time": time_match.group(0) if time_match else None,
    }
 
 
# =========================================================
# 7. MAIN RESPONSE ENGINE (HYBRID AI CORE)
# =========================================================
def get_response(user_input: str) -> str:
 
    if not user_input.strip():
        return "Please provide a message."
 
    intent = detect_intent(user_input)
    entities = extract_entities(user_input)
 
    # -------------------------
    # HUMAN CONVERSATION
    # -------------------------
    if intent == "GREETING":
        return "Hi! How can I assist you today?"
 
    if intent == "SMALL_TALK":
        return "I'm doing well, thanks! How can I help?"
 
    # -------------------------
    # BOOKING (handled by app.py)
    # -------------------------
    if intent == "BOOK_SERVICE":
        if not entities["date"] or not entities["time"]:
            return "Sure - what date and time would you like the service?"
        return f"Great - booking for {entities['date']} at {entities['time']}. Please confirm."
 
    # -------------------------
    # IT SUPPORT
    # -------------------------
    if intent == "IT_SUPPORT":
        if "email" in user_input.lower():
            return "Try restarting your email client or checking your internet connection."
        if "password" in user_input.lower():
            return "You can reset your password using your organisation's portal."
        return "Please provide more details about the issue."
 
    # -------------------------
    # KNOWLEDGE (DYNAMIC SEARCH)
    # -------------------------
    if intent == "KNOWLEDGE":
        result = search_knowledge(user_input)
 
        if result:
            return result
 
        return "I could not find a precise answer, but I am continuously learning."
 
    # -------------------------
    # GLOBAL FALLBACK
    # -------------------------
    result = search_knowledge(user_input)
 
    if result:
        return result
 
    return f"I understand your request: '{user_input}'. I am continuously learning to assist better."