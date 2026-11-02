#!/usr/bin/env python3
"""Phase 2b — Test des eigenen Handelssystems (S1–S4). Regeln VOR der Auswertung
festgelegt und eingecheckt (02.11.2026). Nach dem ersten Lauf wird nichts mehr angepasst.

ZWECK
  Bisher wurde nur die Ampel (Marktumfeld) getestet. Hier wird gemessen, ob die
  eigenen Auswahlkriterien für Einzelaktien einen Vorteil bringen, welcher Ausstieg
  passt und welche Verlustserien realistisch sind. Das Ergebnis ist eine Information,
  KEIN Handelsstopp (Absprache mit Ferit): Ein „bringt nichts“ heißt nur, dass sich
  ein Kriterium in diesen Daten nicht messbar auszahlt.

DATEN
  Tageskurse (OHLC, bereinigt) der HEUTIGEN S&P-500-Mitglieder, 31.10.2016–30.10.2026,
  Sektor laut GICS (datasets/s-and-p-500-companies), Sektor-ETFs XLK … XLRE.
  Survivorship-Verzerrung: ausgeschiedene Aktien fehlen. Absolute Ergebnisse sind
  dadurch zu gut; Vergleiche zwischen Varianten sind belastbarer als die Höhe.
  Prüfzeiträume: A = 2017-11-01 … 2021-12-31, B = 2022-01-01 … 2026-09-30.

GRUNDSIGNAL T (Rücksetzer-Einstieg „Bewegung–Korrektur–Bewegung“), Signal am Schluss t:
  1. Phase 3: Schluss > EMA50 > EMA200
  2. Korrektur: an mindestens einem der 5 Vortage lag der Schluss unter der EMA20
  3. Bewegung: Schluss t über EMA20
  Einstieg: Eröffnung t+1. Anfangsstopp: tiefstes Tief der letzten 10 Tage (bis t).
  Stoppabstand muss zwischen 1 % und 15 % liegen, sonst kein Trade.
  Liegt die Eröffnung t+1 unter dem Stopp, entfällt der Trade.

DEINE DREI KRITERIEN (einzeln zuschaltbar)
  K1 Hochnähe:   Das 52-Wochen-Hoch (höchstes Hoch der letzten 252 Tage) wurde in den
                 letzten 30 Handelstagen erreicht. (Allzeithoch ist mit 10 Jahren Daten
                 nicht sauber bestimmbar; das 52-Wochen-Hoch ist die Näherung.)
  K2 Platz:      Widerstand = 52-Wochen-Hoch. Liegt der Schluss t darüber oder darauf,
                 gibt es keinen Widerstand (bestanden). Sonst muss gelten:
                 (Widerstand − Schluss) > (Schluss − Stopp).
  K3 RS Sektor:  3-Monats-Performance (63 Tage) der Aktie minus die des eigenen
                 Sektor-ETFs > 0. Für XLC vor Juni 2018: gleichgewichteter Schnitt der
                 Sektoraktien aus den Daten.

AUSSTIEGE (S2)
  E1 Ziel CRV 2   E2 Ziel CRV 3   (je mit Anfangsstopp)
  E3 Schluss unter EMA20 → Ausstieg zur nächsten Eröffnung (Anfangsstopp gilt weiter)
  E4 Nachziehen auf das tiefste Tief der letzten 10 Tage (nur nach oben)
  E5 ATR-Trailing: höchster Schluss seit Einstieg − 3 × ATR14 (nur nach oben)
  Alle: höchstens 120 Handelstage. Stopp intraday zum Stoppkurs, bei Eröffnung unter
  dem Stopp zur Eröffnung. Kosten 0,1 % des Positionswerts je Trade (hin und zurück).
  Standard für S1 und S4: E4.

PORTFOLIO (S1, S3, S4)
  Höchstens 10 Positionen, Risiko 0,25 % des Kontos je Trade (Positionsgröße aus dem
  Stoppabstand), keine Aktie doppelt. Mehr Kandidaten als freie Plätze: zufällige
  Auswahl, 20 Durchläufe mit festen Startwerten, berichtet wird der Mittelwert.
  Tageswertung zum Schlusskurs. Kennzahlen: Erwartungswert je Trade in R,
  Trefferquote, Gewinnfaktor, Rendite pro Jahr, größter Verlust, Sharpe (ohne Zins).

MIT AMPEL
  Neue Einstiege nur, wenn die neue Ampel (referenz_ampel_v2.csv, Signal t) GO,
  VOREINSTIEG oder CAUTION zeigt; bei STOP und REVERSE keine neuen Einstiege.

S1  Alle 8 Kombinationen von K1/K2/K3 auf T, mit und ohne Ampel, Ausstieg E4.
    Ein Kriterium „trägt bei“, wenn es den Erwartungswert in R in BEIDEN Zeiträumen
    erhöht (Vergleich T+Rest mit gegen ohne das Kriterium).
S2  Ausstiege E1–E5 auf T+K1+K2+K3 mit Ampel.
S3  Mit der Variante T+K1+K2+K3, Ampel, E4: Verlustserien und größter Verlust;
    zusätzlich 10.000-mal neu gemischte Trade-Reihenfolge (95-%-Werte).
S4  52-Wochen-Ausbruch: Phase 3 und Schluss t > höchstes Hoch der 252 Vortage.
    Stopp, Einstieg, Ausstieg und Portfolio wie oben. Mit und ohne K3, mit Ampel.
    Vergleich mit S1 (T+K1+K2+K3), zusätzlich getrennt nach Ampelzustand und nach
    Marktbreite (P3-Anteil der Aktien unter/über 50 %, breite_taeglich.csv).

Viele Varianten gleichzeitig → Zufallstreffer möglich; Unterschiede unter ~0,05 R
sind nicht als Befund zu lesen.

Aufruf: python3 system_test.py <aktien-ordner> <roh-ordner> <constituents.csv> <ausgabe-ordner>
"""
import json
import os
import sys
from itertools import product

