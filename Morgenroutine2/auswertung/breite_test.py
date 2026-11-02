#!/usr/bin/env python3
"""Test Marktbreite aus Einzelaktien — Regeln VOR der Auswertung festgelegt (02.11.2026).

Daten: tägliche Kurse der HEUTIGEN S&P-500-Mitglieder (öffentlicher GitHub-Abzug,
31.10.2016–30.10.2026). Achtung Survivorship: ausgeschiedene Aktien fehlen, neue
Tiefs werden v. a. in frühen Jahren zu selten gezählt.

Kennzahlen je Handelstag:
  NH / NL   = Anteil Aktien mit neuem 52-Wochen-Hoch (Hoch >= Max der 252 Vortage)
              bzw. neuem 52-Wochen-Tief (Tief <= Min der 252 Vortage), in %
  NHNL10    = 10-Tage-Durchschnitt von (NH - NL)
  P3_ANTEIL = Anteil Aktien in Phase 3 (Schluss > EMA50 > EMA200), in %
  P3_D5     = Veränderung von P3_ANTEIL gegenüber vor 5 Handelstagen, in Prozentpunkten

REGELN (Basis = neue Ampel AM1 + AM4; unverändert lassen):
  B1 "Netto-Hochs negativ":   NHNL10 < 0  ->  GO und VOREINSTIEG werden CAUTION.
  B2 "Breite bestätigt GO":    P3_ANTEIL < 50  ->  GO wird CAUTION.
  B3 "Breite dreht hoch":      CAUTION und P3_D5 >= +5 und P3_ANTEIL >= 40
                               ->  VOREINSTIEG-Gewicht (75 %).
  Prüfzeiträume: 2017-11 bis 2021-12 und 2022-01 bis 2026-09.
  Freigabe nur bei besserer Sharpe-Kennzahl in BEIDEN Zeiträumen.
  Drei Regeln gleichzeitig geprüft -> Zufallstreffer möglich; Ergebnis entsprechend vorsichtig lesen.

Aufruf: python3 breite_test.py <rohdaten-ordner> <ausgabe-ordner> <aktien-ordner>
"""
import json, os, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from ampel_auswertung import kennzahlen, GEWICHT, neu_ampel  # noqa: E402
from ampel_rueckrechnung import lade  # noqa: E402
from am4_voreinstieg_test import voreinstieg, GEWICHT_VOR  # noqa: E402

QUELLE = "https://raw.githubusercontent.com/mano000may/Hackathon-Project/HEAD/data/{}.csv"


def tickerliste():
    s = open(os.path.join(os.path.dirname(__file__), "..", "START_Morgenroutine_v6.py"), encoding="utf-8").read()
    return re.search(r'SP500_SYMS = "([^"]+)"', s).group(1).split(",")


def laden(ordner):
    os.makedirs(ordner, exist_ok=True)
    def hol(t):
        p = os.path.join(ordner, t + ".csv")
        if not os.path.exists(p):
            try:
                open(p, "wb").write(urllib.request.urlopen(QUELLE.format(t), timeout=60).read())
            except Exception:
                return t, False
        return t, True
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(hol, tickerliste()))
    return [t for t, ok in res if ok]


def kennzahlen_breite(ordner, ticker):
    C, H, L = {}, {}, {}
    for t in ticker:
        d = pd.read_csv(os.path.join(ordner, t + ".csv"), parse_dates=["Date"]).set_index("Date").sort_index()
        d = d[~d.index.duplicated()]
        C[t], H[t], L[t] = d["Close"], d["High"], d["Low"]
    C, H, L = pd.DataFrame(C), pd.DataFrame(H), pd.DataFrame(L)
    da = C.notna()
    nh = (H >= H.shift(1).rolling(252, min_periods=252).max()) & da
    nl = (L <= L.shift(1).rolling(252, min_periods=252).min()) & da
    gueltig = H.shift(1).rolling(252, min_periods=252).max().notna().sum(axis=1)
    e50 = C.ewm(span=50, adjust=False).mean(); e200 = C.ewm(span=200, adjust=False).mean()
    p3 = (C > e50) & (e50 > e200) & da
    b = pd.DataFrame({"NH": nh.sum(axis=1) / gueltig * 100, "NL": nl.sum(axis=1) / gueltig * 100,
                      "P3_ANTEIL": p3.sum(axis=1) / da.sum(axis=1) * 100, "aktien": da.sum(axis=1)})
    b["NHNL10"] = (b.NH - b.NL).rolling(10).mean()
    b["P3_D5"] = b.P3_ANTEIL - b.P3_ANTEIL.shift(5)
    return b[b.index >= "2017-11-01"]


