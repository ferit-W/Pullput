"""Korrigierte Backtest-Engine (Audit). Regeln: audit/VORAB_REGELN.md, Konfiguration: audit/konfiguration.json.

Strategie (unverändert): SPX-Bull-Put-Spread, Short-Put-Delta -0,80, Long-Put 100*S/2750 tiefer, Ziellaufzeit 21 T,
max. 4 Positionen, max. 1 Einstieg je Handelstag, Vortagesschluss >= EMA 200 des Vortags, Einsatz 0,85 % des Kontowerts
inkl. Gebühren, Halten bis Verfall.

Modellschalter (alle getrennt abschaltbar, Legacy-Modus reproduziert engine.py exakt):
  verfaelle      'synthetisch' | 'monatlich' (V-M) | 'weekly_annahme' (V-W)
  t_legacy       True: T = Zieltage/365 ab Einstieg (alt), False: tatsächliche Zeit bis zur Abrechnung
  raster         0 = keine Rundung, sonst Strike-Raster in Punkten des Produkts
  ganze          True: ganze Kontrakte, abgerundet
  stress         'legacy' | 'drei'  (siehe VORAB_REGELN Abschnitt 6)
  zins_basis     'cash' (alt, inkl. Prämien) | 'equity'
"""
import math
import json
import numpy as np
import pandas as pd

ROOT = __file__.rsplit('/', 2)[0]

LISTING = {  # Weekly-Listing-Beginn (VORAB_REGELN Abschnitt 1, nicht am Original geprüft)
    4: pd.Timestamp('2005-10-28'),  # Freitag
    2: pd.Timestamp('2016-02-23'),  # Mittwoch
    0: pd.Timestamp('2016-08-15'),  # Montag
    1: pd.Timestamp('2022-04-18'),  # Dienstag
    3: pd.Timestamp('2022-05-11'),  # Donnerstag
}

STANDARD = dict(
    start='2007-01-01', ende='2016-12-31', startkapital=100000.0,
    produkt='SPX', skala=1.0, multiplikator=100.0,
    tage_ziel=21, dte_min=14, dte_max=28, verfaelle='monatlich',
    delta=0.80, breite=100.0, breite_ref=2750.0, max_pos=4, ema=200, einsatz=0.0085,
    ivf=0.766, skew=5.5,           # sigma = ivf*VX/100*(1 + skew*ln(K/S)); +5,5 = engine.py skew=-5.5
    sigma_min=0.05, r_preis=0.04, q_div=0.0,
    zins_cash=0.04, zins_basis='equity',
    slip=0.25, fee_kontrakt_seite=1.80, fee_abrechnung=0.0,
    raster=5.0, ganze=False, t_legacy=False, stress='drei', vx_lag=0,
)

LEGACY = dict(STANDARD, verfaelle='synthetisch', t_legacy=True, raster=0.0, ganze=False, stress='legacy',
              zins_basis='cash')


def ncdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def lade_daten(vx_zuordnung='korrigiert'):
    """vx_zuordnung: 'alt' = Kalendertag von (Zeitstempel + 3 h) wie engine.py;
    'korrigiert' = erster SPX-Handelstag am oder nach (Zeitstempel + 3 h). Seit 2025 trägt die Kerze des Handelstags
    nach einem Feiertag den Zeitstempel des Sonntagabends davor; 'alt' ordnet sie dem Feiertag zu und verwirft sie."""
    s = pd.read_csv(f'{ROOT}/daten/SPX_1D.csv')
    v = pd.read_csv(f'{ROOT}/daten/VX1_1D.csv')
    s['datum'] = pd.to_datetime(s.time, unit='s').dt.normalize()
    v['datum'] = (pd.to_datetime(v.time, unit='s') + pd.Timedelta(hours=3)).dt.normalize()
    s = s.drop_duplicates('datum').set_index('datum')[['open', 'high', 'low', 'close']]
    if vx_zuordnung == 'korrigiert':
        pos = s.index.searchsorted(v['datum'])
        ok = pos < len(s.index)
        v = v[ok].copy()
        v['datum'] = s.index[pos[ok]]
        v = v.drop_duplicates('datum', keep='last')
    v = v.drop_duplicates('datum').set_index('datum')[['high', 'close']].rename(columns={'high': 'vx_high', 'close': 'vx'})
    d = s.join(v, how='left')
    d['vx_gefuellt'] = d.vx.isna()
    d[['vx', 'vx_high']] = d[['vx', 'vx_high']].ffill()   # nur Vergangenheit, kein Blick nach vorn
    return d


