"""Vollständige Audit-Auswertung. Start: python3 audit/lauf.py (im Repo-Hauptordner). Schreibt nach audit/ergebnisse/."""
import json
import sys
from multiprocessing import Pool
import pandas as pd

sys.path.insert(0, __file__.rsplit('/', 2)[0])
sys.path.insert(0, __file__.rsplit('/', 1)[0])
import engine as E1  # noqa: E402
import engine2 as E2  # noqa: E402

AUS = __file__.rsplit('/', 1)[0] + '/ergebnisse'
DATEN = {'alt': E2.lade_daten('alt'), 'neu': E2.lade_daten('korrigiert')}
ZEITRAUM = {'H1': ('2007-01-01', '2016-12-31'), 'H2': ('2017-01-01', '2026-12-31'), 'Gesamt': ('2007-01-01', '2026-12-31')}

KORR = dict(t_legacy=False, stress='drei', zins_basis='equity', raster=5.0)          # korrigiertes Modell
XSP = dict(produkt='XSP', skala=0.1, raster=1.0, slip=0.05)                           # XSP-Szenario

VARIANTEN = [
    # Stufe A: Modellkorrekturen, synthetische Verfälle, Strategie unverändert (kumulativ)
    ('A1 Original-Logik, Datenende-Fehler behoben', 'A', dict(E2.LEGACY)),
    ('A2 + Laufzeit = tatsächliche Restlaufzeit', 'A', dict(E2.LEGACY, t_legacy=False)),
    ('A3 + Stress: 3 Kombinationen inkl. Verfallstag', 'A', dict(E2.LEGACY, t_legacy=False, stress='drei')),
    ('A4 + Cashzins nur auf Kontowert', 'A', dict(E2.LEGACY, t_legacy=False, stress='drei', zins_basis='equity')),
    ('A5 + 5-Punkte-Strikeraster', 'A', dict(E2.STANDARD, **KORR, verfaelle='synthetisch')),
    ('A6 + VX1-Datumszuordnung korrigiert (korrigiertes Modell, synthetisch)', 'A', dict(E2.STANDARD, **KORR, verfaelle='synthetisch')),
    # Stufe B: historisch handelbare Verfälle
    ('B1 V-W: Weeklys ab Einführung (Listing-Annahme 28 T)', 'B', dict(E2.STANDARD, **KORR, verfaelle='weekly_annahme')),
    ('B2 V-M: nur Monatsverfälle (AM)', 'B', dict(E2.STANDARD, **KORR, verfaelle='monatlich')),
    # Stufe C: ganze Kontrakte, 100.000 USD
    ('C1 SPX ganze Kontrakte, V-W', 'C', dict(E2.STANDARD, **KORR, verfaelle='weekly_annahme', ganze=True)),
    ('C2 SPX ganze Kontrakte, V-M', 'C', dict(E2.STANDARD, **KORR, verfaelle='monatlich', ganze=True)),
    ('C3 XSP ganze Kontrakte, V-W (XSP-Verfälle = SPX unterstellt)', 'C', dict(E2.STANDARD, **{**KORR, **XSP}, verfaelle='weekly_annahme', ganze=True)),
    ('C4 XSP ganze Kontrakte, V-M (XSP-Verfälle = SPX unterstellt)', 'C', dict(E2.STANDARD, **{**KORR, **XSP}, verfaelle='monatlich', ganze=True)),
]
SZEN = [  # Stufe D: Empfindlichkeiten auf B1 und B2 (Szenarioannahmen, Handelsregeln unverändert)
    ('ohne Cashzins (reines Optionsergebnis)', dict(zins_cash=0.0)),
    ('Zins 0 % (Cash und Bepreisung)', dict(zins_cash=0.0, r_preis=0.0)),
    ('Zins 2 % (Cash und Bepreisung)', dict(zins_cash=0.02, r_preis=0.02)),
    ('Dividende 2 % p. a.', dict(q_div=0.02)),
    ('Abschlag 0,5 Pkt', dict(slip=0.5)),
    ('Abschlag 1,0 Pkt', dict(slip=1.0)),
    ('Abschlag 1,5 Pkt', dict(slip=1.5)),
    ('Gebühren verdoppelt (3,60 je Kontrakt und Seite)', dict(fee_kontrakt_seite=3.60)),
    ('Gebühr auch bei Abrechnung (1,80 je Spread)', dict(fee_abrechnung=1.80)),
    ('VX1 vom Vortag für Einstieg', dict(vx_lag=1)),
    ('Skew 0 (flach)', dict(skew=0.0)),
    ('Skew −3 (marktübliche Richtung)', dict(skew=-3.0)),
    ('Cashzins inkl. Prämien', dict(zins_basis='cash')),
]


