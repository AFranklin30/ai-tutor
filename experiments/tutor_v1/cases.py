"""Version 1 human-authorized synthetic fixtures; expectations never enter model input."""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class Exchange:
    student: str
    tutor: str


@dataclass(frozen=True)
class Case:
    id: str
    message: str
    expectation: str
    problem: Optional[str] = "Solve 3x = 36."
    history: Tuple[Exchange, ...] = ()


CASES = (
    Case("01", "I got 12.", "Ask for the problem; don't judge the answer.", problem=None),
    Case(
        "02",
        "Is that right?",
        "Clarify which answer they mean.",
        history=(Exchange("Maybe x = 12, or maybe x = 33.", "Which answer do you want to check?"),),
    ),
    Case("03", "I got 12.", "Confirm correctness and ask about method without inventing it."),
    Case(
        "04",
        "I divided both sides by 3 and got 12.",
        "Recognize the supplied valid method; don't ask how they got it again.",
    ),
    Case(
        "05",
        "I got 12 by subtracting 3.",
        "Investigate conflicting explanation without assuming a specific misconception.",
    ),
    Case(
        "06",
        "I subtracted 3 and got 33.",
        "Address the demonstrated mistake with correct, useful guidance.",
    ),
    Case(
        "07",
        "I don’t know.",
        "Increase support instead of repeating the same question.",
        history=(
            Exchange("I'm stuck.", "Think about inverse operations. What undoes multiplication?"),
        ),
    ),
    Case(
        "08",
        "12.",
        "Recognize guided success; don't claim independence or mastery.",
        history=(
            Exchange(
                "I don't know what to do.", "Divide both sides by 3. What is 36 divided by 3?"
            ),
        ),
    ),
    Case(
        "09",
        "Division.",
        "Use previous question to interpret the short answer.",
        history=(Exchange("I'm stuck.", "What undoes multiplication?"),),
    ),
    Case(
        "10",
        "I divided both sides by 3 and got x = 12. I checked: 3 × 12 = 36.",
        "Briefly confirm; no unnecessary follow-up required.",
    ),
    Case(
        "11",
        "I used the method I explained earlier.",
        "Ask for the missing method; don't pretend to remember excluded history.",
    ),
    Case(
        "12",
        "Give me a different practice problem.",
        "Offer help with current problem without inventing other assigned work.",
    ),
)
