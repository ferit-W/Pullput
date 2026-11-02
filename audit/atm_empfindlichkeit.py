"""Modell-Empfindlichkeit der ATM-Varianten (ganze Kontrakte). Start: python3 audit/atm_empfindlichkeit.py"""
import itertools, sys
from multiprocessing import Pool
import pandas as pd
sys.path.insert(0, __file__.rsplit('/', 1)[0])
import atm_lauf as A
SZ = [('Referenz', {}), ('Vol-Faktor 0,85 statt 0,766', dict(ivf=0.85)), ('Vol-Faktor 1,0 (VX1 unskaliert)', dict(ivf=1.0)),
      ('Vol-Faktor 0,70', dict(ivf=0.70)), ('Skew 0', dict(skew=0.0)), ('Skew −3', dict(skew=-3.0)),
      ('Zins 0 % (Cash und Bepreisung)', dict(zins_cash=0.0, r_preis=0.0)), ('Dividende 2 %', dict(q_div=0.02))]
def lauf(j):
    name, sz, zr, c = j
    k = A.E2.backtest(A.D, **dict(c, start=A.ZR[zr][0], ende=A.ZR[zr][1]))['kennzahlen']
    return dict(variante=name, szenario=sz, zeitraum=zr, rendite_pa=k['rendite_pa'], max_drawdown_stress=k['max_drawdown_stress'], trades=k['trades'])
if __name__ == '__main__':
    jobs = [(f'{z}-{p}-{b}', sn, zr, dict(A.cfg(z, p, b), **sc)) for z, p, b in itertools.product('WM', ('SPX', 'XSP'), (5, 10))
            for sn, sc in SZ for zr in ('H1', 'H2')]
    with Pool(4) as P:
        df = pd.DataFrame(P.map(lauf, jobs, chunksize=2))
    df.to_csv(A.AUS + '/vergleich_atm_empfindlichkeit.csv', index=False)
    df['wert'] = (df.rendite_pa * 100).round(1).astype(str) + ' / ' + (df.max_drawdown_stress * 100).round(1).astype(str)
    pv = df.pivot_table(index=['variante', 'szenario'], columns='zeitraum', values='wert', aggfunc='first', sort=False)
    pd.set_option('display.width', 200); pd.set_option('display.max_rows', 200)
    print(pv.to_string())
