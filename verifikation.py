"""Unabhaengige Pruefung der Engine und der festgeschriebenen Variante. Keine Auswahl, nur Kontrolle."""
import json, math, sys
import numpy as np
import pandas as pd
from multiprocessing import Pool
from engine import *

d = lade_daten()
NEU = dict(max_pos=4, ema=200, einsatz=0.0085)
ergebnis = {}
fehler = []


def check(name, ok, info=''):
    print(('OK   ' if ok else 'FEHL ') + name + (f'  [{info}]' if info else ''))
    ergebnis[name] = dict(ok=bool(ok), info=str(info))
    if not ok:
        fehler.append(name)


# ---------- A. Formeln ----------
mod = Modell(0.766, -5.5, 0.04)
rng = np.random.default_rng(1)
z = rng.standard_normal(2_000_000)
max_abw = 0.0
for S, K, T, vx in [(2000, 2050, 21 / 365, 18), (4000, 3900, 21 / 365, 30), (1300, 1330, 21 / 365, 45)]:
    sg = mod.sigma(S, K, vx)
    ST = S * np.exp((0.04 - 0.5 * sg * sg) * T + sg * math.sqrt(T) * z)
    mc = math.exp(-0.04 * T) * np.maximum(K - ST, 0).mean()
    max_abw = max(max_abw, abs(mc - mod.put(S, K, T, vx)) / max(mc, 1e-9))
check('A1 Put-Preis = Monte-Carlo (2 Mio. Pfade)', max_abw < 0.005, f'max. rel. Abw. {max_abw:.4%}')

S, T, vx = 3000.0, 21 / 365, 20.0
K = mod.strike_fuer_delta(S, T, vx, 0.8)
dl = mod.put_delta(S, K, T, vx)
sg = mod.sigma(S, K, vx)
def bs_put_festes_sigma(S_):
    d1 = (math.log(S_ / K) + (0.04 + 0.5 * sg * sg) * T) / (sg * math.sqrt(T))
    return K * math.exp(-0.04 * T) * ncdf(-(d1 - sg * math.sqrt(T))) - S_ * ncdf(-d1)
fd = (bs_put_festes_sigma(S + 0.01) - bs_put_festes_sigma(S - 0.01)) / 0.02
check('A2 Strike für Delta 0,8 liefert |Delta| = 0,8', abs(dl + 0.8) < 1e-6, f'Delta {dl:.6f}, K/S {K / S:.4f}')
check('A3 Delta-Formel = numerische Ableitung', abs(fd - dl) < 1e-4, f'{fd:.6f} vs {dl:.6f}')

verletz = 0
for S_ in np.linspace(1000, 8000, 40):
    for vx_ in (10, 20, 40, 80):
        for T_ in (1 / 365, 7 / 365, 21 / 365):
            K1 = mod.strike_fuer_delta(S_, T_, vx_, 0.8); w = 100 * S_ / 2750
            v = mod.put(S_, K1, T_, vx_) - mod.put(S_, K1 - w, T_, vx_)
            if not (-1e-9 <= v <= w + 1e-9):
                verletz += 1
check('A4 Spreadwert immer zwischen 0 und Breite', verletz == 0, f'{verletz} Verletzungen von 480')

# ---------- B. Daten ----------
s_raw = pd.read_csv(f'{ROOT}/daten/SPX_1D.csv')
v_raw = pd.read_csv(f'{ROOT}/daten/VX1_1D.csv')
sub = d.loc['2007':]
ffill = int(sub.index.isin(
    (pd.to_datetime(v_raw.time, unit='s') + pd.Timedelta(hours=3)).dt.normalize()).__invert__().sum())
check('B1 Keine doppelten Handelstage', d.index.is_unique)
check('B2 VX1-Lücken ab 2007 (vorwärts gefüllt) < 1 %', ffill / len(sub) < 0.01, f'{ffill} von {len(sub)} Tagen')
check('B3 Keine fehlenden Kurse ab 2007', not sub[['close', 'low', 'vx', 'vx_high']].isna().any().any())
check('B4 low <= close <= high, vx_high >= vx', bool(((sub.low <= sub.close + 1e-9) & (sub.vx_high >= sub.vx - 1e-9)).all()))
r_spx = sub.close.pct_change()
korr = {k: float(r_spx.corr(sub.vx.diff().shift(k))) for k in (-1, 0, 1)}
check('B5 Datumszuordnung VX1: stärkste Gegenbewegung am selben Tag', korr[0] < min(korr[-1], korr[1]) and korr[0] < -0.5,
      ', '.join(f'Versatz {k}: {v:.2f}' for k, v in korr.items()))
