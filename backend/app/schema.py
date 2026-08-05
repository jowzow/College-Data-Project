from __future__ import annotations

from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0"


class StrictModel(BaseModel):
    """Base model used for every public contract in the application."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
        use_enum_values=False,
    )


class SourceType(str, Enum):
    USER_TEXT = "user_text"
    USER_FORM = "user_form"
    REDDIT = "reddit"
    IMPORT = "import"
    TEST = "test"


class ApplicationRound(str, Enum):
    EARLY_DECISION = "early_decision"
    EARLY_ACTION = "early_action"
    RESTRICTIVE_EARLY_ACTION = "restrictive_early_action"
    REGULAR_DECISION = "regular_decision"
    ROLLING = "rolling"
    UNKNOWN = "unknown"


class AwardLevel(str, Enum):
    SCHOOL = "school"
    LOCAL = "local"
    REGIONAL = "regional"
    STATE = "state"
    NATIONAL = "national"
    INTERNATIONAL = "international"
    UNKNOWN = "unknown"


class LeadershipLevel(str, Enum):
    NONE = "none"
    MEMBER = "member"
    INFORMAL_LEAD = "informal_lead"
    OFFICER = "officer"
    PRESIDENT_OR_CAPTAIN = "president_or_captain"
    FOUNDER = "founder"
    UNKNOWN = "unknown"


class ComparisonType(str, Enum):
    SHARED = "shared"
    LEFT_STRONGER_EVIDENCE = "left_stronger_evidence"
    RIGHT_STRONGER_EVIDENCE = "right_stronger_evidence"
    DIFFERENT_DIRECTION = "different_direction"
    INSUFFICIENT_INFORMATION = "insufficient_information"


class Provenance(StrictModel):
    source: SourceType = SourceType.USER_TEXT
    source_reference: str | None = None
    original_text: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    extraction_notes: list[str] = Field(default_factory=list)


class Demographics(StrictModel):
    """Optional metadata. These fields must not be used to score activity quality."""

    gender: str | None = None
    race_ethnicity: list[str] = Field(default_factory=list)
    country: str | None = None
    state_or_region: str | None = None
    citizenship: str | None = None
    school_type: str | None = None
    school_context: str | None = None
    hooks: list[str] = Field(default_factory=list)


class AcademicProfile(StrictModel):
    gpa_unweighted: float | None = Field(default=None, ge=0.0, le=5.0)
    gpa_weighted: float | None = Field(default=None, ge=0.0, le=10.0)
    gpa_scale: float | None = Field(default=4.0, gt=0.0, le=10.0)
    class_rank: int | None = Field(default=None, ge=1)
    class_size: int | None = Field(default=None, ge=1)
    sat_total: int | None = Field(default=None, ge=400, le=1600)
    act_composite: int | None = Field(default=None, ge=1, le=36)
    coursework: list[str] = Field(default_factory=list)
    course_rigor_notes: str | None = None

    @model_validator(mode="after")
    def validate_rank(self) -> AcademicProfile:
        if self.class_rank is not None and self.class_size is not None:
            if self.class_rank > self.class_size:
                raise ValueError("class_rank cannot be larger than class_size")
        return self


class Extracurricular(StrictModel):
    activity_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=3000)
    role: str | None = Field(default=None, max_length=200)
    organization: str | None = Field(default=None, max_length=200)
    category_hint: str | None = Field(default=None, max_length=100)
    grades: list[str] = Field(default_factory=list)
    years: float | None = Field(default=None, ge=0.0, le=20.0)
    hours_per_week: float | None = Field(default=None, ge=0.0, le=168.0)
    weeks_per_year: float | None = Field(default=None, ge=0.0, le=52.0)
    leadership_positions: list[str] = Field(default_factory=list)
    measurable_outcomes: list[str] = Field(default_factory=list)
    source_text: str | None = None


class Award(StrictModel):
    award_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    level: AwardLevel = AwardLevel.UNKNOWN
    year_or_grade: str | None = None
    source_text: str | None = None


class Profile(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    profile_id: str = Field(default_factory=lambda: str(uuid4()))
    display_name: str | None = Field(default=None, max_length=100)
    graduation_year: int | None = Field(default=None, ge=2000, le=2100)
    intended_majors: list[str] = Field(default_factory=list)
    target_colleges: list[str] = Field(default_factory=list)
    application_round: ApplicationRound = ApplicationRound.UNKNOWN
    academics: AcademicProfile = Field(default_factory=AcademicProfile)
    demographics: Demographics | None = None
    extracurriculars: list[Extracurricular] = Field(default_factory=list)
    awards: list[Award] = Field(default_factory=list)
    additional_context: list[str] = Field(default_factory=list)
    provenance: Provenance = Field(default_factory=Provenance)


class SignalDimensions(StrictModel):
    leadership_level: LeadershipLevel = LeadershipLevel.UNKNOWN
    duration_years: float | None = Field(default=None, ge=0.0, le=20.0)
    commitment_score: float = Field(default=0.0, ge=0.0, le=1.0)
    impact_score: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    dataset_prevalence: float | None = Field(default=None, ge=0.0, le=1.0)


class TaggedExtracurricular(StrictModel):
    activity: Extracurricular
    category: str = Field(min_length=1, max_length=100)
    subtags: list[str] = Field(default_factory=list)
    signals: SignalDimensions = Field(default_factory=SignalDimensions)
    tagging_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    tagging_notes: list[str] = Field(default_factory=list)


class TaggedAward(StrictModel):
    award: Award
    category: str = Field(min_length=1, max_length=100)
    subtags: list[str] = Field(default_factory=list)
    evidence_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    tagging_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    tagging_notes: list[str] = Field(default_factory=list)


class TaggedProfile(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    taxonomy_version: str = "1.0"
    profile: Profile
    extracurriculars: list[TaggedExtracurricular] = Field(default_factory=list)
    awards: list[TaggedAward] = Field(default_factory=list)


class DiffItem(StrictModel):
    diff_item_id: str = Field(default_factory=lambda: str(uuid4()))
    label: str = Field(min_length=1, max_length=300)
    comparison_type: ComparisonType
    left_ref: str | None = None
    right_ref: str | None = None
    left_summary: str | None = None
    right_summary: str | None = None
    explanation: str = Field(min_length=1, max_length=3000)
    shared_tags: list[str] = Field(default_factory=list)
    left_only_tags: list[str] = Field(default_factory=list)
    right_only_tags: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class DiffSection(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    items: list[DiffItem] = Field(default_factory=list)


class DiffResult(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    left_profile_id: str
    right_profile_id: str
    sections: list[DiffSection] = Field(default_factory=list)
    overall_summary: str
    warnings: list[str] = Field(default_factory=list)


class AdvicePriority(StrictModel):
    title: str
    rationale: str
    next_steps: list[str] = Field(default_factory=list)
    time_horizon: str | None = None


class AdviceResult(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    profile_id: str
    comparison_profile_id: str
    summary: str
    priorities: list[AdvicePriority] = Field(default_factory=list)
    disclaimers: list[str] = Field(default_factory=list)


class RawProfileRequest(StrictModel):
    raw_input: str = Field(min_length=1)


class CompareTaggedProfilesRequest(StrictModel):
    left: TaggedProfile
    right: TaggedProfile


class CompareRawProfilesRequest(StrictModel):
    left_raw: str = Field(min_length=1)
    right_raw: str = Field(min_length=1)