import numpy as np
import pandas as pd

HIER = os.path.dirname(os.path.abspath(__file__))
ZEITRAUM = {"A": ("2017-11-01", "2021-12-31"), "B": ("2022-01-01", "2026-09-30")}
RISIKO = 0.0025
SLOTS = 10
KOSTEN = 0.001
MAX_TAGE = 120
LAEUFE = 20
SEKTOR_ETF = {"Information Technology": "XLK", "Communication Services": "XLC", "Consumer Discretionary": "XLY",
              "Financials": "XLF", "Health Care": "XLV", "Industrials": "XLI", "Consumer Staples": "XLP",
              "Energy": "XLE", "Materials": "XLB", "Utilities": "XLU", "Real Estate": "XLRE"}


# ── Daten ──────────────────────────────────────────────────────────────────────
def lade_panel(ordner):
    O, H, L, C = {}, {}, {}, {}
    for fn in sorted(os.listdir(ordner)):
        if not fn.endswith(".csv"):
            continue
        t = fn[:-4]
        try:
            d = pd.read_csv(os.path.join(ordner, fn), parse_dates=["Date"]).dropna().drop_duplicates("Date").set_index("Date").sort_index()
        except Exception:
            continue
        if len(d) < 300:
            continue
        O[t], H[t], L[t], C[t] = d.Open, d.High, d.Low, d.Close
    f = lambda x: pd.DataFrame(x).sort_index()
    return f(O), f(H), f(L), f(C)


def ema(df, n):
    """EMA mit SMA-Startwert wie in der Morgenroutine/Rückrechnung."""
    out = df.copy() * np.nan
    a = 2 / (n + 1)
    arr = df.values
    res = np.full(arr.shape, np.nan)
    for j in range(arr.shape[1]):
        col = arr[:, j]
        ok = np.where(~np.isnan(col))[0]
        if len(ok) < n:
            continue
        s = ok[0]
        e = np.nanmean(col[s:s + n])
        res[s + n - 1, j] = e
        for i in range(s + n, len(col)):
            v = col[i]
            if not np.isnan(v):
                e = v * a + e * (1 - a)
            res[i, j] = e
    out.loc[:, :] = res
    return out


def atr(H, L, C, n=14):
    pc = C.shift(1)
    tr = pd.DataFrame(np.maximum.reduce([(H - L).values, (H - pc).abs().values, (L - pc).abs().values]), index=C.index, columns=C.columns)
    return tr.rolling(n).mean()


