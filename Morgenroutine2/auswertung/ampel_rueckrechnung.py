#!/usr/bin/env python3
"""Rückrechnung der Morgenroutine-Ampel (v6.17) auf historischen Daten.

Bildet computeAmpel(), panikComponents(), luedePhase(), deriveVixTerm() und
tagesKonsequenz() aus ferit_morgenroutine_v6.html nach. Abweichungen zum Live-
Programm sind bewusst und unten in ANNAHMEN dokumentiert.

Aufruf:  python3 ampel_rueckrechnung.py <rohdaten-ordner> <ausgabe-ordner>
"""
import json, os, sys
import numpy as np
import pandas as pd

ANNAHMEN = [
    "Signal aus dem Schlusskurs von Tag t (die Routine läuft am Morgen danach).",
    "Handelbar erst ab Schluss t+1: alle Folgerenditen beginnen einen Tag nach dem Signal (vorsichtig).",
    "EMA wie im Programm: Fenster der letzten 502 Handelstage (Yahoo range=2y), Startwert = SMA.",
    "Manuelle Sentimentwerte (PCR, AAII-Bear, NAAIM) als letzter bis Tag t veröffentlichter Wert.",
    "PCR-Equity nur bis 04.10.2019 verfügbar, danach fehlt das Signal (wie ein leeres Feld im Programm).",
    "Fear & Greed erst ab 03.01.2011; vor 2011 wird der Score ohne F&G normiert (Programmlogik).",
    "Terminwoche (FOMC/Arbeitsmarkt/Earnings) ist NICHT nachgebildet — die Konsequenz-Zeile ist ohne diesen Größen-Dämpfer.",
    "Indexdaten DIA/IWM enden am 08.09.2026; Auswertung endet dort.",
    "Datenquellen: öffentliche GitHub-Abzüge Dritter, siehe quellen.json.",
]
SEKTOREN = ["XLK", "XLC", "XLY", "XLF", "XLV", "XLI", "XLP", "XLE", "XLB", "XLU", "XLRE"]
US = ["SPY", "QQQ", "DIA", "IWM"]
FENSTER = 502


def lade(roh, k):
    p = os.path.join(roh, k + ".csv")
    if k in ("DIA", "IWM"):
        d = pd.read_csv(p, header=None, names=["date", "close"])
    else:
        d = pd.read_csv(p)
        ren = {"Date": "date", "Close": "close", "price": "close", "Time": "date", "Last": "close"}
        d = d.rename(columns={c: ren[c] for c in d.columns if c in ren})
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["date", "close"]).drop_duplicates("date")
    return d.set_index("date")["close"].astype(float).sort_index()


def lade_sentiment(roh):
    fg = pd.read_csv(os.path.join(roh, "FG.csv"), parse_dates=["Date"]).set_index("Date")["Fear Greed"]
    aa = pd.read_csv(os.path.join(roh, "AAII.csv"), parse_dates=["date"]).set_index("date")["bearish"] * 100
    na = pd.read_csv(os.path.join(roh, "NAAIM.csv"), parse_dates=["Date"]).set_index("Date")["naaim_mean"]
    pc = pd.read_csv(os.path.join(roh, "PCR.csv"), parse_dates=["date"]).set_index("date")["value"]
    return {k: v[~v.index.duplicated()].sort_index() for k, v in
            {"fg": fg, "bear": aa, "naaim": na, "pcr": pc}.items()}


def ema_fenster(s, p, L=FENSTER):
    """EMA wie im JS: über die letzten L Werte, Startwert SMA der ersten p."""
    x = s.values
    k = 2 / (p + 1)
    w = np.empty(L)
    w[:p] = (1 / p) * (1 - k) ** (L - p)
    j = np.arange(p, L)
    w[p:] = k * (1 - k) ** (L - 1 - j)
    out = np.full(len(x), np.nan)
    if len(x) >= L:
        from numpy.lib.stride_tricks import sliding_window_view
        out[L - 1:] = sliding_window_view(x, L) @ w
    return pd.Series(out, index=s.index)


def phase(px, e20, e50, e200):
    if any(pd.isna(v) for v in (px, e20, e50, e200)):
        return "–"
    if px > e50 and e50 > e200:
        return "P3"
    if px < e20 and e20 < e200:
        return "P6"
    if e50 > e200:
        return "P5" if (px < e50 and px < e200) else "P4"
    if px > e200 and px > e50:
        return "P2"
    if px < e50 and px < e200:
        return "P5"
    return "P1"


