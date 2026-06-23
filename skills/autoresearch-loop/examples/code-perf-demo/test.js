// Independent correctness oracle (the guardrail). A trivially-correct reference
// implementation computes the expected result; solution.analyze must match it.
// This is what stops the optimizer from "winning" by breaking correctness.
const assert = require('node:assert');
const { analyze } = require('./solution.js');
const { makeText } = require('./gen.js');

function reference(text) {
  const words = text.split(/\s+/).filter((w) => w.length > 0);
  const m = new Map();
  for (const w of words) {
    const lw = w.toLowerCase();
    m.set(lw, (m.get(lw) || 0) + 1);
  }
  const pairs = [...m.entries()].sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1));
  const top = pairs.slice(0, 10).map(([k, c]) => [k, c]);
  let checksum = 0;
  for (const [k, c] of top) {
    for (let i = 0; i < k.length; i++) checksum = (checksum + k.charCodeAt(i) * c) % 1000000007;
  }
  return { top, checksum };
}

for (const seed of [1, 42, 12345]) {
  const text = makeText(3000, 400, seed);
  const got = analyze(text);
  const exp = reference(text);
  assert.deepStrictEqual(got.top, exp.top, `top mismatch (seed ${seed})`);
  assert.strictEqual(got.checksum, exp.checksum, `checksum mismatch (seed ${seed})`);
}
console.log('checks: ok');
