#!/bin/bash
set -euo pipefail
node --check solution.js   # fast syntax pre-check (<1s) before the workload
node bench.js              # emits: METRIC ms=<median>