def term_regime(vix, v3):
    if pd.isna(vix) or pd.isna(v3) or v3 <= 0:
        return None
    r = vix / v3
    return "contango" if r < 0.98 else "flat" if r < 1.02 else "back-light" if r < 1.10 else "back-strong"


def panik(vix, vvix, fg, pcr, bear, naaim, term):
    C = []
    def add(w, p): C.append((w, p))
    add(24, None if pd.isna(vix) else 0 if vix < 18 else 6 if vix < 22 else 13 if vix < 28 else 19 if vix < 35 else 24)
    add(10, None if pd.isna(vvix) else 0 if vvix < 90 else 4 if vvix < 110 else 7 if vvix < 130 else 10)
    add(20, None if pd.isna(fg) else 0 if fg > 45 else 5 if fg > 35 else 10 if fg > 25 else 15 if fg > 15 else 20)
    add(14, None if pd.isna(pcr) else 0 if pcr < 0.7 else 4 if pcr < 1.0 else 9 if pcr < 1.2 else 14)
    add(12, None if pd.isna(bear) else 0 if bear < 30 else 4 if bear < 40 else 8 if bear < 50 else 12)
    add(10, None if pd.isna(naaim) else 0 if naaim > 60 else 3 if naaim > 40 else 7 if naaim > 20 else 10)
    add(10, None if not term else 0 if term == "contango" else 3 if term == "flat" else 6 if term == "back-light" else 10)
    score = sum(p or 0 for _, p in C)
    cov = sum(w for w, p in C if p is not None)
    return (round(score / cov * 100) if cov >= 50 else None), cov


def ampel(p3, p6, n, vix, fg, part, partTot, rsBeat, rsTot, pan, term):
    narrow = rsBeat is not None and rsTot >= 6 and rsBeat < 3
    pz = pan if pan is not None else -1  # null >= x ist im JS false
    if fg is not None and not pd.isna(fg) and not pd.isna(vix) and fg <= 15 and vix > 30 and term in ("back-strong", "back-light"):
        return "REVERSE", ["Extremangst"]
    gr = []
    if p6 >= 2 or (vix > 28) or pz >= 70 or (part is not None and part < 3 and p3 < 2):
        if p6 >= 2: gr.append("p6>=2")
        if vix > 28: gr.append("vix>28")
        if pz >= 70: gr.append("panik>=70")
        if part is not None and part < 3 and p3 < 2: gr.append("breite<3")
        return "STOP", gr
    if p3 < 3 or vix >= 20 or (part is not None and part < 6) or narrow or pz >= 45 or term in ("back-light", "back-strong"):
        if p3 < 3: gr.append("p3<3")
        if vix >= 20: gr.append("vix>=20")
        if part is not None and part < 6: gr.append("breite<6")
        if narrow: gr.append("fuehrung_eng")
        if pz >= 45: gr.append("panik>=45")
        if term in ("back-light", "back-strong"): gr.append("backwardation")
        return "CAUTION", gr
    if p3 >= 3 and vix < 20 and (part is None or part >= 6) and p6 == 0:
        return "GO", []
    return "CAUTION", ["unklar"]


def konsequenz(farbe, p3, p6):
    if p3 >= 3: r, g = "LONG", "normal"
    elif p6 >= 3: r, g = "SHORT", "normal"
    elif p3 == 2: r, g = "LONG", "reduziert"
    elif p6 == 2: r, g = "SHORT", "reduziert"
    else: r, g = "NUR_GAPS", "klein"
    if r != "SHORT":
        if farbe == "REVERSE" and g == "normal": g = "reduziert"
        elif farbe == "STOP": r, g = "KEINE", "-"
        elif farbe == "CAUTION" and g == "normal": g = "reduziert"
    return r, g


