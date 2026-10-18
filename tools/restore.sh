#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'List-based restore is retired in Android TV Harness.' 'Use python3 -m harness --serial TARGET restore RUN_ID for exact recorded-state recovery.' >&2
exit 1
