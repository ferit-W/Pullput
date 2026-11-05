"""50 Einstiegsfilter auf M-SPX-10 (Regeln: audit/VORAB_REGELN_FILTER50.md). Start: python3 -I audit/filter50.py"""
import json
import sys
from multiprocessing import Pool
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, 'audit')
import atm_lauf as A  # noqa: E402

D = A.D
idx = D.index
C = D.close
VX = D.vx
ret = C.pct_change()
sh = lambda x: x.shift(1)            # nur Vortagesinformation


def ema(n):
    return C.ewm(span=n, adjust=False).mean()


rv20 = ret.rolling(20).std() * np.sqrt(252)
hi252 = C.rolling(252).max()
F = {}
# Trend und Momentum
F['T01 Schluss >= EMA 50'] = sh(C >= ema(50))
F['T02 Schluss >= EMA 100'] = sh(C >= ema(100))
F['T03 Schluss >= EMA 150'] = sh(C >= ema(150))
F['T04 EMA 50 >= EMA 200'] = sh(ema(50) >= ema(200))
F['T05 EMA 100 >= EMA 200'] = sh(ema(100) >= ema(200))
F['T06 EMA 200 steigt (20 T)'] = sh(ema(200) > ema(200).shift(20))
F['T07 EMA 200 steigt (60 T)'] = sh(ema(200) > ema(200).shift(60))
F['T08 12-Monats-Rendite > 0'] = sh(C / C.shift(252) - 1 > 0)
F['T09 6-Monats-Rendite > 0'] = sh(C / C.shift(126) - 1 > 0)
F['T10 3-Monats-Rendite > 0'] = sh(C / C.shift(63) - 1 > 0)
F['T11 1-Monats-Rendite > -3 %'] = sh(C / C.shift(21) - 1 > -0.03)
F['T12 1-Monats-Rendite > 0'] = sh(C / C.shift(21) - 1 > 0)
F['T13 Schluss >= SMA 50'] = sh(C >= C.rolling(50).mean())
F['T14 Schluss >= 97 % des 20-T-Hochs'] = sh(C >= 0.97 * C.rolling(20).max())
# Nähe zum Hoch
for nm, p in (('H01 <= 2 % unter 252-T-Hoch', 0.02), ('H02 <= 5 % unter 252-T-Hoch', 0.05),
              ('H03 <= 10 % unter 252-T-Hoch', 0.10), ('H04 <= 15 % unter 252-T-Hoch', 0.15)):
    F[nm] = sh(1 - C / hi252 <= p)
# Volatilität
for nm, th in (('V01 VX1 < 18', 18), ('V02 VX1 < 20', 20), ('V03 VX1 < 22', 22), ('V04 VX1 < 25', 25), ('V05 VX1 < 30', 30), ('V06 VX1 < 35', 35)):
    F[nm] = sh(VX < th)
for nm, th in (('V07 VX1 > 12', 12), ('V08 VX1 > 14', 14), ('V09 VX1 > 16', 16)):
    F[nm] = sh(VX > th)
F['V10 VX1 zwischen 15 und 25'] = sh((VX >= 15) & (VX <= 25))
F['V11 VX1 <= 20-T-Mittel'] = sh(VX <= VX.rolling(20).mean())
F['V12 VX1 >= 20-T-Mittel'] = sh(VX >= VX.rolling(20).mean())
F['V13 VX1 5-T-Aenderung < +15 %'] = sh(VX / VX.shift(5) - 1 < 0.15)
F['V14 VX1 5-T-Aenderung > -15 %'] = sh(VX / VX.shift(5) - 1 > -0.15)
F['V15 realisierte Vola < VX1'] = sh(rv20 < VX / 100)
F['V16 realisierte Vola < 15 %'] = sh(rv20 < 0.15)
F['V17 realisierte Vola < 20 %'] = sh(rv20 < 0.20)
# Kurzfristige Bewegung
F['P01 Vortagesrendite > -1 %'] = sh(ret > -0.01)
F['P02 Vortagesrendite > 0'] = sh(ret > 0)
F['P03 5-T-Rendite > -2 %'] = sh(C / C.shift(5) - 1 > -0.02)
F['P04 5-T-Rendite > 0'] = sh(C / C.shift(5) - 1 > 0)
F['P05 Schluss ueber 20-T-Tief'] = sh(C > C.rolling(20).min())
# Kalender (Tag selbst)
wd, mo = pd.Series(idx.weekday, index=idx), pd.Series(idx.month, index=idx)
F['K01 nur Montag'] = wd == 0
F['K02 nur Dienstag'] = wd == 1
F['K03 nur Mittwoch'] = wd == 2
F['K04 nur Donnerstag'] = wd == 3
F['K05 nur Mo+Di'] = wd.isin([0, 1])
F['K06 nur Mi+Do'] = wd.isin([2, 3])
F['K07 nicht September/Oktober'] = ~mo.isin([9, 10])
F['K08 nur November bis April'] = mo.isin([11, 12, 1, 2, 3, 4])
F['K09 nicht Juni bis August'] = ~mo.isin([6, 7, 8])
F['K10 nicht Januar'] = mo != 1
assert len(F) == 50, len(F)
F = {k: v.reindex(idx).fillna(False).astype(bool).values for k, v in F.items()}

MODELLE = {'A': dict(ivf=0.766, skew=-6.0), 'B': dict(ivf=1.0, skew=0.0)}
VOLL = ('2007-01-01', '2026-12-31')


