from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from app.schema import (
    AwardLevel,
    LeadershipLevel,
    Profile,
    SignalDimensions,
    TaggedAward,
    TaggedExtracurricular,
    TaggedProfile,
)

_TAXONOMY_PATH = Path(__file__).with_name("taxonomy.json")

_LEADERSHIP_PRIORITY = [
    (LeadershipLevel.FOUNDER, ("founder", "co-founder")),
    (LeadershipLevel.PRESIDENT_OR_CAPTAIN, ("president", "captain")),
    (LeadershipLevel.OFFICER, ("vice president", "officer", "chair", "director")),
    (LeadershipLevel.INFORMAL_LEAD, ("lead", "organized", "managed", "coordinated")),
    (LeadershipLevel.MEMBER, ("member", "participant")),
]


@lru_cache(maxsize=1)
def _load_taxonomy() -> dict[str, object]:
    with _TAXONOMY_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def tag_profile(profile: Profile) -> TaggedProfile:
    """Attach explainable categories and signal dimensions to a Profile."""

    taxonomy = _load_taxonomy()
    tagged_activities = [
        _tag_activity(activity, taxonomy) for activity in profile.extracurriculars
    ]
    tagged_awards = [_tag_award(award, taxonomy) for award in profile.awards]

    return TaggedProfile(
        taxonomy_version=str(taxonomy["taxonomy_version"]),
        profile=profile,
        extracurriculars=tagged_activities,
        awards=tagged_awards,
    )


def _tag_activity(activity, taxonomy: dict[str, object]) -> TaggedExtracurricular:
    text = " ".join(
        value
        for value in [
            activity.name,
            activity.description,
            activity.role,
            activity.organization,
            activity.category_hint,
            activity.source_text,
        ]
        if value
    ).lower()

    category, category_matches = _best_keyword_group(
        text,
        taxonomy["activity_categories"],
    )
    subtags = _all_matching_groups(text, taxonomy["activity_subtags"])
    leadership_level = _leadership_level(text)
    commitment_score = _commitment_score(activity)
    impact_score = _impact_score(activity, text)
    evidence_strength = _evidence_strength(
        activity=activity,
        leadership_level=leadership_level,
        commitment_score=commitment_score,
        impact_score=impact_score,
    )

    confidence = 0.55 if category == "other" else min(0.95, 0.65 + 0.07 * category_matches)
    notes = []
    if category == "other":
        notes.append("No taxonomy keyword matched; category defaults to 'other'.")
    if not activity.description:
        notes.append("Description is missing, so signal estimates are conservative.")

    return TaggedExtracurricular(
        activity=activity,
        category=category,
        subtags=subtags,
        signals=SignalDimensions(
            leadership_level=leadership_level,
            duration_years=activity.years,
            commitment_score=commitment_score,
            impact_score=impact_score,
            evidence_strength=evidence_strength,
            dataset_prevalence=None,
        ),
        tagging_confidence=round(confidence, 3),
        tagging_notes=notes,
    )


def _tag_award(award, taxonomy: dict[str, object]) -> TaggedAward:
    text = " ".join(value for value in [award.name, award.description] if value).lower()
    category, matches = _best_keyword_group(text, taxonomy["award_categories"])
    subtags = []
    if award.level is not AwardLevel.UNKNOWN:
        subtags.append(f"level:{award.level.value}")

    level_strength = {
        AwardLevel.UNKNOWN: 0.35,
        AwardLevel.SCHOOL: 0.45,
        AwardLevel.LOCAL: 0.5,
        AwardLevel.REGIONAL: 0.6,
        AwardLevel.STATE: 0.7,
        AwardLevel.NATIONAL: 0.85,
        AwardLevel.INTERNATIONAL: 0.95,
    }[award.level]
    description_bonus = 0.1 if award.description else 0.0
    evidence_strength = min(1.0, level_strength + description_bonus)
    confidence = 0.55 if category == "other" else min(0.95, 0.65 + 0.07 * matches)

    return TaggedAward(
        award=award,
        category=category,
        subtags=subtags,
        evidence_strength=round(evidence_strength, 3),
        tagging_confidence=round(confidence, 3),
        tagging_notes=[] if category != "other" else ["No award taxonomy keyword matched."],
    )


def _best_keyword_group(text: str, groups: object) -> tuple[str, int]:
    assert isinstance(groups, dict)
    best_name = "other"
    best_count = 0
    for name, keywords in groups.items():
        assert isinstance(keywords, list)
        count = sum(1 for keyword in keywords if str(keyword).lower() in text)
        if count > best_count:
            best_name = str(name)
            best_count = count
    return best_name, best_count


def _all_matching_groups(text: str, groups: object) -> list[str]:
    assert isinstance(groups, dict)
    matches = []
    for name, keywords in groups.items():
        assert isinstance(keywords, list)
        if any(str(keyword).lower() in text for keyword in keywords):
            matches.append(str(name))
    return matches


def _leadership_level(text: str) -> LeadershipLevel:
    for level, keywords in _LEADERSHIP_PRIORITY:
        if any(keyword in text for keyword in keywords):
            return level
    return LeadershipLevel.NONE


def _commitment_score(activity) -> float:
    duration = min((activity.years or 0.0) / 4.0, 1.0)
    if activity.hours_per_week is not None and activity.weeks_per_year is not None:
        annual_hours = activity.hours_per_week * activity.weeks_per_year
        intensity = min(annual_hours / 500.0, 1.0)
    elif activity.hours_per_week is not None:
        intensity = min(activity.hours_per_week / 15.0, 1.0)
    else:
        intensity = 0.0
    return round(0.6 * duration + 0.4 * intensity, 3)


def _impact_score(activity, text: str) -> float:
    score = 0.0
    if activity.measurable_outcomes or re.search(r"\b\d+\b", text):
        score += 0.45
    if any(word in text for word in ("users", "served", "raised", "published", "deployed")):
        score += 0.25
    if any(word in text for word in ("statewide", "national", "international", "district-wide")):
        score += 0.2
    if any(word in text for word in ("created", "built", "launched", "organized", "founded")):
        score += 0.1
    return round(min(score, 1.0), 3)


def _evidence_strength(
    activity,
    leadership_level: LeadershipLevel,
    commitment_score: float,
    impact_score: float,
) -> float:
    leadership_score = {
        LeadershipLevel.NONE: 0.0,
        LeadershipLevel.MEMBER: 0.15,
        LeadershipLevel.INFORMAL_LEAD: 0.45,
        LeadershipLevel.OFFICER: 0.65,
        LeadershipLevel.PRESIDENT_OR_CAPTAIN: 0.8,
        LeadershipLevel.FOUNDER: 0.9,
        LeadershipLevel.UNKNOWN: 0.0,
    }[leadership_level]
    description_score = min(len(activity.description or "") / 250.0, 1.0)
    score = (
        0.25 * leadership_score
        + 0.25 * commitment_score
        + 0.35 * impact_score
        + 0.15 * description_score
    )
    return round(min(score, 1.0), 3)
