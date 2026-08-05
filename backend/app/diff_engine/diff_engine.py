from __future__ import annotations

from collections.abc import Callable

from app.schema import (
    ComparisonType,
    DiffItem,
    DiffResult,
    DiffSection,
    TaggedAward,
    TaggedExtracurricular,
    TaggedProfile,
)


def compare_profiles(left: TaggedProfile, right: TaggedProfile) -> DiffResult:
    """Create an explainable comparison without using sensitive demographics."""

    academic_items = _compare_academics(left, right)
    activity_items = _compare_activities(left.extracurriculars, right.extracurriculars)
    award_items = _compare_awards(left.awards, right.awards)

    sections = [
        DiffSection(name="academics", items=academic_items),
        DiffSection(name="extracurriculars", items=activity_items),
        DiffSection(name="awards", items=award_items),
    ]

    all_items = [item for section in sections for item in section.items]
    counts = {comparison_type: 0 for comparison_type in ComparisonType}
    for item in all_items:
        counts[item.comparison_type] += 1

    overall_summary = (
        f"Found {counts[ComparisonType.SHARED]} broadly shared comparisons, "
        f"{counts[ComparisonType.LEFT_STRONGER_EVIDENCE]} areas with stronger evidence on "
        f"the left, {counts[ComparisonType.RIGHT_STRONGER_EVIDENCE]} on the right, and "
        f"{counts[ComparisonType.DIFFERENT_DIRECTION]} differences that should not be "
        "directly ranked."
    )

    return DiffResult(
        left_profile_id=left.profile.profile_id,
        right_profile_id=right.profile.profile_id,
        sections=sections,
        overall_summary=overall_summary,
        warnings=[
            "This comparison is descriptive and is not an admission probability.",
            "Race and gender are not used to score activities or determine similarity.",
            "Self-reported profiles may be incomplete, exaggerated, or unrepresentative.",
        ],
    )


def _compare_academics(left: TaggedProfile, right: TaggedProfile) -> list[DiffItem]:
    left_academics = left.profile.academics
    right_academics = right.profile.academics
    specifications: list[tuple[str, float | int | None, float | int | None, float]] = [
        ("Unweighted GPA", left_academics.gpa_unweighted, right_academics.gpa_unweighted, 0.15),
        ("Weighted GPA", left_academics.gpa_weighted, right_academics.gpa_weighted, 0.2),
        ("SAT", left_academics.sat_total, right_academics.sat_total, 50),
        ("ACT", left_academics.act_composite, right_academics.act_composite, 2),
        (
            "Course count",
            len(left_academics.coursework),
            len(right_academics.coursework),
            2,
        ),
    ]
    return [
        _numeric_diff_item(label, left_value, right_value, tolerance)
        for label, left_value, right_value, tolerance in specifications
        if left_value is not None or right_value is not None
    ]


def _numeric_diff_item(
    label: str,
    left_value: float | int | None,
    right_value: float | int | None,
    tolerance: float,
) -> DiffItem:
    if left_value is None or right_value is None:
        return DiffItem(
            label=label,
            comparison_type=ComparisonType.INSUFFICIENT_INFORMATION,
            left_summary=_format_number(left_value),
            right_summary=_format_number(right_value),
            explanation="One profile is missing this metric, so a comparison is not reliable.",
            confidence=0.45,
        )

    difference = float(left_value) - float(right_value)
    if abs(difference) <= tolerance:
        comparison_type = ComparisonType.SHARED
        explanation = f"The reported values are within the comparison tolerance of {tolerance}."
    elif difference > 0:
        comparison_type = ComparisonType.LEFT_STRONGER_EVIDENCE
        explanation = "The left profile reports a higher value for this academic metric."
    else:
        comparison_type = ComparisonType.RIGHT_STRONGER_EVIDENCE
        explanation = "The right profile reports a higher value for this academic metric."

    return DiffItem(
        label=label,
        comparison_type=comparison_type,
        left_summary=_format_number(left_value),
        right_summary=_format_number(right_value),
        explanation=explanation,
        confidence=0.9,
    )


