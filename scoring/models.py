from pydantic import BaseModel, Field, model_validator
# BaseModel gives us validated Pydantic models.
# Field lets us put restrictions on individual fields.
# model_validator lets us validate rules involving multiple fields.


class CompetencyScore(BaseModel):
    # Represents the evaluation result for ONE competency.

    name: str
    # Example:
    # "Problem Solving"
    # "Communication"
    # "Role Motivation"


    score: int = Field(ge=1, le=5)
    # The score MUST be between 1 and 5.
    #
    # ge = greater than or equal to
    # le = less than or equal to
    #
    # So:
    # 0 ❌
    # 1 ✅
    # 3 ✅
    # 5 ✅
    # 6 ❌


    evidence: list[str]
    # Verbatim candidate quotes supporting this score.
    #
    # Example:
    # [
    #     "I redesigned the household membership model...",
    #     "I tested the authorization flow locally..."
    # ]


    justification: str
    # Explanation of WHY the candidate received the score.


    @model_validator(mode="after")
    def evidence_first(self):
        # This validator runs AFTER Pydantic has built
        # the CompetencyScore object.

        if self.score > 1 and not self.evidence:
            # Any score above 1 means the evaluator claims
            # the candidate demonstrated some ability.
            #
            # Therefore there MUST be transcript evidence.
            #
            # An empty list evaluates to False in Python,
            # so "not self.evidence" means the evidence list is empty.

            raise ValueError(
                "A competency score above 1 must include transcript evidence."
            )
            # Reject the scorecard instead of accepting
            # an unsupported positive score.

        return self
        # Pydantic validators using mode="after"
        # must return the validated object.


class Scorecard(BaseModel):
    # Represents the complete evaluation for ONE interview session.

    session_id: str
    # Connect this scorecard back to the interview
    # that produced it.


    scores: list[CompetencyScore]
    # Contains the result for each competency.


    overall: float = 0.0
    # Final weighted score.
    # It starts at 0 until we calculate it.


    def compute_overall(self, weights: dict[str, int]) -> float:
        # weights will look roughly like:
        #
        # {
        #     "Relevant Experience": 25,
        #     "Problem Solving": 30,
        #     "Communication": 20,
        #     "Role Motivation": 15,
        #     "Collaboration and Ownership": 10
        # }

        weighted_total = 0
        # This will accumulate:
        #
        # score × competency weight


        total_weight = 0
        # This lets us calculate the weighted average safely.


        for competency_score in self.scores:
            # Go through each competency result.

            if competency_score.name not in weights:
                # Every scored competency must exist in the rubric.
                #
                # Otherwise we wouldn't know how important
                # that competency is supposed to be.

                raise ValueError(
                    f"No weight found for competency: {competency_score.name}"
                )


            weight = weights[competency_score.name]
            # Find this competency's rubric weight.


            weighted_total += competency_score.score * weight
            # Example:
            #
            # Problem Solving:
            # score = 4
            # weight = 30
            #
            # 4 × 30 = 120


            total_weight += weight
            # Keep track of all weights we've actually used.


        if total_weight == 0:
            # Avoid dividing by zero if the rubric is empty
            # or something went wrong.

            raise ValueError("Total competency weight cannot be zero.")


        overall = weighted_total / total_weight
        # Calculate the weighted average.
        #
        # Example:
        #
        # weighted_total = 380
        # total_weight = 100
        #
        # 380 / 100 = 3.8


        return round(overall, 2)
        # Mentor asked for the result rounded to 2 decimal places.