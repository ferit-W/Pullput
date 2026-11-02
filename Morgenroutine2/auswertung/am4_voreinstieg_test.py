#!/usr/bin/env python3
"""Test AM4 "VOREINSTIEG" — Regel VOR der Auswertung festgelegt (02.11.2026).

REGEL (unverändert lassen, sonst ist der Test wertlos):
  Greift nur, wenn die heutige Ampel STOP oder CAUTION zeigt UND in den letzten
  60 Handelstagen mindestens ein STOP-Tag lag (Erholung nach Stress). Dann alle:
    1. mind. 3 von 4 US-Indizes in P3 (Kurs > EMA50 > EMA200)
    2. kein Index in P6
    3. mind. 6 von 11 Sektoren über ihrer EMA200
    4. VIX-Termstruktur Contango (VIX/VIX3M < 0,98)
  Investitionsgrad bei VOREINSTIEG: 75 % (CAUTION 50 %, GO 100 %).
  Geprüft getrennt 2007-2016 und 2017-2026; Freigabe nur bei Verbesserung in BEIDEN.

Aufruf: python3 am4_voreinstieg_test.py <rohdaten-ordner> <ausgabe-ordner>
"""
import json, os, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from ampel_auswertung import kennzahlen, GEWICHT, neu_ampel  # noqa: E402
from ampel_rueckrechnung import lade  # noqa: E402

FENSTER_NACH_STOP = 60
GEWICHT_VOR = 0.75
TIEFS = ["2009-03-09", "2011-10-03", "2016-02-11", "2018-04-02", "2018-12-24", "2020-03-23", "2022-10-12", "2025-04-08"]


def voreinstieg(df, basis):
    stop_kurz = (basis == "STOP").astype(int).rolling(FENSTER_NACH_STOP, min_periods=1).max().astype(bool)
    bed = ((df.p3 >= 3) & (df.p6 == 0) & (df.breite200 >= 6) & (df.term == "contango"))
    neu = basis.copy()
    neu[basis.isin(["STOP", "CAUTION"]) & stop_kurz & bed] = "VOREINSTIEG"
    return neu


def main(roh, aus):
    df = pd.read_csv(os.path.join(aus, "ampel_taeglich.csv"), parse_dates=["date"], index_col="date")
    spy = lade(roh, "SPY")
    ret = (spy.shift(-2) / spy.shift(-1) - 1).reindex(df.index)
    g = dict(GEWICHT, VOREINSTIEG=GEWICHT_VOR)
    heute = df.ampel
    am1 = neu_ampel(df, breite_col="breite200")
    V = {"Ampel heute": heute, "AM4 Voreinstieg": voreinstieg(df, heute),
         "AM1 Breite EMA200": am1, "AM1 + AM4": voreinstieg(df, am1)}
    zeit = {"gesamt": slice(None, None), "2007-2016": slice(None, "2016-12-31"), "2017-2026": slice("2017-01-01", None)}
    E = {"regel": __doc__.split("REGEL")[1].split("Aufruf")[0].strip(),
         "varianten": {n: {z: kennzahlen(s.map(g).loc[zs], ret.loc[zs]) for z, zs in zeit.items()} for n, s in V.items()}}

    vor = V["AM4 Voreinstieg"]
    m = vor == "VOREINSTIEG"
    E["voreinstieg_tage"] = int(m.sum())
    E["voreinstieg_episoden"] = int((m & ~m.shift(fill_value=False)).sum())
    sub = df[m]
    E["voreinstieg_folgen"] = {"spy_20T_mittel_pct": round(sub.spy_fwd20.mean() * 100, 2),
                               "spy_20T_positiv_pct": round((sub.spy_fwd20 > 0).mean() * 100, 0),
                               "spy_60T_mittel_pct": round(sub.spy_fwd60.mean() * 100, 2),
                               "rueckschlag_20T_mittel_pct": round(sub.spy_maxdd20.mean() * 100, 2),
                               "rueckschlag_ueber7pct_anteil": round((sub.spy_maxdd20 <= -0.07).mean() * 100, 0)}
    # Fehlstarts: Episoden, nach deren Beginn innerhalb 20 Tagen > 7 % Rückschlag kam
    starts = sub.index[(m & ~m.shift(fill_value=False))[m]]
    E["fehlstarts"] = [{"beginn": str(t.date()), "rueckschlag_20T_pct": round(df.loc[t, "spy_maxdd20"] * 100, 1)}
                       for t in starts if df.loc[t, "spy_maxdd20"] <= -0.07]
    E["alle_episoden"] = [{"beginn": str(t.date()), "spy_20T_pct": round(df.loc[t, "spy_fwd20"] * 100, 1),
                           "spy_60T_pct": round(df.loc[t, "spy_fwd60"] * 100, 1) if pd.notna(df.loc[t, "spy_fwd60"]) else None,
                           "rueckschlag_20T_pct": round(df.loc[t, "spy_maxdd20"] * 100, 1)} for t in starts]
    tiefs = []
    for t in TIEFS:
        s = spy.reindex(df.index)
        a = heute[t:]; b = vor[t:]
        ga = a[a == "GO"].index[:1]; vb = b[b.isin(["VOREINSTIEG", "GO"])].index[:1]
        f = lambda x: (str(x[0].date()), round((s[x[0]] / s[t] - 1) * 100, 1)) if len(x) else (None, None)
        (d1, p1), (d2, p2) = f(ga), f(vb)
        tiefs.append({"tief": t, "erstes_GO_heute": d1, "erholung_bis_dahin_pct": p1,
                      "erstes_VOREINSTIEG_oder_GO": d2, "erholung_bis_dahin_pct_neu": p2})
    E["nach_tiefs"] = tiefs
    json.dump(E, open(os.path.join(aus, "am4_voreinstieg.json"), "w"), ensure_ascii=False, indent=1)
    return E


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1], sys.argv[2]), ensure_ascii=False, indent=1))
