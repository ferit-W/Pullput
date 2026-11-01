"""Backtest-Engine fuer Bull-Put-Spreads auf SPX (Modellpreise).

Rekonstruktion der frueheren Engine (Code nicht mehr vorhanden). Festgelegte Regeln laut ERGEBNIS_vorher.md:
- Einstieg zum Schlusskurs, wenn Vortagesschluss >= EMA und weniger als max_pos Positionen offen
- Short-Put per Delta (Modellflaeche), Long-Put `breite` Punkte tiefer (mit Kurs skaliert)
- Laufzeit `tage` Kalendertage, Halten bis Verfall (Cash-Settlement zum Schlusskurs), kein Stop/TP
- Max. Verlust je Position = einsatz * Konto; Zins 4 % p. a. auf Cash
- Kosten: Abschlag `slip` Punkte auf die Kreditpraemie + `fee` USD je Spread
- Drawdown taeglich inkl. Intraday-Stress (Bewertung zu Tagestief SPX und Tageshoch VX1)
Unbekannte Modelldetails (IV-Faktor, Skew, Breiten-Referenz) sind Parameter und werden nur auf Haelfte 1 kalibriert.
"""
import math
import numpy as np
import pandas as pd

ROOT = __file__.rsplit('/', 1)[0]


def lade_daten():
    s = pd.read_csv(f'{ROOT}/daten/SPX_1D.csv')
    v = pd.read_csv(f'{ROOT}/daten/VX1_1D.csv')
    s['datum'] = pd.to_datetime(s.time, unit='s').dt.normalize()
    # VX1-Session beginnt am Vorabend (22/23 Uhr UTC) -> Handelstag = Folgetag
    v['datum'] = (pd.to_datetime(v.time, unit='s') + pd.Timedelta(hours=3)).dt.normalize()
    s = s.drop_duplicates('datum').set_index('datum')[['open', 'high', 'low', 'close']]
    v = v.drop_duplicates('datum').set_index('datum')[['high', 'close']].rename(
        columns={'high': 'vx_high', 'close': 'vx'})
    d = s.join(v, how='left')
    d[['vx', 'vx_high']] = d[['vx', 'vx_high']].ffill()
    return d


def ncdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


class Modell:
    """Volatilitaetsflaeche: sigma(K) = ivf * VX/100 * (1 - skew * ln(K/S)), Untergrenze 0,05."""

    def __init__(self, ivf=0.766, skew=-5.5, r=0.04):
        self.ivf, self.skew, self.r = ivf, skew, r

    def sigma(self, S, K, vx):
        return max(0.05, self.ivf * vx / 100.0 * (1.0 - self.skew * math.log(K / S)))

    def put(self, S, K, T, vx):
        if T <= 1e-9:
            return max(K - S, 0.0)
        sg = self.sigma(S, K, vx)
        sq = sg * math.sqrt(T)
        d1 = (math.log(S / K) + (self.r + 0.5 * sg * sg) * T) / sq
        d2 = d1 - sq
        return K * math.exp(-self.r * T) * ncdf(-d2) - S * ncdf(-d1)

    def put_delta(self, S, K, T, vx):
        sg = self.sigma(S, K, vx)
        sq = sg * math.sqrt(T)
        d1 = (math.log(S / K) + (self.r + 0.5 * sg * sg) * T) / sq
        return ncdf(d1) - 1.0

    def strike_fuer_delta(self, S, T, vx, delta):
        """|Put-Delta| = delta; Bisektion in log-Moneyness."""
        lo, hi = -1.0, 1.0  # ln(K/S)
        for _ in range(60):
            m = 0.5 * (lo + hi)
            if -self.put_delta(S, S * math.exp(m), T, vx) < delta:
                lo = m
            else:
                hi = m
        return S * math.exp(0.5 * (lo + hi))


DEFAULT = dict(tage=21, delta=0.8, breite=100.0, breite_ref=2750.0, max_pos=3, ema=100, einsatz=0.011,
               slip=0.25, fee=3.60, zins=0.04, ivf=0.766, skew=-5.5,
               # Erweiterungen (Standard = aus)
               min_abstand=1,      # min. Handelstage zwischen zwei Einstiegen
               ema_kurz=0,         # zusaetzlicher kurzer Trendfilter (0 = aus)
               max_risiko=None,    # Obergrenze Summe max. Verlust offener Positionen (Anteil Konto)
               vx_max=None,        # kein Einstieg wenn VX1 > vx_max
               dd_bremse=None,     # (schwelle, faktor): Einsatz * faktor, wenn Konto-DD > schwelle
               zins_basis='cash',  # 'cash' (inkl. vereinnahmter Praemien) oder 'equity' (nur Kontowert)
               ema_steigung=0,     # >0: Einstieg nur wenn EMA heute > EMA vor n Handelstagen
               )


