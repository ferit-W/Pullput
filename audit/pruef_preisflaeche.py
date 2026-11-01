"""Pruefung der Modell-Preisflaeche auf statische Arbitrage (Monotonie, Steigung, Konvexitaet, Schranken)."""
import json, math, sys
import numpy as np
sys.path.insert(0, __file__.rsplit('/', 2)[0])
from engine import Modell

def pruefe(skew_code, vx_liste, t_liste, k_lo, k_hi, schritt=0.0025):
    mod = Modell(0.766, skew_code, 0.04)
    S = 1000.0
    out = []
    for vx in vx_liste:
        for td in t_liste:
            T = td / 365
            ks = S * np.arange(k_lo, k_hi + 1e-9, schritt)
            p = np.array([mod.put(S, k, T, vx) for k in ks])
            dk = np.diff(ks)
            stg = np.diff(p) / dk
            konv = p[:-2] - 2 * p[1:-1] + p[2:]
            df = math.exp(-0.04 * T)
            out.append(dict(vx=vx, tage=td,
                            monotonie_verletzt=int((stg < -1e-9).sum()),
                            steigung_ueber_df=int((stg > df + 1e-9).sum()),
                            konvex_verletzt=int((konv < -1e-7).sum()),
                            schranke_verletzt=int(((p < np.maximum(ks * df - S, 0) - 1e-7) | (p > ks * df + 1e-7)).sum()),
                            punkte=len(ks),
                            erste_konv_verletzung=(float(ks[1:-1][konv < -1e-7][0] / S) if (konv < -1e-7).any() else None)))
    return out

if __name__ == '__main__':
    erg = {}
    for name, sk in (('kalibriert (+5,5 im Doku-Sinn)', -5.5), ('flach (0)', 0.0), ('marktüblich (−3 im Doku-Sinn)', 3.0)):
        r = pruefe(sk, [10, 15, 20, 30, 40, 60, 71], [1, 7, 14, 21, 28], 0.90, 1.15)
        erg[name] = r
        tot = {k: sum(x[k] for x in r) for k in ('monotonie_verletzt', 'steigung_ueber_df', 'konvex_verletzt', 'schranke_verletzt', 'punkte')}
        print(name, tot)
        for x in r:
            if x['konvex_verletzt'] or x['steigung_ueber_df'] or x['monotonie_verletzt'] or x['schranke_verletzt']:
                print('   ', x)
    # Vega des typischen Spreads (K1/S 1,039, K2/S 1,003)
    mod = Modell(0.766, -5.5, 0.04); S = 1000.0
    vega = []
    for vx in (10, 15, 20, 30, 40):
        v = lambda x: mod.put(S, 1039, 21/365, x) - mod.put(S, 1003, 21/365, x)
        vega.append(dict(vx=vx, spreadwert=v(vx), aenderung_bei_plus_1_vx=v(vx + 1) - v(vx)))
    print('Spread-Vega (Wert Short-Spread, positiv = Verlust fuer Verkaeufer):', [(x['vx'], round(x['aenderung_bei_plus_1_vx'], 3)) for x in vega])
    erg['spread_vega'] = vega
    json.dump(erg, open(__file__.rsplit('/', 1)[0] + '/ergebnisse/preisflaeche.json', 'w'), indent=1, ensure_ascii=False)
