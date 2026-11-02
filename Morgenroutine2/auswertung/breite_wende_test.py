#!/usr/bin/env python3
"""Test B4 "BREITEN-WENDE" — Regel VOR der Auswertung festgelegt (02.11.2026).

Idee (Lüddemann-Panik-Wende über die Marktbreite): erst Kapitulation — fast alle
Aktien gefallen —, dann Stabilisierung — neue Tiefs werden weniger, Breite dreht.

REGEL (unverändert lassen, sonst ist der Test wertlos):
  Signal am Tag t, wenn ALLE gelten:
    1. Kapitulation: in den letzten 10 Handelstagen (inkl. t) war P3_ANTEIL < 20
       ODER NHNL10 < -5
    2. Neue Tiefs halbiert: NL(t) <= 0,5 * Maximum von NL der letzten 10 Tage
    3. Breite dreht: P3_ANTEIL(t) > P3_ANTEIL(t-3)
  Danach 15 Handelstage mit mind. 33 % Investitionsgrad (wie AM9), Abbruch, wenn
  SPY unter den tiefsten Schluss der 10 Tage vor dem Signal fällt.
  Basis: neue Ampel (AM1 + AM4). Zeiträume 2017-11 bis 2021-12 / 2022-01 bis 2026-09.
  Freigabe nur bei besserer Sharpe-Kennzahl in BEIDEN Zeiträumen.

Voraussetzung: breite_test.py wurde vorher ausgeführt (breite_taeglich.csv).
Aufruf: python3 breite_wende_test.py <rohdaten-ordner> <ausgabe-ordner>
"""
import json, os, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from ampel_auswertung import kennzahlen, GEWICHT, neu_ampel  # noqa: E402
from ampel_rueckrechnung import lade  # noqa: E402
from am4_voreinstieg_test import voreinstieg, GEWICHT_VOR, TIEFS  # noqa: E402
from am9_panik_einstieg_test import panik_zustand, panik_signal, GEWICHT_PANIK  # noqa: E402


def main(roh, aus):
    df = pd.read_csv(os.path.join(aus, "ampel_taeglich.csv"), parse_dates=["date"], index_col="date")
    b = pd.read_csv(os.path.join(aus, "breite_taeglich.csv"), parse_dates=["date"], index_col="date")
    df = df.join(b, how="inner")
    spy = lade(roh, "SPY")
    ret = (spy.shift(-2) / spy.shift(-1) - 1).reindex(df.index)
    g = dict(GEWICHT, VOREINSTIEG=GEWICHT_VOR)

    k1 = ((df.P3_ANTEIL < 20) | (df.NHNL10 < -5)).astype(int).rolling(10, min_periods=1).max().astype(bool)
    k2 = df.NL <= 0.5 * df.NL.rolling(10, min_periods=1).max()
    k3 = df.P3_ANTEIL > df.P3_ANTEIL.shift(3)
    sig = k1 & k2 & k3
    akt = panik_zustand(df, spy, sig)

    basis = voreinstieg(df, neu_ampel(df, breite_col="breite200")).map(g)
    mit = basis.where(~akt, basis.clip(lower=GEWICHT_PANIK))
    am9 = panik_zustand(df, spy, panik_signal(df, spy, lade(roh, "VIX"), lade(roh, "VIX3M")))
    mit9 = basis.where(~am9, basis.clip(lower=GEWICHT_PANIK))
    V = {"AM1 + AM4 (neue Ampel)": basis, "B4 Breiten-Wende": mit, "zum Vergleich AM9 im selben Zeitraum": mit9}
    zeit = {"gesamt": slice(None, None), "2017-11 bis 2021-12": slice(None, "2021-12-31"),
            "2022-01 bis 2026-09": slice("2022-01-01", None)}
    E = {"regel": __doc__.split("REGEL")[1].split("Voraussetzung")[0].strip(),
         "varianten": {n: {z: kennzahlen(e.loc[zs], ret.loc[zs]) for z, zs in zeit.items()} for n, e in V.items()}}
    starts = sig[sig & ~sig.shift(fill_value=False)].index
    neu = [t for i, t in enumerate(starts) if i == 0 or not akt.shift(fill_value=False).loc[t]]
    s = spy.reindex(df.index)
    E["signale"] = [{"tag": str(t.date()), "p3_anteil": round(df.loc[t, "P3_ANTEIL"], 1),
                     "spy_20T_pct": None if pd.isna(df.loc[t, "spy_fwd20"]) else round(df.loc[t, "spy_fwd20"] * 100, 1),
                     "spy_60T_pct": None if pd.isna(df.loc[t, "spy_fwd60"]) else round(df.loc[t, "spy_fwd60"] * 100, 1),
                     "rueckschlag_20T_pct": None if pd.isna(df.loc[t, "spy_maxdd20"]) else round(df.loc[t, "spy_maxdd20"] * 100, 1)}
                    for t in neu]
    sd = pd.DataFrame(E["signale"])
    E["zusammenfassung"] = {"anzahl": int(len(sd)), "spy_20T_mittel_pct": round(sd.spy_20T_pct.mean(), 2),
                            "spy_20T_positiv_pct": round((sd.spy_20T_pct > 0).mean() * 100, 0),
                            "spy_60T_mittel_pct": round(sd.spy_60T_pct.mean(), 2),
                            "rueckschlag_ueber7pct_anteil": round((sd.rueckschlag_20T_pct <= -7).mean() * 100, 0),
                            "aktive_tage": int(akt.sum())}
    E["nach_tiefs"] = [{"tief": t, "signale_innerhalb_45_tage": [x["tag"] for x in E["signale"]
                        if abs((pd.Timestamp(x["tag"]) - pd.Timestamp(t)).days) <= 45],
                        "abstand_zum_tief_pct": [round((s[pd.Timestamp(x["tag"])] / s[pd.Timestamp(t)] - 1) * 100, 1)
                        for x in E["signale"] if abs((pd.Timestamp(x["tag"]) - pd.Timestamp(t)).days) <= 45]}
                       for t in TIEFS if pd.Timestamp(t) >= df.index.min()]
    json.dump(E, open(os.path.join(aus, "breite_wende_test.json"), "w"), ensure_ascii=False, indent=1)
    return E


if __name__ == "__main__":
    E = main(sys.argv[1], sys.argv[2])
    print(json.dumps({k: E[k] for k in ("varianten", "zusammenfassung", "nach_tiefs")}, ensure_ascii=False, indent=1))
    for x in E["signale"]:
        print(x)
