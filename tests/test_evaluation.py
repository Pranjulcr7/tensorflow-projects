from overnight_agent.evaluation import Trial, is_refusal, summarize


def test_refusal_is_separate_from_capability_and_completion():
    rows = [
        Trial("a", "m", True, False, False, False, "refused"),
        Trial("b", "m", False, True, False, False, "attempted inaccurately"),
        Trial("c", "m", False, True, True, True, "complete"),
    ]
    metrics = summarize(rows)["m"]
    assert metrics["refusal_rate"] == 1 / 3
    assert metrics["capability_rate"] == 2 / 3
    assert metrics["accuracy_given_non_refusal"] == 1 / 2
    assert is_refusal("I cannot complete that")
