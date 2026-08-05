import json
from pathlib import Path

from app.schema import DiffResult, Profile, TaggedProfile

FIXTURES = Path(__file__).parent / "fixtures"


def test_shared_json_fixtures_match_contracts() -> None:
    profile = Profile.model_validate_json((FIXTURES / "profile.json").read_text(encoding="utf-8"))
    tagged = TaggedProfile.model_validate_json(
        (FIXTURES / "tagged_profile.json").read_text(encoding="utf-8")
    )
    diff = DiffResult.model_validate_json(
        (FIXTURES / "diff_result.json").read_text(encoding="utf-8")
    )

    assert tagged.profile.profile_id == profile.profile_id
    assert diff.left_profile_id == profile.profile_id
