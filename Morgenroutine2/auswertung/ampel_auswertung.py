#!/usr/bin/env python3
"""Auswertung der zurückgerechneten Ampel.

Liest ampel_taeglich.csv (aus ampel_rueckrechnung.py) und die SPY-Kurse,
schreibt auswertung.json und gibt eine lesbare Zusammenfassung aus.

Varianten wurden VOR der Auswertung festgelegt (siehe VARIANTEN) und werden
getrennt in zwei Zeiträumen geprüft (2007–2016 / 2017–2026). Eine Variante gilt
nur dann als Verbesserung, wenn sie in BEIDEN Hälften besser abschneidet.

Aufruf: python3 ampel_auswertung.py <rohdaten-ordner> <ausgabe-ordner>
"""
import json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from ampel_rueckrechnung import ampel, lade  # noqa: E402

GEWICHT = {"GO": 1.0, "CAUTION": 0.5, "REVERSE": 0.5, "STOP": 0.0}


def neu_ampel(df, *, breite_col="breite", vix_absolut=True, panik_aktiv=True, kredit=False):
    out = []
    for t, r in df.iterrows():
        vix = r.vix if vix_absolut else 0.0
        pan = r.panik if (panik_aktiv and not pd.isna(r.panik)) else None
        part = None if pd.isna(r[breite_col]) else int(r[breite_col])
        rsb = None if pd.isna(r.rsBeat) else int(r.rsBeat)
        term = r.term if isinstance(r.term, str) else None
        f, _ = ampel(int(r.p3), int(r.p6), int(r.n), vix, r.fg, part, int(r.breiteTot) or 11,
                     rsb, int(r.rsTot) or 11, pan, term)
        if not vix_absolut and term == "back-strong" and f in ("GO", "CAUTION"):
            f = "STOP"
        if kredit and not pd.isna(r.hy_chg63):
            if r.hy_chg63 > 1.0:
                f = "STOP" if f != "REVERSE" else f
            elif r.hy_chg63 > 0.5 and f == "GO":
                f = "CAUTION"
        out.append(f)
    return pd.Series(out, index=df.index)


def bestaetigt(s, tage=2):
    """Zustandswechsel erst, wenn der neue Zustand `tage` Tage in Folge gilt."""
    out, cur, kand, n = [], s.iloc[0], None, 0
    for v in s:
        if v == cur:
            kand, n = None, 0
        elif v == kand:
            n += 1
            if n >= tage:
                cur, kand, n = v, None, 0
        else:
            kand, n = v, 1
            if tage <= 1:
                cur, kand, n = v, None, 0
        out.append(cur)
    return pd.Series(out, index=s.index)


def kennzahlen(expo, ret):
    """expo: Anteil investiert je Signaltag t; ret: Rendite des Tages t+2 (Umsetzung zum Schluss t+1)."""
    r = (expo * ret).dropna()
    if not len(r):
        return {}
    eq = (1 + r).cumprod()
    jahre = len(r) / 252
    dd = (eq / eq.cummax() - 1).min()
    vol = r.std() * np.sqrt(252)
    return {"rendite_pa": round((eq.iloc[-1] ** (1 / jahre) - 1) * 100, 2),
            "max_drawdown": round(dd * 100, 1),
            "vola_pa": round(vol * 100, 1),
            "sharpe_ohne_zins": round((r.mean() * 252) / vol, 2) if vol > 0 else None,
            "investiert_anteil": round(expo.reindex(r.index).mean() * 100, 0),
            "wechsel_pro_jahr": round((expo.reindex(r.index).diff().abs() > 0).sum() / jahre, 1)}


