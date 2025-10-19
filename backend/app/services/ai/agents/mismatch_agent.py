from typing import Any, Dict
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.services.ai.llm_client import get_llm
from app.services.ai import Agent


PROMPT_SYSTEM = (
    "You are Mismatch Detector for the hiring funnel. Your job: normalize JD and CV into compact,"
    " factual structures and detect precise mismatches with severity. Prefer concrete facts from the"
    " CV/JD over heuristics. When CV comes from PDF/OCR, aggressively extract skills, years, cities,"
    " CEFR levels, and KZT salary numbers. Output strictly valid JSON per schema, no extra text."
    " Evidence quotes must be ≤ 12 words, verbatim from source."
)

PROMPT_USER = (
    "Role & Goal:\n"
    "- Input: raw JD text and raw CV text (possibly from PDF).\n"
    "- Tasks: normalize, detect mismatches, mark missing_data, attach micro-evidence.\n"
    "Extraction rules:\n"
    "  * Skills: tokenize by commas/lines; normalize to lowercase, dedupe; keep exact tokens (no synonyms).\n"
    "  * Experience: prefer explicit numbers like '3 years', '2+ лет'; map to total_experience_years.\n"
    "  * Langs: detect CEFR tokens A1..C2 and map to objects.\n"
    "  * Education: map keywords bachelor/master/phd/associate/certificate/highschool.\n"
    "  * Location: city tokens; Employment format: office/hybrid/remote when mentioned.\n"
    "  * Salary: detect KZT numbers; set salary_expectation.value and unknown=false when present.\n"
    "Policy:\n"
    "- Only facts; if absent -> missing_data.\n"
    "- No synonyms expansion; keep strict vocabularies.\n"
    "- Severity: high(blocker), medium(compensable), low(cosmetic).\n\n"
    "Input JSON:\n{input_json}\n\n"
    "Output JSON schema EXACTLY (keys and shapes):\n{schema_json}\n\n"
    "Rules:\n"
    "- Strict JSON only.\n"
    "- Evidence quotes ≤ 12 words each (verbatim).\n"
    "- No duplication of same mismatch type.\n"
    "- If JD lacks criterion → do not flag mismatch (use missing_data if needed).\n"
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