class Modell:
    def __init__(self, c):
        self.ivf, self.skew, self.smin, self.r, self.q = c['ivf'], c['skew'], c['sigma_min'], c['r_preis'], c['q_div']

    def sigma(self, S, K, vx):
        return max(self.smin, self.ivf * vx / 100.0 * (1.0 + self.skew * math.log(K / S)))

    def put(self, S, K, T, vx):
        if T <= 1e-9:
            return max(K - S, 0.0)
        sg = self.sigma(S, K, vx)
        sq = sg * math.sqrt(T)
        d1 = (math.log(S / K) + (self.r - self.q + 0.5 * sg * sg) * T) / sq
        return K * math.exp(-self.r * T) * ncdf(-(d1 - sq)) - S * math.exp(-self.q * T) * ncdf(-d1)

    def put_delta(self, S, K, T, vx):
        sg = self.sigma(S, K, vx)
        sq = sg * math.sqrt(T)
        d1 = (math.log(S / K) + (self.r - self.q + 0.5 * sg * sg) * T) / sq
        return math.exp(-self.q * T) * (ncdf(d1) - 1.0)

    def strike_fuer_delta(self, S, T, vx, delta):
        lo, hi = -1.0, 1.0
        for _ in range(60):
            m = 0.5 * (lo + hi)
            if -self.put_delta(S, S * math.exp(m), T, vx) < delta:
                lo = m
            else:
                hi = m
        K = S * math.exp(0.5 * (lo + hi))
        ok = abs(-self.put_delta(S, K, T, vx) - delta) < 1e-4
        return K, ok


class Kalender:
    def __init__(self, idx):
        self.idx = idx
        self.tage = set(idx)
        self.letzter = idx[-1]

    def handelstag(self, t):
        if t <= self.letzter:
            return t in self.tage
        return t.weekday() < 5

    def vorheriger(self, t):
        while not self.handelstag(t):
            t -= pd.Timedelta(days=1)
        return t

    def dritter_freitag(self, jahr, monat):
        t = pd.Timestamp(jahr, monat, 1)
        t += pd.Timedelta(days=(4 - t.weekday()) % 7 + 14)
        return t

    def kandidaten(self, heute, modus, dmin, dmax):
        """Liste (verfallsdatum, abrechnung 'AM'|'PM') verfügbar am Tag `heute` mit dmin..dmax Kalendertagen."""
        out = {}
        for m_off in range(0, 3):
            j, m = heute.year, heute.month + m_off
            j += (m - 1) // 12
            m = (m - 1) % 12 + 1
            f3 = self.dritter_freitag(j, m)
            v = self.vorheriger(f3)
            if dmin <= (v - heute).days <= dmax:
                out[v] = 'AM'
        if modus == 'weekly_annahme':
            for k in range(dmin, dmax + 1):
                t = heute + pd.Timedelta(days=k)
                wd = t.weekday()
                if wd > 4 or heute < LISTING[wd]:
                    continue
                if wd == 4:
                    if t == self.dritter_freitag(t.year, t.month):
                        continue  # 3. Freitag = AM-Monatsverfall (oben)
                    v = self.vorheriger(t)
                else:
                    if not self.handelstag(t):
                        continue
                    v = t
                if dmin <= (v - heute).days <= dmax and v not in out:
                    out[v] = 'PM'
        return sorted(out.items())


def runden(x, g):
    return round(x / g) * g if g > 0 else x


