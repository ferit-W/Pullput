#!/usr/bin/env python3
"""Setup-Scanner „Rücksetzer im Trend“ (Phase 4: T3, N2, N5, N3).

Sucht einmal täglich im S&P 500 und im DAX nach genau dem Einstieg, der im Systemtest
(auswertung/SYSTEM_TEST.md, Phase 2b) geprüft wurde:

  T   Phase 3 (Schluss > EMA50 > EMA200), an einem der 5 Vortage Schluss unter EMA20,
      heute Schluss wieder über EMA20. Stopp = tiefstes Tief der letzten 10 Tage,
      Stoppabstand 1–15 %.
  K2  Platz bis zum Widerstand (52-Wochen-Hoch) größer als der Stoppabstand, oder
      kein Widerstand (Kurs am Hoch). Im Test in beiden Zeiträumen hilfreich → Filter.
  K3  Relative Stärke 63 Tage gegen den eigenen Sektor-ETF (DAX-Werte: gegen den DAX).
      Im Test gemischt → nur Anzeige und Sortierung, kein Filter.
  K1  Nähe zum 52-Wochen-Hoch hat im Test geschadet → nicht verwendet, nur als Info.

Dazu:
  N5  Liquidität: Durchschnittsumsatz der letzten 20 Tage (Schluss × Volumen) in der
      Handelswährung. Schwelle aus handelsplan.json (Mio.), höchstens N Vorschläge.
      Ausgewiesen wird, wie viele Treffer an der Liquidität scheiterten.
  N3  Quartalszahlen: Termin aus der Kursabfrage, Warnung bei Zahlen in den nächsten
      10 Kalendertagen (typische Haltedauer).

Ergebnis ist eine Vorauswahl. Chartbild und Entscheidung bleiben bei dir (TradingView).
"""
import json
import math
import os
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

HIER = os.path.dirname(os.path.abspath(__file__))


# ── Rechnen (ohne Netz, testbar) ─────────────────────────────────────────────────
def ema_serie(werte, n):
    """EMA wie in der Morgenroutine: SMA der ersten n Werte als Start."""
    out = [None] * len(werte)
    if len(werte) < n:
        return out
    k = 2 / (n + 1)
    e = sum(werte[:n]) / n
    out[n - 1] = e
    for i in range(n, len(werte)):
        e = werte[i] * k + e * (1 - k)
        out[i] = e
    return out


def pruefe_titel(c, h, l, v, bench=None):
    """c/h/l/v: Listen (älteste zuerst, ohne Lücken). bench: Schlusskurse des Vergleichsindex
    gleicher Länge oder None. Gibt dict mit Signal und Kennzahlen zurück oder None."""
    n = len(c)
    if n < 260:
        return None
    e20, e50, e200 = ema_serie(c, 20), ema_serie(c, 50), ema_serie(c, 200)
    i = n - 1
    if None in (e20[i], e50[i], e200[i]):
        return None
    p3 = c[i] > e50[i] > e200[i]
    korrektur = any(c[j] < e20[j] for j in range(i - 5, i) if e20[j] is not None)
    signal = p3 and korrektur and c[i] > e20[i]
    stopp = min(l[i - 9:i + 1])
    abst = (c[i] - stopp) / c[i] if c[i] else None
    hoch = max(h[i - 251:i + 1])
    platz = hoch - c[i]
    am_hoch = c[i] >= hoch
    k2 = am_hoch or (platz > (c[i] - stopp))
    platz_x = None if am_hoch or c[i] <= stopp else platz / (c[i] - stopp)
    rs = None
    if bench and len(bench) == n and bench[i - 63] and c[i - 63]:
        rs = (c[i] / c[i - 63] - 1) - (bench[i] / bench[i - 63] - 1)
    umsatz = sum(c[j] * (v[j] or 0) for j in range(i - 19, i + 1)) / 20
    return {
        "signal": bool(signal and abst is not None and 0.01 <= abst <= 0.15),
        "p3": p3, "kurs": round(c[i], 4), "ema20": round(e20[i], 4),
        "stopp": round(stopp, 4), "stopp_pct": round(abst * 100, 2) if abst is not None else None,
        "hoch52": round(hoch, 4), "abstand_hoch_pct": round((c[i] / hoch - 1) * 100, 2),
        "k2": bool(k2), "platz_x": round(platz_x, 2) if platz_x is not None else None, "am_hoch": bool(am_hoch),
        "rs63_pct": round(rs * 100, 2) if rs is not None else None,
        "umsatz20": umsatz,
    }


