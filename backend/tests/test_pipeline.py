from app.pipeline import run_comparison

LEFT = """
Academics:
- UW GPA: 3.8
- SAT: 1470
Extracurriculars:
- Coding club member - Built small Python projects for 2 years.
"""

RIGHT = """
Academics:
- UW GPA: 3.9
- SAT: 1520
Extracurriculars:
- Robotics captain - Led a 12-person robotics team for 3 years.
"""


def test_pipeline_returns_all_three_sections() -> None:
    result = run_comparison(LEFT, RIGHT)

    assert [section.name for section in result.sections] == [
        "academics",
        "extracurriculars",
        "awards",
    ]
    assert result.left_profile_id
    assert result.right_profile_id
    assert result.warnings
