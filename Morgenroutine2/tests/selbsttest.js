// ════════════════════════════════════════════════════════════════════════════
// Selbsttest der Morgenroutine (V16) — läuft OHNE Internet und ohne Browser.
//
// Aufruf im Ordner Morgenroutine2:   node tests/selbsttest.js
//
// Der Test lädt das Skript aus ferit_morgenroutine_v6.html in eine abgeschottete
// Umgebung (Node vm) mit einer Attrappe für Browser und Netz. Geprüft werden die
// ECHTEN Funktionen der Seite, keine Kopien — wer dort etwas ändert, merkt hier
// sofort, wenn ein früher behobener Fehler zurückkommt.
//
// Abgedeckt:  Phasenlogik · Ampel · Börsenfeiertage und Halbtage ·
//             Zeitumrechnung New York → Berlin · Makro-Einstufung und Region ·
//             Uhrzeit-Korrektur · Wochenfenster
// ════════════════════════════════════════════════════════════════════════════
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'ferit_morgenroutine_v6.html'), 'utf8');
const code = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
  .filter(m => !/\ssrc=/.test(m[0].slice(0, 120))).map(m => m[1]).join('\n;\n');

// ── Attrappe: jedes Element, jede Funktion schluckt alles und gibt sich selbst zurück ──
function attrappe() {
  const f = function () { return p; };
  const p = new Proxy(f, {
    get: (t, k) => {
      if (k === Symbol.toPrimitive) return () => '';
      if (k === 'then') return undefined;              // kein Promise-Verhalten
      if (k === 'length') return 0;
      if (k === 'value' || k === 'textContent' || k === 'innerHTML') return '';
      if (k === 'classList') return { add() {}, remove() {}, toggle() {}, contains() { return false; } };
      if (k === 'dataset' || k === 'style') return {};
      return p;
    },
    set: () => true, apply: () => p, construct: () => p,
  });
  return p;
}
const speicher = {};
const localStorage = {
  getItem: k => (k in speicher ? speicher[k] : null),
  setItem: (k, v) => { speicher[k] = String(v); },
  removeItem: k => { delete speicher[k]; },
  key: i => Object.keys(speicher)[i] ?? null,
  get length() { return Object.keys(speicher).length; },
};
const document = {
  getElementById: () => null, querySelector: () => null, querySelectorAll: () => [],
  createElement: () => attrappe(), addEventListener() {}, body: attrappe(), documentElement: attrappe(),
};
const ctx = {
  console, Date, Math, JSON, Intl, Promise, Array, Object, String, Number, RegExp, Map, Set, Symbol,
  parseInt, parseFloat, isFinite, isNaN, encodeURIComponent, decodeURIComponent, URL, Blob: function () {},
  setTimeout: () => 0, clearTimeout() {}, setInterval: () => 0, clearInterval() {},
  fetch: () => Promise.reject(new Error('offline')), AbortController: class { constructor() { this.signal = {}; } abort() {} },
  localStorage, sessionStorage: localStorage, document, navigator: { userAgent: 'node' },
  location: { protocol: 'http:', href: 'http://localhost:8765/', hostname: 'localhost' },
  alert() {}, confirm: () => false, prompt: () => null, matchMedia: () => ({ matches: false, addEventListener() {} }),
  addEventListener() {}, removeEventListener() {},
};
ctx.window = ctx; ctx.self = ctx; ctx.globalThis = ctx;
vm.createContext(ctx);
// Top-Level-const/let sind im vm nicht als Eigenschaften sichtbar — deshalb am Ende exportieren.
const exporte = ['luedePhase','computeAmpel','usBoersenStatus','xetraStatus','etNachBerlin','makroStufe','makroRegion',
  'korrigiereZeit','wochenTermine','isoLokal','mrSyncWert','STATE','SK'];
vm.runInContext(code + '\n;globalThis.__T={' + exporte.map(n => `${n}:(typeof ${n}!=='undefined'?${n}:undefined)`).join(',') + '};',
  ctx, { filename: 'ferit_morgenroutine_v6.html' });
const T = ctx.__T;

// ── Mini-Testrahmen ──────────────────────────────────────────────────────────
let ok = 0, fehl = 0;
function pruefe(name, ist, soll) {
  const gut = JSON.stringify(ist) === JSON.stringify(soll);
  if (gut) ok++; else fehl++;
  console.log((gut ? '  ✓ ' : '  ✗ ') + name + (gut ? '' : `\n      erwartet ${JSON.stringify(soll)}, erhalten ${JSON.stringify(ist)}`));
}
const abschnitt = t => console.log('\n' + t);

// ── Phasenlogik (Lüddemann) ──────────────────────────────────────────────────
abschnitt('Phasenlogik');
if (typeof T.luedePhase === 'function') {
  pruefe('P3: Kurs > EMA50 > EMA200', T.luedePhase(110, 108, 105, 100).code, 'P3');
  pruefe('P6: Kurs < EMA20 < EMA200', T.luedePhase(90, 95, 97, 100).code, 'P6');
  pruefe('Übergang ist weder P3 noch P6', ['P3','P6'].includes(T.luedePhase(101, 103, 99, 100).code), false);
} else { fehl++; console.log('  ✗ luedePhase nicht gefunden'); }

