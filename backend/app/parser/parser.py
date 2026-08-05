from __future__ import annotations

import re
from collections.abc import Iterable

from app.schema import (
    AcademicProfile,
    ApplicationRound,
    Award,
    AwardLevel,
    Demographics,
    Extracurricular,
    Profile,
    Provenance,
    SourceType,
)

_SECTION_ALIASES = {
    "demographics": "demographics",
    "academics": "academics",
    "stats": "academics",
    "extracurriculars": "extracurriculars",
    "extracurricular activities": "extracurriculars",
    "ecs": "extracurriculars",
    "awards": "awards",
    "honors": "awards",
    "target colleges": "target_colleges",
    "colleges": "target_colleges",
    "additional information": "additional_context",
    "additional context": "additional_context",
}

_ROUND_MAP = {
    "ed": ApplicationRound.EARLY_DECISION,
    "early decision": ApplicationRound.EARLY_DECISION,
    "ea": ApplicationRound.EARLY_ACTION,
    "early action": ApplicationRound.EARLY_ACTION,
    "rea": ApplicationRound.RESTRICTIVE_EARLY_ACTION,
    "restrictive early action": ApplicationRound.RESTRICTIVE_EARLY_ACTION,
    "rd": ApplicationRound.REGULAR_DECISION,
    "regular decision": ApplicationRound.REGULAR_DECISION,
    "rolling": ApplicationRound.ROLLING,
}

_LEADERSHIP_WORDS = (
    "founder",
    "co-founder",
    "president",
    "vice president",
    "captain",
    "officer",
    "chair",
    "lead",
    "director",
)


def parse_profile(raw_input: str) -> Profile:
    """Convert ChanceMe-style text into a validated Profile.

    The implementation is deliberately deterministic. Replace its internal helpers with
    a production parser later while preserving this public signature.
    """

    if not raw_input or not raw_input.strip():
        raise ValueError("raw_input cannot be empty")

    academics = AcademicProfile()
    demographics_data: dict[str, object] = {}
    extracurriculars: list[Extracurricular] = []
    awards: list[Award] = []
    intended_majors: list[str] = []
    target_colleges: list[str] = []
    additional_context: list[str] = []
    extraction_notes: list[str] = []
    application_round = ApplicationRound.UNKNOWN

    section: str | None = None
    for raw_line in raw_input.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        heading = _normalize_heading(line)
        if heading in _SECTION_ALIASES:
            section = _SECTION_ALIASES[heading]
            continue

        key, value = _split_key_value(_strip_bullet(line))
        normalized_key = key.lower() if key else ""

        if normalized_key in {"intended major", "intended majors", "major"} and value:
            intended_majors.extend(_split_list(value))
            continue
        if normalized_key in {"application round", "round"} and value:
            application_round = _parse_round(value)
            continue
        if normalized_key in {"graduation year", "class of"} and value:
            # Parsed below after loop through a temporary context note.
            additional_context.append(f"Graduation year: {value}")
            continue

        if section == "academics":
            academics = _parse_academic_line(line, academics, extraction_notes)
        elif section == "demographics":
            _parse_demographic_line(line, demographics_data, extraction_notes)
        elif section == "extracurriculars":
            extracurriculars.append(_parse_extracurricular(line))
        elif section == "awards":
            awards.append(_parse_award(line))
        elif section == "target_colleges":
            target_colleges.extend(_split_list(_strip_bullet(line)))
        elif section == "additional_context":
            additional_context.append(_strip_bullet(line))
        else:
            extraction_notes.append(f"Unclassified line: {line}")

    demographics = Demographics(**demographics_data) if demographics_data else None
    graduation_year = _extract_graduation_year(additional_context)

    return Profile(
        graduation_year=graduation_year,
        intended_majors=_dedupe(intended_majors),
        target_colleges=_dedupe(target_colleges),
        application_round=application_round,
        academics=academics,
        demographics=demographics,
        extracurriculars=extracurriculars,
        awards=awards,
        additional_context=additional_context,
        provenance=Provenance(
            source=SourceType.USER_TEXT,
            original_text=raw_input,
            confidence=_estimate_parse_confidence(
                academics=academics,
                extracurriculars=extracurriculars,
                awards=awards,
            ),
            extraction_notes=extraction_notes,
        ),
    )


def _normalize_heading(line: str) -> str:
    cleaned = re.sub(r"^[#>*\-\s]+", "", line).strip().rstrip(":").strip().lower()
    return cleaned


def _strip_bullet(line: str) -> str:
    return re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()


def _split_key_value(line: str) -> tuple[str | None, str | None]:
    if ":" not in line:
        return None, None
    key, value = line.split(":", 1)
    return key.strip(), value.strip()


def _split_list(value: str) -> list[str]:
    pieces = re.split(r"[,;|]", value)
    return [piece.strip() for piece in pieces if piece.strip()]


