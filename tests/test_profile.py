import json

import pytest

from overnight_agent.profile import CandidateProfile, UnknownFactError


def test_only_returns_sourced_known_facts(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(
        json.dumps(
            {
                "facts": {
                    "name": {"value": "Ada", "source": "resume line 1"},
                    "phone": {"value": "", "source": ""},
                    "guess": {"value": "something", "source": ""},
                }
            }
        )
    )
    profile = CandidateProfile.load(path)
    assert profile.require("name") == ("Ada", {"fact": "name", "source": "resume line 1"})
    assert profile.answer("phone") is None
    with pytest.raises(UnknownFactError):
        profile.require("guess")
