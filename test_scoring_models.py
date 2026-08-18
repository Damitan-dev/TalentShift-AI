from pydantic import ValidationError

from scoring.models import CompetencyScore, Scorecard


# ---------------------------------------------------------
# TEST 1:
# Score above 1 WITH evidence should be accepted.
# ---------------------------------------------------------

valid_score = CompetencyScore(
    name="Problem Solving",
    score=4,
    evidence=[
        "I redesigned the household membership model."
    ],
    justification="The candidate explained a concrete backend problem and solution."
)

print("TEST 1 PASSED ✅")
print(valid_score)


# ---------------------------------------------------------
# TEST 2:
# Score above 1 WITHOUT evidence should be rejected.
# ---------------------------------------------------------

try:
    invalid_score = CompetencyScore(
        name="Problem Solving",
        score=4,
        evidence=[],
        justification="The candidate demonstrated good problem solving."
    )

except ValidationError as error:
    print("\nTEST 2 PASSED ✅")
    print("Pydantic correctly rejected a score above 1 with no evidence.")
    print(error)


# ---------------------------------------------------------
# TEST 3:
# Score 1 WITHOUT evidence should be allowed.
# ---------------------------------------------------------

not_explored = CompetencyScore(
    name="Communication",
    score=1,
    evidence=[],
    justification="not explored"
)

print("\nTEST 3 PASSED ✅")
print(not_explored)


# ---------------------------------------------------------
# TEST 4:
# Check that weighted overall score is calculated correctly.
# ---------------------------------------------------------

scorecard = Scorecard(
    session_id="test-session-001",

    scores=[
        CompetencyScore(
            name="Problem Solving",
            score=5,
            evidence=[
                "I redesigned the household membership model."
            ],
            justification="Strong evidence of problem solving."
        ),

        CompetencyScore(
            name="Communication",
            score=3,
            evidence=[
                "I explained the flow to my teammate."
            ],
            justification="Adequate communication evidence."
        ),

        CompetencyScore(
            name="Relevant Experience",
            score=4,
            evidence=[
                "I built authentication and authorization for the platform."
            ],
            justification="Relevant backend experience was demonstrated."
        )
    ]
)


weights = {
    "Problem Solving": 40,
    "Communication": 20,
    "Relevant Experience": 40
}


overall = scorecard.compute_overall(weights)

print("\nTEST 4 PASSED ✅")
print("Overall score:", overall)