def episoden(spy, df, schwelle=-0.10):
    """Rückgänge des SPY um mindestens 10 % vom Hoch: wann reagierte die Ampel?"""
    s = spy.reindex(df.index)
    res, i = [], 0
    hoch_wert, hoch_tag, in_dd = s.iloc[0], s.index[0], False
    tief_wert, tief_tag = None, None
    for t, v in s.items():
        if not in_dd:
            if v >= hoch_wert:
                hoch_wert, hoch_tag = v, t
            elif v / hoch_wert - 1 <= schwelle:
                in_dd, tief_wert, tief_tag = True, v, t
        else:
            if v < tief_wert:
                tief_wert, tief_tag = v, t
            if v >= hoch_wert:  # neues Hoch -> Episode beendet
                res.append((hoch_tag, tief_tag, t))
                in_dd, hoch_wert, hoch_tag = False, v, t
    if in_dd:
        res.append((hoch_tag, tief_tag, None))
    out = []
    for h, tf, ende in res:
        seg = df.loc[h:tf]
        stop = seg[seg.ampel == "STOP"]
        erst = stop.index[0] if len(stop) else None
        nach = df.loc[tf:ende] if ende is not None else df.loc[tf:]
        go = nach[nach.ampel == "GO"]
        go_tag = go.index[0] if len(go) else None
        out.append({
            "hoch": str(h.date()), "tief": str(tf.date()), "erholt": str(ende.date()) if ende is not None else None,
            "tiefe_pct": round((s[tf] / s[h] - 1) * 100, 1),
            "ampel_am_hoch": df.loc[h, "ampel"],
            "erster_STOP": str(erst.date()) if erst is not None else None,
            "handelstage_bis_STOP": int(len(df.loc[h:erst]) - 1) if erst is not None else None,
            "verlust_bis_STOP_pct": round((s[erst] / s[h] - 1) * 100, 1) if erst is not None else None,
            "anteil_rueckgang_bis_STOP_pct": round((s[erst] / s[h] - 1) / (s[tf] / s[h] - 1) * 100) if erst is not None else None,
            "erstes_GO_nach_tief": str(go_tag.date()) if go_tag is not None else None,
            "erholung_bis_GO_verpasst_pct": round((s[go_tag] / s[tf] - 1) * 100, 1) if go_tag is not None else None,
            "handelstage_tief_bis_GO": int(len(df.loc[tf:go_tag]) - 1) if go_tag is not None else None,
        })
    return out


def cluster_tage(maske, abstand=10):
    tage = maske[maske].index
    if not len(tage):
        return []
    gruppen, start, vor = [], tage[0], tage[0]
    pos = {t: i for i, t in enumerate(maske.index)}
    for t in tage[1:]:
        if pos[t] - pos[vor] > abstand:
            gruppen.append((start, vor)); start = t
        vor = t
    gruppen.append((start, vor))
    return gruppen


