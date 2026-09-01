import re

_STOP = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
    "what", "how", "does", "do", "is", "are", "it", "my", "this", "that",
    "from", "only", "then", "when", "must", "should", "can", "your", "their",
}

def _tokens(text: str) -> set[str]:
    return {
        t for t in re.findall(r"[a-z0-9-]+", text.lower())
        if t not in _STOP and len(t) > 2
    }


def evidence_support(text: str, evidence: str) -> float:
    """Deterministic lexical support signal; never treated as semantic proof."""
    claim = _tokens(text)
    if not claim:
        return 1.0
    return len(claim & _tokens(evidence)) / len(claim)


def filter_grounded_answer(data: dict, evidence: str) -> tuple[dict, list[str]]:
    """Remove generated claims with no lexical anchor in retrieved evidence.

    This is deliberately conservative. It cannot prove entailment, so anything
    lacking enough overlap is omitted rather than presented as grounded.
    """
    warnings: list[str] = []
    meaning = data.get("meaning", "") or ""
    cause = data.get("likely_cause", "") or ""
    escalation = data.get("escalation", "") or ""
    if meaning and evidence_support(meaning, evidence) < 0.18:
        meaning = ""
        warnings.append("Generated meaning lacked a sufficient evidence anchor.")
    if cause and evidence_support(cause, evidence) < 0.12:
        cause = ""
        warnings.append("Generated cause lacked a sufficient evidence anchor.")
    if escalation and evidence_support(escalation, evidence) < 0.12:
        escalation = ""
        warnings.append("Generated escalation lacked a sufficient evidence anchor.")
    steps=[]
    for step in data.get("steps", []) or []:
        if isinstance(step, str) and evidence_support(step, evidence) >= 0.18:
            steps.append(step)
        else:
            warnings.append("One generated troubleshooting step was removed because it was not anchored in retrieved evidence.")
    return {"meaning":meaning,"likely_cause":cause,"steps":steps,"escalation":escalation}, warnings
