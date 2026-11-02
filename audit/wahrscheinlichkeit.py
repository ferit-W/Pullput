"""Vergleich Delta-0,8 (V-M, B2) gegen ATM-Varianten: Signifikanz der Überrendite und Robustheit über Szenarien."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, __file__.rsplit('/', 1)[0])
E = __file__.rsplit('/', 1)[0] + '/ergebnisse'
VAR = {'Delta 0,8 (V-M)': 'konto_taeglich_B2_Gesamt.csv', 'M-SPX-10': 'atm_konto_taeglich_M-SPX-10_Gesamt.csv',
       'M-SPX-5': 'atm_konto_taeglich_M-SPX-5_Gesamt.csv', 'M-XSP-5': 'atm_konto_taeglich_M-XSP-5_Gesamt.csv',
       'W-SPX-10': 'atm_konto_taeglich_W-SPX-10_Gesamt.csv', 'W-SPX-5': 'atm_konto_taeglich_W-SPX-5_Gesamt.csv'}
rng = np.random.default_rng(7)
zeilen = []
for name, f in VAR.items():
    tl = pd.read_csv(f'{E}/{f}', index_col=0, parse_dates=True)
    m = tl.kontowert.resample('ME').last()
    r = m.pct_change().dropna()
    x = r - (1.04 ** (1 / 12) - 1)                        # Überrendite gegenüber 4 % Cash
    t = x.mean() / x.std(ddof=1) * np.sqrt(len(x))
    # Block-Bootstrap (12-Monats-Blöcke): Anteil der Ziehungen mit positiver mittlerer Überrendite
    bl = 12; n = len(x); pos = 0
    for _ in range(4000):
        idx = np.concatenate([np.arange(s, s + bl) % n for s in rng.integers(0, n, n // bl + 1)])[:n]
        pos += x.values[idx].mean() > 0
    # rollierende 5-Jahres-Fenster mit positiver Überrendite
    roll = (1 + x).rolling(60).apply(np.prod, raw=True).dropna()
    zeilen.append(dict(variante=name, monate=n, ueberrendite_pa=float((1 + x.mean()) ** 12 - 1), t_wert=float(t),
                       bootstrap_anteil_positiv=pos / 4000, anteil_verlustmonate=float((r < 0).mean()),
                       schlechtester_monat=float(r.min()), anteil_5j_fenster_ueber_cash=float((roll > 1).mean())))
sig = pd.DataFrame(zeilen)
# Szenario-Robustheit: Anteil Szenarien × Hälften mit Rendite > 4 % (= schlägt Cash)
v = pd.read_csv(f'{E}/vergleich.csv'); d = v[v.variante.str.startswith('D B2')]
ref = v[v.variante.str.startswith('B2 ') & v.zeitraum.isin(['H1', 'H2'])]
b2 = pd.concat([ref, d]); b2 = b2[~b2.variante.str.contains('ohne Cashzins|Zins 0|Zins 2')]
a = pd.read_csv(f'{E}/vergleich_atm_empfindlichkeit.csv'); a = a[~a.szenario.str.contains('Zins 0')]
k = pd.read_csv(f'{E}/vergleich_atm.csv'); k = k[k.variante.str.contains('Abschlag')]
rob = [dict(variante='Delta 0,8 (V-M)', szenarien=len(b2), anteil_ueber_cash=float((b2.rendite_pa > 0.04).mean()),
            min_rendite=float(b2.rendite_pa.min()), max_dd=float(b2.max_drawdown_stress.max()))]
for nm in ('M-SPX-10', 'M-SPX-5', 'M-XSP-5', 'W-SPX-10', 'W-SPX-5'):
    s = pd.concat([a[a.variante == nm][['rendite_pa', 'max_drawdown_stress']],
                   k[k.variante.str.startswith(nm + ' ')][['rendite_pa', 'max_drawdown_stress']]])
    rob.append(dict(variante=nm, szenarien=len(s), anteil_ueber_cash=float((s.rendite_pa > 0.04).mean()),
                    min_rendite=float(s.rendite_pa.min()), max_dd=float(s.max_drawdown_stress.max())))
rob = pd.DataFrame(rob)
out = sig.merge(rob, on='variante')
out.to_csv(f'{E}/wahrscheinlichkeit.csv', index=False)
pd.set_option('display.width', 250); print(out.round(3).to_string(index=False))