def main(roh, aus):
    df = pd.read_csv(os.path.join(aus, "ampel_taeglich.csv"), parse_dates=["date"], index_col="date")
    spy = lade(roh, "SPY")
    ret = (spy.shift(-2) / spy.shift(-1) - 1).reindex(df.index)
    E = {}

    # 1) Zustände, Dauer, Flackern
    zust = df.ampel
    laeufe = (zust != zust.shift()).cumsum()
    dauer = zust.groupby(laeufe).agg(["first", "size"])
    E["verteilung_pct"] = (zust.value_counts(normalize=True) * 100).round(1).to_dict()
    E["mittlere_dauer_handelstage"] = dauer.groupby("first")["size"].mean().round(1).to_dict()
    E["eintagesphasen_anteil_pct"] = round((dauer["size"] == 1).mean() * 100, 1)
    E["wechsel_pro_jahr"] = round((zust != zust.shift()).sum() / (len(zust) / 252), 1)

    # 2) Folgerenditen je Zustand
    fw = {}
    for z, g in df.groupby("ampel"):
        fw[z] = {"tage": int(len(g)),
                 "spy_5T_mittel_pct": round(g.spy_fwd5.mean() * 100, 2),
                 "spy_20T_mittel_pct": round(g.spy_fwd20.mean() * 100, 2),
                 "spy_20T_positiv_pct": round((g.spy_fwd20 > 0).mean() * 100, 0),
                 "spy_60T_mittel_pct": round(g.spy_fwd60.mean() * 100, 2),
                 "rueckschlag_20T_mittel_pct": round(g.spy_maxdd20.mean() * 100, 2),
                 "rueckschlag_20T_ueber5pct_anteil": round((g.spy_maxdd20 <= -0.05).mean() * 100, 0)}
    fw["ALLE"] = {"tage": int(len(df)), "spy_5T_mittel_pct": round(df.spy_fwd5.mean() * 100, 2),
                  "spy_20T_mittel_pct": round(df.spy_fwd20.mean() * 100, 2),
                  "spy_20T_positiv_pct": round((df.spy_fwd20 > 0).mean() * 100, 0),
                  "spy_60T_mittel_pct": round(df.spy_fwd60.mean() * 100, 2),
                  "rueckschlag_20T_mittel_pct": round(df.spy_maxdd20.mean() * 100, 2),
                  "rueckschlag_20T_ueber5pct_anteil": round((df.spy_maxdd20 <= -0.05).mean() * 100, 0)}
    E["folgerenditen"] = fw

    # 3) Auslöser einzeln
    trig = {}
    for z in ("STOP", "CAUTION"):
        g = df[df.ampel == z]
        for grund in sorted({x for v in g.gruende.dropna() for x in v.split("|")}):
            h = g[g.gruende.fillna("").str.split("|").apply(lambda l: grund in l)]
            trig[f"{z}:{grund}"] = {"tage": int(len(h)), "spy_20T_mittel_pct": round(h.spy_fwd20.mean() * 100, 2),
                                    "spy_20T_positiv_pct": round((h.spy_fwd20 > 0).mean() * 100, 0),
                                    "rueckschlag_20T_mittel_pct": round(h.spy_maxdd20.mean() * 100, 2)}
    E["ausloeser"] = trig

    # 4) Konsequenz-Zeile
    kz = {}
    for (r, g_), g in df.groupby(["richtung", "groesse"]):
        kz[f"{r} {g_}"] = {"tage": int(len(g)), "spy_20T_mittel_pct": round(g.spy_fwd20.mean() * 100, 2),
                           "spy_20T_positiv_pct": round((g.spy_fwd20 > 0).mean() * 100, 0)}
    E["konsequenz"] = kz

    # 5) Panik-Score-Stufen (Kontrarian?)
    pb = pd.cut(df.panik, [-1, 19, 37, 54, 71, 100], labels=["ruhig <20", "normal 20-37", "erhöht 38-54", "hoch 55-71", "extrem 72+"])
    E["panik_stufen"] = {str(k): {"tage": int(len(g)), "spy_20T_mittel_pct": round(g.spy_fwd20.mean() * 100, 2),
                                  "spy_60T_mittel_pct": round(g.spy_fwd60.mean() * 100, 2),
                                  "spy_20T_positiv_pct": round((g.spy_fwd20 > 0).mean() * 100, 0)}
                         for k, g in df.groupby(pb, observed=True)}

    # 6) Große Rückgänge
    E["einbrueche"] = episoden(spy, df)

    # 7) Lücken: GO vor Absturz, STOP vor Rallye (als Episoden zusammengefasst)
    fehl = cluster_tage((df.ampel == "GO") & (df.spy_maxdd20 <= -0.07))
    verp = cluster_tage((df.ampel == "STOP") & (df.spy_fwd20 >= 0.07))
    E["luecken"] = {
        "GO_vor_Ruecksetzer_7pct": [{"von": str(a.date()), "bis": str(b.date()),
                                     "max_ruecksetzer_pct": round(df.loc[a:b, "spy_maxdd20"].min() * 100, 1)} for a, b in fehl],
        "STOP_vor_Anstieg_7pct": [{"von": str(a.date()), "bis": str(b.date()),
                                   "max_anstieg_20T_pct": round(df.loc[a:b, "spy_fwd20"].max() * 100, 1)} for a, b in verp]}

    # 8) Varianten (vorab festgelegt)
    V = {
        "Kaufen und halten": pd.Series(1.0, index=df.index),
        "Ampel heute": df.ampel.map(GEWICHT),
        "Ampel, nur GO investiert": (df.ampel == "GO").astype(float),
        "V1 Ampel mit 2-Tage-Bestätigung": bestaetigt(df.ampel, 2).map(GEWICHT),
        "V2 Breite über EMA200 statt EMA50": neu_ampel(df, breite_col="breite200").map(GEWICHT),
        "V3 + Kreditspread-Signal": neu_ampel(df, kredit=True).map(GEWICHT),
        "V4 ohne Panik-Score als Auslöser": neu_ampel(df, panik_aktiv=False).map(GEWICHT),
        "V5 VIX-Termstruktur statt VIX-Niveau": neu_ampel(df, vix_absolut=False).map(GEWICHT),
        "V6 Kombi V1+V2+V3": bestaetigt(neu_ampel(df, breite_col="breite200", kredit=True), 2).map(GEWICHT),
        "Einfach: SPY über EMA200": df.spy_ueber_e200.astype(float),
    }
    zeit = {"gesamt 2007-07 bis 2026-09": slice(None, None),
            "Hälfte 1: 2007-07 bis 2016-12": slice(None, "2016-12-31"),
            "Hälfte 2: 2017-01 bis 2026-09": slice("2017-01-01", None)}
    E["varianten"] = {name: {zn: kennzahlen(ex.loc[zs], ret.loc[zs]) for zn, zs in zeit.items()} for name, ex in V.items()}

    # 9) Abgleich mit echten Snapshots
    E["abgleich_snapshots"] = {d: df.loc[d, ["ampel", "p3", "p6", "breite", "rsBeat", "vix"]].to_dict()
                               for d in ("2026-09-04", "2026-09-08") if d in df.index.strftime("%Y-%m-%d")}
    E["zeitraum"] = [str(df.index.min().date()), str(df.index.max().date())]
    json.dump(E, open(os.path.join(aus, "auswertung.json"), "w"), ensure_ascii=False, indent=1, default=str)
    return E


if __name__ == "__main__":
    E = main(sys.argv[1], sys.argv[2])
    print(json.dumps({k: E[k] for k in ("verteilung_pct", "mittlere_dauer_handelstage", "eintagesphasen_anteil_pct",
                                        "wechsel_pro_jahr", "folgerenditen")}, ensure_ascii=False, indent=1))
