#!/bin/bash
set -euo pipefail
node test.js 2>&1 | tail -20   # correctness oracle; nonzero exit blocks a keep
