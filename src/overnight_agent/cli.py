from __future__ import annotations

import argparse
import json
from pathlib import Path

from .browser import BrowserAgent
from .evaluation import load_trials, write_report
from .jobs import Job
from .profile import CandidateProfile
from .report import morning_report
from .testsite import serve
from .tracker import Tracker, now
from .training import compatibility, train


def synthetic_pdf(path: Path) -> None:
    # Tiny valid one-page PDF, used only by the controlled test fixture.
    content = b"BT /F1 12 Tf 72 720 Td (Synthetic research resume) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for idx, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{idx} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(data)
    data += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    data += b"".join(f"{off:010d} 00000 n \n".encode() for off in offsets[1:])
    data += (
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    path.write_bytes(data)


def demo(args: argparse.Namespace) -> int:
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    profile_path, resume_path = root / "synthetic-profile.json", root / "synthetic-resume.pdf"
    profile_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "facts": {
                    "name": {
                        "value": "Research Candidate",
                        "source": "controlled synthetic fixture",
                    },
                    "email": {
                        "value": "candidate@example.test",
                        "source": "controlled synthetic fixture",
                    },
                    "start_date": {"value": "2027-01-01", "source": "controlled synthetic fixture"},
                },
            },
            indent=2,
        )
    )
    synthetic_pdf(resume_path)
    server, _ = serve(upload_dir=root / "uploads")
    url = f"http://127.0.0.1:{server.server_port}/"
    tracker = Tracker(root / "demo.sqlite")
    job = Job(
        "controlled",
        "local-1",
        "Applied ML Engineer",
        "Local Research Co",
        url,
        "Machine learning",
        "Local",
        "full-time",
        "2027-01-01",
        fit_score=1.0,
    )
    app_id, _ = tracker.add_job(job)
    try:
        result = BrowserAgent(
            CandidateProfile.load(profile_path), resume_path, root
        ).apply_controlled(url)
        fields = {
            "browser_trace": result.get("trace"),
            "answer_provenance": result.get("provenance", {}),
        }
        if result["state"] == "submitted":
            fields.update(submission_confirmation=result["confirmation"], submitted_at=now())
        else:
            fields["blocked_reason"] = result.get("reason")
        tracker.transition(app_id, result["state"], **fields)
    finally:
        server.shutdown()
        server.server_close()
    report_path = morning_report(tracker, root / "morning-report.md")
    print(json.dumps({"result": result, "report": str(report_path)}, indent=2))
    return 0 if result["state"] == "submitted" else 2


def evaluate(args: argparse.Namespace) -> int:
    trials = load_trials(args.trials)
    metrics = write_report(trials, args.output, fixture=args.fixture)
    print(json.dumps(metrics, indent=2))
    return 0


def training(args: argparse.Namespace) -> int:
    config = json.loads(Path(args.config).read_text())
    print(
        json.dumps(
            {"compatibility": compatibility(), "command": train(config, args.execute)}, indent=2
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="overnight-agent")
    sub = parser.add_subparsers(dest="command", required=True)
    p_demo = sub.add_parser("demo", help="run controlled browser E2E")
    p_demo.add_argument("--output", default="artifacts/demo")
    p_demo.set_defaults(func=demo)
    p_eval = sub.add_parser("evaluate", help="score baseline and adapter trials")
    p_eval.add_argument("--trials", default="fixtures/evaluation_trials.json")
    p_eval.add_argument("--output", default="artifacts/evaluation/report.md")
    p_eval.add_argument("--fixture", action="store_true")
    p_eval.set_defaults(func=evaluate)
    p_train = sub.add_parser("train", help="validate or run MLX LoRA command")
    p_train.add_argument("--config", default="configs/lora.json")
    p_train.add_argument("--execute", action="store_true")
    p_train.set_defaults(func=training)
    p_site = sub.add_parser("test-site", help="serve the controlled application site")
    p_site.add_argument("--port", type=int, default=8765)

    def run_site(ns):
        server, _ = serve(port=ns.port)
        print(f"http://127.0.0.1:{server.server_port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        return 0

    p_site.set_defaults(func=run_site)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
