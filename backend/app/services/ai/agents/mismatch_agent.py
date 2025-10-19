from typing import Any, Dict
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.services.ai.llm_client import get_llm
from app.services.ai import Agent


PROMPT_SYSTEM = (
    "You are a deterministic Mismatch Detector for hiring. You must output STRICT JSON matching the schema. "
    "Goal: build factual job_struct/cv_struct and detect mismatches with severity. Use only explicit evidence. "
    "Be aggressive in extraction from messy PDF/OCR: scan bullet lists, tables, and inline sentences. "
    "Normalize tokens: lowercase skills; CEFR A1..C2; employment_type=office|hybrid|remote; KZT salary numbers. "
    "IMPORTANT: Do NOT invent skills. If a must-have token occurs in CV text even once, include it in cv_struct.skills. "
    "Evidence quotes must be ≤12 words, verbatim."
)

PROMPT_USER = (
    "Role & Goal:\n"
    "- Input: raw JD text and raw CV text (possibly from PDF).\n"
    "- Tasks: normalize, detect mismatches, mark missing_data, attach micro-evidence.\n"
    "Extraction rules:\n"
    "  * Skills: tokenize by commas/lines and exact token scan across CV text; lowercase, dedupe; no synonyms.\n"
    "  * Experience: prefer explicit numbers like '3 years', '2+ лет'; map to total_experience_years.\n"
    "  * Langs: detect CEFR A1..C2; return best level objects.\n"
    "  * Education: normalize to bachelor/master/phd/associate/certificate/highschool.\n"
    "  * Location & format: city names + office/hybrid/remote.\n"
    "  * Salary: detect KZT amounts and set salary_expectation.value with unknown=false when seen.\n"
    "Policy:\n"
    "- Only facts; if absent -> missing_data. No invention.\n"
    "- Severity: high(blocker), medium(compensable), low(cosmetic).\n"
    "- If hints.must_have_skills provided: for each token, do case-insensitive search in CV text; when found, add to cv_struct.skills.\n\n"
    "Input JSON:\n{input_json}\n\n"
    "Output JSON schema EXACTLY (keys and shapes):\n{schema_json}\n\n"
    "Rules:\n"
    "- Strict JSON only.\n"
    "- Evidence quotes ≤ 12 words each (verbatim).\n"
    "- No duplication of same mismatch type.\n"
    "- If JD lacks criterion → do NOT emit mismatch (use missing_data instead).\n"
)

SCHEMA_EXAMPLE = {
    "job_struct": {
        "title": "string",
        "min_experience_years": 0,
        "required_skills": ["string"],
        "nice_to_have": ["string"],
        "lang_requirement": [{"lang": "EN", "level": "B2"}],
        "education_min": "bachelor|master|phd|associate|certificate|highschool|unknown",
        "location_requirement": {"city": "string", "employment_type": "office|hybrid|remote|contract|part-time|full-time|unknown"},
        "salary_range": {"min": 0, "max": 0, "currency": "KZT"},
        "domain": "string",
    },
    "cv_struct": {
        "name": "string",
        "total_experience_years": 0,
        "skills": ["string"],
        "langs": [{"lang": "EN", "level": "B1"}],
        "education_level": "bachelor|master|phd|associate|certificate|highschool|unknown",
        "location": {"city": "string"},
        "employment_type": "office|hybrid|remote|contract|part-time|full-time|unknown",
        "relocation_ready": False,
        "salary_expectation": {"value": 0, "currency": "KZT", "unknown": True},
        "domain_tags": ["string"],
        "notes": "string",
    },
    "mismatches": [
        {
            "criterion": "experience",
            "mismatch_type": "experience_below_min",
            "severity": "high",
            "detail": "...",
            "evidence": {"jd": "...", "cv": "..."},
        }
    ],
    "missing_data": ["..."],
    "coverage_snapshot": {
        "must_have_covered": ["string"],
        "must_have_missing": ["string"],
        "skills_overlap": ["string"],
    },
}


class MismatchDetectorAgent(Agent):
    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        llm = get_llm(temperature=0)
        prompt = ChatPromptTemplate.from_messages([
            ("system", PROMPT_SYSTEM),
            ("user", PROMPT_USER),
        ])
        chain = prompt | llm | StrOutputParser()

        input_json = json.dumps(payload, ensure_ascii=False)
        schema_json = json.dumps(SCHEMA_EXAMPLE, ensure_ascii=False)
        raw = chain.invoke({"input_json": input_json, "schema_json": schema_json})

        # Try to find JSON in output (guard)
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end >= start:
            raw = raw[start : end + 1]

        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("Invalid JSON result")
        return data
