#!/bin/bash
set -euo pipefail

BRANCH=$(git branch --show-current)
SHA=$(git rev-parse --short HEAD)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE_DIR="test-outputs/${BRANCH}_${SHA}_${TIMESTAMP}"

mkdir -p "$ARCHIVE_DIR"

# Log run metadata
{
  echo "Branch: $BRANCH"
  echo "Commit: $SHA"
  echo "Started: $(date -Iseconds)"
  echo "Working directory: $(pwd)"
} | tee "$ARCHIVE_DIR/run_info.txt"

echo ""
echo "Running golden tests for branch: $BRANCH"
echo "Archive directory: $ARCHIVE_DIR"
echo ""

# Run the 10.24 pipeline using the actual CLI
# Note: Outputs go to hardcoded dirs (Reformat/, All-to-Date/, Analysis/)
poetry run adhs-etl run --month 10.24 --raw-dir ./ALL-MONTHS/Raw\ 10.24

# Copy outputs to archive directory for comparison
echo "Archiving outputs..."
cp -r Reformat/ "$ARCHIVE_DIR/" 2>/dev/null || true
cp -r All-to-Date/ "$ARCHIVE_DIR/" 2>/dev/null || true
cp -r Analysis/ "$ARCHIVE_DIR/" 2>/dev/null || true

# Log completion
echo "Finished: $(date -Iseconds)" | tee -a "$ARCHIVE_DIR/run_info.txt"
echo ""
echo "Tests complete. Outputs archived to: $ARCHIVE_DIR"
