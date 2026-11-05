"""Sensitivität der ATM-Monatsstrategie (M-SPX-10, ganze Kontrakte, 2007-2026) gegen marktbeobachtete Preisparameter.
Vorab festgelegtes Kriterium 'marktkonsistent': mittlere modellierte Mid-Prämie / Breite zwischen 0,34 und 0,40
(beobachtet in den SPXW-Ketten 29.10.-05.11.2026: 0,367). Die Rendite geht nicht in das Kriterium ein; alle Kombinationen werden gezeigt.
Start: python3 -I audit/ketten_backtest.py"""
import itertools
import sys
from multiprocessing import Pool
import numpy as np
import pandas as pd
sys.path.insert(0, 'audit')
import atm_lauf as A  # noqa: E402

IVF = (0.717, 0.766, 1.0)      # 0,717 = beobachteter ATM-IV/VX1 an 2 Tagen; 0,766 = alter Faktor; 1,0 = ChatGPT-Referenz
SKEW = (0.0, -3.0, -6.0, -7.4, -9.0)   # -7,4 = beobachtete lokale Steigung (Form 1 + s*ln(K/S))
SLIP = (0.25, 0.66)            # 0,25 = bisherige Annahme; 0,66 = beobachtete Halbspanne (= natürlicher Preis)


def lauf(j):
    ivf, sk, slip = j
    c = dict(A.cfg('M', 'SPX', 10), ivf=ivf, skew=sk, slip=slip)
    r = A.E2.backtest(A.D, **dict(c, start='2007-01-01', ende='2026-12-31'))
    k = r['kennzahlen']
    tr = r['trades']
    return dict(ivf=ivf, skew=sk, slip=slip, rendite=k['rendite_pa'], dd=k['max_drawdown_stress'], treffer=k['trefferquote'],
                trades=k['trades'], mid_je_breite=float(np.mean([q['mid'] / q['w'] for q in tr])),
                gewinn_je_spread_pkt=float(np.mean([q['ergebnis'] / (q['n'] * 100) for q in tr])))


if __name__ == '__main__':
    with Pool(4) as P:
        df = pd.DataFrame(P.map(lauf, list(itertools.product(IVF, SKEW, SLIP)), chunksize=1))
    df['marktkonsistent'] = df.mid_je_breite.between(0.34, 0.40)
    df.to_csv('audit/ergebnisse/ketten_backtest_sensitivitaet.csv', index=False)
    pd.set_option('display.width', 200)
    out = df.copy()
    for c in ('rendite', 'dd', 'treffer'):
        out[c] = (out[c] * 100).round(1)
    out['mid_je_breite'] = out.mid_je_breite.round(3)
    out['gewinn_je_spread_pkt'] = out.gewinn_je_spread_pkt.round(2)
    print(out.to_string(index=False))
