"""ATM-Variante mit festem Einstiegsrhythmus (Regeln: audit/VORAB_REGELN_ATM.md). Start: python3 audit/atm_lauf.py"""
import itertools
import sys
from multiprocessing import Pool
import pandas as pd

sys.path.insert(0, __file__.rsplit('/', 1)[0])
import engine2 as E2  # noqa: E402

AUS = __file__.rsplit('/', 1)[0] + '/ergebnisse'
D = E2.lade_daten()
ZR = {'H1': ('2007-01-01', '2016-12-31'), 'H2': ('2017-01-01', '2026-12-31'), 'Gesamt': ('2007-01-01', '2026-12-31')}
PRODUKT = {'SPX': dict(produkt='SPX', skala=1.0, raster=5.0, slip=0.25),
           'XSP': dict(produkt='XSP', skala=0.1, raster=1.0, slip=0.05)}
ZYK = {'W': 'woche', 'M': 'monat'}


def cfg(z, p, b, ganze=True, slipfaktor=1):
    c = dict(E2.STANDARD, **PRODUKT[p], zyklus=ZYK[z], strike_modus='atm', breite_fest=b, ganze=ganze)
    c['slip'] = PRODUKT[p]['slip'] * slipfaktor
    return c


def lauf(job):
    name, zr, c = job
    return name, zr, E2.backtest(D, **dict(c, start=ZR[zr][0], ende=ZR[zr][1]))


if __name__ == '__main__':
    jobs = []
    for z, p, b in itertools.product('WM', ('SPX', 'XSP'), (5, 10)):
        basis = f'{z}-{p}-{b}'
        for zr in ZR:
            jobs.append((f'{basis} ganze', zr, cfg(z, p, b)))
        for zr in ('H1', 'H2'):
            jobs.append((f'{basis} Bruchteile', zr, cfg(z, p, b, ganze=False)))
            jobs.append((f'{basis} ganze, Abschlag x2', zr, cfg(z, p, b, slipfaktor=2)))
            jobs.append((f'{basis} ganze, Abschlag x4', zr, cfg(z, p, b, slipfaktor=4)))
            jobs.append((f'{basis} ganze, ohne Cashzins', zr, dict(cfg(z, p, b), zins_cash=0.0)))
    with Pool(4) as P:
        res = P.map(lauf, jobs, chunksize=1)
    zeilen = []
    for name, zr, r in res:
        k = r['kennzahlen']
        tr = r['trades']
        kredit_anteil = sum(q['kredit'] / q['w'] for q in tr) / len(tr) if tr else None
        zeilen.append(dict(variante=name, zeitraum=zr, **k, kredit_je_breite=kredit_anteil,
                           n_median=float(pd.Series([q['n'] for q in tr]).median()) if tr else None))
        if name.endswith(' ganze'):
            slug = name.split()[0]
            pd.DataFrame(tr + [dict(q, offen_bei_ende=True) for q in r['offen']]).to_csv(f'{AUS}/atm_trades_{slug}_{zr}.csv', index=False)
            r['tage'].to_csv(f'{AUS}/atm_konto_taeglich_{slug}_{zr}.csv')
            E2.jahresergebnisse(r).rename('rendite').to_csv(f'{AUS}/atm_jahre_{slug}_{zr}.csv')
    df = pd.DataFrame(zeilen)
    df.to_csv(f'{AUS}/vergleich_atm.csv', index=False)
    pd.set_option('display.width', 250)
    pd.set_option('display.max_rows', 300)
    sp = ['variante', 'zeitraum', 'rendite_pa', 'max_drawdown_stress', 'trades', 'trefferquote', 'avg_gewinn', 'avg_verlust',
          'kosten_gesamt', 'zins_gesamt', 'tage_konto_zu_klein', 'kredit_je_breite', 'n_median', 'risiko_je_einstieg_median',
          'max_offenes_risiko_anteil']
    print(df[sp].round(4).to_string(index=False))