def _parse_round(value: str) -> ApplicationRound:
    normalized = value.strip().lower()
    return _ROUND_MAP.get(normalized, ApplicationRound.UNKNOWN)


def _parse_academic_line(
    line: str,
    academics: AcademicProfile,
    notes: list[str],
) -> AcademicProfile:
    text = _strip_bullet(line)
    lower = text.lower()
    updates: dict[str, object] = {}

    rank_match = re.search(r"(?:rank|class rank)\s*[:=]?\s*(\d+)\s*/\s*(\d+)", lower)
    if rank_match:
        updates["class_rank"] = int(rank_match.group(1))
        updates["class_size"] = int(rank_match.group(2))

    if "sat" in lower:
        match = re.search(r"\b(\d{3,4})\b", text)
        if match:
            updates["sat_total"] = int(match.group(1))
    elif "act" in lower:
        match = re.search(r"\b(\d{1,2})\b", text)
        if match:
            updates["act_composite"] = int(match.group(1))
    elif any(token in lower for token in ("uw gpa", "unweighted gpa", "gpa uw")):
        match = re.search(r"(\d+(?:\.\d+)?)", text)
        if match:
            updates["gpa_unweighted"] = float(match.group(1))
    elif any(token in lower for token in ("w gpa", "weighted gpa", "gpa w")):
        match = re.search(r"(\d+(?:\.\d+)?)", text)
        if match:
            updates["gpa_weighted"] = float(match.group(1))
    elif any(token in lower for token in ("coursework", "courses", "aps", "ap classes")):
        _, value = _split_key_value(text)
        if value:
            updates["coursework"] = _dedupe(academics.coursework + _split_list(value))
    elif "rigor" in lower:
        _, value = _split_key_value(text)
        updates["course_rigor_notes"] = value or text
    elif not rank_match:
        notes.append(f"Could not parse academic line: {line}")

    return academics.model_copy(update=updates)


def _parse_demographic_line(
    line: str,
    data: dict[str, object],
    notes: list[str],
) -> None:
    key, value = _split_key_value(_strip_bullet(line))
    if not key or not value:
        notes.append(f"Could not parse demographic line: {line}")
        return

    key = key.lower()
    mapping = {
        "gender": "gender",
        "country": "country",
        "location": "state_or_region",
        "state": "state_or_region",
        "region": "state_or_region",
        "citizenship": "citizenship",
        "school type": "school_type",
        "school context": "school_context",
    }
    if key in {"race", "ethnicity", "race/ethnicity"}:
        data["race_ethnicity"] = _split_list(value)
    elif key in {"hooks", "hook"}:
        data["hooks"] = _split_list(value)
    elif key in mapping:
        data[mapping[key]] = value
    else:
        notes.append(f"Unknown demographic field: {key}")


def _parse_extracurricular(line: str) -> Extracurricular:
    source_text = _strip_bullet(line)
    if " - " in source_text:
        name, description = source_text.split(" - ", 1)
    elif ":" in source_text:
        name, description = source_text.split(":", 1)
    else:
        name, description = source_text, None

    full_text = source_text.lower()
    leadership_positions = [word for word in _LEADERSHIP_WORDS if word in full_text]
    role = leadership_positions[0] if leadership_positions else None

    years_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", full_text)
    hours_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\s*/?\s*(?:week|wk)", full_text)
    weeks_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:weeks?|wks?)\s*/?\s*(?:year|yr)", full_text)

    measurable_outcomes = []
    if re.search(r"\b\d+\b", source_text):
        measurable_outcomes.append(source_text)

    return Extracurricular(
        name=name.strip()[:200],
        description=description.strip() if description else None,
        role=role,
        years=float(years_match.group(1)) if years_match else None,
        hours_per_week=float(hours_match.group(1)) if hours_match else None,
        weeks_per_year=float(weeks_match.group(1)) if weeks_match else None,
        leadership_positions=leadership_positions,
        measurable_outcomes=measurable_outcomes,
        source_text=source_text,
    )


def _parse_award(line: str) -> Award:
    source_text = _strip_bullet(line)
    lower = source_text.lower()
    level = AwardLevel.UNKNOWN
    for candidate in AwardLevel:
        if candidate is not AwardLevel.UNKNOWN and candidate.value in lower:
            level = candidate
            break

    return Award(name=source_text[:300], level=level, source_text=source_text)


def _extract_graduation_year(context: Iterable[str]) -> int | None:
    for item in context:
        match = re.search(r"\b(20\d{2})\b", item)
        if match:
            return int(match.group(1))
    return None


def _estimate_parse_confidence(
    academics: AcademicProfile,
    extracurriculars: list[Extracurricular],
    awards: list[Award],
) -> float:
    signals = [
        academics.gpa_unweighted is not None or academics.gpa_weighted is not None,
        academics.sat_total is not None or academics.act_composite is not None,
        bool(extracurriculars),
        bool(awards),
    ]
    return round(0.45 + 0.125 * sum(signals), 3)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result
