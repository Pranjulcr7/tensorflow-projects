from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from .profile import CandidateProfile
from .safety import SubmissionPolicy, page_block_reason


class BrowserAgent:
    def __init__(
        self,
        profile: CandidateProfile,
        resume: str | Path,
        artifact_dir: str | Path,
        policy: SubmissionPolicy | None = None,
        headless: bool = True,
    ) -> None:
        self.profile, self.resume = profile, Path(resume)
        self.artifact_dir = Path(artifact_dir)
        self.policy = policy or SubmissionPolicy()
        self.headless = headless
        self.actions: list[dict] = []
        self.provenance: dict[str, dict] = {}

    def record(self, action: str, **details) -> None:
        self.actions.append(
            {"at": datetime.now(timezone.utc).isoformat(), "action": action, **details}
        )

    def sourced(self, field: str, fact: str) -> str:
        value, source = self.profile.require(fact)
        self.provenance[field] = source
        return str(value)

    def apply_controlled(self, url: str) -> dict:
        allowed, reason = self.policy.decision(url)
        if not allowed:
            return {"state": "blocked", "reason": reason}
        if not self.resume.is_file():
            raise FileNotFoundError(f"Resume not found: {self.resume}")
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Install the project and run `playwright install chromium`") from exc

        trace_dir = self.artifact_dir / "browser"
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_zip = trace_dir / "trace.zip"
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=self.headless)
            context = browser.new_context()
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()
            page.goto(url, wait_until="networkidle")
            self.record("navigate", url=url)
            page.click("#apply")
            page.fill('[name="name"]', self.sourced("name", "name"))
            page.fill('[name="email"]', self.sourced("email", "email"))
            page.fill('[name="start_date"]', self.sourced("start_date", "start_date"))
            self.record("fill", fields=["name", "email", "start_date"])
            page.click("button")
            page.wait_for_load_state("networkidle")
            blocked = page_block_reason(page.locator("body").inner_text())
            if blocked:
                context.tracing.stop(path=trace_zip)
                browser.close()
                return {"state": "blocked", "reason": blocked, "trace": str(trace_zip)}
            page.set_input_files('[name="resume"]', str(self.resume.resolve()))
            motivation = (
                "I am interested in this role and would welcome the opportunity to contribute."
            )
            page.fill('[name="motivation"]', motivation)
            page.check('[name="ai_used"]')
            self.provenance["motivation"] = {
                "fact": "template",
                "source": "repository factual template",
            }
            self.record("upload_and_answer", ai_disclosed=True)
            page.click("button")
            page.wait_for_load_state("networkidle")
            page.fill('[name="verification"]', "13")
            self.record("solve_controlled_verification", expression="7 + 6", answer="13")
            page.click("#submit")
            page.wait_for_selector("#success")
            confirmation = page.locator("#confirmation").inner_text()
            self.record("submit", confirmation=confirmation)
            context.tracing.stop(path=trace_zip)
            browser.close()
        actions_path = trace_dir / "actions.json"
        actions_path.write_text(json.dumps(self.actions, indent=2))
        return {
            "state": "submitted",
            "confirmation": confirmation,
            "trace": str(trace_zip),
            "actions": str(actions_path),
            "provenance": self.provenance,
        }

    def inspect_real_site(self, url: str) -> dict:
        """Policy-only dry-run entry point. It never reads password stores or submits."""
        allowed, reason = self.policy.decision(url)
        if not allowed:
            self.record("blocked_before_submission", url=url, reason=reason)
            return {"state": "draft", "reason": reason, "url": url}
        return {
            "state": "review_required",
            "reason": "browser implementation supports controlled site only",
        }