def lauf(job):
    name, stufe, zr, cfg = job
    a, b = ZEITRAUM[zr]
    daten = 'alt' if name[:2] in ('A1', 'A2', 'A3', 'A4', 'A5') else 'neu'
    r = E2.backtest(DATEN[daten], **dict(cfg, start=a, ende=b))
    return name, stufe, zr, r


def betroffene_trades():
    """Wie viele Trades der Original-Simulation hatten einen damals nicht verfügbaren Verfall?"""
    D = DATEN['alt']
    kal = E2.Kalender(D.index)
    out = {}
    for zr in ('H1', 'H2'):
        a, b = ZEITRAUM[zr]
        r = E2.backtest(D, **dict(E2.LEGACY, start=a, ende=b))
        alle = r['trades'] + r['offen']
        n = len(alle)
        nicht_w = nicht_m = am_falsch = 0
        wochentag = {}
        for q in alle:
            v, t = q['verfall'], q['ein_datum']
            kw = dict(kal.kandidaten(t, 'weekly_annahme', 0, 40))
            km = dict(kal.kandidaten(t, 'monatlich', 0, 40))
            if v not in kw:
                nicht_w += 1
                wochentag[v.day_name()] = wochentag.get(v.day_name(), 0) + 1
            if v not in km:
                nicht_m += 1
            if km.get(v) == 'AM':
                am_falsch += 1
        out[zr] = dict(trades=n, nicht_verfuegbar_VW=nicht_w, anteil_VW=nicht_w / n, nicht_verfuegbar_VM=nicht_m,
                       anteil_VM=nicht_m / n, als_PM_gerechnet_aber_AM=am_falsch, nicht_verfuegbar_nach_wochentag_VW=wochentag)
    return out


if __name__ == '__main__':
    jobs = [(n, s, zr, c) for n, s, c in VARIANTEN for zr in ZEITRAUM]
    for basis_name, basis in (('B1', VARIANTEN[6][2]), ('B2', VARIANTEN[7][2])):
        for sn, sc in SZEN:
            jobs += [(f'D {basis_name} · {sn}', 'D', zr, dict(basis, **sc)) for zr in ('H1', 'H2')]
    with Pool(4) as P:
        res = P.map(lauf, jobs, chunksize=1)
    zeilen = []
    # A0 = alte Engine wie dokumentiert
    for zr in ('H1', 'H2'):
        a = E1.backtest(E1.lade_daten(), *ZEITRAUM[zr], max_pos=4, ema=200, einsatz=0.0085)
        zeilen.append(dict(variante='A0 Ausgangsstand (engine.py, unverändert)', stufe='A', zeitraum=zr,
                           rendite_pa=a['cagr'], max_drawdown_stress=a['dd'], max_drawdown_schluss=a['dd_schluss'],
                           trades_pa=a['ntr'], trefferquote=a['trefferquote']))
    for name, stufe, zr, r in res:
        zeilen.append(dict(variante=name, stufe=stufe, zeitraum=zr, **r['kennzahlen']))
        if stufe in 'ABC':
            slug = name.split()[0] + '_' + zr
            tr = pd.DataFrame(r['trades'] + [dict(q, offen_bei_ende=True) for q in r['offen']])
            tr.to_csv(f'{AUS}/trades_{slug}.csv', index=False)
            r['tage'].to_csv(f'{AUS}/konto_taeglich_{slug}.csv')
            E2.jahresergebnisse(r).rename('rendite').to_csv(f'{AUS}/jahre_{slug}.csv')
    json.dump({'hinweis': 'Vollständige Konfiguration je Variante; Stufe D = Basis B1/B2 plus angegebene Abweichung',
               'standard_engine2': E2.STANDARD, 'legacy': E2.LEGACY,
               'varianten': {n: c for n, _, c in VARIANTEN}, 'szenarien_stufe_D': {n: c for n, c in SZEN}},
              open(__file__.rsplit('/', 1)[0] + '/konfiguration.json', 'w'), indent=1, ensure_ascii=False)
    df = pd.DataFrame(zeilen)
    df.to_csv(f'{AUS}/vergleich.csv', index=False)
    bt = betroffene_trades()
    json.dump(bt, open(f'{AUS}/betroffene_trades.json', 'w'), indent=1, ensure_ascii=False)
    pd.set_option('display.width', 250)
    pd.set_option('display.max_rows', 200)
    pd.set_option('display.max_colwidth', 70)
    sp = ['variante', 'zeitraum', 'rendite_pa', 'max_drawdown_stress', 'max_drawdown_schluss', 'trades_pa',
          'trefferquote', 'tage_konto_zu_klein', 'tage_kein_verfall', 'max_offenes_risiko_anteil']
    print(df[sp].round(4).to_string(index=False))
    print(json.dumps(bt, indent=1, ensure_ascii=False))
