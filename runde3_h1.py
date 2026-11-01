"""Runde 3: modellneutrale Hebel, Struktur 21 T / Delta 0,8 / 100 Pkt fest. NUR Haelfte 1."""
import json, itertools, statistics
from multiprocessing import Pool
import auswahl_h1 as A
from engine import *
A.ACHSEN = dict(max_pos=[2, 3, 4, 5, 6], ema=[50, 75, 100, 150, 200], min_abstand=[1, 2, 3, 5, 7],
                ema_kurz=[0, 10, 20, 50], max_risiko=[None, 0.03, 0.04])
A.KEYS = list(A.ACHSEN)
d = A.d
def f(p):
    r = backtest(d, *H1, **p, einsatz=0.033 / p['max_pos'])
    return dict(p, cagr=r['cagr'], dd=r['dd'], mar=r['cagr'] / r['dd'], xmar=(r['cagr'] - 0.04) / r['dd'])
if __name__ == '__main__':
    grid = [dict(zip(A.KEYS, v)) for v in itertools.product(*A.ACHSEN.values())]
    with Pool(4) as P:
        res = P.map(f, grid, chunksize=10)
    json.dump(res, open('ergebnisse/runde3_raster_h1.json', 'w'), indent=0)
    tab = {A.schluessel(r): r for r in res}
    plateau = [r for r in res if statistics.median(x['xmar'] for x in A.nachbarn(r, tab)) >= 0.85 * r['xmar']]
    a = sorted(plateau, key=lambda r: -r['mar'])[:30]
    b = sorted(plateau, key=lambda r: -r['xmar'])[:30]
    top = list({A.schluessel(r): r for r in a + b}.values())
    print(len(plateau), 'von', len(res), 'Plateau; tune', len(top))
    with Pool(4) as P:
        kand = [k for k in P.map(A.einsatz_tunen, [A.struktur(r) for r in top]) if k]
    kand.sort(key=lambda k: (not k['ok'], -k['cagr']))
    json.dump(kand, open('ergebnisse/runde3_auswahl_h1.json', 'w'), indent=1)
    for k in kand[:15]:
        print(k['ok'], k['struktur'], k['einsatz'], round(k['cagr'], 4), round(k['dd'], 4),
              [round(float(x), 3) for x in k['teil_dd']], [round(float(x), 3) for x in k['teil_cagr']])