// ── Ampel ────────────────────────────────────────────────────────────────────
abschnitt('Ampel');
ctx.document.getElementById = () => attrappe();      // renderRegime() zeichnet — hier ins Leere
function ampel({p3 = 4, p6 = 0, vix = 15, fg = 60, ueber = 8, schlagen = 6, term = null}) {
  const ph = i => ({ code: i < p3 ? 'P3' : i < p3 + p6 ? 'P6' : 'P4' });
  T.STATE.indices = [0, 1, 2, 3].map(i => ({ key: 'I' + i, us: true, phase: ph(i) }));
  T.STATE.sectors = Array.from({ length: 11 }, (_, i) => ({ etf: 'S' + i, aboveEma50: i < ueber, rs1m: i < schlagen ? 1 : -1 }));
  T.STATE.vix = vix; T.STATE.fg = { score: fg }; T.STATE.vixTerm = term ? { regime: term } : null;
  return T.computeAmpel().label;
}
if (typeof T.computeAmpel === 'function') {
  pruefe('GO: 4/4 in P3, VIX 15, breite Beteiligung', ampel({}), 'GO');
  pruefe('CAUTION: VIX 22', ampel({ vix: 22 }), 'CAUTION');
  pruefe('CAUTION: nur 2/4 in P3', ampel({ p3: 2 }), 'CAUTION');
  pruefe('STOP: 2 Indizes in P6', ampel({ p3: 1, p6: 2 }), 'STOP');
  pruefe('STOP: VIX 30', ampel({ vix: 30, fg: 40 }), 'STOP');
  pruefe('REVERSE: F&G 10, VIX 35, Backwardation', ampel({ p3: 0, p6: 3, vix: 35, fg: 10, term: 'back-strong' }), 'REVERSE');
} else { fehl++; console.log('  ✗ computeAmpel nicht gefunden'); }

// ── Börsenkalender ───────────────────────────────────────────────────────────
abschnitt('Börsenkalender');
const tag = s => new Date(s + 'T12:00:00');
pruefe('XETRA Ostermontag 2027 zu', T.xetraStatus(tag('2027-03-29')).offen, false);
pruefe('XETRA 1. Mai 2026 zu', T.xetraStatus(tag('2026-05-01')).offen, false);
pruefe('XETRA Heiligabend 2026 zu', T.xetraStatus(tag('2026-12-24')).offen, false);
pruefe('XETRA normaler Dienstag offen', T.xetraStatus(tag('2026-11-03')).offen, true);
pruefe('NYSE Thanksgiving 2026 zu', T.usBoersenStatus(tag('2026-11-26')).offen, false);
pruefe('NYSE Tag nach Thanksgiving 2026 halber Tag', !!T.usBoersenStatus(tag('2026-11-27')).halb, true);
pruefe('NYSE Ostermontag 2027 offen', T.usBoersenStatus(tag('2027-03-29')).offen, true);

// ── Zeitumrechnung ───────────────────────────────────────────────────────────
abschnitt('Zeitumrechnung New York → Berlin');
pruefe('Sommer: 8:30 ET = 14:30', T.etNachBerlin('08:30', tag('2026-07-15')), '14:30');
pruefe('Winter: 8:30 ET = 14:30', T.etNachBerlin('08:30', tag('2026-12-10')), '14:30');
pruefe('Umstellungswoche Oktober: 8:30 ET = 13:30', T.etNachBerlin('08:30', tag('2026-10-28')), '13:30');
pruefe('Umstellungswoche März: 14:00 ET = 19:00', T.etNachBerlin('14:00', tag('2027-03-17')), '19:00');

// ── Makro-Einstufung (Testtitel aus dem Prüfbericht, F2/F3) ──────────────────
abschnitt('Makro-Einstufung');
const stufen = {
  'EZB-Zinsentscheid': 'hoch', 'Eurozone: EZB-Zinsentscheid': 'hoch',
  'Deutschland: ifo-Geschäftsklima': 'mittel', 'Deutschland: ZEW-Konjunkturerwartungen': 'mittel',
  'USA: Verbraucherpreisindex (CPI)': 'hoch', 'US Nonfarm Payrolls': 'hoch', 'ADP Non-Farm Employment': 'mittel',
  'Kanada Zinsentscheid': 'niedrig', 'China PMI': 'niedrig', 'Eurozone CPI': 'mittel',
  'Deutschland: Arbeitslosenquote': 'niedrig',
};
Object.entries(stufen).forEach(([t, s]) => pruefe(`„${t}“ → ${s}`, T.makroStufe(t), s));
pruefe('„Industrieproduktion“ ist nicht Ausland (F3)', T.makroRegion('Industrieproduktion') !== 'sonst', true);
pruefe('„UK: BIP“ ist Ausland', T.makroRegion('UK: BIP'), 'sonst');

// ── Uhrzeit-Korrektur (F4) ───────────────────────────────────────────────────
abschnitt('Uhrzeit-Korrektur');
const ch = { title: 'Schweiz: Verbraucherpreise (CPI)', time: '08:30', day: 'Di' }; T.korrigiereZeit(ch);
pruefe('Schweizer CPI bleibt 08:30', ch.time, '08:30');
const ez = { title: 'Eurozone GDP', time: '11:00', day: 'Di' }; T.korrigiereZeit(ez);
pruefe('Eurozone GDP ohne Fehlalarm', !!ez.timeWarn, false);

// ── Watchlist-Sync (F5/V10) ──────────────────────────────────────────────────
abschnitt('Watchlist-Sync');
const a = T.mrSyncWert(T.SK.watch, JSON.stringify([{ ticker: 'AAPL', price: 100, e20: 1 }]));
const b = T.mrSyncWert(T.SK.watch, JSON.stringify([{ ticker: 'AAPL', price: 101, e20: 2, pe: 30 }]));
pruefe('reine Kursänderung ändert den Sync-Inhalt nicht', a === b, true);

// ── Ergebnis ─────────────────────────────────────────────────────────────────
console.log(`\n${ok} bestanden, ${fehl} fehlgeschlagen`);
process.exit(fehl ? 1 : 0);
