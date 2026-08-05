from fastapi import FastAPI

from app.diff_engine import compare_profiles
from app.parser import parse_profile
from app.pipeline import run_comparison
from app.schema import (
    CompareRawProfilesRequest,
    CompareTaggedProfilesRequest,
    DiffResult,
    Profile,
    RawProfileRequest,
    TaggedProfile,
)
from app.tagger import tag_profile

app = FastAPI(
    title="College Profile Comparator API",
    version="0.1.0",
    description=(
        "Parses, tags, and compares college applicant profiles using explainable placeholder "
        "logic. It does not calculate admission probabilities."
    ),
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/profiles/parse", response_model=Profile)
def parse_profile_endpoint(request: RawProfileRequest) -> Profile:
    return parse_profile(request.raw_input)


@app.post("/profiles/tag", response_model=TaggedProfile)
def tag_profile_endpoint(profile: Profile) -> TaggedProfile:
    return tag_profile(profile)


@app.post("/profiles/compare", response_model=DiffResult)
def compare_profiles_endpoint(request: CompareTaggedProfilesRequest) -> DiffResult:
    return compare_profiles(request.left, request.right)


@app.post("/pipeline/compare-raw", response_model=DiffResult)
def compare_raw_profiles_endpoint(request: CompareRawProfilesRequest) -> DiffResult:
    return run_comparison(request.left_raw, request.right_raw)
