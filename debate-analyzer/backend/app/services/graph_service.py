import json
import re
import os
import networkx as nx
from app.config import settings

def load_prompt_version(version: str) -> str:
    prompt_path = os.path.join("prompts", f"graph_prompt_{version}.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def call_graph_llm(prompt: str, llm_client) -> dict:
    response = llm_client.invoke(prompt)
    text = response.content if hasattr(response, 'content') else str(response)

    text = re.sub(r'```json|```', '', text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        retry_prompt = prompt + "\n\nIMPORTANT: Your last response was not valid JSON. Return ONLY the JSON object. Nothing else."
        response2 = llm_client.invoke(retry_prompt)
        text2 = response2.content if hasattr(response2, 'content') else str(response2)
        text2 = re.sub(r'```json|```', '', text2).strip()
        return json.loads(text2)

def build_networkx(graph_json: dict) -> nx.DiGraph:
    G = nx.DiGraph()
    for node in graph_json.get("nodes", []):
        G.add_node(node["id"], **node)
    for edge in graph_json.get("edges", []):
        G.add_edge(edge["source"], edge["target"], **edge)
    return G

def detect_topic_shifts(graph_json: dict) -> list:
    shifts = []
    # Simplified mock logic: we extract edges marked as shifts
    for edge in graph_json.get("edges", []):
        if edge.get("relation") == "shifts_to":
            shifts.append({
                "from_topic": edge["source"],
                "to_topic": edge["target"],
                "time_seconds": 0.0, # Without segment timestamps in the prompt, we estimate or default to 0
                "speaker_label": "Unknown"
            })
    return shifts

def evaluate_graph(graph_json: dict, llm_client) -> float:
    EVAL_PROMPT = f"""
    Score this knowledge graph built from a debate session on a scale of 1-5
    for each criterion. Return ONLY valid JSON.

    {{
      "completeness": <1-5>,
      "clarity": <1-5>,
      "connectivity": <1-5>,
      "hierarchy": <1-5>,
      "insight": <1-5>,
      "average": <1-5>,
      "reasoning": "one sentence"
    }}

    Graph JSON:
    {json.dumps(graph_json)}
    """
    try:
        response = llm_client.invoke(EVAL_PROMPT)
        text = response.content if hasattr(response, 'content') else str(response)
        text = re.sub(r'```json|```', '', text).strip()
        data = json.loads(text)
        return float(data.get("average", 3.0))
    except Exception:
        return 3.0

def explain_graph(graph_json: dict, llm_client) -> dict:
    EXPLAIN_PROMPT = f"""
    Analyze the following knowledge graph from a debate and provide:
    1. A detailed explanation of what this graph shows (who argued what, what were the main conflicts, and what was the consensus).
    2. A summarized conclusion of the whole debate session.

    Return the result ONLY as a SINGLE JSON object. DO NOT return multiple objects.
    {{
      "explanation": "detailed markdown string",
      "conclusion": "short markdown string"
    }}

    Graph JSON:
    {json.dumps(graph_json)}
    """
    try:
        response = llm_client.invoke(EXPLAIN_PROMPT)
        text = response.content if hasattr(response, 'content') else str(response)
        
        # Robust JSON extraction
        text = re.sub(r'```json|```', '', text).strip()
        
        # If the LLM returned multiple objects like {..}, {..}, try to wrap them or take the first/last
        # But better to just try to find the first { and last } and see if it's one object.
        # Here we also handle the specific case seen in logs: {..}, {..}
        if "}," in text and text.count("{") > 1:
            # Try to fix {..}, {..} into a single object by combining keys if they are unique
            try:
                # Very hacky fix for the specific observed failure
                combined = {}
                blocks = re.findall(r'\{[^{}]+\}', text)
                for b in blocks:
                    combined.update(json.loads(b))
                data = combined
            except:
                data = json.loads(text) # Fallback to normal
        else:
            data = json.loads(text)
            
        return {
            "explanation": data.get("explanation", "Could not generate explanation."),
            "conclusion": data.get("conclusion", "Could not generate conclusion.")
        }
    except Exception as e:
        import traceback
        print(f"Error in explain_graph: {e}")
        traceback.print_exc()
        return {
            "explanation": "Could not generate explanation due to an internal error.",
            "conclusion": "Could not generate conclusion due to an internal error."
        }

def save_graph_to_db(session_id: str, graph_json: dict, shifts: list, eval_score: float, explanation: str, conclusion: str, db):
    from app.models.db_models import GraphData, TopicShift
    
    # Clean up old data for this session
    db.query(TopicShift).filter(TopicShift.session_id == session_id).delete()
    existing_gd = db.query(GraphData).filter(GraphData.session_id == session_id).first()
    
    if existing_gd:
        existing_gd.nodes_json = json.dumps(graph_json.get("nodes", []))
        existing_gd.edges_json = json.dumps(graph_json.get("edges", []))
        existing_gd.prompt_version = settings.PROMPT_VERSION
        existing_gd.explanation = explanation
        existing_gd.conclusion = conclusion
        existing_gd.eval_score = eval_score
    else:
        gd = GraphData(
            session_id=session_id,
            nodes_json=json.dumps(graph_json.get("nodes", [])),
            edges_json=json.dumps(graph_json.get("edges", [])),
            prompt_version=settings.PROMPT_VERSION,
            explanation=explanation,
            conclusion=conclusion,
            eval_score=eval_score
        )
        db.add(gd)
    
    for s in shifts:
        ts = TopicShift(
            session_id=session_id,
            time_seconds=s["time_seconds"],
            from_topic=s["from_topic"],
            to_topic=s["to_topic"],
            speaker_label=s["speaker_label"]
        )
        db.add(ts)
    
    db.commit()

def run_improvement_check():
    pass # To be implemented in background thread
