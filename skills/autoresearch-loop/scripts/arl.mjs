#!/usr/bin/env node
// arl — autoresearch-loop CLI (Claude-native port of pi-autoresearch's
// run_experiment / log_experiment tools). Dependency-free Node ESM.
//
// Ported faithfully from davebcn87/pi-autoresearch (MIT):
//   - METRIC name=value stdout contract + parser
//   - Median Absolute Deviation (MAD) confidence scoring
//   - .auto/ session layout + append-only log.jsonl
//   - git keep (commit) / discard (revert code, preserve .auto/)
//   - checks.sh backpressure after a passing benchmark
//
// Subcommands:
//   arl init   --name N --metric M [--unit U] [--direction lower|higher]
//   arl run    [--timeout S] [--checks-timeout S]   (runs .auto/measure.sh, then .auto/checks.sh)
//   arl log    --status keep|discard|crash|checks_failed --metric X --desc "..."
//              [--asi k=v ...] [--cost-unit U --cost N]   (appends row, scores, commits/reverts)
//   arl status                                       (baseline/best/confidence summary)

import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync, appendFileSync } from 'node:fs';
import path from 'node:path';

const AUTO = '.auto';
const LOG = path.join(AUTO, 'log.jsonl');
const STATE = path.join(AUTO, 'state.json');
const MEASURE = path.join(AUTO, 'measure.sh');
const CHECKS = path.join(AUTO, 'checks.sh');
const LAST = path.join(AUTO, 'last.json'); // most recent run's parsed result (so `arl log` need not re-run)
const METRIC_LINE_PREFIX = 'METRIC';
// Reserved names that must never be treated as user metrics.
const DENIED_METRIC_NAMES = new Set(['status', 'run', 'segment']);

// ---------- ported: METRIC line parsing ----------
// pi-autoresearch: new RegExp(`^${PREFIX}\\s+([\\w.µ]+)=(\\S+)\\s*$`, "gm")
function parseMetricLines(output) {
  const metrics = {};
  const regex = new RegExp(`^${METRIC_LINE_PREFIX}\\s+([\\w.µ]+)=(\\S+)\\s*$`, 'gm');
  let m;
  while ((m = regex.exec(output)) !== null) {
    const name = m[1];
    if (DENIED_METRIC_NAMES.has(name)) continue;
    const value = Number(m[2]);
    if (Number.isFinite(value)) metrics[name] = value;
  }
  return metrics;
}

// ---------- ported: MAD confidence ----------
function sortedMedian(values) {
  if (values.length === 0) return 0;
  const s = [...values].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 === 0 ? (s[mid - 1] + s[mid]) / 2 : s[mid];
}
const isBetter = (v, ref, dir) => (dir === 'lower' ? v < ref : v > ref);

// Returns { confidence: number|null, color } over the current segment.
function computeConfidence(rows, segment, direction) {
  const cur = rows.filter((r) => r.segment === segment && Number.isFinite(r.metric) && r.metric > 0);
  if (cur.length < 3) return { confidence: null, color: 'n/a' };
  const values = cur.map((r) => r.metric);
  const median = sortedMedian(values);
  const mad = sortedMedian(values.map((v) => Math.abs(v - median)));
  if (mad === 0) return { confidence: null, color: 'n/a' };
  const seg = cur.filter((r) => r.segment === segment);
  const baseline = seg.length ? seg[0].metric : null; // first row in segment = baseline
  if (baseline === null) return { confidence: null, color: 'n/a' };
  let bestKept = null;
  for (const r of cur) {
    if (r.status === 'keep' && r.metric > 0 && (bestKept === null || isBetter(r.metric, bestKept, direction))) {
      bestKept = r.metric;
    }
  }
  if (bestKept === null || bestKept === baseline) return { confidence: null, color: 'n/a' };
  const c = Math.abs(bestKept - baseline) / mad;
  const color = c >= 2.0 ? 'green' : c >= 1.0 ? 'yellow' : 'red';
  return { confidence: c, color };
}

// ---------- helpers ----------
const sh = (cmd, args, opts = {}) =>
  spawnSync(cmd, args, { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024, ...opts });
const die = (msg) => { console.error(`arl: ${msg}`); process.exit(1); };
const readState = () => (existsSync(STATE) ? JSON.parse(readFileSync(STATE, 'utf8')) : null);
const readRows = () =>
  existsSync(LOG)
    ? readFileSync(LOG, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l))
    : [];
function parseArgs(argv) {
  const a = { _: [], asi: {} };
  for (let i = 0; i < argv.length; i++) {
    const t = argv[i];
    if (t === '--asi') { const [k, ...v] = argv[++i].split('='); a.asi[k] = v.join('='); }
    else if (t.startsWith('--')) a[t.slice(2)] = (argv[i + 1] && !argv[i + 1].startsWith('--')) ? argv[++i] : true;
    else a._.push(t);
  }
  return a;
}

