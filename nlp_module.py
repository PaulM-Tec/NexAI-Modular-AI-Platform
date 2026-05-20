
"""
NLP Module for AI Core Project
- Entity extraction using spaCy
- Intent classification using HuggingFace zero-shot classification
- Integration with orm_models.py to store InteractionLog entries
"""

import spacy
from transformers import pipeline
from orm_models import get_session, InteractionLog

# Load spaCy model for entity extraction
nlp_spacy = spacy.load("en_core_web_sm")

# Load HuggingFace zero-shot classification pipeline
zero_shot_classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

# Define candidate intents
CANDIDATE_INTENTS = ["ASK_NEXT_STEP", "BOOK_SERVICE", "GENERAL_QUERY"]

def extract_entities(text: str):
    """Extract named entities from text using spaCy."""
    doc = nlp_spacy(text)
    return [(ent.text, ent.label_) for ent in doc.ents]

def classify_intent(text: str):
    """Classify intent using zero-shot classification."""
    result = zero_shot_classifier(text, CANDIDATE_INTENTS)
    return {"intent": result["labels"][0], "score": result["scores"][0]}

def process_user_message(session_id: int, message: str):
    """Process user message: classify intent, extract entities, and store in DB."""
    # NLP processing
    intent_result = classify_intent(message)
    entities_result = extract_entities(message)

    # Save to DB
    db = get_session()
    log = InteractionLog(
        session_id=session_id,
        direction="user",
        message=message,
        intent=intent_result["intent"],
        entities={"extracted": entities_result}
    )
    db.add(log)
    db.commit()
    db.close()

    return intent_result, entities_result

if __name__ == "__main__":
    # Quick test (requires a valid session_id in DB)
    print(process_user_message(session_id=1, message="Book a car service in Cape Town tomorrow"))
