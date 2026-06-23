# Ideas backlog
- Replace parallel-array indexOf frequency count with a Map (kills O(n*vocab)).
- Single pass; avoid building an intermediate pairs array.
- Partial top-10 selection instead of full sort of the whole vocab.
- Avoid recomputing toLowerCase / hoist invariants.
