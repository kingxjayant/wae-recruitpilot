"""Parsing utilities: extract structured signals from resume / JD text.

Everything here is deterministic, offline and dependency-free. LLM output is
used ONLY as an advisory layer on top of this (see llm.py); scoring never
depends on it, so results are reproducible and unit-testable.
"""
import json
import re
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"
with open(_DATA_DIR / "skills_taxonomy.json", "r", encoding="utf-8") as _f:
    TAXONOMY = json.load(_f)

# Flatten taxonomy once: canonical name -> list of alias regexes
_SKILL_PATTERNS = []  # list of (canonical, compiled_regex)
for _category, _skills in TAXONOMY.items():
    for _skill, _aliases in _skills.items():
        for _alias in _aliases:
            _SKILL_PATTERNS.append(
                (_skill, re.compile(r"(?<![A-Za-z0-9])" + re.escape(_alias.lower()) + r"(?![A-Za-z0-9])"))
            )

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+91[-\s]?[6-9]\d{9}|\b[6-9]\d{4}[-\s]?\d{5}\b|\b[6-9]\d{9}\b)")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/[A-Za-z0-9_\-/]+", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_\-/]+", re.I)

ACHIEVEMENT_KEYWORDS = [
    "project", "projects", "internship", "intern", "hackathon", "won", "winner",
    "lead", "led", "founded", "research", "published", "certificate", "certification",
    "award", "scholarship", "kaggle", "open source", "github", "volunteer",
    "club", "society", "president", "captain", "mentor",
]

DEGREE_PATTERNS = [
    ("PhD", re.compile(r"\bph\.?d\b|\bdoctorate\b", re.I)),
    ("MCA", re.compile(r"\bm\.?c\.?a\b", re.I)),
    ("BCA", re.compile(r"\bb\.?c\.?a\b", re.I)),
    ("M.Tech", re.compile(r"\bm\.?\s?tech\b|\bm\.?e\.?\b(?!.rusted)|\bms\s?engineering\b", re.I)),
    ("B.Tech", re.compile(r"\bb\.?\s?tech\b|\bb\.?e\.?\b", re.I)),
    ("MBA", re.compile(r"\bmba\b", re.I)),
    ("M.Sc", re.compile(r"\bm\.?\s?sc\b|\bmsc\b", re.I)),
    ("B.Sc", re.compile(r"\bb\.?\s?sc\b|\bbsc\b", re.I)),
    ("B.Com", re.compile(r"\bb\.?\s?com\b|\bbcom\b", re.I)),
    ("M.Com", re.compile(r"\bm\.?\s?com\b", re.I)),
    ("Diploma", re.compile(r"\bdiploma\b", re.I)),
    ("B.A", re.compile(r"\bb\.?\s?a\b(?!\w)", re.I)),
]


def _norm(text):
    return (text or "").lower()


def extract_skills(text):
    """Return sorted list of canonical skill names found in text."""
    low = _norm(text)
    found = set()
    for canonical, rx in _SKILL_PATTERNS:
        if rx.search(low):
            found.add(canonical)
    return sorted(found)


def skill_overlap(jd_text, resume_text):
    jd_skills = set(extract_skills(jd_text))
    resume_skills = set(extract_skills(resume_text))
    matched = sorted(jd_skills & resume_skills)
    missing = sorted(jd_skills - resume_skills)
    extra = sorted(resume_skills - jd_skills)
    return {
        "jd_skills": sorted(jd_skills),
        "resume_skills": sorted(resume_skills),
        "matched": matched,
        "missing": missing,
        "extra": extra,
    }


def extract_cgpa(text):
    """Best-effort CGPA extraction (0-10 scale). Returns float or None."""
    low = _norm(text)
    candidates = []
    for m in re.finditer(r"(\d{1,2}(?:\.\d+)?)\s*(?:/\s*10)?\s*(?:cgpa|gpa|cpi|sgpa)", low):
        candidates.append(float(m.group(1)))
    for m in re.finditer(r"(?:cgpa|gpa|cpi|sgpa)\s*(?:of|:|\-|minimum|min|at least|above|is|=)?\s*(\d{1,2}(?:\.\d+)?)", low):
        candidates.append(float(m.group(1)))
    vals = [v for v in candidates if 0 <= v <= 10]
    return max(vals) if vals else None


def extract_percentage(text):
    low = _norm(text)
    vals = []
    for m in re.finditer(r"(\d{2}(?:\.\d+)?)\s*%", low):
        v = float(m.group(1))
        if 0 <= v <= 100:
            vals.append(v)
    # also "78 percent"
    for m in re.finditer(r"(\d{2}(?:\.\d+)?)\s*percent", low):
        vals.append(float(m.group(1)))
    return max(vals) if vals else None


def jd_cgpa_cutoff(jd_text):
    """Extract a minimum-CGPA cutoff stated in the JD, if any."""
    low = _norm(jd_text)
    near = []
    for m in re.finditer(r"(?:minimum|min|at least|above|greater than|>=)?[^\d]{0,30}(\d{1,2}(?:\.\d+)?)\s*(?:cgpa|gpa|cpi)", low):
        v = float(m.group(1))
        if 4.0 <= v <= 10.0:
            near.append(v)
    for m in re.finditer(r"(?:cgpa|gpa|cpi)[^\d]{0,30}?(\d{1,2}(?:\.\d+)?)", low):
        v = float(m.group(1))
        if 4.0 <= v <= 10.0:
            near.append(v)
    return min(near) if near else None


def extract_experience_years(text):
    low = _norm(text)
    years = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years|yrs|year)", low):
        v = float(m.group(1))
        if 0 <= v <= 40:
            years.append(v)
    return max(years) if years else None


def extract_degrees(text):
    found = []
    for name, rx in DEGREE_PATTERNS:
        if rx.search(text or ""):
            found.append(name)
    return found


def count_achievements(text):
    low = _norm(text)
    return sum(low.count(k) for k in ACHIEVEMENT_KEYWORDS)


def extract_contacts(text):
    emails = EMAIL_RE.findall(text or "")
    phones = PHONE_RE.findall(text or "")
    return {"emails": emails, "phones": phones}
