"""Runde 4: Bremse, VX-Deckel, EMA-Steigung. NUR Haelfte 1, Einsatz je Struktur getunt."""
import json, itertools, statistics
from multiprocessing import Pool
import auswahl_h1 as A
ACHSEN = dict(dd_bremse=[None, (0.05, 0.5), (0.05, 0.75), (0.08, 0.5), (0.08, 0.75), (0.10, 0.5), (0.10, 0.75)],
              vx_max=[None, 35, 30, 25], ema_steigung=[0, 20], max_pos=[3, 4, 5], ema=[150, 200])
KEYS = list(ACHSEN)
def key(s): return tuple(str(s[k]) for k in KEYS)
if __name__ == '__main__':
    grid = [dict(zip(KEYS, v)) for v in itertools.product(*ACHSEN.values())]
    with Pool(4) as P:
        kand = P.map(A.einsatz_tunen, grid, chunksize=4)
    tab = {key(k['struktur']): k for k in kand if k}
    for k in tab.values():
        nb = []
        for ax in KEYS:
            ws = ACHSEN[ax]; i = ws.index(k['struktur'][ax])
            for j in (i - 1, i + 1):
                if 0 <= j < len(ws):
                    q = dict(k['struktur']); q[ax] = ws[j]
                    if key(q) in tab: nb.append(tab[key(q)]['cagr'])
        k['nb_median'] = statistics.median(nb) if nb else 0
        k['plateau'] = bool(k['nb_median'] >= 0.9 * k['cagr'])
    out = sorted(tab.values(), key=lambda k: (not (k['ok'] and k['plateau']), -k['cagr']))
    json.dump(out, open('ergebnisse/runde4_h1.json', 'w'), indent=1, default=str)
    for k in out[:15]:
        print(k['ok'], k['plateau'], k['struktur'], k['einsatz'], round(k['cagr'], 4), round(k['dd'], 4),
              [round(float(x), 3) for x in k['teil_dd']], round(k['nb_median'], 4))