def main(roh, aus, aktien):
    ticker = laden(aktien)
    b = kennzahlen_breite(aktien, ticker)
    df = pd.read_csv(os.path.join(aus, "ampel_taeglich.csv"), parse_dates=["date"], index_col="date")
    df = df.join(b, how="inner")
    spy = lade(roh, "SPY")
    ret = (spy.shift(-2) / spy.shift(-1) - 1).reindex(df.index)
    g = dict(GEWICHT, VOREINSTIEG=GEWICHT_VOR)
    basis = voreinstieg(df, neu_ampel(df, breite_col="breite200"))
    b1 = basis.where(~((df.NHNL10 < 0) & basis.isin(["GO", "VOREINSTIEG"])), "CAUTION")
    b2 = basis.where(~((df.P3_ANTEIL < 50) & (basis == "GO")), "CAUTION")
    b3 = basis.where(~((basis == "CAUTION") & (df.P3_D5 >= 5) & (df.P3_ANTEIL >= 40)), "VOREINSTIEG")
    V = {"AM1 + AM4 (neue Ampel)": basis, "B1 Netto-Hochs negativ": b1, "B2 Breite bestätigt GO": b2,
         "B3 Breite dreht hoch": b3, "Ampel heute (alt)": df.ampel}
    zeit = {"gesamt": slice(None, None), "2017-11 bis 2021-12": slice(None, "2021-12-31"),
            "2022-01 bis 2026-09": slice("2022-01-01", None)}
    E = {"aktien_geladen": len(ticker), "zeitraum": [str(df.index.min().date()), str(df.index.max().date())],
         "varianten": {n: {z: kennzahlen(s.map(g).loc[zs], ret.loc[zs]) for z, zs in zeit.items()} for n, s in V.items()}}
    # beschreibend: Folgerenditen nach Stufen
    def stufen(col, bins, labels):
        k = pd.cut(df[col], bins, labels=labels)
        return {str(l): {"tage": int(len(x)), "spy_20T_mittel_pct": round(x.spy_fwd20.mean() * 100, 2),
                         "spy_20T_positiv_pct": round((x.spy_fwd20 > 0).mean() * 100, 0),
                         "rueckschlag_20T_mittel_pct": round(x.spy_maxdd20.mean() * 100, 2),
                         "rueckschlag_ueber7pct_anteil": round((x.spy_maxdd20 <= -0.07).mean() * 100, 0)}
                for l, x in df.groupby(k, observed=True)}
    E["nach_NHNL10"] = stufen("NHNL10", [-100, -5, -1, 0, 1, 3, 100], ["< -5", "-5 bis -1", "-1 bis 0", "0 bis 1", "1 bis 3", "> 3"])
    E["nach_P3_ANTEIL"] = stufen("P3_ANTEIL", [-1, 20, 35, 50, 65, 101], ["< 20 %", "20-35 %", "35-50 %", "50-65 %", "> 65 %"])
    E["nach_P3_D5"] = stufen("P3_D5", [-100, -10, -5, -1, 1, 5, 10, 100], ["<= -10", "-10 bis -5", "-5 bis -1", "+-1", "+1 bis +5", "+5 bis +10", ">= +10"])
    E["aktuell"] = b.tail(5).round(2).reset_index().astype(str).to_dict("records")
    df[["NH", "NL", "NHNL10", "P3_ANTEIL", "P3_D5", "aktien"]].round(2).to_csv(os.path.join(aus, "breite_taeglich.csv"))
    json.dump(E, open(os.path.join(aus, "breite_test.json"), "w"), ensure_ascii=False, indent=1)
    return E


if __name__ == "__main__":
    print(json.dumps(main(*sys.argv[1:4]), ensure_ascii=False, indent=1))
