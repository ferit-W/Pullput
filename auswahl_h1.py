"""Runde 2: Anwendung der festgeschriebenen Auswahlregel (STAND.md, Schritt 3) – NUR Haelfte 1."""
import json, statistics, sys
from multiprocessing import Pool
from engine import *

ACHSEN = dict(tage=[14, 21, 28, 35, 45], delta=[0.6, 0.7, 0.8, 0.9], breite=[50, 100, 150, 200],
              max_pos=[2, 3, 4, 6], ema=[50, 100, 200], min_abstand=[1, 5], ema_kurz=[0, 20])
KEYS = list(ACHSEN)
DD_ZIEL, CAGR_MIN, DD_TEIL = 0.15, 0.125, 0.17
TEIL = [('2007-01-01', '2011-12-31'), ('2012-01-01', '2016-12-31')]
d = lade_daten()


def schluessel(r):
    return tuple(r[k] for k in KEYS)


def nachbarn(r, tab):
    out = []
    for k in KEYS:
        ws = ACHSEN[k]
        i = ws.index(r[k])
        for j in (i - 1, i + 1):
            if 0 <= j < len(ws):
                q = dict(r)
                q[k] = ws[j]
                if schluessel(q) in tab:
                    out.append(tab[schluessel(q)])
    return out


def struktur(r):
    return {k: r[k] for k in KEYS}


def einsatz_tunen(s):
    """Groesster Einsatz (0,05-%-Raster), bei dem H1-DD <= DD_ZIEL."""
    best = None
    f = 0.003
    while f <= 0.03:
        r = backtest(d, *H1, **s, einsatz=round(f, 4))
        if r['dd'] > DD_ZIEL:
            break
        best = (round(f, 4), r)
        f += 0.0005
    if best is None:
        return None
    f, r = best
    teile = [backtest(d, *t, **s, einsatz=f) for t in TEIL]
    return dict(struktur=s, einsatz=f, cagr=r['cagr'], dd=r['dd'], ntr=r['ntr'],
                teil_dd=[t['dd'] for t in teile], teil_cagr=[t['cagr'] for t in teile],
                ok=bool(r['cagr'] >= CAGR_MIN and all(t['dd'] < DD_TEIL for t in teile)))


if __name__ == '__main__':
    res = json.load(open('ergebnisse/runde1_h1.json'))
    tab = {schluessel(r): r for r in res}
    plateau = []
    for r in res:
        nb = nachbarn(r, tab)
        med = statistics.median(x['mar'] for x in nb)
        if med >= 0.85 * r['mar']:
            plateau.append(dict(r, nb_median=med))
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    a = sorted(plateau, key=lambda r: -r['mar'])[:n]
    b = sorted(plateau, key=lambda r: -(r['cagr'] - 0.04) / r['dd'])[:n]   # Ueberrendite-MAR (Korrektur Zins)
    top = list({schluessel(r): r for r in a + b}.values())
    print(f'{len(plateau)} von {len(res)} Strukturen bestehen Plateau-Pflicht; tune Top {len(top)}')
    with Pool(4) as P:
        kand = P.map(einsatz_tunen, [struktur(r) for r in top])
    kand = [k for k in kand if k]
    kand.sort(key=lambda k: (not k['ok'], -k['cagr']))
    json.dump(kand, open('ergebnisse/runde2_auswahl_h1.json', 'w'), indent=1)
    for k in kand[:15]:
        print(k['ok'], k['struktur'], k['einsatz'], round(k['cagr'], 4), round(k['dd'], 4),
              [round(x, 3) for x in k['teil_dd']], [round(x, 3) for x in k['teil_cagr']])
