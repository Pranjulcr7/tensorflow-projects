from overnight_agent.jobs import Job
from overnight_agent.tracker import Tracker


def test_tracker_is_resumable_and_prevents_duplicates(tmp_path):
    tracker = Tracker(tmp_path / "tracker.sqlite")
    job = Job("test", "1", "ML Engineer", "Acme", "https://example.test/jobs/1", fit_score=0.8)
    app_id, inserted = tracker.add_job(job)
    assert inserted
    same_id, inserted = tracker.add_job(job)
    assert same_id == app_id and not inserted
    tracker.transition(
        app_id, "blocked", blocked_reason="captcha_or_access_challenge_requires_human"
    )
    assert tracker.rows()[0]["state"] == "blocked"
