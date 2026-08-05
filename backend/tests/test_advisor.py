from app.advisor import generate_advice
from app.parser import parse_profile
from app.pipeline import run_comparison

LEFT = """
Academics:
- UW GPA: 3.8
Extracurriculars:
- Coding club - Member.
"""

RIGHT = """
Academics:
- UW GPA: 3.9
Extracurriculars:
- Coding nonprofit founder - Built an app used by 100 students for 3 years.
"""


def test_advisor_returns_grounded_placeholder_priorities() -> None:
    left_profile = parse_profile(LEFT)
    comparison = run_comparison(LEFT, RIGHT)

    advice = generate_advice(left_profile, comparison)

    assert advice.profile_id == left_profile.profile_id
    assert advice.priorities
    assert "copy" in advice.summary.lower()
