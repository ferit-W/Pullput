"""Runde 1: Strukturraster NUR auf Haelfte 1. Gesamtrisiko konstant (einsatz = 3,3 % / max_pos)."""
import json, itertools, sys
from multiprocessing import Pool
from engine import *
d = lade_daten()
def f(p):
    r = backtest(d, *H1, **p)
    return dict(p, cagr=r['cagr'], dd=r['dd'], ntr=r['ntr'], mar=r['cagr'] / r['dd'])
if __name__ == '__main__':
    grid = []
    for tage, delta, breite, mp, ema, ab, ek in itertools.product(
            [14, 21, 28, 35, 45], [0.6, 0.7, 0.8, 0.9], [50, 100, 150, 200], [2, 3, 4, 6],
            [50, 100, 200], [1, 5], [0, 20]):
        grid.append(dict(tage=tage, delta=delta, breite=breite, max_pos=mp, ema=ema, min_abstand=ab,
                         ema_kurz=ek, einsatz=0.033 / mp))
    with Pool(4) as P:
        res = P.map(f, grid, chunksize=20)
    json.dump(res, open('ergebnisse/runde1_h1.json', 'w'), indent=0)
    res.sort(key=lambda r: -r['mar'])
    for r in res[:25]: print({k: round(v, 3) if isinstance(v, float) else v for k, v in r.items()})
