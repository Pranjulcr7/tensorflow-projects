from overnight_agent.jobs import Job, canonical_url, filter_jobs


def test_normalizes_scores_filters_and_deduplicates():
    a = Job(
        "one",
        "1",
        "Senior ML Engineer",
        "Acme",
        "HTTPS://EXAMPLE.COM/j/1?ref=x",
        "recommender systems",
        employment_type="full-time",
        start_date="2027-01-01",
    )
    duplicate = Job(
        "two",
        "2",
        "Senior ML Engineer",
        "ACME",
        "https://example.com/j/1",
        "recommender systems",
        employment_type="full-time",
    )
    bad = Job("one", "3", "ML Intern", "Acme", "https://example.com/j/3", "unpaid")
    config = {
        "titles": ["ml engineer", "recommender"],
        "employment_types": ["full-time"],
        "start_on_or_after": "2027-01-01",
        "exclude_keywords": ["unpaid"],
    }
    result = filter_jobs([a, duplicate, bad], config)
    assert len(result) == 1
    assert result[0].fit_score == 0.65
    assert canonical_url(a.url) == "https://example.com/j/1"
