"""Explainable, deterministic scoring rubric (0-100).

Weights
  skills 45 | experience 20 | education 15 | academics (CGPA/%) 10 | extras 10

No LLM is involved in scoring. Verdict thresholds live here so tests and UI
stay in sync.
"""
import math

from . import parsing

WEIGHTS = {"skills": 45, "experience": 20, "education": 15, "cgpa": 10, "extras": 10}
SHORTLIST_AT = 75
HOLD_AT = 55


def _skills_points(jd_text, resume_text):
    overlap = parsing.skill_overlap(jd_text, resume_text)
    required = overlap["jd_skills"]
    matched = overlap["matched"]
    flags = []
    if required:
        pts = 45.0 * len(matched) / len(required)
    else:
        pts = 22.0  # JD states no recognisable skills -> neutral score
        flags.append("No specific skills detected in JD; skills scored neutral (22/45)")
    if not resume_text.strip():
        pts = 0.0
    return round(pts), overlap, flags


def _experience_points(jd_text, resume_text):
    jd_req = parsing.extract_experience_years(jd_text)
    yrs = parsing.extract_experience_years(resume_text)
    flags = []
    if jd_req:
        if yrs is None:
            pts = 10
            flags.append("Years of experience not stated in resume")
        else:
            pts = round(min(1.0, yrs / jd_req) * WEIGHTS["experience"])
    else:
        pts = 15 if yrs else 12
    return pts, yrs, jd_req, flags


def _education_points(jd_text, resume_text):
    jd_degrees = parsing.extract_degrees(jd_text)
    rs_degrees = parsing.extract_degrees(resume_text)
    flags = []
    if jd_degrees:
        if any(d in rs_degrees for d in jd_degrees):
            pts = WEIGHTS["education"]
        elif rs_degrees:
            pts = 11
            flags.append(f"JD asks for {', '.join(jd_degrees)}; resume shows {', '.join(rs_degrees)}")
        else:
            pts = 4
            flags.append("No degree detected in resume though JD specifies one")
    else:
        pts = WEIGHTS["education"] if rs_degrees else 6
        if not rs_degrees:
            flags.append("No degree detected in resume")
    return pts, rs_degrees, flags


def _cgpa_points(jd_text, resume_text):
    cutoff = parsing.jd_cgpa_cutoff(jd_text)
    cgpa = parsing.extract_cgpa(resume_text)
    pct = parsing.extract_percentage(resume_text)
    flags = []
    value10 = None  # resume academics normalised to /10
    if cgpa is not None:
        value10 = cgpa
    elif pct is not None:
        value10 = pct / 10.0
    if value10 is None:
        pts = 6
        flags.append("CGPA / percentage not stated in resume")
    else:
        v = value10
        if v >= 8.5:
            pts = 10
        elif v >= 7.5:
            pts = 9
        elif v >= 6.5:
            pts = 8
        elif v >= 6.0:
            pts = 6
        elif v >= 5.0:
            pts = 4
        else:
            pts = 2
    if cutoff is not None:
        stated = cgpa if cgpa is not None else (pct / 10.0 if pct is not None else None)
        if stated is None:
            flags.append(f"JD states minimum CGPA {cutoff}; resume does not state academics")
            pts = min(pts, 4)
        elif stated < cutoff:
            flags.append(f"Below JD minimum CGPA cutoff of {cutoff}")
            pts = min(pts, 4)
    return pts, cgpa, pct, cutoff, flags


def _extras_points(resume_text):
    n = parsing.count_achievements(resume_text)
    if n >= 4:
        pts = 10
    elif n == 3:
        pts = 8
    elif n == 2:
        pts = 6
    elif n == 1:
        pts = 4
    else:
        pts = 2
    return pts, n


def score_candidate(resume_text, jd_text):
    """Pure function. Raises ValueError on empty JD (caller maps to 400)."""
    if jd_text is None or not str(jd_text).strip():
        raise ValueError("Job description is empty")
    if resume_text is None or not str(resume_text).strip():
        return {
            "total": 0, "verdict": "Reject",
            "breakdown": {k: 0 for k in WEIGHTS},
            "overlap": {"jd_skills": parsing.extract_skills(jd_text), "resume_skills": [],
                        "matched": [], "missing": parsing.extract_skills(jd_text), "extra": []},
            "flags": ["Empty resume received"], "years_experience": None,
            "required_experience": parsing.extract_experience_years(jd_text),
            "degrees": [], "cgpa": None, "percentage": None, "achievement_signals": 0,
        }

    s_pts, overlap, s_flags = _skills_points(jd_text, resume_text)
    e_pts, yrs, jd_req, e_flags = _experience_points(jd_text, resume_text)
    d_pts, degrees, d_flags = _education_points(jd_text, resume_text)
    c_pts, cgpa, pct, cutoff, c_flags = _cgpa_points(jd_text, resume_text)
    x_pts, n_ach = _extras_points(resume_text)

    breakdown = {"skills": s_pts, "experience": e_pts, "education": d_pts,
                 "cgpa": c_pts, "extras": x_pts}
    total = int(math.floor(sum(breakdown.values()) + 0.5))  # deterministic round
    total = max(0, min(100, total))

    if total >= SHORTLIST_AT:
        verdict = "Shortlist"
    elif total >= HOLD_AT:
        verdict = "Hold"
    else:
        verdict = "Reject"

    return {
        "total": total,
        "verdict": verdict,
        "breakdown": breakdown,
        "overlap": overlap,
        "flags": s_flags + e_flags + d_flags + c_flags,
        "years_experience": yrs,
        "required_experience": jd_req,
        "degrees": degrees,
        "cgpa": cgpa,
        "percentage": pct,
        "jd_cgpa_cutoff": cutoff,
        "achievement_signals": n_ach,
    }
