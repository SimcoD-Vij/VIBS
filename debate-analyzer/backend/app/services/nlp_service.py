import spacy
import spacy.cli
from langchain_community.llms import Ollama
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from app.config import settings
import time

def get_llm_client():
    if settings.LLM_PROVIDER == "openai":
        return ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY)
    elif settings.LLM_PROVIDER == "anthropic":
        return ChatAnthropic(model="claude-haiku-4-5-20251001", api_key=settings.ANTHROPIC_API_KEY)
    else:
        # Default to Ollama
        return Ollama(model=settings.OLLAMA_MODEL, base_url=settings.OLLAMA_BASE_URL)

def summarize_speaker(speaker_text: str, llm_client) -> str:
    prompt_template = """
    You are analyzing a debate session transcript.
    Below is everything one speaker said throughout the debate.
    Extract their 3 to 5 key arguments or opinions as bullet points.
    Each bullet should be one concise sentence.
    Do not pad or repeat. If they said very little, write fewer bullets.
    Do not include filler words like "um" or "uh".

    SPEAKER TEXT:
    {speaker_text}

    Return only the bullet points, no introduction, no headers.
    """
    prompt = PromptTemplate.from_template(prompt_template)
    chain = prompt | llm_client
    
    for attempt in range(2):
        try:
            response = chain.invoke({"speaker_text": speaker_text})
            # Ollama returns string directly, chat models might return AIMessage
            text = response.content if hasattr(response, 'content') else str(response)
            return text.strip()
        except Exception as e:
            if attempt == 0:
                time.sleep(2)
            else:
                print(f"LLM Summarize failed: {e}")
                return "Summary unavailable"
    return "Summary unavailable"

def extract_topics(full_text: str) -> list:
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        spacy.cli.download("en_core_web_sm")
        nlp = spacy.load("en_core_web_sm")

    doc = nlp(full_text)

    # Entities
    entities = list(set([ent.text for ent in doc.ents 
                         if ent.label_ in ["ORG","PERSON","GPE","LAW","NORP","PRODUCT"]]))
                         
    STOPLIST = ["the", "a", "an", "this", "that", "it", "they", "we", "you", "i"]

    topics = list(set([
        chunk.text.lower() for chunk in doc.noun_chunks
        if len(chunk.text.split()) >= 2
        and chunk.root.pos_ == "NOUN"
        and chunk.text.lower() not in STOPLIST
    ]))[:20]

    all_topics = list(set(entities + topics))[:25]
    return all_topics
