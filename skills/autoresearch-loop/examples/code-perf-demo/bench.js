// Benchmark: time analyze() over a fixed large input. Warm up, then take the
// median of several runs for a low-noise metric. Emits `METRIC ms=<median>`.
const { analyze } = require('./solution.js');
const { makeText } = require('./gen.js');

const text = makeText(40000, 1500, 12345); // fixed seed → identical workload
const RUNS = 7;
const times = [];
for (let i = 0; i < RUNS + 1; i++) {
  const t0 = process.hrtime.bigint();
  const r = analyze(text);
  const t1 = process.hrtime.bigint();
  if (i > 0) times.push(Number(t1 - t0) / 1e6); // drop the first (warmup)
  if (r.checksum < 0) console.error('guard'); // prevent dead-code elimination
}
times.sort((a, b) => a - b);
const median = times[Math.floor(times.length / 2)];
console.log(`METRIC ms=${median.toFixed(2)}`);
