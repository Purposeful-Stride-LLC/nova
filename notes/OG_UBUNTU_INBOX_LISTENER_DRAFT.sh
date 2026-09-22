#!/usr/bin/env bash
# DRAFT — thin STEP inbox on OG Ubuntu node. Install only after SSH profile is real.
# Watches ~/nova-inbox for STEP_*.md, runs allowlisted handler, writes RESULT_*.md + PROOF.
set -euo pipefail
INBOX="${HOME}/nova-inbox"
OUTBOX="${HOME}/nova-outbox"
mkdir -p "$INBOX" "$OUTBOX"
ALLOW_BIN="${ALLOW_BIN:-/usr/bin/ollama:/usr/bin/python3:/bin/cat}"

handle_one() {
  local step="$1"
  local base
  base="$(basename "$step" .md)"
  local result="${OUTBOX}/RESULT_${base#STEP_}.md"
  local proof="${OUTBOX}/PROOF_${base#STEP_}.txt"
  {
    echo "# RESULT for ${base}"
    echo "host: $(hostname)"
    echo "zulu: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo
    # v1: echo plan only — real dispatch is allowlisted later
    echo "Received STEP (not auto-executing shell). First lines:"
    head -n 40 "$step"
  } >"$result"
  local bytes
  bytes=$(wc -c <"$result" | tr -d ' ')
  echo "PROOF: bytes=${bytes} file=${result}" | tee "$proof"
  mv "$step" "${INBOX}/done/"
}

mkdir -p "${INBOX}/done"
shopt -s nullglob
for step in "${INBOX}"/STEP_*.md; do
  handle_one "$step"
done