def sektor_benchmark(C, roh, sektoren):
    """Sektorkurs je Aktie (Spalten wie C)."""
    etf = {}
    for e in set(SEKTOR_ETF.values()):
        d = pd.read_csv(os.path.join(roh, e + ".csv"), parse_dates=["date"]).set_index("date")["price"]
        etf[e] = d.reindex(C.index).ffill()
    # Gleichgewichteter Sektorschnitt (für XLC vor Juni 2018)
    ret = C.pct_change(fill_method=None)
    gw = {}
    for s in set(sektoren.values()):
        cols = [t for t in C.columns if sektoren.get(t) == s]
        gw[s] = (1 + ret[cols].mean(axis=1).fillna(0)).cumprod()
    B = pd.DataFrame(index=C.index, columns=C.columns, dtype=float)
    for t in C.columns:
        s = sektoren.get(t)
        if not s:
            continue
        e = etf[SEKTOR_ETF[s]]
        B[t] = e.where(e.notna(), np.nan)
        if e.isna().any():
            # Lücke (XLC vor Juni 2018): gleichgewichteter Schnitt
            B[t] = B[t].where(B[t].notna(), gw[s])
    return B


# ── Signale und Kriterien ───────────────────────────────────────────────────────
def merkmale(O, H, L, C, B):
    e20, e50, e200 = ema(C, 20), ema(C, 50), ema(C, 200)
    p3 = (C > e50) & (e50 > e200)
    unter20 = (C < e20)
    korrektur = unter20.shift(1).astype(float).rolling(5).max() > 0
    T = p3 & korrektur & (C > e20)
    stop = L.rolling(10).min()
    hoch252 = H.rolling(252).max()
    hoch252_vor = H.shift(1).rolling(252).max()
    # Tage seit dem 52-Wochen-Hoch (innerhalb der letzten 30)
    neu_hoch = (H >= hoch252)
    k1 = neu_hoch.astype(float).rolling(30).max() > 0
    platz = hoch252 - C
    k2 = (C >= hoch252) | (platz > (C - stop))
    rs = (C / C.shift(63) - 1) - (B / B.shift(63) - 1)
    k3 = rs > 0
    ausbruch = p3 & (C > hoch252_vor)
    return dict(e20=e20, T=T, stop=stop, k1=k1, k2=k2, k3=k3, ausbruch=ausbruch, atr=atr(H, L, C), rs=rs)


def trade_ergebnis(i, j, A, ausstieg):
    """Simuliert einen Trade der Aktie j mit Signal am Index i (A = Numpy-Arrays)."""
    O, H, L, C, STOP, E20, ATR = A["O"], A["H"], A["L"], A["C"], A["stop"], A["e20"], A["atr"]
    n = C.shape[0]
    if i + 1 >= n:
        return None
    stop0 = STOP[i, j]
    ein = O[i + 1, j]
    if not (np.isfinite(stop0) and np.isfinite(ein)) or ein <= stop0:
        return None
    risiko = ein - stop0
    if not (0.01 <= risiko / ein <= 0.15):
        return None
    stopp = stop0
    ziel = ein + (2 if ausstieg == "E1" else 3) * risiko if ausstieg in ("E1", "E2") else None
    hoechst = -np.inf
    pfad = []
    aus_k, aus_i = None, None
    k = i + 1
    letzte = min(n - 1, i + MAX_TAGE)
    while k <= letzte:
        o, h, l, c = O[k, j], H[k, j], L[k, j], C[k, j]
        if not np.isfinite(c):
            break
        if k > i + 1 and o <= stopp:
            aus_k, aus_i = o, k
            break
        if l <= stopp:
            aus_k, aus_i = stopp, k
            break
        if ziel is not None and h >= ziel:
            aus_k, aus_i = (max(o, ziel) if k > i + 1 else ziel), k
            break
        pfad.append((c - ein) / risiko)
        if ausstieg == "E3" and c < E20[k, j] and k + 1 < n:
            aus_k, aus_i = O[k + 1, j], k + 1
            break
        if ausstieg == "E4":
            stopp = max(stopp, np.nanmin(L[max(0, k - 9):k + 1, j]))
        if ausstieg == "E5":
            hoechst = max(hoechst, c)
            a = ATR[k, j]
            if np.isfinite(a):
                stopp = max(stopp, hoechst - 3 * a)
        k += 1
    if aus_i is None:
        aus_i = min(k - 1, letzte)
        if aus_i <= i:
            return None
        aus_k = C[aus_i, j]
        if not np.isfinite(aus_k):
            return None
        pfad = pfad[:-1]          # letzter Tag wird unten als Endwert eingetragen
    r = (aus_k - ein) / risiko - KOSTEN * ein / risiko
    pfad.append(r)
    return {"i": i, "j": j, "ein_i": i + 1, "aus_i": aus_i, "r": r, "pfad": pfad}


