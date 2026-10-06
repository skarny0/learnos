#!/usr/bin/env bash
# Batch of real AI-tutor runs: every model x style x seed. Each run is traced to Langfuse and saved
# to data/reference/ (env trace + summary with outcome). Log: data/reference/batch.log
#   caffeinate -i scripts/run_batch.sh            # keep the Mac awake while it runs
set -uo pipefail
cd "$(dirname "$0")/.."
MODELS=${MODELS:-"gpt-5.4-mini gpt-5.4"}
STYLES=${STYLES:-"helpful socratic"}
SEEDS=${SEEDS:-"$(seq 1000 1009)"}
LOG=data/reference/batch.log
mkdir -p data/reference
for m in $MODELS; do for st in $STYLES; do for sd in $SEEDS; do
  echo "=== $(date +%H:%M:%S) $m $st $sd" >> "$LOG"
  .venv/bin/python scripts/run_agent.py --model "$m" --instance friday-build-01-demo --style "$st" --seed "$sd" --max-steps 40 2>&1 \
    > /tmp/learnos_run.$$ 2>&1 || echo "FAILED (exit $?):" >> "$LOG"
  grep -E "^episode|post_test|harms|Langfuse trace|Langfuse check failed|Error|Exception" /tmp/learnos_run.$$ >> "$LOG"
done; done; done
rm -f /tmp/learnos_run.$$
echo "=== $(date +%H:%M:%S) DONE" >> "$LOG"
