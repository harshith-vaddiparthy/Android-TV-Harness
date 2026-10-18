#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'Bulk disable scripts are retired in Android TV Harness.' 'Use python3 -m harness --serial TARGET plan REQUEST.json, review the plan, then apply ID.' >&2
exit 1