r2020 = d.loc['2020-03-16']
check('B6 Stichprobe 16.03.2020 (SPX −12 %, VX1 stark erhöht)', r2020.close < 2450 and r2020.vx > 40,
      f'SPX {r2020.close:.0f}, VX1 {r2020.vx:.1f}')

# ---------- C. Unabhaengiger Nachrechner (Trade-Protokoll) ----------
def nachrechnen(h):
    r = backtest(d, *h, **NEU)
    idx = d.index
    i0, i1, P = r['i0'], r['i1'], r['params']
    alle = r['trades'] + r['offen']
    fluss = {}
    for q in alle:
        fluss[q['ein_idx']] = fluss.get(q['ein_idx'], 0) + q['n'] * (q['kredit'] * 100 - P['fee'])
    for q in r['trades']:
        fluss[q['exp_idx']] = fluss.get(q['exp_idx'], 0) - q['zahlung']
    cash = 100000.0
    for i in range(i0, i1):
        if i > i0:
            cash *= (1 + P['zins']) ** ((idx[i] - idx[i - 1]).days / 365)
        cash += fluss.get(i, 0)
    S, VX = d.close.iloc[i1 - 1], d.vx.iloc[i1 - 1]
    letzter = idx[i1 - 1].to_datetime64().astype('datetime64[D]')
    offen_wert = sum(q['n'] * 100 * (mod.put(S, q['K1'], (q['exp_datum'] - letzter).astype(int) / 365, VX)
                                     - mod.put(S, q['K2'], (q['exp_datum'] - letzter).astype(int) / 365, VX))
                     for q in r['offen'])
    eq_nach = cash - offen_wert
    # Einzelpruefungen je Trade
    C = d.close.values
    probleme = 0
    kurve = np.array(r['kurve'])
    for q in alle:
        i = q['ein_idx']
        ok = abs(q['K1'] - q['K2'] - q['w']) < 1e-6 and q['K1'] > q['S_ein']
        ok &= (q['exp_datum'] - idx[i].to_datetime64().astype('datetime64[D]')).astype(int) == 21
        ok &= q['exp_idx'] > i and idx[q['exp_idx']] <= pd.Timestamp(q['exp_datum'])
        ok &= C[i - 1] >= d.close.ewm(span=200, adjust=False).mean().values[i - 1]
        if 'zahlung' in q:
            ok &= abs(q['S_end'] - C[q['exp_idx']]) < 1e-9
            ok &= -1e-6 <= q['zahlung'] <= q['n'] * q['w'] * 100 + 1e-6
        probleme += not ok
    # Einsatz: max. Verlust inkl. Gebuehr = Einsatz * Konto vor Einstieg (Equity vor Einstieg = Kurve ohne neuen Trade)
    einsatz_ist = []
    for q in alle:
        einsatz_ist.append(q['n'] * (q['maxl'] * 100 + P['fee']))
    max_pos_ist = max(sum(1 for q in alle if q['ein_idx'] <= i < q['exp_idx'])
                      for i in range(i0, i1))
    return dict(eq_engine=r['kurve'][-1], eq_nach=eq_nach, probleme=probleme, n=len(alle), max_pos=max_pos_ist,
                dd=r['dd'], dd_schluss=r['dd_schluss'], cagr=r['cagr'],
                einsatz_rel=float(np.median([e / r['kurve'][q['ein_idx'] - i0] for e, q in zip(einsatz_ist, alle)])))

for name, h in (('H1', H1), ('H2', H2)):
    x = nachrechnen(h)
    check(f'C1 {name}: Endkapital Engine = Nachrechner', abs(x['eq_engine'] / x['eq_nach'] - 1) < 1e-9,
          f"{x['eq_engine']:.2f} vs {x['eq_nach']:.2f}")
    check(f'C2 {name}: alle Trades regelkonform (Strikes, 21 T, Filter, Settlement)', x['probleme'] == 0,
          f"{x['probleme']} Abweichungen bei {x['n']} Trades")
    check(f'C3 {name}: nie mehr als 4 Positionen offen', x['max_pos'] <= 4, f"max. {x['max_pos']}")
    check(f'C4 {name}: Einsatz je Trade ≈ 0,85 % des Kontos', abs(x['einsatz_rel'] - 0.0085) < 0.0005,
          f"Median {x['einsatz_rel']:.4%}")
    ergebnis[f'kennzahlen_{name}'] = {k: x[k] for k in ('cagr', 'dd', 'dd_schluss')}