# ── Portfolio ───────────────────────────────────────────────────────────────────
def portfolio(trades_je_tag, n_tage, erlaubt, seed):
    rng = np.random.default_rng(seed)
    offen = []          # (aus_i, j, trade)
    belegt = set()
    tag_r = np.zeros(n_tage)
    genommen = []
    for t in range(n_tage):
        offen = [x for x in offen if x[0] >= t]
        belegt = {x[1] for x in offen}
        frei = SLOTS - len(offen)
        if frei > 0 and erlaubt[t]:
            kand = [tr for tr in trades_je_tag.get(t, []) if tr["j"] not in belegt]
            if kand:
                rng.shuffle(kand)
                for tr in kand[:frei]:
                    offen.append((tr["aus_i"], tr["j"], tr))
                    genommen.append(tr)
                    # Tagesweise R-Veränderung ab Einstiegstag eintragen
                    vor = 0.0
                    for d, rr in enumerate(tr["pfad"]):
                        tt = tr["ein_i"] + d
                        if tt < n_tage:
                            tag_r[tt] += rr - vor
                        vor = rr
    return tag_r * RISIKO, genommen


def kennz(tagesrendite, idx, trades, von, bis):
    m = (idx >= pd.Timestamp(von)) & (idx <= pd.Timestamp(bis))
    r = pd.Series(tagesrendite, index=idx)[m]
    eq = (1 + r).cumprod()
    jahre = max(len(r) / 252, 1e-9)
    tr = [t for t in trades if von <= str(idx[t["ein_i"]].date()) <= bis]
    R = np.array([t["r"] for t in tr]) if tr else np.array([])
    gew, verl = R[R > 0].sum(), -R[R < 0].sum()
    return {
        "trades": int(len(R)),
        "erwartung_R": round(float(R.mean()), 3) if len(R) else None,
        "treffer_pct": round(float((R > 0).mean() * 100), 1) if len(R) else None,
        "gewinnfaktor": round(float(gew / verl), 2) if verl > 0 else None,
        "rendite_pa_pct": round(float((eq.iloc[-1] ** (1 / jahre) - 1) * 100), 2) if len(eq) else None,
        "max_verlust_pct": round(float(((eq / eq.cummax()) - 1).min() * 100), 2) if len(eq) else None,
        "sharpe": round(float(r.mean() / r.std() * np.sqrt(252)), 2) if r.std() > 0 else None,
    }


def mittel(listen):
    out = {}
    for k in listen[0]:
        v = [x[k] for x in listen if x[k] is not None]
        out[k] = round(float(np.mean(v)), 3) if v else None
    return out


def serien(R):
    """Längste Verlustserie und Summe der schlechtesten Serie in R."""
    lang, akt, schlecht, summe = 0, 0, 0.0, 0.0
    for r in R:
        if r <= 0:
            akt += 1
            summe += r
            lang = max(lang, akt)
            schlecht = min(schlecht, summe)
        else:
            akt, summe = 0, 0.0
    return lang, schlecht