def auswahl(treffer, min_umsatz, max_n):
    """Liquidität filtern, Platz-Check als Filter, sortieren nach RS gegen Sektor."""
    sig = [t for t in treffer if t.get("signal")]
    liquide = [t for t in sig if (t.get("umsatz20") or 0) >= min_umsatz]
    mit_platz = [t for t in liquide if t.get("k2")]
    mit_platz.sort(key=lambda t: (t.get("rs63_pct") is None, -(t.get("rs63_pct") or 0)))
    return {"signale": len(sig), "an_liquiditaet_gescheitert": len(sig) - len(liquide),
            "ohne_platz": len(liquide) - len(mit_platz), "vorschlaege": mit_platz[:max_n],
            "weitere": max(0, len(mit_platz) - max_n)}


# ── Daten holen (über die Funktionen des Servers) ───────────────────────────────
def _chart(yget, sym):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/%s?range=2y&interval=1d"
           % urllib.parse.quote(sym))
    ch = json.loads(yget(url, timeout=20).read().decode("utf-8", "ignore"))
    res = (ch.get("chart", {}).get("result") or [None])[0]
    if not res:
        return None
    ts = res.get("timestamp") or []
    q = (res.get("indicators", {}).get("quote") or [{}])[0]
    zeilen = []
    for k in range(len(ts)):
        try:
            c, h, l = q["close"][k], q["high"][k], q["low"][k]
            v = (q.get("volume") or [None] * len(ts))[k]
        except (KeyError, IndexError, TypeError):
            continue
        if None in (c, h, l):
            continue
        zeilen.append((ts[k], c, h, l, v or 0))
    return zeilen


