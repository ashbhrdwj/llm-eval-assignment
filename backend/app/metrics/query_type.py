from typing import Dict

def classify_query_text(text: str) -> str:
    """Very small heuristic classifier to tag queries as:
    - 'explanation' (explain/why/describe/overview)
    - 'problem_solving' (solve, compute, calculate, implement)
    - 'analysis' (compare, analyze, evaluate, critique)
    - 'other' otherwise
    """
    if not text:
        return "other"
    t = text.lower()
    if any(w in t for w in ["explain", "why", "describe", "overview", "summar"]):
        return "explanation"
    if any(w in t for w in ["solve", "calculate", "compute", "implement", "write code", "derive"]):
        return "problem_solving"
    if any(w in t for w in ["compare", "analyze", "evaluate", "critique", "contrast"]):
        return "analysis"
    return "other"
