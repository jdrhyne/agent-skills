// Deterministic input generator (seeded LCG) — same text every run so the
// metric is comparable across trials. Used by both bench and test.
function makeText(nWords, vocabSize, seed) {
  let s = seed >>> 0;
  const rand = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  const vocab = [];
  for (let i = 0; i < vocabSize; i++) {
    // Zipf-ish: short words common, longer rare.
    const len = 3 + Math.floor(rand() * 8);
    let w = '';
    for (let j = 0; j < len; j++) w += String.fromCharCode(97 + Math.floor(rand() * 26));
    vocab.push(w);
  }
  const out = [];
  for (let i = 0; i < nWords; i++) {
    // Skew toward the front of the vocab so a few words dominate.
    const r = rand();
    const idx = Math.floor(r * r * vocabSize);
    out.push(vocab[idx]);
  }
  return out.join(' ');
}
module.exports = { makeText };
