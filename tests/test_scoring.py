import pytest

from scoring.models import CompetencyScore, Scorecard
from scoring.engine import score_transcript


def test_score_bounds():
    # Scores are only allowed on TalentSift's 1–5 scale.

    with pytest.raises(ValueError):
        CompetencyScore(
            name="x",
            score=6,
            evidence=["q"],
            justification="j"
        )


def test_evidence_first_rejects_unbacked_scores():
    # A positive score without supporting evidence is invalid.

    with pytest.raises(ValueError):
        CompetencyScore(
            name="Problem Solving",
            score=4,
            evidence=[],
            justification="Strong problem solving."
        )


    # But score 1 may have no evidence because
    # the competency may not have been explored.
    score = CompetencyScore(
        name="Problem Solving",
        score=1,
        evidence=[],
        justification="not explored"
    )


    assert score.score == 1
    assert score.evidence == []


def test_weighted_overall():

    scorecard = Scorecard(
        session_id="test-session",

        scores=[
            CompetencyScore(
                name="Problem Solving",
                score=5,
                evidence=["I redesigned the membership model."],
                justification="Strong problem-solving evidence."
            ),

            CompetencyScore(
                name="Communication",
                score=3,
                evidence=["I explained the change to my teammate."],
                justification="Adequate communication."
            ),

            CompetencyScore(
                name="Relevant Experience",
                score=4,
                evidence=["I built authentication and authorization."],
                justification="Relevant backend experience."
            )
        ]
    )


    weights = {
        "Problem Solving": 40,
        "Communication": 20,
        "Relevant Experience": 40
    }


    # Calculated by hand:
    #
    # (5×40 + 3×20 + 4×40) / 100
    # = (200 + 60 + 160) / 100
    # = 420 / 100
    # = 4.2

    result = scorecard.compute_overall(weights)

    assert result == 4.2


def test_empty_transcript_scores_all_ones():

    rubric = {
        "Problem Solving": {
            "weight": 50,
            "strong_answer_looks_like": "Explains a concrete problem and solution."
        },

        "Communication": {
            "weight": 50,
            "strong_answer_looks_like": "Explains ideas clearly."
        }
    }


    scorecard = score_transcript(
        session_id="empty-session",
        transcript="",
        candidate_transcript="",
        rubric=rubric
    )


    assert len(scorecard.scores) == 2


    for competency in scorecard.scores:

        assert competency.score == 1

        assert competency.evidence == []

        assert competency.justification == "not explored"


    assert scorecard.overall == 1.0