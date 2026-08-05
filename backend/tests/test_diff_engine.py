from app.diff_engine import compare_profiles
from app.parser import parse_profile
from app.schema import ComparisonType
from app.tagger import tag_profile

LEFT = """
Demographics:
- Gender: Male
- Race/Ethnicity: Asian
Academics:
- UW GPA: 3.90
- SAT: 1500
Extracurriculars:
- Varsity football captain - Played for 4 years and led 30 players.
Awards:
- State athletic award
"""

RIGHT = """
Demographics:
- Gender: Female
- Race/Ethnicity: Hispanic
Academics:
- UW GPA: 3.92
- SAT: 1510
Extracurriculars:
- Varsity soccer captain - Played for 4 years and led 28 players.
Awards:
- State athletic award
"""


def test_diff_treats_comparable_team_sports_as_shared() -> None:
    result = compare_profiles(tag_profile(parse_profile(LEFT)), tag_profile(parse_profile(RIGHT)))

    activities = next(section for section in result.sections if section.name == "extracurriculars")
    assert len(activities.items) == 1
    assert activities.items[0].comparison_type == ComparisonType.SHARED
    assert "race" not in activities.items[0].explanation.lower()
    assert "gender" not in activities.items[0].explanation.lower()
