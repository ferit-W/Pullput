#!/usr/bin/env python3
"""Test AM9 "PANIK-EINSTIEG" — Regel VOR der Auswertung festgelegt (02.11.2026).

Lüddemann-Gedanke: Wenn die Panik am größten ist, ist die Wahrscheinlichkeit einer
Trendwende hoch. Einstieg klein, aber erst bei einem ersten Zeichen von Stabilisierung.

REGEL (unverändert lassen, sonst ist der Test wertlos):
  Signal am Tag t, wenn ALLE gelten:
    1. Panik-Score >= 55 an mindestens einem der letzten 5 Handelstage (inkl. t)
    2. Stabilisierung: VIX < VIX3M  ODER  VIX < eigener 5-Tage-Durchschnitt
    3. SPY-Schluss t > höchster Schluss der 3 Vortage
  Danach Zustand PANIK-EINSTIEG für 15 Handelstage (inkl. Signaltag) mit 33 %
  Investitionsgrad — als Untergrenze: ein höherer Grad aus der Ampel gilt weiter.
  Abbruch vorher, wenn SPY unter den tiefsten Schluss der 10 Tage vor dem Signal fällt.
  Geprüft auf Basis "Ampel heute" und "AM1 + AM4", getrennt 2007-2016 / 2017-2026.
  Freigabe nur bei Verbesserung in BEIDEN Zeiträumen.

Aufruf: python3 am9_panik_einstieg_test.py <rohdaten-ordner> <ausgabe-ordner>
"""
import json, os, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from ampel_auswertung import kennzahlen, GEWICHT, neu_ampel  # noqa: E402
from ampel_rueckrechnung import lade  # noqa: E402
from am4_voreinstieg_test import voreinstieg, GEWICHT_VOR, TIEFS  # noqa: E402

HALTEDAUER, GEWICHT_PANIK = 15, 1 / 3


def panik_signal(df, spy, vix, vix3m):
    s = spy.reindex(df.index)
    v = vix.reindex(df.index).ffill(); v3 = vix3m.reindex(df.index).ffill()
    b1 = (df.panik.fillna(0) >= 55).astype(int).rolling(5, min_periods=1).max().astype(bool)
    b2 = (v < v3) | (v < v.rolling(5).mean())
    b3 = s > s.shift(1).rolling(3).max()
    return b1 & b2 & b3


def panik_zustand(df, spy, signal):
    s = spy.reindex(df.index)
    tief10 = s.shift(1).rolling(10).min()
    aktiv = pd.Series(False, index=df.index)
    idx = list(df.index); i = 0
    while i < len(idx):
        if signal.iloc[i]:
            grenze = tief10.iloc[i]
            for j in range(i, min(i + HALTEDAUER, len(idx))):
                if j > i and s.iloc[j] < grenze:
                    break
                aktiv.iloc[j] = True
            i = j + 1 if j > i else i + 1
        else:
            i += 1
    return aktiv


def main(roh, aus):
    df = pd.read_csv(os.path.join(aus, "ampel_taeglich.csv"), parse_dates=["date"], index_col="date")
    spy = lade(roh, "SPY"); vix = lade(roh, "VIX"); v3 = lade(roh, "VIX3M")
    ret = (spy.shift(-2) / spy.shift(-1) - 1).reindex(df.index)
    g = dict(GEWICHT, VOREINSTIEG=GEWICHT_VOR)
    sig = panik_signal(df, spy, vix, v3)
    akt = panik_zustand(df, spy, sig)
    heute = df.ampel
    am14 = voreinstieg(df, neu_ampel(df, breite_col="breite200"))
    def mit_panik(basis):
        e = basis.map(g)
        return e.where(~akt, e.clip(lower=GEWICHT_PANIK))
    V = {"Ampel heute": heute.map(g), "Ampel heute + AM9": mit_panik(heute),
         "AM1 + AM4": am14.map(g), "AM1 + AM4 + AM9": mit_panik(am14)}
    zeit = {"gesamt": slice(None, None), "2007-2016": slice(None, "2016-12-31"), "2017-2026": slice("2017-01-01", None)}
    E = {"regel": __doc__.split("REGEL")[1].split("Aufruf")[0].strip(),
         "varianten": {n: {z: kennzahlen(e.loc[zs], ret.loc[zs]) for z, zs in zeit.items()} for n, e in V.items()}}
    starts = sig[sig & ~sig.shift(fill_value=False)].index
    # nur Signale, die einen neuen Zustand eröffnen (nicht innerhalb eines aktiven)
    neu = [t for t in starts if not akt.shift(fill_value=False).loc[t] or t == starts[0]]
    E["signale"] = [{"tag": str(t.date()), "ampel": heute.loc[t], "panik_max5": float(df.panik.rolling(5, min_periods=1).max().loc[t]),
                     "spy_20T_pct": round(df.loc[t, "spy_fwd20"] * 100, 1) if pd.notna(df.loc[t, "spy_fwd20"]) else None,
                     "spy_60T_pct": round(df.loc[t, "spy_fwd60"] * 100, 1) if pd.notna(df.loc[t, "spy_fwd60"]) else None,
                     "rueckschlag_20T_pct": round(df.loc[t, "spy_maxdd20"] * 100, 1) if pd.notna(df.loc[t, "spy_maxdd20"]) else None}
                    for t in neu]
    sd = pd.DataFrame(E["signale"])
    E["zusammenfassung_signale"] = {"anzahl": int(len(sd)),
                                    "spy_20T_mittel_pct": round(sd.spy_20T_pct.mean(), 2),
                                    "spy_20T_positiv_pct": round((sd.spy_20T_pct > 0).mean() * 100, 0),
                                    "spy_60T_mittel_pct": round(sd.spy_60T_pct.mean(), 2),
                                    "rueckschlag_20T_mittel_pct": round(sd.rueckschlag_20T_pct.mean(), 2),
                                    "rueckschlag_ueber7pct_anteil": round((sd.rueckschlag_20T_pct <= -7).mean() * 100, 0),
                                    "aktive_tage": int(akt.sum())}
    s = spy.reindex(df.index)
    E["nach_tiefs"] = []
    for t in TIEFS:
        nahe = [x for x in neu if abs((pd.Timestamp(x) - pd.Timestamp(t)).days) <= 45]
        E["nach_tiefs"].append({"tief": t, "signale_innerhalb_45_tage": [str(x.date()) for x in nahe],
                                "abstand_zum_tief_pct": [round((s[x] / s[t] - 1) * 100, 1) for x in nahe]})
    json.dump(E, open(os.path.join(aus, "am9_panik_einstieg.json"), "w"), ensure_ascii=False, indent=1)
    return E


if __name__ == "__main__":
    E = main(sys.argv[1], sys.argv[2])
    print(json.dumps({k: E[k] for k in ("varianten", "zusammenfassung_signale", "nach_tiefs")}, ensure_ascii=False, indent=1))
    for x in E["signale"]:
        print(x)
