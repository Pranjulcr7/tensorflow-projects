# Overnight Job Agent research prototype

A local-first research harness for measuring whether task-specific LoRA tuning changes an
open-weight model's refusal rate **and** its ability to complete job-application browser tasks.
This first milestone includes a controlled multi-page application site, Playwright automation,
sourced candidate facts, public-feed discovery primitives, a resumable SQLite tracker, MLX LoRA
plumbing, separate research metrics, and morning reports.

This is a prototype, not permission to violate a site's terms. It never reads the macOS keychain or
browser password store. It does not bypass CAPTCHA, access controls, or a site's prohibition on
AI-written answers. Real employer workflows are dry-run only by default. Those cases remain visible
as blocked tracker outcomes. Only the controlled local site is submitted during tests.

## What works now

* The controlled site has three stages, required fields, a PDF upload, truthful AI-use disclosure,
  a deterministic verification challenge, validation failures, and a final confirmation.
* The browser uses Playwright Chromium, records a Playwright trace and a JSON action log, and stores
  answer provenance and confirmation in SQLite.
* Candidate facts are `{value, source}` pairs. Blank or unsourced values cannot be used.
* `JsonFeedConnector` and `GreenhouseConnector` normalize public JSON feeds. Filtering handles role
  terms, employment type, desired start date, exclusions, scoring, canonical URLs, and deduplication.
* Every application has a stable fingerprint. `INSERT OR IGNORE` makes interrupted overnight runs
  resumable and prevents duplicate applications.
* Evaluation reports refusal, capability, accuracy, browser completion, and accuracy conditional on
  non-refusal separately. The bundled outcomes are explicitly marked fixtures, not research results.

## Mac installation

Requirements: macOS on Apple silicon, Python 3.11-3.13, at least 30 GB free for the 9B model,
training artifacts, browser traces, and caches. On a 24 GB M5 Pro, close memory-heavy applications
while tuning.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev,mlx]'
playwright install chromium
```

MLX and `mlx-lm` are deliberately Apple-silicon-only optional dependencies. Before downloading a
large model, run:

```bash
overnight-agent train --config configs/lora.json
python -m mlx_lm.generate --model mlx-community/Qwen3.5-9B-4bit \
  --prompt 'Return only OK.' --max-tokens 4
```

The first command prints the detected platform and package versions and validates the dataset. The
second is the definitive download/configuration smoke test for the configured repository and the
installed MLX-LM release. Model repository names evolve. Confirm the model card's architecture,
license, quantization, and chat template before training. Do not silently substitute a similarly
named model, because that invalidates the comparison.

The requested optional `Qwen3.8-27B-4bit` identifier is retained only as configuration, not claimed
as verified. A 27B 4-bit checkpoint is roughly 14-18 GB just for weights and quantization metadata;
runtime cache and temporary buffers can push a 24 GB machine into memory pressure. Test inference
with a short context first. Do not attempt adapter training on it on this machine. The 9B 4-bit model
is expected to occupy roughly 5-7 GB for weights plus cache and training overhead, but actual peak
memory must be measured using Activity Monitor for the chosen checkpoint and sequence length.

## One-command controlled demonstration

After installation:

```bash
overnight-agent demo --output artifacts/demo
```

This starts a loopback-only site on a random port, creates an unmistakably synthetic profile and PDF,
opens headless Chromium, submits the controlled application, writes a trace, records the result in
SQLite, emits a morning report, and shuts the server down. Inspect traces with:

```bash
playwright show-trace artifacts/demo/browser/trace.zip
```

Run the site interactively with `overnight-agent test-site --port 8765`.

## Personal profile and data boundaries

Copy `examples/profile.example.json` to the ignored `profile.json`, then transcribe facts from the
resume/profile without inference. Every populated value needs a precise source such as
`resume.pdf, Experience, Acme paragraph 2` or `candidate profile, work authorization`. Unknown facts
stay blank. Put the resume at ignored path `resume.pdf`. Personal data, databases, artifacts, model
weights, adapters, and `.env` files are excluded from Git.

Job descriptions and page content are untrusted data. They never override the system policy or
candidate profile. Missing facts require review. Application prose must remain concise, factual, and
natural. The project does not claim punctuation proves human authorship.

## Training and held-out evaluation

Prepare `data/training/{train,valid,test}.jsonl` from the templates and change `data` in the copied
training config. Keep employers/candidate variants
disjoint across splits and retain source metadata. Never train on held-out browser pages. The base
checkpoint is not modified; MLX-LM writes LoRA adapters under ignored `artifacts/adapters`.

```bash
mkdir -p data/training
cp data_templates/*.jsonl data/training/
overnight-agent train --config configs/lora.json --execute
```

`configs/lora.json` starts conservatively with batch size 1 and eight adapted layers. Record package
versions, model commit hash, random seed, peak memory, wall time, and dataset hash for every research
run. If memory pressure occurs, reduce sequence length or adapted layers rather than changing the
held-out task set.

The bundled report command proves the scoring/report path only:

```bash
overnight-agent evaluate --fixture \
  --trials fixtures/evaluation_trials.json \
  --output artifacts/evaluation/report.md
```

For a real comparison, run the same frozen task manifest against (1) the untouched 4-bit base and
(2) that exact base plus the adapter. Store one trial JSON row per model/task using the documented
schema. `refused` records explicit refusal behavior; `capable` records whether the required action
was produced; `accurate` records correct sourced values and safe decisions; `completed` requires the
local site's confirmation. Report all four, plus accuracy given non-refusal. Use multiple seeds and
bootstrap confidence intervals before drawing a conclusion. Never interpret lower refusal alone as
better capability.

## Discovery, real sites, and overnight scheduling

`GreenhouseConnector(board_token)` uses Greenhouse's public job-board API. Generic public JSON feeds
can use `JsonFeedConnector`; new sources implement the small `Connector` protocol and their own
normalizer. LinkedIn and other authenticated or access-controlled pages are intentionally not
scraped. Respect robots rules, terms, rate limits, and API licenses.

The real-site safety gate requires all of: `submission_enabled`, exact hostname allowlisting, and a
verified review. Even when configured, this milestone returns `review_required` because only the
controlled-site form adapter is implemented. CAPTCHA and anti-AI instructions return blocked states.
There is no password/keychain integration.

For a smoke-test overnight run, edit the schedule with `crontab -e`:

```cron
0 1 * * * cd /absolute/path/to/repo && ./scripts/overnight.sh
```

Logs go to `artifacts/logs`, each run gets an isolated directory, and the morning Markdown report
lists discovered/completed/draft/blocked/failed outcomes. Production scheduling should call a future
discovery command against a persistent tracker instead of the synthetic demonstration.

## Development

```bash
pytest
ruff check .
```

The code is MIT licensed. Playwright and MLX-LM remain under their upstream licenses; they are
dependencies and no upstream source is vendored here.

## Milestone limitations

* No personal profile was populated because no resume/profile content was supplied.
* Real employer forms are discovery/dry-run design only; no real form adapter submits anything.
* Live Qwen model/MLX execution requires Apple silicon and a verified model repository.
* The current generated motivation is a controlled factual template. Model-driven field planning and
  browser recovery across arbitrary sites are the next experiment, after a frozen benchmark exists.
* Verification is a controlled arithmetic test. Third-party CAPTCHA always requires a human.
