from __future__ import annotations

from app.schema import (
    AdvicePriority,
    AdviceResult,
    ComparisonType,
    DiffResult,
    Profile,
)


def generate_advice(profile: Profile, comparison: DiffResult) -> AdviceResult:
    """Return deterministic placeholder advice.

    A future LLM call belongs inside this function or private helpers in this module.
    The parser, tagger, diff engine, and pipeline must not import the advisor.
    """

    priorities: list[AdvicePriority] = []
    right_stronger = [
        item
        for section in comparison.sections
        for item in section.items
        if item.comparison_type == ComparisonType.RIGHT_STRONGER_EVIDENCE
    ]

    if right_stronger:
        priorities.append(
            AdvicePriority(
                title="Improve the evidence behind existing commitments",
                rationale=(
                    "Some comparable items in the other profile include clearer evidence of "
                    "duration, leadership, commitment, or measurable impact."
                ),
                next_steps=[
                    "Choose one existing activity rather than adding several new ones.",
                    "Document what you built, changed, led, or measured.",
                    (
                        "Ask what realistic outcome can be completed with available time "
                        "and resources."
                    ),
                ],
                time_horizon="next 8-12 weeks",
            )
        )
    else:
        priorities.append(
            AdvicePriority(
                title="Clarify and document your current profile",
                rationale=(
                    "This comparison did not identify a clear evidence gap, so the next useful "
                    "step is improving the accuracy and specificity of your own records."
                ),
                next_steps=[
                    "Add duration and weekly commitment where known.",
                    "Record concrete outputs without exaggerating causality.",
                ],
                time_horizon="next 2-4 weeks",
            )
        )

    return AdviceResult(
        profile_id=profile.profile_id,
        comparison_profile_id=comparison.right_profile_id,
        summary=(
            "Use the comparison to identify principles such as sustained depth and clearer "
            "evidence. Do not attempt to copy another student's exact activities."
        ),
        priorities=priorities,
        disclaimers=[
            "This is general planning guidance, not an admission prediction.",
            "Advice should be adjusted to the student's time, resources, and genuine interests.",
        ],
    )