def _compare_activities(
    left_items: list[TaggedExtracurricular],
    right_items: list[TaggedExtracurricular],
) -> list[DiffItem]:
    pairs, unmatched_left, unmatched_right = _greedy_align(
        left_items,
        right_items,
        similarity=_activity_similarity,
        threshold=0.45,
    )

    results = [_activity_pair_diff(left, right, similarity) for left, right, similarity in pairs]
    results.extend(_unmatched_activity_diff(item, side="left") for item in unmatched_left)
    results.extend(_unmatched_activity_diff(item, side="right") for item in unmatched_right)
    return results


def _activity_similarity(left: TaggedExtracurricular, right: TaggedExtracurricular) -> float:
    category_score = 0.65 if left.category == right.category else 0.0
    tag_score = 0.25 * _jaccard(set(left.subtags), set(right.subtags))
    name_score = 0.1 * _jaccard(
        set(left.activity.name.lower().split()),
        set(right.activity.name.lower().split()),
    )
    return round(category_score + tag_score + name_score, 3)


def _activity_pair_diff(
    left: TaggedExtracurricular,
    right: TaggedExtracurricular,
    similarity: float,
) -> DiffItem:
    shared_tags = sorted(set(left.subtags) & set(right.subtags))
    left_only = sorted(set(left.subtags) - set(right.subtags))
    right_only = sorted(set(right.subtags) - set(left.subtags))

    if min(left.tagging_confidence, right.tagging_confidence) < 0.5:
        comparison_type = ComparisonType.INSUFFICIENT_INFORMATION
        explanation = "At least one activity has low tagging confidence."
    else:
        strength_gap = left.signals.evidence_strength - right.signals.evidence_strength
        if abs(strength_gap) <= 0.12:
            comparison_type = ComparisonType.SHARED
            explanation = (
                "These activities occupy a similar category and have comparable documented "
                "depth. The activity names do not need to match exactly."
            )
        elif strength_gap > 0:
            comparison_type = ComparisonType.LEFT_STRONGER_EVIDENCE
            explanation = (
                "The left activity has stronger documented evidence based on leadership, "
                "duration, commitment, and measurable impact—not because its category is "
                "inherently better."
            )
        else:
            comparison_type = ComparisonType.RIGHT_STRONGER_EVIDENCE
            explanation = (
                "The right activity has stronger documented evidence based on leadership, "
                "duration, commitment, and measurable impact—not because its category is "
                "inherently better."
            )

    return DiffItem(
        label=f"{left.category}: {left.activity.name} ↔ {right.activity.name}",
        comparison_type=comparison_type,
        left_ref=left.activity.activity_id,
        right_ref=right.activity.activity_id,
        left_summary=_activity_summary(left),
        right_summary=_activity_summary(right),
        explanation=explanation,
        shared_tags=shared_tags,
        left_only_tags=left_only,
        right_only_tags=right_only,
        confidence=round(min(similarity, left.tagging_confidence, right.tagging_confidence), 3),
    )


def _unmatched_activity_diff(item: TaggedExtracurricular, side: str) -> DiffItem:
    is_left = side == "left"
    return DiffItem(
        label=f"Different direction: {item.activity.name}",
        comparison_type=ComparisonType.DIFFERENT_DIRECTION,
        left_ref=item.activity.activity_id if is_left else None,
        right_ref=None if is_left else item.activity.activity_id,
        left_summary=_activity_summary(item) if is_left else None,
        right_summary=None if is_left else _activity_summary(item),
        explanation=(
            "No sufficiently similar activity was found in the other profile. This is a "
            "different direction, not automatically a deficiency."
        ),
        left_only_tags=item.subtags if is_left else [],
        right_only_tags=[] if is_left else item.subtags,
        confidence=item.tagging_confidence,
    )


def _compare_awards(
    left_items: list[TaggedAward],
    right_items: list[TaggedAward],
) -> list[DiffItem]:
    pairs, unmatched_left, unmatched_right = _greedy_align(
        left_items,
        right_items,
        similarity=_award_similarity,
        threshold=0.55,
    )
    results = [_award_pair_diff(left, right, similarity) for left, right, similarity in pairs]
    results.extend(_unmatched_award_diff(item, side="left") for item in unmatched_left)
    results.extend(_unmatched_award_diff(item, side="right") for item in unmatched_right)
    return results


