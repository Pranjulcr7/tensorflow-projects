#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p artifacts/logs
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
exec .venv/bin/overnight-agent demo --output "artifacts/runs/$timestamp" \
  >"artifacts/logs/$timestamp.log" 2>&1