// ---------- subcommands ----------
function cmdInit(a) {
  if (!a.name || !a.metric) die('init requires --name and --metric');
  mkdirSync(AUTO, { recursive: true });
  const prev = readState();
  const segment = prev ? (prev.segment ?? 0) + 1 : 0; // re-init = new baseline segment
  const state = {
    name: a.name, metricName: a.metric, metricUnit: a.unit || '',
    direction: a.direction === 'higher' ? 'higher' : 'lower', segment,
  };
  writeFileSync(STATE, JSON.stringify(state, null, 2) + '\n');
  console.log(`init: "${state.name}" metric=${state.metricName}${state.metricUnit ? ' (' + state.metricUnit + ')' : ''} ${state.direction}-is-better segment=${segment}`);
}

function writeLast(obj) { writeFileSync(LAST, JSON.stringify(obj) + '\n'); }

function cmdRun(a) {
  if (!existsSync(MEASURE)) die(`missing ${MEASURE} — write the trial harness first`);
  const state = readState();
  const t0 = Date.now();
  const r = sh('bash', [MEASURE], { timeout: (Number(a.timeout) || 600) * 1000 });
  const seconds = (Date.now() - t0) / 1000;
  const out = (r.stdout || '') + (r.stderr || '');
  if (r.status !== 0) {
    console.log(`run: BENCHMARK FAILED (exit ${r.status}, ${seconds.toFixed(1)}s)`);
    console.log(out.split('\n').slice(-40).join('\n'));
    writeLast({ ok: false, metric: null, metrics: {}, checksPassed: false, seconds, ts: new Date().toISOString() });
    console.log('\n→ arl log --status crash  (--metric not needed)');
    return;
  }
  const metrics = parseMetricLines(out);
  if (Object.keys(metrics).length === 0) {
    console.log(`run: no METRIC lines found (${seconds.toFixed(1)}s). measure.sh must emit "METRIC name=value".`);
    console.log(out.split('\n').slice(-20).join('\n'));
    return;
  }
  // Primary metric = the one matching the session's metricName (else the only/first parsed).
  const names = Object.keys(metrics);
  const primaryName = state && metrics[state.metricName] !== undefined ? state.metricName : names[0];
  const primary = metrics[primaryName];
  console.log(`run: ok (${seconds.toFixed(1)}s) primary ${primaryName}=${primary} metrics=${JSON.stringify(metrics)}`);
  // checks.sh backpressure (does not affect primary metric)
  let checksPassed = true;
  if (existsSync(CHECKS)) {
    const c = sh('bash', [CHECKS], { timeout: (Number(a['checks-timeout']) || 300) * 1000 });
    checksPassed = c.status === 0;
    if (!checksPassed) {
      console.log('checks: FAILED — cannot keep this result. Last 80 lines:');
      console.log(((c.stdout || '') + (c.stderr || '')).split('\n').slice(-80).join('\n'));
      writeLast({ ok: true, metric: primary, metrics, checksPassed: false, seconds, ts: new Date().toISOString() });
      console.log('\n→ arl log --status checks_failed  (--metric not needed)');
      return;
    }
    console.log('checks: passed');
  }
  writeLast({ ok: true, metric: primary, metrics, checksPassed, seconds, ts: new Date().toISOString() });
  console.log(`\n→ decide: arl log --status keep|discard  (--metric defaults to ${primary}; override if needed)`);
}

function gitRevertCodePreserveAuto() {
  // Revert tracked code changes but preserve .auto/ (log, prompt, state).
  sh('git', ['checkout', '--', '.', ':(exclude).auto']);
  sh('git', ['clean', '-fd', '--', '.', ':(exclude).auto']);
}

function cmdLog(a) {
  const state = readState();
  if (!state) die('no state — run `arl init` first');
  const status = a.status;
  if (!['keep', 'discard', 'crash', 'checks_failed'].includes(status)) die('--status must be keep|discard|crash|checks_failed');
  const rows = readRows();
  const run = rows.length;
  // Default --metric (and checks status) from the last `arl run` so the
  // benchmark isn't run twice per trial. Explicit --metric overrides.
  const last = existsSync(LAST) ? JSON.parse(readFileSync(LAST, 'utf8')) : null;
  const metric = a.metric !== undefined ? Number(a.metric) : (last && last.metric !== null ? Number(last.metric) : NaN);
  if (a.metric === undefined && (!last || last.metric === null))
    die('no --metric given and no .auto/last.json — run `arl run` first, or pass --metric');
  if (status === 'keep' && last && last.checksPassed === false && a.force === undefined)
    die('refusing to keep: last run failed checks. Log --status checks_failed, or pass --force to override.');
  const row = {
    run, segment: state.segment, status,
    metric: Number.isFinite(metric) ? metric : null,
    metricName: state.metricName, unit: state.metricUnit, direction: state.direction,
    description: a.desc || '', asi: a.asi || {},
    cost: a.cost ? { unit: a['cost-unit'] || 'tokens', amount: Number(a.cost) } : null,
    ts: new Date().toISOString(), commit: null,
  };
  if (status === 'keep') {
    sh('git', ['add', '-A']);
    const c = sh('git', ['commit', '-m', `autoresearch #${run}: ${row.description || 'keep'} [${state.metricName}=${row.metric}]`]);
    const rev = sh('git', ['rev-parse', '--short', 'HEAD']);
    row.commit = (rev.stdout || '').trim() || null;
    if (c.status !== 0) console.log('warn: git commit failed (nothing to commit?)');
  } else {
    gitRevertCodePreserveAuto(); // discard / crash / checks_failed all revert code
  }
  appendFileSync(LOG, JSON.stringify(row) + '\n');
  const updated = readRows();
  const { confidence, color } = computeConfidence(updated, state.segment, state.direction);
  const cStr = confidence === null ? 'n/a (need 3+ runs / measurable noise)' : `${confidence.toFixed(1)}× [${color}]`;
  console.log(`log: #${run} ${status} metric=${row.metric}${state.metricUnit} ${row.commit ? '@' + row.commit : '(reverted)'}`);
  console.log(`confidence: ${cStr}  ${confidence !== null && confidence < 1.0 ? '— within noise; consider re-running before trusting' : ''}`);
}