def backtest(d, start, ende, **kw):
    p = dict(DEFAULT)
    p.update(kw)
    mod = Modell(p['ivf'], p['skew'], p.get('r_preis', p['zins']))
    ema = d.close.ewm(span=p['ema'], adjust=False).mean().values
    emak = d.close.ewm(span=p['ema_kurz'], adjust=False).mean().values if p['ema_kurz'] else None
    idx = d.index
    i0 = idx.searchsorted(pd.Timestamp(start))
    i1 = idx.searchsorted(pd.Timestamp(ende), side='right')
    C, L, VX, VXH = d.close.values, d.low.values, d.vx.values, d.vx_high.values
    tage_arr = idx.values.astype('datetime64[D]')

    cash = 100000.0
    pos = []  # dict(K1,K2,n,exp_idx,exp_datum)
    peak = cash
    maxdd = 0.0
    dd_hoch = dd_tief = None
    peak_dat = idx[i0]
    eq_kurve = []
    ntr = 0
    letzter_einstieg = -10**9
    gewinne = []
    trades = []
    dd_schluss = 0.0
    eq_prev = cash

    def bewerte(i, S, vx):
        tot = 0.0
        for q in pos:
            T = (q['exp_datum'] - tage_arr[i]).astype(int) / 365.0
            tot += q['n'] * 100.0 * (mod.put(S, q['K1'], T, vx) - mod.put(S, q['K2'], T, vx))
        return tot

    for i in range(i0, i1):
        if i > i0:
            dt = (tage_arr[i] - tage_arr[i - 1]).astype(int)
            basis = cash if p['zins_basis'] == 'cash' else eq_prev
            cash += basis * ((1.0 + p['zins']) ** (dt / 365.0) - 1.0)
        S = C[i]
        # Verfall
        rest = []
        for q in pos:
            if q['exp_idx'] == i:
                zahl = q['n'] * 100.0 * (max(q['K1'] - S, 0) - max(q['K2'] - S, 0))
                cash -= zahl
                gewinne.append(q['n'] * (q['kredit'] * 100 - p['fee']) - zahl)
                trades.append(dict(q, S_end=S, zahlung=zahl, ergebnis=gewinne[-1]))
            else:
                rest.append(q)
        pos = rest
        # Stress-Bewertung (vor neuem Einstieg, offene Positionen zum Tagestief)
        eq_stress = cash - bewerte(i, L[i], VXH[i])
        eq_vor = cash - bewerte(i, S, VX[i])
        # Einstieg
        filt = C[i - 1] >= ema[i - 1]
        if emak is not None:
            filt = filt and C[i - 1] >= emak[i - 1]
        if p['ema_steigung'] and ema[i - 1] <= ema[i - 1 - p['ema_steigung']]:
            filt = False
        if p['vx_max'] is not None and VX[i] > p['vx_max']:
            filt = False
        if filt and len(pos) < p['max_pos'] and i - letzter_einstieg >= p['min_abstand']:
            exp_d = tage_arr[i] + np.timedelta64(p['tage'], 'D')
            j = idx.searchsorted(pd.Timestamp(exp_d), side='right') - 1  # letzter Handelstag <= Verfall
            if j > i:
                T = (exp_d - tage_arr[i]).astype(int) / 365.0
                K1 = mod.strike_fuer_delta(S, T, VX[i], p['delta'])
                w = p['breite'] * S / p['breite_ref']
                K2 = K1 - w
                kredit = mod.put(S, K1, T, VX[i]) - mod.put(S, K2, T, VX[i]) - p['slip']
                maxl = w - kredit
                f = p['einsatz']
                if p['dd_bremse'] is not None and eq_vor < peak * (1 - p['dd_bremse'][0]):
                    f *= p['dd_bremse'][1]
                risiko_offen = sum(q['n'] * q['maxl'] * 100 for q in pos)
                budget = f * eq_vor
                if p['max_risiko'] is not None:
                    budget = min(budget, max(0.0, p['max_risiko'] * eq_vor - risiko_offen))
                if maxl > 0 and kredit > 0 and budget > 0:
                    n = budget / (maxl * 100.0 + p['fee'])
                    cash += n * (kredit * 100.0 - p['fee'])
                    pos.append(dict(K1=K1, K2=K2, n=n, exp_idx=j, exp_datum=exp_d, kredit=kredit, maxl=maxl,
                                    ein_idx=i, S_ein=S, vx_ein=VX[i], w=w))
                    ntr += 1
                    letzter_einstieg = i
        eq = cash - bewerte(i, S, VX[i])
        if eq > peak:
            peak, peak_dat = eq, idx[i]
        dd = 1 - min(eq, eq_stress) / peak
        if dd > maxdd:
            maxdd, dd_hoch, dd_tief = dd, peak_dat, idx[i]
        dd_schluss = max(dd_schluss, 1 - eq / peak)
        eq_prev = eq
        eq_kurve.append(eq)
    jahre = (tage_arr[i1 - 1] - tage_arr[i0]).astype(int) / 365.25
    cagr = (eq_kurve[-1] / 100000.0) ** (1 / jahre) - 1
    return dict(cagr=cagr, dd=maxdd, ntr=ntr / jahre, dd_hoch=str(dd_hoch.date()), dd_tief=str(dd_tief.date()),
                trefferquote=float(np.mean(np.array(gewinne) > 0)) if gewinne else None,
                dd_schluss=dd_schluss, trades=trades, offen=pos, kurve=eq_kurve, i0=i0, i1=i1, params=p)


H1 = ('2007-01-01', '2016-12-31')
H2 = ('2017-01-01', '2026-12-31')
