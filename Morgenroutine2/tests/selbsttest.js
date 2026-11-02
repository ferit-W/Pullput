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
const exporte = ['luedePhase','computeAmpel','ampelRegel','voreinstiegPruefung','trendUndRisiko','usBoersenStatus','xetraStatus','etNachBerlin','makroStufe','makroRegion',
  'korrigiereZeit','wochenTermine','kreditAusCsv','folgeRenditen','datumAus','breitenWendePruefung','nachziehVorschlag','isoLokal','mrSyncWert','STATE','SK'];
vm.runInContext(code + '\n;globalThis.__T={' + exporte.map(n => `${n}:(typeof ${n}!=='undefined'?${n}:undefined)`).join(',') + ',kpi:()=>KPIDAYS};',
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
  T.STATE.sectors = Array.from({ length: 11 }, (_, i) => ({ etf: 'S' + i, aboveEma50: i < ueber, aboveEma200: i < ueber, rs1m: i < schlagen ? 1 : -1 }));
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

// ── Voreinstieg live: STOP-Rückschau aus Kursreihen ──────────────────────────
abschnitt('Voreinstieg mit Rückschau aus Kursreihen');
function liveFall(spitzeVorTagen) {
  const L = 400, t0 = Date.UTC(2025, 0, 2) / 1000;
  const times = []; for (let i = 0, d = 0; i < L; d++) { const w = new Date((t0 + d * 86400) * 1000).getUTCDay(); if (w === 0 || w === 6) continue; times.push(t0 + d * 86400 + 14 * 3600); i++; }
  const steigend = Array.from({ length: L }, (_, i) => 100 + i * 0.2);
  T.STATE.indices = ['SPY', 'QQQ', 'DIA', 'IWM'].map(k => ({ key: k, us: true, phase: { code: 'P3' }, closes: steigend.slice(), times }));
  T.STATE.sectors = Array.from({ length: 11 }, (_, i) => ({ etf: 'S' + i, aboveEma50: true, aboveEma200: true, rs1m: 1, closes: steigend.slice(), times }));
  const vx = Array.from({ length: L }, () => 15); if (spitzeVorTagen != null) vx[L - 1 - spitzeVorTagen] = 35;
  T.STATE.vixSeries = { closes: vx, times };
  T.STATE.vix = 22; T.STATE.vix3m = 25; T.STATE.fg = { score: 40 }; T.STATE.vixTerm = { regime: 'contango', ratio: 0.88 };
  const v = T.computeAmpel();
  return { label: v.label, tageSeit: v.voreinstieg.rueck.tageSeit, basis: v.basis };
}
{
  const a = liveFall(30), b = liveFall(null), c = liveFall(65);
  pruefe('VIX-Spitze vor 30 Tagen, heute VIX 22 → VOREINSTIEG', [a.label, a.tageSeit, a.basis], ['VOREINSTIEG', 30, 'CAUTION']);
  pruefe('ohne STOP in der Rückschau → CAUTION', b.label, 'CAUTION');
  pruefe('STOP vor 65 Tagen (außerhalb des Fensters) → CAUTION', c.label, 'CAUTION');
}

// ── Ampel gegen die Rückrechnung 2007–2026 (AM8: Prüfstand) ───────────────────
// Die Referenz erzeugt auswertung/referenz_ampel_v2.py mit dem Python-Code, mit dem
// die Regeln getestet wurden. Die Seite muss an JEDEM Tag dasselbe liefern.
abschnitt('Ampel gegen Rückrechnung 2007–2026');
{
  const refPfad = path.join(__dirname, '..', 'auswertung', 'ergebnisse', 'referenz_ampel_v2.csv');
  if (!fs.existsSync(refPfad)) { fehl++; console.log('  ✗ Referenzdatei fehlt: python3 auswertung/referenz_ampel_v2.py'); }
  else {
    const zeilen = fs.readFileSync(refPfad, 'utf8').trim().split(/\r?\n/);
    const kopf = zeilen[0].split(','); const sp = k => kopf.indexOf(k);
    const zahl = v => (v === '' || v === undefined || isNaN(+v)) ? null : +v;
    const basisListe = []; let gleich = 0, abw = []; let ve = 0;
    zeilen.slice(1).forEach(z => {
      const c = z.split(',');
      const x = { p3: +c[sp('p3')], p6: +c[sp('p6')], n: +c[sp('n')], vix: zahl(c[sp('vix')]), fg: zahl(c[sp('fg')]),
        part: zahl(c[sp('breite200')]), partTot: zahl(c[sp('breiteTot')]) || 11, rsBeat: zahl(c[sp('rsBeat')]),
        rsTot: zahl(c[sp('rsTot')]) || 11, term: c[sp('term')] || null };
      const basis = T.ampelRegel(x).label;
      basisListe.push(basis);
      const fenster = basisListe.slice(-60);
      const letzterStop = fenster.lastIndexOf('STOP');
      const rueck = { tageSeit: letzterStop < 0 ? null : fenster.length - 1 - letzterStop };
      const V = T.voreinstiegPruefung({ ...x, base: basis, rueck, termRatio: null, indizes: [] });
      const label = V.aktiv ? 'VOREINSTIEG' : basis;
      if (V.aktiv) ve++;
      if (label === c[sp('ampel_v2')]) gleich++; else abw.push(c[0] + ': JS ' + label + ' / Python ' + c[sp('ampel_v2')]);
    });
    pruefe(`alle ${zeilen.length - 1} Handelstage identisch (davon ${ve} VOREINSTIEG)`, abw.slice(0, 5), []);
  }
}

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

// ── Kreditspread (AM5): CSV im FRED-Format ───────────────────────────────────
abschnitt('Kreditspread');
{
  const zeilen = ['observation_date,BAMLH0A0HYM2'];
  for (let i = 0; i < 70; i++) zeilen.push(`2026-07-${String(i).padStart(2, '0')},${(3 + i * 0.01).toFixed(2)}`);
  zeilen.push('2026-10-29,.');                       // FRED markiert Lücken mit Punkt
  const k = T.kreditAusCsv(zeilen.join('\n'));
  pruefe('letzter gültiger Wert, Lücke übersprungen', k && k.wert, 3.69);
  pruefe('Veränderung über 63 Beobachtungen', k && +k.chg63.toFixed(2), 0.63);
  pruefe('leere Antwort → null', T.kreditAusCsv(''), null);
}

// ── Archiv: Folgerenditen wie in der Rückrechnung (A1c) ───────────────────────
abschnitt('Archiv-Folgerenditen');
{
  const times = [], closes = [];
  for (let i = 0; i < 100; i++) { times.push(Date.UTC(2026, 0, 2 + i, 20) / 1000); closes.push(100 + i); }
  const tag = T.datumAus(times[10]);
  const u = T.folgeRenditen({ [tag]: {} }, closes, times)[tag];
  // Signal t = Index 10 (Kurs 110), Umsetzung t+1 = 111, fwd5 = Kurs 116 / 111 − 1
  pruefe('fwd5 ab Schluss t+1', u.spy_fwd5, +(116 / 111 - 1).toFixed(5));
  pruefe('fwd60 ab Schluss t+1', u.spy_fwd60, +(171 / 111 - 1).toFixed(5));
  pruefe('vorhandene Werte bleiben unangetastet', Object.keys(T.folgeRenditen({ [tag]: { spy_fwd5: 1, spy_fwd20: 1, spy_fwd60: 1, spy_maxdd20: 1 } }, closes, times)).length, 0);
  const letzter = T.datumAus(times[98]);
  pruefe('zu junger Tag bekommt noch nichts', T.folgeRenditen({ [letzter]: {} }, closes, times)[letzter], undefined);
}

// ── Breiten-Wende (B4) wie in breite_wende_test.py ───────────────────────────
abschnitt('Breiten-Wende');
{
  const K = T.kpi(); Object.keys(K).forEach(k => delete K[k]);
  for (let i = 9; i >= 1; i--) { const d = new Date(Date.now() - i * 864e5).toISOString().slice(0, 10);
    K[d] = { ak_p3: 15, ak_nh: 0.5, ak_nl: i === 5 ? 12 : 8 }; }
  T.STATE.aktienBreite = { US: { p3: 25, nh: 1, nl: 5 } };
  const a = T.breitenWendePruefung();
  pruefe('Kapitulation, Tiefs halbiert (5 ≤ 6), Breite dreht → Signal', [a.aktiv, a.liste.map(x => x.ok)], [true, [true, true, true]]);
  T.STATE.aktienBreite = { US: { p3: 25, nh: 1, nl: 7 } };
  pruefe('Tiefs nicht halbiert (7 > 6) → kein Signal', T.breitenWendePruefung().aktiv, false);
  Object.keys(K).forEach(k => { K[k].ak_p3 = 50; K[k].ak_nl = 0.5; K[k].ak_nh = 3; });
  T.STATE.aktienBreite = { US: { p3: 55, nh: 3, nl: 0.5 } };
  pruefe('ohne Kapitulation → kein Signal', T.breitenWendePruefung().liste[0].ok, false);
  Object.keys(K).forEach(k => delete K[k]);
}

// ── Positions-Monitor: Stopp nachziehen nach E4/E5 (T2) ───────────────────────
abschnitt('Stopp nachziehen');
{
  const n = 60, times = [], closes = [], highs = [], lows = [];
  for (let i = 0; i < n; i++) { times.push(Date.UTC(2026, 6, 1 + i, 20) / 1000); const c = 100 + i * 0.5; closes.push(c); highs.push(c + 1); lows.push(c - 1); }
  const d = { closes, highs, lows, times, price: closes[n - 1] };
  const ein = T.datumAus(times[20]);
  const long = T.nachziehVorschlag({ direction: 'Long', slPrice: 105, dateOpened: ein }, d);
  pruefe('E4 Long = tiefstes Tief der letzten 10 Tage', long.e4, Math.min(...lows.slice(-10)));
  pruefe('E5 Long = höchster Schluss seit Einstieg − 3 × ATR', +long.e5.toFixed(4), +(closes[n - 1] - 3 * long.atr).toFixed(4));
  const schonHoch = T.nachziehVorschlag({ direction: 'Long', slPrice: 128, dateOpened: ein }, d);
  pruefe('kein Vorschlag, wenn er den Stopp nicht verbessert', [schonHoch.e4, schonHoch.e5], [null, null]);
  const kurz = T.nachziehVorschlag({ direction: 'Short', slPrice: 140, dateOpened: ein }, d);
  pruefe('Short: Vorschlag liegt über dem Kurs (hier keiner, Kurs steigt)', kurz.e4 === null || kurz.e4 > d.price, true);
}

// ── Ergebnis ─────────────────────────────────────────────────────────────────
console.log(`\n${ok} bestanden, ${fehl} fehlgeschlagen`);
process.exit(fehl ? 1 : 0);