def lauf(j):
    mod, name = j
    c = dict(A.cfg('M', 'SPX', 10), **MODELLE[mod])
    if name is not None:
        c['extra_filter'] = F[name]
    r = A.E2.backtest(D, **dict(c, start=VOLL[0], ende=VOLL[1]))
    k = r['kennzahlen']
    tr = pd.DataFrame(r['trades'])
    tr['pkt'] = tr.ergebnis / (tr.n * 100)
    tr['ein'] = pd.to_datetime(tr.ein_datum)
    return mod, name, dict(rendite=k['rendite_pa'], dd=k['max_drawdown_stress'], trades=int(k['trades']), treffer=k['trefferquote'],
                           edge=float(tr.pkt.mean())), (tr[['ein_datum', 'verfall', 'pkt']] if name is None else None)


def cluster_test(df, mask):
    """Welch-t auf Verfallstermin-Mittelwerten: zugelassene gegen gestrichene Trades."""
    a = df[mask].groupby('verfall').pkt.mean()
    b = df[~mask].groupby('verfall').pkt.mean()
    if len(a) < 5 or len(b) < 5:
        return np.nan, np.nan, float(a.mean()) if len(a) else np.nan, float(b.mean()) if len(b) else np.nan
    t, p = stats.ttest_ind(a, b, equal_var=False)
    return float(t), float(p), float(a.mean()), float(b.mean())


if __name__ == '__main__':
    jobs = [(m, None) for m in MODELLE] + [(m, n) for m in MODELLE for n in F]
    with Pool(4) as P:
        res = P.map(lauf, jobs, chunksize=1)
    basis = {m: (kz, tr) for m, n, kz, tr in res if n is None}
    zeilen = []
    for m in MODELLE:
        kz0, tr0 = basis[m]
        tr0 = tr0.copy()
        tr0['ein'] = pd.to_datetime(tr0.ein_datum)
        for mm, n, kz, _ in res:
            if mm != m or n is None:
                continue
            f = pd.Series(F[n], index=idx)
            erlaubt = f.reindex(tr0.ein).values
            t, p, ea, eb = cluster_test(tr0, erlaubt)
            h1 = (tr0.ein < '2017-01-01').values
            _, _, a1, b1 = cluster_test(tr0[h1], erlaubt[h1])
            _, _, a2, b2 = cluster_test(tr0[~h1], erlaubt[~h1])
            zeilen.append(dict(modell=m, filtername=n, trades_gefiltert=kz['trades'], anteil_trades=erlaubt.mean(), rendite=kz['rendite'], dd=kz['dd'],
                               edge_filter_backtest=kz['edge'], edge_basis=kz0['edge'], edge_zugelassen=ea, edge_gestrichen=eb,
                               diff=ea - eb, t=t, p=p, diff_2007_16=a1 - b1, diff_2017_26=a2 - b2))
    df = pd.DataFrame(zeilen)
    # Holm-Korrektur je Modell
    df['p_holm'] = np.nan
    for m in MODELLE:
        s = df[df.modell == m].sort_values('p')
        n = s.p.notna().sum()
        run = 0.0
        for rank, (i, row) in enumerate(s.iterrows()):
            if np.isnan(row.p):
                continue
            run = max(run, min(1.0, (n - rank) * row.p))
            df.loc[i, 'p_holm'] = run
    df['signifikant_holm'] = df.p_holm < 0.05
    df['gleiches_vorzeichen_halben'] = (np.sign(df.diff_2007_16) == np.sign(df.diff_2017_26)) & (df['diff'] > 0)
    df['genug_trades'] = df.anteil_trades >= 0.30
    piv = df.pivot(index='filtername', columns='modell', values=['signifikant_holm', 'gleiches_vorzeichen_halben', 'genug_trades'])
    best = (piv['signifikant_holm'].all(axis=1) & piv['gleiches_vorzeichen_halben'].all(axis=1) & piv['genug_trades'].all(axis=1))
    df['bestanden'] = df.filtername.map(best)
    df.to_csv('audit/ergebnisse/filter50.csv', index=False)
    zus = {'basis': {m: dict(rendite=basis[m][0]['rendite'], dd=basis[m][0]['dd'], trades=basis[m][0]['trades'], edge=basis[m][0]['edge']) for m in MODELLE},
           'rohe_p_unter_5_prozent': {m: int((df[df.modell == m].p < 0.05).sum()) for m in MODELLE},
           'holm_signifikant': {m: int(df[df.modell == m].signifikant_holm.sum()) for m in MODELLE},
           'bestanden': sorted(best[best].index.tolist())}
    json.dump(zus, open('audit/ergebnisse/filter50_zusammenfassung.json', 'w'), indent=1, ensure_ascii=False)
    pd.set_option('display.width', 250)
    pd.set_option('display.max_rows', 200)
    print(json.dumps(zus, indent=1, ensure_ascii=False))
    for m in MODELLE:
        s = df[df.modell == m].sort_values('p')[['filtername', 'anteil_trades', 'rendite', 'dd', 'edge_filter_backtest', 'diff', 't', 'p', 'p_holm',
                                                  'diff_2007_16', 'diff_2017_26']]
        print(f'\n== Modell {m}: Basis Rendite {basis[m][0]["rendite"]:.4f}, Edge {basis[m][0]["edge"]:.3f} Pkt/Spread; sortiert nach p ==')
        print(s.round(3).head(14).to_string(index=False))
