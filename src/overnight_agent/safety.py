from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class SubmissionPolicy:
    controlled_hosts: tuple[str, ...] = ("127.0.0.1", "localhost")
    real_submission_enabled: bool = False
    allowlisted_hosts: tuple[str, ...] = ()
    verified_review: bool = False

    def decision(self, url: str) -> tuple[bool, str]:
        host = (urlsplit(url).hostname or "").lower()
        if host in self.controlled_hosts:
            return True, "controlled_test_site"
        if not self.real_submission_enabled:
            return False, "real_submission_disabled"
        if host not in self.allowlisted_hosts:
            return False, "host_not_allowlisted"
        if not self.verified_review:
            return False, "verified_review_required"
        return True, "explicitly_allowlisted_and_reviewed"


BLOCKING_CHALLENGE_TERMS = ("captcha", "recaptcha", "hcaptcha", "turnstile")


def page_block_reason(text: str) -> str | None:
    lowered = text.lower()
    if any(term in lowered for term in BLOCKING_CHALLENGE_TERMS):
        return "captcha_or_access_challenge_requires_human"
    if "do not use ai" in lowered or "no ai" in lowered:
        return "site_prohibits_ai_generated_answer"
    return None
