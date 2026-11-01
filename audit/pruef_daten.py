"""Prüfung VX1-Rollregel, Session-Zuordnung (Sommerzeit) und Kalender-Abgleich SPX/VX1."""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, __file__.rsplit('/', 1)[0])
import engine2 as E2
ROOT = E2.ROOT
v = pd.read_csv(f'{ROOT}/daten/VX1_1D.csv'); s = pd.read_csv(f'{ROOT}/daten/SPX_1D.csv')
v['utc'] = pd.to_datetime(v.time, unit='s'); s['utc'] = pd.to_datetime(s.time, unit='s')
v['monat'] = v.utc.dt.month; s['monat'] = s.utc.dt.month
erg = {}
# 1) Sommerzeit: VX-Session-Start 22 Uhr UTC (CDT) bzw. 23 Uhr UTC (CST); SPX 13:30 (EDT) bzw. 14:30 (EST)
erg['vx_stunde_nach_monat'] = {int(m): {int(h): int(n) for h, n in r.items() if n} for m, r in pd.crosstab(v.monat, v.utc.dt.hour).iterrows()}
erg['spx_stunde_nach_monat'] = {int(m): {int(h): int(n) for h, n in r.items() if n} for m, r in pd.crosstab(s.monat, s.utc.dt.hour).iterrows()}
d = E2.lade_daten(); sub = d.loc['2007':]
vxd = set((v.utc + pd.Timedelta(hours=3)).dt.normalize())
erg['spx_tage_ohne_vx_ab_2007'] = [str(t.date()) for t in sub.index if t not in vxd]
erg['vx_tage_ohne_spx_ab_2007'] = sorted(str(t.date()) for t in vxd if t >= pd.Timestamp('2007-01-01') and t not in set(sub.index) and t <= sub.index[-1])
# 2) VX-Verfall: Mittwoch 30 Tage vor dem 3. Freitag des Folgemonats (bei Feiertag Handelstag davor) -> Rolltag = nächster Handelstag
kal = E2.Kalender(d.index)
roll = []
for j in range(2007, 2027):
    for m in range(1, 13):
        jj, mm = (j, m + 1) if m < 12 else (j + 1, 1)
        f3 = kal.dritter_freitag(jj, mm)
        vf = kal.vorheriger(f3 - pd.Timedelta(days=30))
        nxt = d.index[d.index > vf]
        if len(nxt) and nxt[0] <= d.index[-1]:
            roll.append(nxt[0])
roll = pd.DatetimeIndex(roll)
dvx = sub.vx.diff(); rspx = sub.close.pct_change()
X = np.vstack([np.ones(len(sub)), rspx.fillna(0)]).T
beta = np.linalg.lstsq(X[1:], dvx.fillna(0).values[1:], rcond=None)[0]
resid = dvx - (beta[0] + beta[1] * rspx)
ist_roll = sub.index.isin(roll)
erg['roll'] = dict(anzahl_rolltage=int(ist_roll.sum()),
                   mittl_vx_aenderung_rolltag=float(dvx[ist_roll].mean()), mittl_vx_aenderung_sonst=float(dvx[~ist_roll].mean()),
                   mittl_abs_residuum_rolltag=float(resid[ist_roll].abs().mean()), mittl_abs_residuum_sonst=float(resid[~ist_roll].abs().mean()),
                   anteil_rolltage_mit_vx_anstieg=float((dvx[ist_roll] > 0).mean()))
json.dump(erg, open(f'{ROOT}/audit/ergebnisse/datenpruefung.json', 'w'), indent=1, ensure_ascii=False, default=str)
print('VX Stunde je Monat', {m: erg['vx_stunde_nach_monat'][m] for m in (1, 4, 7, 11)})
print('SPX Stunde je Monat', {m: erg['spx_stunde_nach_monat'][m] for m in (1, 4, 7, 11)})
print('SPX-Tage ohne VX ab 2007:', len(erg['spx_tage_ohne_vx_ab_2007']), erg['spx_tage_ohne_vx_ab_2007'][:15])
print('VX-Tage ohne SPX ab 2007:', len(erg['vx_tage_ohne_spx_ab_2007']), erg['vx_tage_ohne_spx_ab_2007'][:10])
print('Roll:', erg['roll'])
