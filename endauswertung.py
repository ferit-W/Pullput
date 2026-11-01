"""Einmalige Auswertung beider Haelften fuer Basis und festgeschriebene Variante (Kostenmodell)."""
import json
from engine import *
d = lade_daten()
V = {'Basis (max 3, EMA 100, 1,10 %)': dict(),
     'Neu (max 4, EMA 200, 0,85 %)': dict(max_pos=4, ema=200, einsatz=0.0085)}
out = []
for name, p in V.items():
    for h, (a, b) in (('H1 2007–2016', H1), ('H2 2017–2026', H2)):
        r = backtest(d, a, b, **p)
        out.append(dict(variante=name, haelfte=h, **{k: (float(v) if not isinstance(v, str) else v) for k, v in r.items()}))
        print(name, h, round(r['cagr'] * 100, 2), round(r['dd'] * 100, 2), round(r['ntr'], 1), r['dd_hoch'], r['dd_tief'])
json.dump(out, open('ergebnisse/endauswertung_neu.json', 'w'), indent=1, ensure_ascii=False)
