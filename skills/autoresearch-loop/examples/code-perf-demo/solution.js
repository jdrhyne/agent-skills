// Hot path under optimization: top-10 word frequencies + a checksum.
// Baseline is deliberately naive. The agent may rewrite analyze() freely as
// long as test.js (the independent correctness oracle) still passes.

function analyze(text) {
  // Frequency count via a Map — O(n). Tokenize with a single regex pass to
  // avoid allocating large intermediate split/filter arrays.
  const m = new Map();
  const re = /\S+/g;
  let match;
  while ((match = re.exec(text)) !== null) {
    const lw = match[0].toLowerCase();
    m.set(lw, (m.get(lw) || 0) + 1);
  }

  // Build pairs, fully sort, take top 10.
  const pairs = [...m.entries()];
  pairs.sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1));
  const top = pairs.slice(0, 10);

  let checksum = 0;
  for (const [k, c] of top) {
    for (let i = 0; i < k.length; i++) {
      checksum = (checksum + k.charCodeAt(i) * c) % 1000000007;
    }
  }
  return { top, checksum };
}

module.exports = { analyze };
