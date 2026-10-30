"""Prompt and response parsing for evidence-grounded research."""

import json
from typing import Any, Dict

from ..models import AnalysisReport, FinanceEvidence


def build_research_prompt(question: str, evidence: FinanceEvidence) -> str:
    evidence_json = evidence.model_dump_json(indent=2)
    return """Analyze the public-company evidence below.

Rules:
- Use only the supplied evidence for factual claims.
- Separate interpretation from facts.
- Do not invent missing values, dates, or sources.
- Do not describe trends, consistency, cash generation, competition, supply chains,
  macro conditions, or other external factors unless they appear in the evidence.
- Every positive signal and risk must be directly supported by a supplied value.
- Mention uncertainty and data limitations explicitly.
- This is educational research, not investment advice.
- Return only valid JSON with exactly these keys:
  ticker, summary, positive_signals, risks, limitations, sources, evidence.

User question:
{question}

Evidence:
{evidence}
""".format(question=question, evidence=evidence_json)


def parse_analysis_response(
    raw_response: str, evidence: FinanceEvidence
) -> AnalysisReport:
    """Parse a model response and enforce the public report contract."""
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].lstrip()
    try:
        payload: Dict[str, Any] = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM returned invalid JSON") from exc

    payload.setdefault("ticker", evidence.ticker)
    payload["positive_signals"] = normalize_findings(
        payload.get("positive_signals", [])
    )
    payload["risks"] = normalize_findings(payload.get("risks", []))
    payload["sources"] = [source.model_dump() for source in evidence_sources(evidence)]
    payload["evidence"] = evidence.model_dump()
    return AnalysisReport.model_validate(payload)


def normalize_findings(findings: Any):
    """Keep the public report contract stable across model response styles."""
    normalized = []
    for finding in findings or []:
        if isinstance(finding, str):
            normalized.append(finding)
        elif isinstance(finding, dict):
            description = finding.get("description") or finding.get("finding")
            supporting_evidence = finding.get("evidence")
            if description and supporting_evidence:
                normalized.append(
                    "%s (evidence: %s)" % (description, supporting_evidence)
                )
            elif description:
                normalized.append(str(description))
            else:
                normalized.append(str(finding))
        else:
            normalized.append(str(finding))
    return normalized


def evidence_sources(evidence: FinanceEvidence):
    """Return the authoritative source records attached to retrieved evidence."""
    sources = []
    if evidence.price is not None:
        sources.append(evidence.price.source)
    if evidence.fundamentals is not None:
        sources.append(evidence.fundamentals.source)
    return sources
