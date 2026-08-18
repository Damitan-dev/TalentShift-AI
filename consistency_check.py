from scoring.engine import (
    score_transcript,
    EvaluationFailedError
)


RUN_COUNT = 5

# Keep the session ID identical across all runs.
# Consistency testing should change as little as possible.
SESSION_ID = "consistency-test-session"


FIXED_TRANSCRIPT = """
Interviewer: Tell me about a difficult backend problem you solved.

Candidate: I discovered that storing household roles directly
on the user model made it difficult to distinguish an owner
from an occupant across households. I redesigned the architecture
using household membership and tested owner-only routes to ensure
occupants could not access them.

Interviewer: How did you explain the architectural change to others?

Candidate: I explained why the old structure caused problems and showed
the new membership relationship before we continued with the implementation.
"""


FIXED_CANDIDATE_TRANSCRIPT = """
I discovered that storing household roles directly
on the user model made it difficult to distinguish an owner
from an occupant across households. I redesigned the architecture
using household membership and tested owner-only routes to ensure
occupants could not access them.

I explained why the old structure caused problems and showed
the new membership relationship before we continued with the implementation.
"""


RUBRIC = {
    "Problem Solving": {
        "weight": 60,
        "strong_answer_looks_like": (
            "Identifies a concrete problem, explains personal actions, "
            "reasoning, and how the solution was verified."
        )
    },

    "Relevant Experience": {
        "weight": 40,
        "strong_answer_looks_like": (
            "Describes backend implementation work personally completed."
        )
    }
}


runs = []


# Run the EXACT SAME evaluation five times.
for run_number in range(1, RUN_COUNT + 1):

    print(f"\n--- RUN {run_number}/{RUN_COUNT} ---")

    try:
        scorecard = score_transcript(
            session_id=SESSION_ID,
            transcript=FIXED_TRANSCRIPT,
            candidate_transcript=FIXED_CANDIDATE_TRANSCRIPT,
            rubric=RUBRIC
        )

        # Save this successful run so we can compare it later.
        runs.append(scorecard)

        # Print this run's result so we can see individual variation.
        for competency in scorecard.scores:
            print(
                f"{competency.name}: "
                f"{competency.score}/5"
            )

        print(f"Overall: {scorecard.overall}")

    except EvaluationFailedError as error:
        # Don't crash the entire experiment because one
        # evaluator run couldn't produce a valid scorecard.
        print(f"❌ Run {run_number} failed.")
        print(error)


# If every evaluator call failed, min/max would have
# nothing to work with.
if not runs:
    raise RuntimeError(
        "No valid evaluation runs were produced."
    )


print("\nCONSISTENCY RESULTS")
print("-" * 80)

print(
    f"{'Competency':<30}"
    f"{'Scores':<20}"
    f"{'Min':<10}"
    f"{'Max':<10}"
    f"{'Spread':<10}"
)


for competency_name in RUBRIC.keys():

    scores = []

    # Get this particular competency's score
    # from every successful evaluation run.
    for scorecard in runs:

        competency = next(
            score
            for score in scorecard.scores
            if score.name == competency_name
        )

        scores.append(competency.score)


    minimum = min(scores)

    maximum = max(scores)

    spread = maximum - minimum


    print(
        f"{competency_name:<30}"
        f"{str(scores):<20}"
        f"{minimum:<10}"
        f"{maximum:<10}"
        f"{spread:<10}"
    )