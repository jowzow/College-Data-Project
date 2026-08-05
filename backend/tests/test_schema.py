import pytest
from pydantic import ValidationError

from app.schema import AcademicProfile, Profile


def test_schema_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Profile(academics=AcademicProfile(), gpa_unweigted=3.9)
