from app.diff_engine import compare_profiles
from app.parser import parse_profile
from app.schema import DiffResult
from app.tagger import tag_profile


def run_comparison(left_raw: str, right_raw: str) -> DiffResult:
    """Run the complete deterministic parsing, tagging, and comparison pipeline."""

    left_profile = parse_profile(left_raw)
    right_profile = parse_profile(right_raw)
    left_tagged = tag_profile(left_profile)
    right_tagged = tag_profile(right_profile)
    return compare_profiles(left_tagged, right_tagged)
