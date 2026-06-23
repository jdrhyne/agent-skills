# Live test result (2026-06-22)

First end-to-end run of the `arl` loop with the code-perf-audit adapter.

| # | change | ms | decision |
|---|--------|----|----------|
| 0 | naive baseline (parallel-array indexOf) | 16.28 | keep |
| 1 | Map frequency count (O(n)) | 4.00 | keep |
| 2 | regex tokenize (avoid split/filter arrays) | 2.77 | keep |
| 3 | toLowerCase object cache | 4.19 | **discard** (auto-reverted) |

Result: **16.28 → 2.77 ms (5.9× faster, −83%)**, correctness oracle green throughout,
final MAD confidence 19.0× (well above the 2.0× "real" threshold).
Demonstrated: keep→commit+stack, discard→auto-revert-preserving-ledger, MAD scoring on real numbers.