def volumen_faktor(yget, sammler):
    """Die TWS meldet das Volumen je nach Wert und Version teils in 100er-Stück. Vergleich
    SPY Sammler gegen Yahoo an denselben Tagen: Faktor 1 oder 100. None = nicht prüfbar."""
    try:
        r = sammler.kerzen_fuer("SPY", 30)
        y = _chart(yget, "SPY") or []
        if not (r.get("ok") and y):
            return None
        ms = {time.strftime("%Y-%m-%d", time.gmtime(t)): v for t, v in zip(r["times"], r["volumes"])}
        q = sorted(yv / ms[d] for d, yv in ((time.strftime("%Y-%m-%d", time.gmtime(t)), v) for t, _, _, _, v in y) if ms.get(d))
        if not q:
            return None
        median = q[len(q) // 2]
        return 100.0 if median > 30 else 1.0
    except Exception:
        return None


def scanne(yget, batch_quote, us_syms, de_syms, plan=None, sammler=None):
    """sammler: Modul marktsammler (oder None). Dann kommen Tageskerzen zuerst aus dem
    Marktsammler; fehlt ein Wert dort oder ist er nicht aktuell, aus Yahoo."""
    plan = plan or {}
    uni = plan.get("universum", {}) if isinstance(plan, dict) else {}
    min_umsatz = float(uni.get("liquiditaet_mio_eur", 1.0)) * 1e6
    mindestkurs = float(uni.get("mindestkurs", 0) or 0)
    max_n = int(uni.get("max_vorschlaege", 20))
    try:
        sektoren = json.load(open(os.path.join(HIER, "sektoren.json"), encoding="utf-8")).get("sektor", {})
    except Exception:
        sektoren = {}
    benchmarks = sorted(set(sektoren.values()) | {"SPY", "^GDAXI"})
    alle = [(s, "US") for s in us_syms] + [(s, "DE") for s in de_syms]

    faktor = volumen_faktor(yget, sammler) if sammler else None
    herkunft = {}

    def hol(sym):
        if sammler:
            try:
                r = sammler.kerzen_fuer(sym, 520)
                if r.get("ok") and r.get("frisch") and len(r["closes"]) >= 260:
                    f = faktor or 1.0
                    herkunft[sym] = "Marktsammler"
                    return sym, list(zip(r["times"], r["closes"], r["highs"], r["lows"], [v * f for v in r["volumes"]]))
            except Exception:
                pass
        try:
            herkunft[sym] = "Yahoo"
            return sym, _chart(yget, sym)
        except Exception:
            return sym, None

    with ThreadPoolExecutor(max_workers=6) as ex:
        daten = dict(ex.map(hol, [s for s, _ in alle] + benchmarks))

    def reihe_zu(bench_sym, zeitstempel):
        z = daten.get(bench_sym) or []
        m = {time.strftime("%Y-%m-%d", time.gmtime(t)): c for t, c, *_ in z}
        out = [m.get(time.strftime("%Y-%m-%d", time.gmtime(t))) for t in zeitstempel]
        # Lücken mit dem letzten bekannten Wert füllen
        letzt = None
        for k, x in enumerate(out):
            if x is None:
                out[k] = letzt
            else:
                letzt = x
        return out

    treffer, fehler = [], 0
    for sym, markt in alle:
        z = daten.get(sym)
        if not z:
            fehler += 1
            continue
        ts = [r[0] for r in z]
        bsym = sektoren.get(sym, "SPY") if markt == "US" else "^GDAXI"
        r = pruefe_titel([r[1] for r in z], [r[2] for r in z], [r[3] for r in z], [r[4] for r in z], reihe_zu(bsym, ts))
        if r and r["kurs"] < mindestkurs:
            r["signal"] = False          # unter dem Mindestkurs aus dem Handelsplan
        if r:
            r.update(symbol=sym, markt=markt, vergleich=bsym, stand=time.strftime("%Y-%m-%d", time.gmtime(ts[-1])), quelle=herkunft.get(sym))
            treffer.append(r)
    erg = {"US": auswahl([t for t in treffer if t["markt"] == "US"], min_umsatz, max_n),
           "DE": auswahl([t for t in treffer if t["markt"] == "DE"], min_umsatz, max_n)}
    # N3: Quartalszahlen nur für die Vorschläge nachschlagen
    vorschl = [t for m in erg.values() for t in m["vorschlaege"]]
    syms = [t["symbol"] for t in vorschl]
    termine = {}
    for k in range(0, len(syms), 50):
        try:
            for q in batch_quote(syms[k:k + 50]) or []:
                et = q.get("earningsTimestamp") or q.get("earningsTimestampStart")
                if et:
                    termine[q.get("symbol")] = et
        except Exception:
            pass
    jetzt = time.time()
    for t in vorschl:
        et = termine.get(t["symbol"])
        t["earnings"] = et
        t["earnings_bald"] = bool(et and -43200 < et - jetzt <= 10 * 86400)
    qn = {}
    for sym, _ in alle:
        if daten.get(sym):
            qn[herkunft.get(sym, "Yahoo")] = qn.get(herkunft.get(sym, "Yahoo"), 0) + 1
    return {"ok": True, "ts": int(jetzt * 1000), "gescannt": len(alle), "ohne_daten": fehler, "quellen": qn,
            "volumen_faktor": faktor, "volumen_geprueft": (faktor is not None) if sammler else None,
            "min_umsatz": min_umsatz, "max_vorschlaege": max_n, "maerkte": erg,
            "regel": "Rücksetzer in P3 + Platz bis Widerstand (Systemtest 2b); RS Sektor zur Sortierung"}
