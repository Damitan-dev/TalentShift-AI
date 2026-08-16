# models.py

from datetime import datetime, timezone
# datetime stores dates/times.
# timezone lets us save timestamps in UTC.

from typing import Literal
# Literal restricts a field to specific allowed values.

from uuid import uuid4
# uuid4 gives each object a unique ID.

from pydantic import BaseModel, Field
# BaseModel gives us validation.
# Field lets us create automatic default values.


def utc_now() -> datetime:
    # Return the current time in UTC.
    return datetime.now(timezone.utc)


class Competency(BaseModel):
    # Name of the competency, e.g. "Problem Solving".
    name: str

    # Explain what the competency measures.
    description: str

    # Importance of this competency for the job.
    weight: int

    # Describe the evidence expected from a strong answer.
    strong_answer_looks_like: str


class Job(BaseModel):
    # Automatically generate a unique job ID.
    id: str = Field(default_factory=lambda: str(uuid4()))

    # Job title.
    title: str

    # Job description.
    description: str

    # Competencies used to evaluate this job.
    competencies: list[Competency]

    # Languages supported for this interview.
    languages: list[str]

    # When this job was created.
    created_at: datetime = Field(default_factory=utc_now)

    # When this job was last changed.
    updated_at: datetime | None = None


class Candidate(BaseModel):
    # Automatically generate a unique candidate ID.
    id: str = Field(default_factory=lambda: str(uuid4()))

    # Candidate's name is optional because evaluation should not depend on it.
    full_name: str | None = None

    # Candidate's preferred interview language.
    preferred_language: str

    # When this candidate record was created.
    created_at: datetime = Field(default_factory=utc_now)


class TranscriptTurn(BaseModel):
    # Only these two speaker names are allowed.
    speaker: Literal["candidate", "interviewer"]

    # The words spoken during this turn.
    text: str

    # When this transcript turn was captured.
    timestamp: datetime = Field(default_factory=utc_now)

    # OpenAI's conversation item ID.
    item_id: str | None = None


class Session(BaseModel):
    # Automatically create a unique interview-session ID.
    id: str = Field(default_factory=lambda: str(uuid4()))

    # Which job is being interviewed for.
    job_id: str

    # Which candidate is taking the interview.
    candidate_id: str

    # Current interview state.
    status: Literal[
        "pending",
        "in_progress",
        "completed",
        "failed"
    ] = "pending"

    # Language selected for this interview.
    language: str

    # Consent belongs to this particular interview session.
    consent_given: bool

    # When the interview began.
    started_at: datetime = Field(default_factory=utc_now)

    # None until the interview has actually ended.
    ended_at: datetime | None = None

    # Full labelled transcript for this interview.
    transcript: list[TranscriptTurn] = Field(default_factory=list)