def _award_similarity(left: TaggedAward, right: TaggedAward) -> float:
    category_score = 0.75 if left.category == right.category else 0.0
    tag_score = 0.25 * _jaccard(set(left.subtags), set(right.subtags))
    return round(category_score + tag_score, 3)


def _award_pair_diff(left: TaggedAward, right: TaggedAward, similarity: float) -> DiffItem:
    gap = left.evidence_strength - right.evidence_strength
    if abs(gap) <= 0.12:
        comparison_type = ComparisonType.SHARED
        explanation = "The awards have a similar category and documented level."
    elif gap > 0:
        comparison_type = ComparisonType.LEFT_STRONGER_EVIDENCE
        explanation = "The left award has a higher documented level or clearer supporting detail."
    else:
        comparison_type = ComparisonType.RIGHT_STRONGER_EVIDENCE
        explanation = "The right award has a higher documented level or clearer supporting detail."

    return DiffItem(
        label=f"{left.category}: {left.award.name} ↔ {right.award.name}",
        comparison_type=comparison_type,
        left_ref=left.award.award_id,
        right_ref=right.award.award_id,
        left_summary=left.award.name,
        right_summary=right.award.name,
        explanation=explanation,
        shared_tags=sorted(set(left.subtags) & set(right.subtags)),
        left_only_tags=sorted(set(left.subtags) - set(right.subtags)),
        right_only_tags=sorted(set(right.subtags) - set(left.subtags)),
        confidence=round(min(similarity, left.tagging_confidence, right.tagging_confidence), 3),
    )


def _unmatched_award_diff(item: TaggedAward, side: str) -> DiffItem:
    is_left = side == "left"
    return DiffItem(
        label=f"Different direction: {item.award.name}",
        comparison_type=ComparisonType.DIFFERENT_DIRECTION,
        left_ref=item.award.award_id if is_left else None,
        right_ref=None if is_left else item.award.award_id,
        left_summary=item.award.name if is_left else None,
        right_summary=None if is_left else item.award.name,
        explanation=(
            "No award with a sufficiently similar category was found in the other profile. "
            "This should not be treated as a direct ranking."
        ),
        left_only_tags=item.subtags if is_left else [],
        right_only_tags=[] if is_left else item.subtags,
        confidence=item.tagging_confidence,
    )


def _greedy_align(
    left_items: list,
    right_items: list,
    similarity: Callable[[object, object], float],
    threshold: float,
) -> tuple[list[tuple[object, object, float]], list[object], list[object]]:
    candidates = []
    for left_index, left_item in enumerate(left_items):
        for right_index, right_item in enumerate(right_items):
            score = similarity(left_item, right_item)
            if score >= threshold:
                candidates.append((score, left_index, right_index))

    candidates.sort(reverse=True)
    used_left: set[int] = set()
    used_right: set[int] = set()
    pairs = []
    for score, left_index, right_index in candidates:
        if left_index in used_left or right_index in used_right:
            continue
        used_left.add(left_index)
        used_right.add(right_index)
        pairs.append((left_items[left_index], right_items[right_index], score))

    unmatched_left = [item for index, item in enumerate(left_items) if index not in used_left]
    unmatched_right = [item for index, item in enumerate(right_items) if index not in used_right]
    return pairs, unmatched_left, unmatched_right


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 0.0
    return len(left & right) / len(left | right)


def _activity_summary(item: TaggedExtracurricular) -> str:
    parts = [item.activity.name, f"category={item.category}"]
    if item.signals.leadership_level:
        parts.append(f"leadership={item.signals.leadership_level.value}")
    if item.signals.duration_years is not None:
        parts.append(f"years={item.signals.duration_years:g}")
    parts.append(f"evidence={item.signals.evidence_strength:.2f}")
    return "; ".join(parts)


def _format_number(value: float | int | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)