def backtest(d, **kw):
    c = dict(STANDARD)
    c.update(kw)
    mod = Modell(c)
    kal = Kalender(d.index)
    ema = d.close.ewm(span=c['ema'], adjust=False).mean().values
    idx = d.index
    i0 = idx.searchsorted(pd.Timestamp(c['start']))
    i1 = idx.searchsorted(pd.Timestamp(c['ende']), side='right')
    sk = c['skala']
    O, C, L = d.open.values * sk, d.close.values * sk, d.low.values * sk
    CU = d.close.values
    VX, VXH = d.vx.values, d.vx_high.values
    mult = c['multiplikator']
    fee_ein = 2 * c['fee_kontrakt_seite']
    pos_idx = {t: i for i, t in enumerate(idx)}

    def T_bis(q, t_heute):
        tage = (q['verfall'] - t_heute).days
        if c['t_legacy']:
            tage = (q['ziel'] - t_heute).days
            return max(tage, 0) / 365.0
        return max(tage - (6.5 / 24 if q['abr'] == 'AM' else 0.0), 0.0) / 365.0

    def wert(q, S, vx, t_heute):
        T = T_bis(q, t_heute)
        return q['n'] * mult * (mod.put(S, q['K1'], T, vx) - mod.put(S, q['K2'], T, vx))

    def innerer(q, S):
        return q['n'] * mult * (max(q['K1'] - S, 0) - max(q['K2'] - S, 0))

    cash = c['startkapital']
    eq_vortag = cash
    peak = cash
    pos, trades, tage_log = [], [], []
    maxdd = maxdd_schluss = 0.0
    dd_hoch = dd_tief = peak_dat = idx[i0]
    zins_kum = 0.0
    kosten_kum = 0.0
    zaehl = dict(filter_aus=0, voll=0, kein_verfall=0, kredit_ungueltig=0, konto_zu_klein=0, delta_nicht_gefunden=0, eroeffnet=0)

    for i in range(i0, i1):
        t = idx[i]
        if i > i0:
            dt = (t - idx[i - 1]).days
            basis = cash if c['zins_basis'] == 'cash' else eq_vortag
            z = basis * ((1 + c['zins_cash']) ** (dt / 365.0) - 1)
            cash += z
            zins_kum += z
        # AM-Abrechnung zur Eröffnung
        rest = []
        for q in pos:
            if q['abr'] == 'AM' and q['verfall'] == t and not c['t_legacy']:
                zahl = innerer(q, O[i])
                cash -= zahl + q['n'] * c['fee_abrechnung']
                trades.append(dict(q, S_abr=O[i], zahlung=zahl, abr_datum=t,
                                   ergebnis=q['gutschrift'] - zahl - q['n'] * c['fee_abrechnung']))
            else:
                rest.append(q)
        pos = rest
        # Stress (Tagesdaten-Szenario)
        if c['stress'] == 'legacy':
            heute_pm = [q for q in pos if q['verfall_idx'] == i]
            offen_stress = [q for q in pos if q['verfall_idx'] != i]
            # alte Engine: Verfallszahlungen des Tages sind vor der Stressbewertung schon gebucht
            eq_stress = cash - sum(innerer(q, C[i]) + q['n'] * c['fee_abrechnung'] for q in heute_pm) - sum(q['n'] * mult * (mod.put(L[i], q['K1'], T_bis(q, t), VXH[i])
                                                    - mod.put(L[i], q['K2'], T_bis(q, t), VXH[i])) for q in offen_stress)
        else:
            kombis = ((L[i], VX[i]), (L[i], VXH[i]), (C[i], VXH[i]))
            schlecht = 0.0
            for S_, v_ in kombis:
                lia = 0.0
                for q in pos:
                    lia += innerer(q, S_) if q['verfall'] == t else wert(q, S_, v_, t)
                schlecht = max(schlecht, lia)
            eq_stress = cash - schlecht
        # PM-Abrechnung zum Schluss (Legacy: alle Abrechnungen zum Schluss)
        rest = []
        for q in pos:
            if q['verfall_idx'] == i:
                zahl = innerer(q, C[i])
                cash -= zahl + q['n'] * c['fee_abrechnung']
                trades.append(dict(q, S_abr=C[i], zahlung=zahl, abr_datum=t,
                                   ergebnis=q['gutschrift'] - zahl - q['n'] * c['fee_abrechnung']))
            else:
                rest.append(q)
        pos = rest
        vx_e = VX[i - c['vx_lag']]
        E = cash - sum(wert(q, C[i], VX[i], t) for q in pos)
        # Einstieg
        if not (CU[i - 1] >= ema[i - 1]):   # Filter immer auf SPX-Niveau (unabhängig vom Produkt)
            zaehl['filter_aus'] += 1
        elif len(pos) >= c['max_pos']:
            zaehl['voll'] += 1
        else:
            if c['verfaelle'] == 'synthetisch':
                ziel = t + pd.Timedelta(days=c['tage_ziel'])
                v = kal.vorheriger(ziel)
                kand = [(v, 'PM')] if v > t else []
            else:
                ziel = None
                kand = kal.kandidaten(t, c['verfaelle'], c['dte_min'], c['dte_max'])
                kand = sorted(kand, key=lambda x: (abs((x[0] - t).days - c['tage_ziel']), x[0]))[:1]
            if not kand:
                zaehl['kein_verfall'] += 1
            else:
                verfall, abr = kand[0]
                q = dict(verfall=verfall, abr=abr, ziel=ziel if ziel is not None else verfall,
                         verfall_idx=pos_idx.get(verfall, 10**9) if abr == 'PM' or c['t_legacy'] else -1)
                T = T_bis(q, t)
                S = C[i]
                K1r, ok = mod.strike_fuer_delta(S, T, vx_e, c['delta'])
                if not ok:
                    zaehl['delta_nicht_gefunden'] += 1
                else:
                    g = c['raster']
                    K1 = runden(K1r, g)
                    w = max(g, runden(c['breite'] * (S / sk) / c['breite_ref'] * sk, g)) if g else c['breite'] * (S / sk) / c['breite_ref'] * sk
                    K2 = K1 - w
                    mid = mod.put(S, K1, T, vx_e) - mod.put(S, K2, T, vx_e)
                    kredit = mid - c['slip']
                    maxl = w - kredit
                    risiko_je = maxl * mult + fee_ein
                    budget = c['einsatz'] * E
                    if kredit <= 0 or maxl <= 0:
                        zaehl['kredit_ungueltig'] += 1
                    else:
                        n = budget / risiko_je
                        if c['ganze']:
                            n = math.floor(n + 1e-9)
                        if n <= 0:
                            zaehl['konto_zu_klein'] += 1
                        else:
                            gut = n * (kredit * mult - fee_ein)
                            cash += gut
                            kosten_kum += n * (c['slip'] * mult + fee_ein)
                            q.update(K1=K1, K2=K2, K1_roh=K1r, w=w, n=n, kredit=kredit, mid=mid, maxl=maxl,
                                     gutschrift=gut, risiko=n * risiko_je, risiko_anteil=n * risiko_je / E,
                                     ein_datum=t, ein_idx=i, S_ein=S, vx_ein=vx_e, T_ein=T, E_ein=E,
                                     dte=(verfall - t).days)
                            pos.append(q)
                            zaehl['eroeffnet'] += 1
        lia = sum(wert(q, C[i], VX[i], t) for q in pos)
        eq = cash - lia
        if eq > peak:
            peak, peak_dat = eq, t
        dd = 1 - min(eq, eq_stress) / peak
        if dd > maxdd:
            maxdd, dd_hoch, dd_tief = dd, peak_dat, t
        maxdd_schluss = max(maxdd_schluss, 1 - eq / peak)
        offen_risiko = sum(q['n'] * (q['maxl'] * mult) for q in pos)
        tage_log.append(dict(datum=t, kontowert=eq, cash=cash, verbindlichkeit=lia, stress_kontowert=eq_stress,
                             offen=len(pos), offenes_max_risiko=offen_risiko,
                             offenes_risiko_anteil=offen_risiko / eq if eq > 0 else float('nan'),
                             zins_kumuliert=zins_kum, drawdown=dd))
        eq_vortag = eq

    tl = pd.DataFrame(tage_log).set_index('datum')
    jahre = (idx[i1 - 1] - idx[i0]).days / 365.25
    ende = tl.kontowert.iloc[-1]
    erg = np.array([q['ergebnis'] for q in trades]) if trades else np.array([])
    kz = dict(
        rendite_pa=(ende / c['startkapital']) ** (1 / jahre) - 1,
        max_drawdown_stress=maxdd, max_drawdown_schluss=maxdd_schluss,
        dd_hoch=str(dd_hoch.date()), dd_tief=str(dd_tief.date()),
        endkapital=ende, trades=len(trades) + len(pos), trades_pa=(len(trades) + len(pos)) / jahre,
        trefferquote=float((erg > 0).mean()) if len(erg) else None,
        avg_gewinn=float(erg[erg > 0].mean()) if (erg > 0).any() else None,
        avg_verlust=float(erg[erg <= 0].mean()) if (erg <= 0).any() else None,
        kosten_gesamt=kosten_kum, zins_gesamt=zins_kum,
        max_offenes_risiko_anteil=float(np.nanmax(tl.offenes_risiko_anteil)),
        risiko_je_einstieg_median=float(np.median([q['risiko_anteil'] for q in trades + pos])) if trades or pos else None,
        risiko_je_einstieg_min=float(np.min([q['risiko_anteil'] for q in trades + pos])) if trades or pos else None,
        risiko_je_einstieg_max=float(np.max([q['risiko_anteil'] for q in trades + pos])) if trades or pos else None,
        **{f'tage_{k}': v for k, v in zaehl.items()},
    )
    return dict(kennzahlen=kz, trades=trades, offen=pos, tage=tl, konfig=c)


def jahresergebnisse(r):
    tl = r['tage']
    j = tl.kontowert.groupby(tl.index.year).last()
    vor = j.shift(1)
    vor.iloc[0] = r['konfig']['startkapital']
    return (j / vor - 1)
