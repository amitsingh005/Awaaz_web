import pytest
from pydantic import ValidationError
from app.services.planner import (
    PlannerPlan,
    PlannerStep,
    check_special_command,
    generate_plan,
)

def test_special_commands():
    assert check_special_command("kahan hoon?")["command"] == "where_am_i"
    assert check_special_command("ruko")["command"] == "stop"
    assert check_special_command("dobara bolo")["command"] == "repeat"
    assert check_special_command("wapas jao")["command"] == "undo"
    assert check_special_command("Delhi se Bhopal train") is None

def test_planner_schema_validation():
    # Valid schema check
    valid_data = {
        "mode": "read",
        "goal": "Search trains from Delhi to Bhopal",
        "query_or_url": "Delhi to Bhopal trains IRCTC",
        "steps": [{"description": "Search IRCTC schedule", "risky": False}],
        "needs_login": False,
    }
    plan = PlannerPlan(**valid_data)
    assert plan.mode == "read"
    assert len(plan.steps) == 1
    assert plan.steps[0].risky is False

    # Invalid mode check
    with pytest.raises(ValidationError):
        PlannerPlan(
            mode="invalid_mode",
            goal="Test",
            query_or_url="Test",
            steps=[],
            needs_login=False,
        )

@pytest.mark.parametrize(
    "request_text,expected_mode,expect_risky",
    [
        ("Delhi se Bhopal ki kal ki train dhundho", "read", False),
        ("Aaj ka mausam kaisa hai Mumbai mein", "read", False),
        ("Yeh Shatabdi ticket mere liye book kar do", "act", True),
        ("Electricity bill ₹850 ka hai, ise abhi pay kar do", "act", True),
    ],
)
def test_live_planner_generation(request_text, expected_mode, expect_risky):
    """
    Tests live Groq LLM planning engine on real Hinglish phrases.
    """
    plan = generate_plan(request_text)
    assert isinstance(plan, PlannerPlan)
    assert plan.mode == expected_mode
    assert len(plan.goal) > 0
    assert len(plan.query_or_url) > 0

    if expect_risky:
        # At least one step must be marked risky
        has_risky = any(s.risky for s in plan.steps)
        assert has_risky, f"Expected risky step for '{request_text}'"