function cmdStatus() {
  const state = readState();
  const rows = readRows();
  if (!state || rows.length === 0) { console.log('status: no experiments yet'); return; }
  const seg = rows.filter((r) => r.segment === state.segment && Number.isFinite(r.metric));
  const baseline = seg.length ? seg[0].metric : null;
  const kept = seg.filter((r) => r.status === 'keep');
  let best = baseline;
  for (const r of kept) if (best === null || isBetter(r.metric, best, state.direction)) best = r.metric;
  const { confidence, color } = computeConfidence(rows, state.segment, state.direction);
  console.log(`session: ${state.name}  (segment ${state.segment}, ${rows.length} runs)`);
  console.log(`metric:  ${state.metricName} (${state.direction} better)`);
  console.log(`baseline: ${baseline}${state.metricUnit}   best: ${best}${state.metricUnit}`);
  if (baseline !== null && best !== null && best !== baseline) {
    const pct = (((best - baseline) / baseline) * 100).toFixed(1);
    console.log(`delta:    ${pct}%`);
  }
  console.log(`confidence: ${confidence === null ? 'n/a' : confidence.toFixed(1) + '× [' + color + ']'}`);
  console.log(`kept:     ${kept.length} / ${rows.length}`);
}

function cmdFinalize() {
  const state = readState();
  const rows = readRows();
  if (!state || rows.length === 0) die('nothing to finalize — no experiments logged');
  const seg = rows.filter((r) => r.segment === state.segment && Number.isFinite(r.metric));
  const baseline = seg.length ? seg[0].metric : null;
  const kept = rows.filter((r) => r.status === 'keep' && r.run > 0); // exclude baseline row
  let best = baseline;
  for (const r of seg) if (r.status === 'keep' && (best === null || isBetter(r.metric, best, state.direction))) best = r.metric;
  const { confidence, color } = computeConfidence(rows, state.segment, state.direction);
  const u = state.metricUnit || '';
  const pct = baseline && best !== null && best !== baseline ? (((best - baseline) / baseline) * 100).toFixed(1) + '%' : 'n/a';
  const totalCost = rows.reduce((s, r) => s + (r.cost ? Number(r.cost.amount) || 0 : 0), 0);
  const lines = [
    `# Autoresearch results — ${state.name}`,
    '',
    `- Metric: \`${state.metricName}\` (${state.direction} is better)`,
    `- Baseline → Best: ${baseline}${u} → ${best}${u}  (${pct})`,
    `- Confidence: ${confidence === null ? 'n/a' : confidence.toFixed(1) + '× [' + color + ']'}`,
    `- Trials: ${rows.length}  (kept ${kept.length}, discarded ${rows.filter((r) => r.status !== 'keep').length})`,
    totalCost ? `- Total cost: ${totalCost}` : null,
    '',
    '## Implemented improvements (kept)',
    '',
    '| # | change | metric | commit |',
    '|---|--------|--------|--------|',
    ...kept.map((r) => `| ${r.run} | ${r.description || ''} | ${r.metric}${u} | ${r.commit || ''} |`),
    '',
    '## Discarded (with reasons)',
    '',
    ...rows.filter((r) => r.status !== 'keep').map((r) => `- #${r.run} ${r.status}: ${r.description || ''}${r.asi && Object.keys(r.asi).length ? '  — ' + JSON.stringify(r.asi) : ''}`),
    '',
  ].filter((l) => l !== null);
  const out = path.join(AUTO, 'RESULTS.md');
  writeFileSync(out, lines.join('\n') + '\n');
  console.log(`finalize: wrote ${out}  (baseline ${baseline}${u} → best ${best}${u}, ${pct}, ${kept.length} kept)`);
}

// ---------- dispatch ----------
const [, , cmd, ...rest] = process.argv;
const a = parseArgs(rest);
switch (cmd) {
  case 'init': cmdInit(a); break;
  case 'run': cmdRun(a); break;
  case 'log': cmdLog(a); break;
  case 'status': cmdStatus(a); break;
  case 'finalize': cmdFinalize(a); break;
  default:
    console.log('usage: arl <init|run|log|status|finalize> [opts]  (see header of scripts/arl.mjs)');
    process.exit(cmd ? 1 : 0);
}
