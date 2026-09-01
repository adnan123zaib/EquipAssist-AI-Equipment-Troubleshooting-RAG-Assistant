import json
import re
from typing import TypedDict

from pydantic import BaseModel, Field
from langgraph.graph import END, START, StateGraph

from app.services.confidence.calculator import calculate_confidence
from app.agents.grounding import filter_grounded_answer, evidence_support
from app.services.generation.providers import GenerationProvider
from app.services.retrieval.hybrid import (
    HybridRetriever,
    RetrievedChunk,
    detect_error_codes,
)


class GeneratedAnswer(BaseModel):
    meaning: str = ""
    likely_cause: str = ""
    steps: list[str] = Field(default_factory=list)
    escalation: str = ""


class AgentState(TypedDict, total=False):
    question: str
    manual_ids: list[str]
    equipment_model: str | None
    owner_user_id: str | None
    top_k: int
    intent: str
    error_codes: list[str]
    hazards: list[str]
    rewritten_query: str
    chunks: list[RetrievedChunk]
    attempts: int
    sufficient: bool
    evidence_reason: str
    conflict: bool
    plan: list[str]
    answer_data: dict
    confidence: dict
    final: dict


class TroubleshootingGraph:
    def __init__(
        self,
        retriever: HybridRetriever,
        generator: GenerationProvider,
        max_attempts: int = 2,
    ):
        self.retriever = retriever
        self.generator = generator
        self.max_attempts = max_attempts
        self.graph = self._build()

    async def analyze(self, s):
        question = s["question"]

        return {
            "intent": "troubleshooting",
            "error_codes": detect_error_codes(question),
            "attempts": 0,
        }

    async def safety(self, s):
        question = s["question"].lower()

        hazards = [
            hazard
            for hazard in [
                "electrical",
                "hydraulic",
                "pressure",
                "thermal",
                "chemical",
                "mechanical",
            ]
            if hazard in question
        ]

        return {
            "hazards": hazards,
        }

    async def rewrite(self, s):
        identifiers = " ".join(
            s.get("error_codes", [])
        )
        model = s.get("equipment_model") or ""

        query = (
            f"{identifiers} "
            f"{model} "
            f"{s['question']} "
            "troubleshooting safety causes verification"
        ).strip()

        return {
            "rewritten_query": query,
        }

    async def retrieve(self, s):
        chunks = await self.retriever.search(
            s["rewritten_query"],
            s["top_k"],
            s.get("manual_ids") or None,
            s.get("owner_user_id"),
        )

        return {
            "chunks": chunks,
            "attempts": s.get("attempts", 0) + 1,
        }

    @staticmethod
    def detect_conflict(chunks):
        """
        Detect contradictory troubleshooting instructions for the
        same error identifier.

        Important:
        The error code and its instruction do not necessarily occur
        in the same sentence.

        Example:

            E05 means motor overtemperature.
            Do not restart until cool.

        The second sentence does not contain E05, but it is still
        part of the evidence associated with E05.

        Therefore, once a retrieved chunk contains an error code,
        all action instructions in that chunk are considered part
        of that error-code evidence.
        """

        by_code = {}

        action_patterns = {
            "restart": re.compile(
                r"\b(?:restart|reboot|reset|power\s+cycle)\b",
                re.IGNORECASE,
            ),
            "stop": re.compile(
                r"\b(?:stop|shutdown|shut\s+down|power\s+off|turn\s+off)\b",
                re.IGNORECASE,
            ),
            "bypass": re.compile(
                r"\b(?:bypass|override|disable)\b",
                re.IGNORECASE,
            ),
            "continue": re.compile(
                r"\b(?:continue|keep\s+running|operate)\b",
                re.IGNORECASE,
            ),
        }

        negative_pattern = re.compile(
            r"\b(?:do\s+not|don't|never|must\s+not|should\s+not|avoid)\b",
            re.IGNORECASE,
        )

        for chunk in chunks:
            text = chunk.text or ""

            # Detect all error identifiers appearing anywhere
            # in the retrieved chunk.
            codes = detect_error_codes(text)

            if not codes:
                continue

            sentences = [
                sentence.strip()
                for sentence in re.split(
                    r"(?<=[.!?])\s+",
                    text,
                )
                if sentence.strip()
            ]

            for code in codes:
                code_key = code.upper()

                # Every instruction in this chunk is associated with
                # the error code because the chunk itself was retrieved
                # as evidence for that identifier.
                for sentence in sentences:
                    for action, pattern in action_patterns.items():
                        if not pattern.search(sentence):
                            continue

                        is_negative = bool(
                            negative_pattern.search(sentence)
                        )

                        # True  -> action prohibited
                        # False -> action explicitly allowed/recommended
                        polarity = is_negative

                        by_code.setdefault(
                            code_key,
                            {},
                        ).setdefault(
                            action,
                            set(),
                        ).add(polarity)

        # Conflict occurs when the same error code contains the same
        # action both prohibited and explicitly instructed.
        for actions in by_code.values():
            for polarities in actions.values():
                if True in polarities and False in polarities:
                    return True

        return False

    async def evaluate(self, s):
        chunks = s.get("chunks", [])
        requested_codes = s.get("error_codes", [])

        if not chunks:
            return {
                "sufficient": False,
                "evidence_reason": (
                    "No relevant manual passages passed the "
                    "retrieval threshold."
                ),
                "conflict": False,
            }

        # ---------------------------------------------------------
        # Error-code question
        # ---------------------------------------------------------
        if requested_codes:
            exact_chunks = [
                chunk
                for chunk in chunks
                if chunk.exact_match
            ]

            if not exact_chunks:
                return {
                    "sufficient": False,
                    "evidence_reason": (
                        "The requested identifier "
                        f"{', '.join(requested_codes)} "
                        "was not found in the selected manuals."
                    ),
                    "conflict": False,
                }

            strongest = max(
                max(
                    chunk.retrieval_score,
                    chunk.reranker_score,
                )
                for chunk in exact_chunks
            )

            conflict = self.detect_conflict(
                exact_chunks
            )

            sufficient = (
                strongest >= 0.40
                and not conflict
            )

            if conflict:
                reason = (
                    "Conflicting passages were retrieved for "
                    "the requested identifier. The system cannot "
                    "safely select one instruction."
                )
            elif strongest >= 0.40:
                reason = (
                    "An exact identifier match was found."
                )
            else:
                reason = (
                    "The identifier match was too weak "
                    "to support instructions."
                )

            return {
                "sufficient": sufficient,
                "evidence_reason": reason,
                "conflict": conflict,
            }

        # ---------------------------------------------------------
        # General symptom/question retrieval
        # ---------------------------------------------------------
        strengths = [
            max(
                chunk.retrieval_score,
                chunk.reranker_score,
            )
            for chunk in chunks
        ]

        strongest = max(strengths)

        top_average = (
            sum(
                sorted(
                    strengths,
                    reverse=True,
                )[:2]
            )
            / min(
                2,
                len(strengths),
            )
        )

        enough = (
            strongest >= 0.52
            or (
                len(strengths) >= 2
                and top_average >= 0.34
            )
        )

        conflict = self.detect_conflict(chunks)

        if conflict:
            reason = (
                "Conflicting passages were retrieved; "
                "the answer requires technician review."
            )
        elif enough:
            reason = (
                "Strong manual evidence was found."
            )
        else:
            reason = (
                "Retrieved passages were too weak or unrelated "
                "to support safe instructions."
            )

        return {
            "sufficient": (
                enough
                and not conflict
            ),
            "evidence_reason": reason,
            "conflict": conflict,
        }

    def route_evidence(self, s):
        if s["sufficient"]:
            return "plan"

        if s["attempts"] < self.max_attempts:
            return "retry"

        return "insufficient"

    async def improve(self, s):
        identifiers = " ".join(
            s.get("error_codes", [])
        )

        model = s.get(
            "equipment_model"
        ) or ""

        query = (
            f"{identifiers} "
            f"{model} "
            f"{s['question']} "
            "fault diagnosis corrective action"
        ).strip()

        return {
            "rewritten_query": query,
        }

    async def plan(self, s):
        return {
            "plan": [
                "isolate hazards",
                "identify documented cause",
                "inspect in manual order",
                "verify repair",
                "escalate if unresolved",
            ]
        }

    async def generate(self, s):
        evidence = "\n---\n".join(
            (
                f"SOURCE {index + 1}: "
                f"[{chunk.metadata['manual_filename']}, "
                f"p. {chunk.metadata['page_number']}, "
                f"\"{chunk.metadata['section_title']}\"]\n"
                f"{chunk.text}"
            )
            for index, chunk in enumerate(
                s["chunks"]
            )
        )

        prompt = (
            f"QUESTION: {s['question']}\n\n"
            "Return JSON with exactly these fields:\n"
            "- meaning\n"
            "- likely_cause\n"
            "- steps (list)\n"
            "- escalation\n\n"
            "Use ONLY the supplied manual evidence.\n"
            "Never invent unsupported troubleshooting procedures.\n"
            "If the evidence is insufficient, say so instead "
            "of guessing.\n\n"
            f"EVIDENCE:\n{evidence}"
        )

        try:
            raw_response = await self.generator.generate(
                prompt
            )

            raw = json.loads(
                raw_response
            )

            data = GeneratedAnswer.model_validate(
                raw
            ).model_dump()

            data, grounding_warnings = (
                filter_grounded_answer(
                    data,
                    evidence,
                )
            )

            claims = [
                data.get("meaning", ""),
                data.get("likely_cause", ""),
                data.get("escalation", ""),
            ]

            claims.extend(
                data.get("steps", [])
            )

            claims = [
                claim
                for claim in claims
                if isinstance(claim, str)
                and claim.strip()
            ]

            evidence_texts = [
                chunk.text
                for chunk in s["chunks"]
            ]

            supported = sum(
                1
                for claim in claims
                if max(
                    (
                        evidence_support(
                            claim,
                            evidence_text,
                        )
                        for evidence_text in evidence_texts
                    ),
                    default=0.0,
                ) >= 0.18
            )

            data["_citation_coverage"] = (
                supported / len(claims)
                if claims
                else 0.0
            )

            if grounding_warnings:
                data["_grounding_warnings"] = (
                    grounding_warnings
                )

        except Exception:
            data = {
                "meaning": (
                    "The provider failed to return a "
                    "validated grounded response."
                ),
                "likely_cause": "",
                "steps": [],
                "escalation": (
                    "Ask a qualified technician and "
                    "retry later."
                ),
            }

        return {
            "answer_data": data,
        }

    async def confidence(self, s):
        data = s["answer_data"]

        coverage = float(
            data.get(
                "_citation_coverage",
                0.0,
            )
        )

        chunks = s["chunks"]

        if len(chunks) < 2:
            agreement = (
                0.5
                if chunks
                else 0.0
            )
        else:
            from app.agents.grounding import _tokens

            first_tokens = _tokens(
                chunks[0].text
            )

            second_tokens = _tokens(
                chunks[1].text
            )

            agreement = (
                len(
                    first_tokens
                    & second_tokens
                )
                / max(
                    1,
                    len(
                        first_tokens
                        | second_tokens
                    ),
                )
            )

        return {
            "confidence": calculate_confidence(
                chunks,
                coverage,
                agreement,
                bool(
                    s.get("error_codes")
                ),
                model_missing=not bool(
                    s.get("equipment_model")
                ),
                conflict=bool(
                    s.get("conflict")
                ),
            )
        }

    async def validate(self, s):
        chunks = s["chunks"]
        data = s["answer_data"]

        claims = [
            data.get("meaning", ""),
            data.get("likely_cause", ""),
            data.get("escalation", ""),
        ]

        claims.extend(
            data.get("steps", [])
        )

        claims = [
            claim
            for claim in claims
            if isinstance(claim, str)
            and claim.strip()
        ]

        selected = []

        for claim in claims:
            ranked = sorted(
                chunks,
                key=lambda chunk: (
                    evidence_support(
                        claim,
                        chunk.text,
                    ),
                    chunk.reranker_score,
                ),
                reverse=True,
            )

            if (
                ranked
                and evidence_support(
                    claim,
                    ranked[0].text,
                ) >= 0.18
            ):
                selected.append(
                    ranked[0]
                )

        # Add explicit safety evidence when available.
        if s.get("hazards"):
            safety_chunks = [
                chunk
                for chunk in chunks
                if "safety"
                in chunk.metadata.get(
                    "section_title",
                    "",
                ).lower()
            ]

            if safety_chunks:
                selected.append(
                    max(
                        safety_chunks,
                        key=lambda chunk:
                        chunk.reranker_score,
                    )
                )

        unique = []
        seen = set()

        for chunk in selected:
            if chunk.chunk_id in seen:
                continue

            seen.add(
                chunk.chunk_id
            )

            unique.append(
                chunk
            )

        ranked_unique = sorted(
            unique,
            key=lambda chunk: (
                chunk.reranker_score,
                chunk.retrieval_score,
            ),
            reverse=True,
        )[:4]

        citations = [
            {
                "manual_id": chunk.metadata[
                    "manual_id"
                ],
                "manual_name": chunk.metadata[
                    "manual_filename"
                ],
                "page_number": chunk.metadata[
                    "page_number"
                ],
                "section_title": chunk.metadata[
                    "section_title"
                ],
                "excerpt": chunk.text[:320],
                "chunk_id": chunk.chunk_id,
                "retrieval_score": round(
                    chunk.retrieval_score,
                    3,
                ),
                "reranker_score": round(
                    chunk.reranker_score,
                    3,
                ),
            }
            for chunk in ranked_unique
        ]

        inline = " ".join(
            (
                f"[{citation['manual_name']}, "
                f"p. {citation['page_number']}, "
                f"\"{citation['section_title']}\"]"
            )
            for citation in citations[:2]
        )

        warnings = []

        if s.get("hazards"):
            warnings.append(
                "Use lockout/tagout and release stored "
                "energy before hazardous inspection when "
                "the cited manual requires it. Do not "
                "bypass guards, interlocks, or protection "
                "devices."
            )

        grounding_warnings = data.get(
            "_grounding_warnings",
            [],
        )

        warnings.extend(
            grounding_warnings
        )

        if (
            not data.get("meaning")
            and not data.get("steps")
            and not data.get("likely_cause")
        ):
            return await self.insufficient(
                {
                    **s,
                    "evidence_reason": (
                        "The provider response could not "
                        "be sufficiently anchored to the "
                        "retrieved manual evidence."
                    ),
                }
            )

        answer = (
            f"Meaning:\n"
            f"{data.get('meaning', '')} "
            f"{inline}\n\n"
            f"Likely cause:\n"
            f"{data.get('likely_cause', '')}\n\n"
            f"Escalate when:\n"
            f"{data.get('escalation', '')}"
        )

        return {
            "final": {
                "answer": answer,
                "troubleshooting_steps": data.get(
                    "steps",
                    [],
                ),
                "safety_warnings": warnings,
                "citations": citations,
                "confidence": s["confidence"],
                "retrieval_attempts": s[
                    "attempts"
                ],
            }
        }

    async def insufficient(self, s):
        chunks = s.get(
            "chunks",
            [],
        )

        cites = [
            {
                "manual_id": chunk.metadata[
                    "manual_id"
                ],
                "manual_name": chunk.metadata[
                    "manual_filename"
                ],
                "page_number": chunk.metadata[
                    "page_number"
                ],
                "section_title": chunk.metadata[
                    "section_title"
                ],
                "excerpt": chunk.text[:260],
                "chunk_id": chunk.chunk_id,
                "retrieval_score": round(
                    chunk.retrieval_score,
                    3,
                ),
                "reranker_score": round(
                    chunk.reranker_score,
                    3,
                ),
            }
            for chunk in chunks[:2]
        ]

        conf = calculate_confidence(
            chunks,
            0.0,
            0.0,
            bool(
                s.get("error_codes")
            ),
            conflict=bool(
                s.get("conflict")
            ),
            indirect=True,
        )

        reason = s.get(
            "evidence_reason",
            "The available manual evidence was insufficient.",
        )

        return {
            "final": {
                "answer": (
                    "I could not find enough reliable "
                    "information in the uploaded manuals "
                    "to answer this safely. "
                    f"Reason: {reason} "
                    "Please verify the selected manual and "
                    "provide the equipment model, exact "
                    "error code, or observable symptom."
                ),
                "troubleshooting_steps": [],
                "safety_warnings": [
                    "Do not attempt speculative repair instructions."
                ],
                "citations": cites,
                "confidence": conf,
                "retrieval_attempts": s.get(
                    "attempts",
                    0,
                ),
            }
        }

    def _build(self):
        graph = StateGraph(
            AgentState
        )

        nodes = [
            ("analyze", self.analyze),
            ("safety", self.safety),
            ("rewrite", self.rewrite),
            ("retrieve", self.retrieve),
            ("evaluate", self.evaluate),
            ("improve", self.improve),
            ("plan", self.plan),
            ("generate", self.generate),
            ("confidence", self.confidence),
            ("validate", self.validate),
            ("insufficient", self.insufficient),
        ]

        for name, node in nodes:
            graph.add_node(
                name,
                node,
            )

        graph.add_edge(
            START,
            "analyze",
        )

        graph.add_edge(
            "analyze",
            "safety",
        )

        graph.add_edge(
            "safety",
            "rewrite",
        )

        graph.add_edge(
            "rewrite",
            "retrieve",
        )

        graph.add_edge(
            "retrieve",
            "evaluate",
        )

        graph.add_conditional_edges(
            "evaluate",
            self.route_evidence,
            {
                "retry": "improve",
                "insufficient": "insufficient",
                "plan": "plan",
            },
        )

        graph.add_edge(
            "improve",
            "retrieve",
        )

        graph.add_edge(
            "plan",
            "generate",
        )

        graph.add_edge(
            "generate",
            "confidence",
        )

        graph.add_edge(
            "confidence",
            "validate",
        )

        graph.add_edge(
            "validate",
            END,
        )

        graph.add_edge(
            "insufficient",
            END,
        )

        return graph.compile()

    async def run(self, **kwargs):
        result = await self.graph.ainvoke(
            kwargs
        )

        return result["final"]