# ---------- D. Kein Blick in die Zukunft ----------
schnitt = d.index.searchsorted(pd.Timestamp('2022-06-01'))
d2 = d.copy()
d2.iloc[schnitt:, :] = d2.iloc[schnitt:, :].values * rng.uniform(0.7, 1.3, size=d2.iloc[schnitt:].shape)
r_a = backtest(d, *H2, **NEU)
r_b = backtest(d2, *H2, **NEU)
k = schnitt - r_a['i0']
gleich = np.allclose(r_a['kurve'][:k], r_b['kurve'][:k], rtol=0, atol=1e-6)
check('D1 Zukunftsdaten verändert -> Equity bis zum Schnitttag identisch', gleich, 'Schnitt 01.06.2022')

r_c = backtest(d, *H2, **NEU)
check('D2 Wiederholter Lauf identisch (deterministisch)', r_c['kurve'] == r_a['kurve'])

# ---------- E. Empfindlichkeiten der festen Variante (keine Auswahl) ----------
def lauf(a):
    name, h, extra = a
    r = backtest(d, *h, **{**NEU, **extra})
    return name, h[0][:4], r['cagr'], r['dd'], r['dd_schluss']
jobs = []
for h in (H1, H2):
    for name, extra in [('Kostenmodell (Referenz)', {}),
                        ('Zins nur auf Kontowert', dict(zins_basis='equity')),
                        ('Abschlag 0,75 Pkt', dict(slip=0.75)),
                        ('Abschlag 1,5 Pkt (Demo-Fill)', dict(slip=1.5)),
                        ('XSP (0,5 Pkt + 36 USD je SPX-Äquiv.)', dict(slip=0.5, fee=36.0)),
                        ('Kalibrierung Nr. 2 (2.800 / −5,5)', dict(breite_ref=2800.0)),
                        ('Kalibrierung Nr. 3 (2.650 / −6,0)', dict(breite_ref=2650.0, skew=-6.0)),
                        ('Kalibrierung Nr. 4 (2.700 / −6,0)', dict(breite_ref=2700.0, skew=-6.0)),
                        ('Einsatz 0,80 % (Diagnose)', dict(einsatz=0.008)),
                        ('Einsatz 0,90 % (Diagnose)', dict(einsatz=0.009))]:
        jobs.append((name, h, extra))
with Pool(4) as P:
    emp = P.map(lauf, jobs)
ergebnis['empfindlichkeit'] = [dict(name=n, haelfte=h, cagr=c, dd=dd, dd_schluss=ds) for n, h, c, dd, ds in emp]
for n, h, c, dd, ds in emp:
    print(f'   {h} {n:40s} Rendite {c:6.2%}  DD {dd:6.2%}  DD nur Schluss {ds:6.2%}')

# Jahresrenditen H2
r = backtest(d, *H2, **NEU)
kurve = pd.Series(r['kurve'], index=d.index[r['i0']:r['i1']])
jahr = kurve.groupby(kurve.index.year).last()
jr = (jahr / jahr.shift(1).fillna(100000.0) - 1)
ergebnis['jahresrenditen_H2'] = {int(k): float(v) for k, v in jr.items()}
print('   Jahresrenditen H2:', ', '.join(f'{k}: {v:.1%}' for k, v in jr.items()))

ergebnis['fehlgeschlagen'] = fehler
json.dump(ergebnis, open(f'{ROOT}/ergebnisse/verifikation.json', 'w'), indent=1, ensure_ascii=False, default=float)
print('\nFehlgeschlagen:', fehler or 'keine')

# ---------- F. Arbitragegrenzen bei der taeglichen Bewertung aller offenen Positionen ----------
def grenzen(h):
    r = backtest(d, *h, **NEU)
    idx = d.index; tage = idx.values.astype('datetime64[D]')
    C, L, VX, VXH = d.close.values, d.low.values, d.vx.values, d.vx_high.values
    n = verl = 0; schlimmst = 0.0
    for q in r['trades'] + r['offen']:
        for i in range(q['ein_idx'], min(q['exp_idx'], r['i1'])):
            T = (q['exp_datum'] - tage[i]).astype(int) / 365
            for S_, v_ in ((C[i], VX[i]), (L[i], VXH[i])):
                v = mod.put(S_, q['K1'], T, v_) - mod.put(S_, q['K2'], T, v_)
                n += 1
                if v < -1e-9 or v > q['w'] + 1e-9:
                    verl += 1; schlimmst = max(schlimmst, max(-v, v - q['w']) / q['w'])
    return n, verl, schlimmst
for name, h in (('H1', H1), ('H2', H2)):
    n, verl, s = grenzen(h)
    check(f'F1 {name}: tägliche Bewertung innerhalb 0..Breite (Schluss + Stress)', verl == 0,
          f'{verl} von {n} Bewertungen, max. Überschreitung {s:.2%} der Breite')
json.dump(ergebnis, open(f'{ROOT}/ergebnisse/verifikation.json', 'w'), indent=1, ensure_ascii=False, default=float)
print('Fehlgeschlagen (final):', fehler)