def main(aktien, roh, constituents, aus):
    os.makedirs(aus, exist_ok=True)
    O, H, L, C = lade_panel(aktien)
    cons = pd.read_csv(constituents)
    sektoren = {str(s).replace(".", "-"): g for s, g in zip(cons["Symbol"], cons["GICS Sector"])}
    cols = [t for t in C.columns if t in sektoren or t.replace(".", "-") in sektoren]
    sektoren = {t: sektoren.get(t, sektoren.get(t.replace(".", "-"))) for t in cols}
    O, H, L, C = O[cols], H[cols], L[cols], C[cols]
    idx = C.index
    print("Aktien:", len(cols), "Tage:", len(idx), idx[0].date(), "…", idx[-1].date())
    B = sektor_benchmark(C, roh, sektoren)
    M = merkmale(O, H, L, C, B)
    A = {"O": O.values, "H": H.values, "L": L.values, "C": C.values, "stop": M["stop"].values,
         "e20": M["e20"].values.astype(float), "atr": M["atr"].values}

    amp = pd.read_csv(os.path.join(HIER, "ergebnisse", "referenz_ampel_v2.csv"), parse_dates=["date"]).set_index("date")["ampel_v2"]
    amp = amp.reindex(idx).ffill()
    erlaubt_ampel = amp.isin(["GO", "VOREINSTIEG", "CAUTION"]).values
    erlaubt_immer = np.ones(len(idx), bool)
    start = idx.searchsorted(pd.Timestamp("2017-11-01"))

    cache = {}

    def signale(basis, k1, k2, k3, ausstieg):
        key = (basis, k1, k2, k3, ausstieg)
        if key in cache:
            return cache[key]
        maske = M["T"] if basis == "T" else M["ausbruch"]
        if k1: maske = maske & M["k1"]
        if k2: maske = maske & M["k2"]
        if k3: maske = maske & M["k3"]
        mv = maske.fillna(False).values
        je_tag = {}
        for i, j in zip(*np.where(mv)):
            if i < start:
                continue
            tr = trade_ergebnis(i, j, A, ausstieg)
            if tr:
                je_tag.setdefault(i, []).append(tr)
        cache[key] = je_tag
        return je_tag

    def lauf(je_tag, erlaubt):
        res = {"A": [], "B": [], "gesamt": []}
        alle_genommen = []
        for s in range(LAEUFE):
            tr_r, gen = portfolio(je_tag, len(idx), erlaubt, s)
            for z, (von, bis) in list(ZEITRAUM.items()) + [("gesamt", ("2017-11-01", "2026-09-30"))]:
                res[z].append(kennz(tr_r, idx, gen, von, bis))
            alle_genommen.append(gen)
        return {z: mittel(v) for z, v in res.items()}, alle_genommen

    E = {"regeln": "siehe Kopf von system_test.py", "aktien": len(cols),
         "zeitraeume": ZEITRAUM, "S1": {}, "S2": {}, "S3": {}, "S4": {}}

    # ── S1 ──
    for k1, k2, k3 in product([False, True], repeat=3):
        name = "T" + ("+K1" if k1 else "") + ("+K2" if k2 else "") + ("+K3" if k3 else "")
        je = signale("T", k1, k2, k3, "E4")
        roh_n = sum(len(v) for v in je.values())
        for amp_name, erl in (("ohne Ampel", erlaubt_immer), ("mit Ampel", erlaubt_ampel)):
            r, _ = lauf(je, erl)
            E["S1"].setdefault(name, {"signale": roh_n})[amp_name] = r
            print("S1", name, amp_name, r["A"]["erwartung_R"], r["B"]["erwartung_R"], r["gesamt"]["trades"])

    # Beitrag je Kriterium (beide Zeiträume, mit Ampel)
    beitrag = {}
    for k in ("K1", "K2", "K3"):
        besser = {"A": 0, "B": 0, "vergleiche": 0}
        for name in E["S1"]:
            if k in name:
                continue
            teile = name.split("+")
            mit = "+".join(["T"] + sorted([x for x in teile[1:]] + [k]))
            if mit not in E["S1"]:
                continue
            besser["vergleiche"] += 1
            for z in ("A", "B"):
                a = E["S1"][name]["mit Ampel"][z]["erwartung_R"]
                b = E["S1"][mit]["mit Ampel"][z]["erwartung_R"]
                if a is not None and b is not None and b > a:
                    besser[z] += 1
        beitrag[k] = besser
    E["S1_beitrag"] = beitrag

    # ── S2 ──
    for aus_v in ("E1", "E2", "E3", "E4", "E5"):
        je = signale("T", True, True, True, aus_v)
        r, _ = lauf(je, erlaubt_ampel)
        E["S2"][aus_v] = r
        print("S2", aus_v, r["A"]["erwartung_R"], r["B"]["erwartung_R"])

    # ── S3 ──
    je = signale("T", True, True, True, "E4")
    _, genommen = lauf(je, erlaubt_ampel)
    rng = np.random.default_rng(7)
    lang_l, schlecht_l, dd_l = [], [], []
    R0 = np.array([t["r"] for t in sorted(genommen[0], key=lambda x: x["aus_i"])])
    for _ in range(10000):
        R = rng.permutation(R0)
        lang, schlecht = serien(R)
        eq = np.cumprod(1 + R * RISIKO)
        dd = (eq / np.maximum.accumulate(eq) - 1).min()
        lang_l.append(lang); schlecht_l.append(schlecht); dd_l.append(dd)
    lang0, schlecht0 = serien(R0)
    E["S3"] = {"trades": int(len(R0)), "laengste_verlustserie": int(lang0), "schlechteste_serie_R": round(float(schlecht0), 2),
               "mc95_laengste_serie": int(np.percentile(lang_l, 95)), "mc95_schlechteste_serie_R": round(float(np.percentile(schlecht_l, 5)), 2),
               "mc95_max_verlust_pct": round(float(np.percentile(dd_l, 5) * 100), 2),
               "hinweis": "Max. Verlust in der Monte-Carlo-Rechnung aus abgeschlossenen Trades, ohne Gleichzeitigkeit; Tageswerte siehe S1."}

    # ── S4 ──
    for k3 in (False, True):
        name = "Ausbruch" + ("+K3" if k3 else "")
        je = signale("A", False, False, k3, "E4")
        r, gen = lauf(je, erlaubt_ampel)
        E["S4"][name] = r
        print("S4", name, r["A"]["erwartung_R"], r["B"]["erwartung_R"])
    # Aufteilung nach Ampel und Breite: Trades aus Lauf 0 von S1 voll und S4 Ausbruch
    breite = pd.read_csv(os.path.join(HIER, "ergebnisse", "breite_taeglich.csv"), parse_dates=["date"]).set_index("date")["P3_ANTEIL"].reindex(idx).ffill()
    aufteilung = {}
    for name, je in (("S1 T+K1+K2+K3", signale("T", True, True, True, "E4")), ("S4 Ausbruch", signale("A", False, False, False, "E4"))):
        alle = [tr for v in je.values() for tr in v]
        d = {}
        for tr in alle:
            a = amp.iloc[tr["i"]]
            b = breite.iloc[tr["i"]]
            for schl in ("Ampel " + str(a), "Breite " + ("unter 50 %" if b < 50 else "ab 50 %") if np.isfinite(b) else "Breite –"):
                d.setdefault(schl, []).append(tr["r"])
        aufteilung[name] = {k: {"signale": len(v), "erwartung_R": round(float(np.mean(v)), 3), "treffer_pct": round(float(np.mean(np.array(v) > 0) * 100), 1)} for k, v in sorted(d.items())}
    E["S4_aufteilung_alle_signale"] = aufteilung

    # Vergleich: SPY halten
    spy = pd.read_csv(os.path.join(roh, "SPY.csv"))
    spy = spy.rename(columns={c: c.lower() for c in spy.columns})
    spalte = "close" if "close" in spy.columns else spy.columns[1]
    spy = spy.set_index(pd.to_datetime(spy[spy.columns[0]]))[spalte].reindex(idx).ffill()
    sr = spy.pct_change(fill_method=None).fillna(0).values
    E["SPY_halten"] = {z: kennz(sr, idx, [], von, bis) for z, (von, bis) in list(ZEITRAUM.items()) + [("gesamt", ("2017-11-01", "2026-09-30"))]}

    json.dump(E, open(os.path.join(aus, "system_test.json"), "w"), ensure_ascii=False, indent=1)
    print("fertig:", os.path.join(aus, "system_test.json"))


if __name__ == "__main__":
    main(*sys.argv[1:5])
