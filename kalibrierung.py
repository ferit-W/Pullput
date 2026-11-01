"""Kalibrierung der unbekannten Modelldetails NUR auf Haelfte 1 (Ziel: Basisvariante 12,3 % / 18,1 %)."""
import json
from multiprocessing import Pool
from engine import *
d = lade_daten()
def f(a):
    br, sk = a
    r = backtest(d, *H1, breite_ref=br, skew=sk)
    return dict(breite_ref=br, skew=sk, cagr=r['cagr'], dd=r['dd'], ntr=r['ntr'])
if __name__ == '__main__':
    grid = [(br, sk) for br in range(2500, 4600, 250) for sk in [-6, -5, -4, -3, -2, -1, 0]] + [(br, sk) for br in range(2600, 2950, 50) for sk in [-6, -5.5, -5, -4.5]]
    with Pool(4) as P:
        res = P.map(f, grid)
    for r in res: r['fehler'] = abs(r['cagr'] - 0.1232) / 0.01 + abs(r['dd'] - 0.1806) / 0.01
    res.sort(key=lambda r: r['fehler'])
    for r in res[:10]: print({k: round(v, 4) for k, v in r.items()})
    json.dump(res, open('ergebnisse/kalibrierung_h1.json', 'w'), indent=1)
