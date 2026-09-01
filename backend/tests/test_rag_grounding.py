import pytest

from app.agents.grounding import evidence_support, filter_grounded_answer
from app.services.retrieval.embeddings import LocalHashEmbeddings
from app.services.retrieval.hybrid import HybridRetriever


MANUAL = [
    ("e05", "E05: Motor Overtemperature\nE05 means the motor temperature input exceeded the configured trip threshold. Allow the motor to cool with the equipment stopped. Check the cooling grille, cooling fan, hydraulic load, and frequent starts.", "E05: Motor Overtemperature"),
    ("e12", "E12: Low Hydraulic Pressure\nE12 means measured hydraulic pressure remained below the configured minimum for ten seconds after startup. Check reservoir fluid level, inlet valve position, suction hose, strainer, filter restriction, leakage, and pump rotation.", "E12: Low Hydraulic Pressure"),
    ("shutdown", "Emergency Shutdown Procedure\nUse emergency shutdown immediately for an uncontrolled hydraulic leak, burst hose, smoke, fire, electrical arcing, severe vibration, unexpected machine movement, failed guard or interlock, or pressure above the safe limit.", "Emergency Shutdown Procedure"),
]



def test_generated_claim_must_have_evidence_anchor():
    evidence = MANUAL[0][1]
    data = {
        "meaning": "E05 indicates motor overtemperature.",
        "likely_cause": "The motor temperature input exceeded the configured trip threshold.",
        "steps": [
            "Check the cooling grille and cooling fan.",
            "Replace the pump bearing immediately.",
        ],
        "escalation": "Contact a qualified technician if E05 returns.",
    }
    filtered, warnings = filter_grounded_answer(data, evidence)
    assert "Replace the pump bearing immediately." not in filtered["steps"]
    assert filtered["meaning"]
    assert warnings


def test_irrelevant_claim_has_zero_or_near_zero_support():
    evidence = MANUAL[0][1]
    assert evidence_support("quantum telemetry calibration procedure", evidence) == 0


def test_empty_evidence_cannot_support_nonempty_claim():
    filtered, warnings = filter_grounded_answer(
        {"meaning":"E05 means motor overtemperature.","likely_cause":"","steps":["Check the cooling fan."],"escalation":""},
        "",
    )
    assert filtered["meaning"] == ""
    assert filtered["steps"] == []
    assert warnings

@pytest.mark.asyncio
async def test_conflicting_evidence_is_not_treated_as_sufficient():
    from app.agents.workflow import TroubleshootingGraph
    from app.services.retrieval.hybrid import RetrievedChunk

    class R: pass
    graph=TroubleshootingGraph(R(), R())
    chunks=[
        RetrievedChunk("a", "E05 means motor overtemperature. Do not restart until cool.", {"manual_id":"a","manual_filename":"a.pdf","page_number":1,"section_title":"E05"}, .8,.8,True),
        RetrievedChunk("b", "E05 means motor overtemperature. Restart immediately after inspection.", {"manual_id":"b","manual_filename":"b.pdf","page_number":2,"section_title":"E05"}, .79,.79,True),
    ]
    result=await graph.evaluate({"error_codes":["E05"],"chunks":chunks})
    assert result["conflict"] is True
    assert result["sufficient"] is False
