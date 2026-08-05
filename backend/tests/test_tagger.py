from pathlib import Path

from app.parser import parse_profile
from app.schema import LeadershipLevel
from app.tagger import tag_profile

FIXTURES = Path(__file__).parent / "fixtures"


def test_tagger_classifies_sports_and_technology() -> None:
    raw = (FIXTURES / "raw_profile.txt").read_text(encoding="utf-8")
    tagged = tag_profile(parse_profile(raw))

    categories = [item.category for item in tagged.extracurriculars]
    assert "athletics" in categories
    assert "technology_engineering" in categories

    football = next(item for item in tagged.extracurriculars if item.category == "athletics")
    assert football.signals.leadership_level == LeadershipLevel.PRESIDENT_OR_CAPTAIN
    assert football.signals.dataset_prevalence is None
