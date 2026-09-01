import json
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.main import app  # noqa: E402

EMAIL = "sample-evaluator@example.com"
PASSWORD = "SampleEval123!"


def authenticate(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Sample Evaluator", "email": EMAIL, "password": PASSWORD},
    )
    if response.status_code == 409:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": EMAIL, "password": PASSWORD},
        )
    response.raise_for_status()
    client.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})


def wait_indexed(client, manual_id: str) -> dict:
    for _ in range(100):
        result = client.get(f"/api/v1/manuals/{manual_id}")
        result.raise_for_status()
        manual = result.json()
        if manual["status"] in {"indexed", "failed"}:
            return manual
        time.sleep(0.1)
    raise RuntimeError("Timed out waiting for sample manual ingestion")


def citation_supports_question(question: str, citation: dict, expected_code: str | None) -> bool:
    text = " ".join(
        [
            citation.get("manual_name", ""),
            citation.get("section_title", ""),
            citation.get("excerpt", ""),
        ]
    ).lower()
    if expected_code and expected_code.lower() in text:
        return True
    question_terms = {
        token
        for token in __import__("re").findall(r"[a-z0-9-]+", question.lower())
        if len(token) > 3
    }
    return len(question_terms & set(__import__("re").findall(r"[a-z0-9-]+", text))) >= 2


with TestClient(app) as client:
    authenticate(client)
    manuals = client.get("/api/v1/manuals").json()
    indexed = [m for m in manuals if m["status"] == "indexed"]
    if not indexed:
        raise SystemExit("Index the sample manual first with scripts/ingest_sample_manual.py")
    manual = indexed[0]

    cases = json.loads((ROOT / "sample_data" / "sample_qa.json").read_text(encoding="utf-8"))
    all_passed = True
    for case in cases:
        started = time.perf_counter()
        response = client.post(
            "/api/v1/chat/query",
            json={"question": case["question"], "manual_ids": [manual["id"]]},
        )
        elapsed = round((time.perf_counter() - started) * 1000)
        response.raise_for_status()
        result = response.json()
        citations = result["citations"]
        expected_sections = case["expected_sections"]
        section_hits = [
            expected.lower()
            for expected in expected_sections
            if any(expected.lower() in c["section_title"].lower() for c in citations)
        ]
        code_hit = (
            not case["expected_code"]
            or any(case["expected_code"].lower() in c["excerpt"].lower() for c in citations)
        )
        citation_supported = bool(citations) and all(
            citation_supports_question(case["question"], c, case["expected_code"])
            for c in citations
        )
        grounded = bool(citations) and citation_supported
        passed = (
            len(section_hits) == len(expected_sections)
            and code_hit
            and grounded
            and result["confidence"]["score"] > 0
        )
        all_passed &= passed
        print(json.dumps({
            "question": case["question"],
            "pass": passed,
            "expected_sections": expected_sections,
            "retrieved_sections": [c["section_title"] for c in citations],
            "pages": [c["page_number"] for c in citations],
            "citation_presence": bool(citations),
            "citation_supported": citation_supported,
            "groundedness": "pass" if grounded else "fail",
            "confidence": result["confidence"],
            "response_time_ms": elapsed,
        }, indent=2))

    raise SystemExit(0 if all_passed else 1)