def berechne(roh):
    px = {k: lade(roh, k) for k in US + SEKTOREN + ["VIX", "VIX3M", "VVIX"]}
    sent = lade_sentiment(roh)
    kal = px["SPY"].index
    kal = kal[(kal >= "2007-07-01") & (kal <= min(px["DIA"].index.max(), px["IWM"].index.max()))]
    ind = {}
    for k in US + SEKTOREN:
        s = px[k]
        ind[k] = pd.DataFrame({"px": s, "e20": ema_fenster(s, 20), "e50": ema_fenster(s, 50),
                               "e200": ema_fenster(s, 200), "p21": s / s.shift(21) - 1}).reindex(kal)
    vix = px["VIX"].reindex(kal).ffill(limit=2)
    v3 = px["VIX3M"].reindex(kal).ffill(limit=2)
    vv = px["VVIX"].reindex(kal).ffill(limit=2)
    asof = {k: v.reindex(kal, method="ffill") for k, v in sent.items()}
    # F&G: täglicher Wert, max. 3 Tage alt; Wochenwerte: max. 10 Tage alt; PCR max. 3 Tage
    for k, lim in (("fg", 3), ("bear", 10), ("naaim", 10), ("pcr", 3)):
        last = sent[k].index.to_series().reindex(kal, method="ffill")
        alt = (kal.to_series() - last).dt.days
        asof[k] = asof[k].where(alt <= lim)
    rows = []
    for t in kal:
        ph = {k: phase(*ind[k].loc[t, ["px", "e20", "e50", "e200"]]) for k in US}
        base = [k for k in US if ph[k] != "–"]
        p3 = sum(ph[k] == "P3" for k in base); p6 = sum(ph[k] == "P6" for k in base); n = len(base)
        sek = [k for k in SEKTOREN if not pd.isna(ind[k].loc[t, "e200"])]
        part = sum(ind[k].loc[t, "px"] > ind[k].loc[t, "e50"] for k in sek) if sek else None
        part200 = sum(ind[k].loc[t, "px"] > ind[k].loc[t, "e200"] for k in sek) if sek else None
        spy1 = ind["SPY"].loc[t, "p21"]
        rsl = [ind[k].loc[t, "p21"] - spy1 for k in sek if not pd.isna(ind[k].loc[t, "p21"])]
        rsBeat = sum(r > 0 for r in rsl) if rsl else None
        term = term_regime(vix[t], v3[t])
        pan, cov = panik(vix[t], vv[t], asof["fg"][t], asof["pcr"][t], asof["bear"][t], asof["naaim"][t], term)
        f, gr = ampel(p3, p6, n, vix[t], asof["fg"][t], part, len(sek) or 11, rsBeat, len(rsl) or 11, pan, term)
        r, g = konsequenz(f, p3, p6)
        rows.append(dict(date=t, ampel=f, gruende="|".join(gr), richtung=r, groesse=g, p3=p3, p6=p6, n=n,
                         vix=vix[t], term=term, panik=pan, abdeckung=cov, breite=part, breiteTot=len(sek),
                         rsBeat=rsBeat, rsTot=len(rsl), breite200=part200, fg=asof["fg"][t],
                         spy_ueber_e200=bool(ind["SPY"].loc[t, "px"] > ind["SPY"].loc[t, "e200"]), **{"ph_" + k: ph[k] for k in US}))
    df = pd.DataFrame(rows).set_index("date")
    hy = pd.read_csv(os.path.join(roh, "HYOAS.csv"))
    hy = pd.Series(pd.to_numeric(hy.iloc[:, 1], errors="coerce").values, index=pd.to_datetime(hy.iloc[:, 0])).dropna().sort_index()
    hy = hy.reindex(df.index, method="ffill")
    df["hy_oas"] = hy
    df["hy_chg63"] = hy - hy.shift(63)
    spy = px["SPY"]
    c = spy.reindex(spy.index)
    for h in (5, 20, 60):
        fwd = c.shift(-(h + 1)) / c.shift(-1) - 1
        df[f"spy_fwd{h}"] = fwd.reindex(df.index)
    lo = c[::-1].rolling(20, min_periods=1).min()[::-1]
    df["spy_maxdd20"] = (lo.shift(-2) / c.shift(-1) - 1).reindex(df.index)
    hi = c[::-1].rolling(20, min_periods=1).max()[::-1]
    df["spy_maxup20"] = (hi.shift(-2) / c.shift(-1) - 1).reindex(df.index)
    df["spy_ret_next"] = (c.shift(-2) / c.shift(-1) - 1).reindex(df.index)
    return df, px


if __name__ == "__main__":
    roh, aus = sys.argv[1], sys.argv[2]
    os.makedirs(aus, exist_ok=True)
    df, _ = berechne(roh)
    df.to_csv(os.path.join(aus, "ampel_taeglich.csv"))
    json.dump(ANNAHMEN, open(os.path.join(aus, "annahmen.json"), "w"), ensure_ascii=False, indent=1)
    print(df["ampel"].value_counts())
