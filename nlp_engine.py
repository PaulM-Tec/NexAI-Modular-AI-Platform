# nlp_engine.py
 
from transformers import pipeline, set_seed
import warnings, logging, os, re
 
# --- NEW imports for TF-IDF embeddings (Step 2.1) ---
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
# ----------------------------------------------------
 
warnings.filterwarnings("ignore")
logging.getLogger("transformers").setLevel(logging.ERROR)
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
 
set_seed(42)
 
MODEL_NAME = "microsoft/DialoGPT-medium"
chatbot = pipeline(
    task="text-generation",
    model=MODEL_NAME,
    framework="pt",
    device=-1,
    return_full_text=False,
    clean_up_tokenization_spaces=True
)
 
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
 
def extract_entities(text: str):
    t = text.lower()
    date_match = re.search(r"\b(tomorrow|today|\d{4}-\d{2}-\d{2})\b", t)
    time_match = re.search(r"\b(\d{1,2}(:\d{2})?\s?(am|pm)?)\b", t)
    return {
        "date": date_match.group(0) if date_match else None,
        "time": time_match.group(0) if time_match else None
    }
 
def get_response(user_input: str, max_tokens: int = 80) -> str:
    if not user_input.strip():
        return "Please provide a message."
    intent = detect_intent(user_input)
    entities = extract_entities(user_input)
 
    if intent == "GREETING":
        return "Hi! How can I help with your vehicle service today?"
 
    if intent == "BOOK_SERVICE":
        if not entities["date"] or not entities["time"]:
            return "Sure—what date and time would you like the service?"
        return f"Great—booking a service on {entities['date']} at {entities['time']}. Please confirm."
 
    if intent == "CANCEL_SERVICE":
        return "Okay, please provide the booking ID or date/time to cancel."
 
    if intent == "RESCHEDULE_SERVICE":
        return "Sure, what new date and time would you like to reschedule to?"
 
    out = chatbot(
        user_input,
        max_new_tokens=max_tokens,
        do_sample=False,
        temperature=0.0,
        top_p=1.0,
        no_repeat_ngram_size=2,
        truncation=True
    )
    text = (out[0].get("generated_text") or "").strip()
    return text if text else "Sorry—I didn't catch that."
 
# ---------------------------
# Step 2.1: TF-IDF embeddings
# ---------------------------
def vectorize_texts(texts, normalize: bool = True, max_features: int = 1024):
    """
    Convert a list of strings to TF-IDF vectors.
    - Fits TF-IDF on 'texts' per call (stateless).
    - If normalize=True, L2-normalizes each vector to unit length.
 
    Returns: numpy.ndarray of shape (len(texts), dim)
    """
    if not isinstance(texts, list) or len(texts) == 0:
        raise ValueError("texts must be a non-empty list of strings")
 
    vec = TfidfVectorizer(max_features=max_features)
    X = vec.fit_transform(texts).toarray()  # shape: (n, dim)
 
    if normalize:
        norms = np.linalg.norm(X, axis=1, keepdims=True) + 1e-12
        X = X / norms
 
    return X