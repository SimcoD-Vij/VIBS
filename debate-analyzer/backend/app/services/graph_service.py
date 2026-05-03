import json
import re
import os
import networkx as nx
from app.config import settings

def load_prompt_version(version: str) -> str:
    prompt_path = os.path.join("prompts", f"graph_prompt_{version}.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def extract_json(text: str) -> str:
    # Try to find content between triple backticks
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        return match.group(1).strip()
    
    # Otherwise, try to find the first '{' and last '}'
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        return text[start:end+1].strip()
    
    return text.strip()

def call_graph_llm(prompt: str, llm_client) -> dict:
    response = llm_client.invoke(prompt)
    text = response.content if hasattr(response, 'content') else str(response)

    clean_text = extract_json(text)

    try:
        return json.loads(clean_text)
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}. Raw text: {text[:200]}...")
        retry_prompt = prompt + "\n\nIMPORTANT: Your last response was not valid JSON. Return ONLY the JSON object. Nothing else."
        response2 = llm_client.invoke(retry_prompt)
        text2 = response2.content if hasattr(response2, 'content') else str(response2)
        clean_text2 = extract_json(text2)
        return json.loads(clean_text2)

def build_networkx(graph_json: dict) -> nx.DiGraph:
    G = nx.DiGraph()
    for node in graph_json.get("nodes", []):
        G.add_node(node["id"], **node)
    for edge in graph_json.get("edges", []):
        G.add_edge(edge["source"], edge["target"], **edge)
    return G

def detect_topic_shifts(graph_json: dict, segments: list) -> list:
    shifts = []
    # nodes list to lookup labels
    nodes = {n["id"]: n for n in graph_json.get("nodes", [])}
    
    for edge in graph_json.get("edges", []):
        if edge.get("relation") == "shifts_to":
            from_topic_id = edge["source"]
            to_topic_id = edge["target"]
            
            target_node = nodes.get(to_topic_id)
            target_label = target_node["label"] if target_node else ""
            
            # Simple keyword match to find first mention of target topic
            keywords = [kw.lower() for kw in target_label.split() if len(kw) > 3]
            
            time_seconds = 0.0
            speaker_label = "Unknown"
            
            if keywords:
                for seg in segments:
                    seg_text_lower = seg["text"].lower()
                    if any(kw in seg_text_lower for kw in keywords):
                        time_seconds = seg["start"]
                        speaker_label = seg["speaker_label"]
                        break
            
            shifts.append({
                "from_topic": from_topic_id,
                "to_topic": to_topic_id,
                "time_seconds": time_seconds,
                "speaker_label": speaker_label
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
        clean_text = extract_json(text)
        
        # If the LLM returned multiple objects like {..}, {..}, try to fix them
        if "}," in clean_text and clean_text.count("{") > 1:
            try:
                combined = {}
                blocks = re.findall(r'\{[^{}]+\}', clean_text)
                for b in blocks:
                    combined.update(json.loads(b))
                data = combined
            except:
                data = json.loads(clean_text)
        else:
            data = json.loads(clean_text)
            
        return {
            "explanation": data.get("explanation", "Could not generate explanation."),
            "conclusion": data.get("conclusion", "Could not generate conclusion.")
        }
    except Exception as e:
        import traceback
        print(f"Error in explain_graph: {e}")
        print(f"Raw text that failed: {text}")
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
    
    # Call improvement check
    try:
        run_improvement_check(db)
    except Exception as e:
        print(f"Improvement check failed: {e}")

def run_improvement_check(db):
    from app.models.db_models import Session, GraphData
    from app.services.nlp_service import get_llm_client
    
    # 1. Count total sessions in DB with status="complete"
    count = db.query(Session).filter(Session.status == "complete").count()
    
    # 2. Only run every 50 sessions
    if count == 0 or count % 50 != 0:
        return
        
    print(f"Running prompt improvement check for session count {count}...")
    
    # 3. Query GraphData ordered by eval_score DESC, limit 5 — these are top performers
    top = db.query(GraphData).order_by(GraphData.eval_score.desc()).limit(5).all()
    
    # 4. Query GraphData ordered by eval_score ASC, limit 5 — these are worst performers
    worst = db.query(GraphData).order_by(GraphData.eval_score.asc()).limit(5).all()
    
    # 5. Load the current prompt
    current_prompt = load_prompt_version(settings.PROMPT_VERSION)
    
    def format_examples(examples):
        out = []
        for ex in examples:
            out.append(f"Eval Score: {ex.eval_score}\nNodes: {ex.nodes_json[:500]}...\nEdges: {ex.edges_json[:500]}...\n")
        return "\n".join(out)
        
    top_examples = format_examples(top)
    worst_examples = format_examples(worst)
    
    # 6. Build improvement prompt
    improvement_prompt = f"""
    You are an AI expert specializing in knowledge graph engineering. 
    Your goal is to improve a prompt that generates knowledge graphs from debate transcripts.
    
    CURRENT PROMPT:
    {current_prompt}
    
    BEST-SCORING EXAMPLES (High connectivity, deep insights):
    {top_examples}
    
    WORST-SCORING EXAMPLES (Flat, disconnected, or generic):
    {worst_examples}
    
    TASK:
    Rewrite the prompt to produce higher-quality graphs like the best examples.
    Focus on better relationship mapping, node weighting, and capturing underlying debate dynamics.
    Keep the JSON schema identical to the current prompt.
    Return ONLY the new prompt text. No preamble, no explanation.
    """
    
    try:
        llm_client = get_llm_client()
        response = llm_client.invoke(improvement_prompt)
        new_prompt_text = response.content if hasattr(response, 'content') else str(response)
        
        # 7. Parse new version number
        current_v = settings.PROMPT_VERSION
        match = re.search(r'v(\d+)', current_v)
        if match:
            new_v_num = int(match.group(1)) + 1
            new_v = f"v{new_v_num}"
        else:
            new_v = "v2"
            
        # 8. Save to prompts/graph_prompt_vX.txt
        new_path = os.path.join("prompts", f"graph_prompt_{new_v}.txt")
        os.makedirs("prompts", exist_ok=True)
        with open(new_path, "w", encoding="utf-8") as f:
            f.write(new_prompt_text)
            
        # 9. Update settings and attempt to update .env
        settings.PROMPT_VERSION = new_v
        print(f"PROMPT UPGRADED TO {new_v}")
        
        # Try to update .env file
        env_path = ".env"
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
            
            with open(env_path, "w") as f:
                found = False
                for line in lines:
                    if line.startswith("PROMPT_VERSION="):
                        f.write(f"PROMPT_VERSION={new_v}\n")
                        found = True
                    else:
                        f.write(line)
                if not found:
                    f.write(f"PROMPT_VERSION={new_v}\n")
                    
    except Exception as e:
        print(f"Error during prompt improvement: {e}")
