from overnight_agent.safety import SubmissionPolicy, page_block_reason


def test_real_submission_requires_all_three_gates():
    url = "https://jobs.example.com/apply"
    assert SubmissionPolicy().decision(url) == (False, "real_submission_disabled")
    assert SubmissionPolicy(real_submission_enabled=True).decision(url) == (
        False,
        "host_not_allowlisted",
    )
    policy = SubmissionPolicy(real_submission_enabled=True, allowlisted_hosts=("jobs.example.com",))
    assert policy.decision(url) == (False, "verified_review_required")
    policy = SubmissionPolicy(
        real_submission_enabled=True, allowlisted_hosts=("jobs.example.com",), verified_review=True
    )
    assert policy.decision(url)[0]


def test_unsafe_page_instructions_are_blocked():
    assert (
        page_block_reason("Please complete hCaptcha")
        == "captcha_or_access_challenge_requires_human"
    )
    assert (
        page_block_reason("Do not use AI for your answer") == "site_prohibits_ai_generated_answer"
    )
