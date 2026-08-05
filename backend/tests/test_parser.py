from pathlib import Path

from app.parser import parse_profile

FIXTURES = Path(__file__).parent / "fixtures"


def test_parser_extracts_core_profile_fields() -> None:
    raw = (FIXTURES / "raw_profile.txt").read_text(encoding="utf-8")

    profile = parse_profile(raw)

    assert profile.academics.gpa_unweighted == 3.91
    assert profile.academics.sat_total == 1530
    assert profile.intended_majors == ["Computer Science"]
    assert len(profile.extracurriculars) == 3
    assert profile.extracurriculars[0].years == 4.0
    assert profile.demographics is not None
    assert profile.demographics.state_or_region == "California"
