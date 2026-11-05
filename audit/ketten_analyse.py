"""Vergleich Modellpreise gegen echte SPXW-Geld-/Briefkurse (daten/ketten/*.csv, 29.10.-05.11.2026).
Start (im Repo-Hauptordner): python3 -I audit/ketten_analyse.py
Gilt nur für 5 Handelstage und SPXW-PM-Kontrakte; es sind keine Aussagen über 2007-2026 oder SPX-AM-Monatskontrakte möglich."""
import glob
import json
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, 'audit')
import engine2 as E2  # noqa: E402

AUS = 'audit/ergebnisse'
frames = []
for f in sorted(glob.glob('daten/ketten/kette_*.csv')):
    d = pd.read_csv(f, sep=';')
    d['datei'] = f.split('_')[-1][:8]
    frames.append(d)
K = pd.concat(frames, ignore_index=True)
K['zeit'] = pd.to_datetime(K.zeit)
K['tag'] = K.zeit.dt.normalize()
K['verfall_dt'] = pd.to_datetime(K.verfall.astype(str), format='%Y%m%d')
K['dte_exakt'] = (K.verfall_dt - K.tag).dt.days
K['mid'] = (K.bid + K.ask) / 2
bericht = {}

# ---- 1. Datenqualität -------------------------------------------------------------------------------------------
bericht['zeilen'] = int(len(K))
bericht['klassen'] = K.klasse.value_counts().to_dict()
bericht['datentyp'] = {int(k): int(v) for k, v in K.datentyp.value_counts().items()}
bericht['dte_stimmt_mit_verfall'] = float((K.dte == K.dte_exakt).mean())
P = K[(K.art == 'P') & K.bid.notna() & K.ask.notna() & (K.ask >= K.bid)].copy()
P['spread_rel'] = (P.ask - P.bid) / P.mid
# Preise aufsteigend im Strike? (Put-Mid muss mit dem Strike steigen)
verl = 0
n = 0
for (z, v), g in P.groupby(['zeit', 'verfall']):
    g = g.sort_values('strike')
    dm = np.diff(g.mid.values)
    n += len(dm)
    verl += int((dm < -1e-9).sum())
bericht['put_mid_monoton'] = dict(paare=n, verletzt=verl)

# ---- 2. Marktimplizite Vola gegen VIX und Skew ------------------------------------------------------------------
zeilen = []
for (z, v), g in P.groupby(['zeit', 'verfall']):
    S, vix = g.spx.iloc[0], g.vix.iloc[0]
    dte = g.dte_exakt.iloc[0]
    g = g[(g.tws_iv > 0.01) & (g.tws_iv < 3)]
    x = np.log(g.strike / S)
    w = g[(x.abs() < 0.05)]
    if dte < 14 or len(w) < 8:
        continue
    xx = np.log(w.strike / S)
    b, a = np.polyfit(xx, w.tws_iv, 1)           # iv(x) = a + b*x  -> b/a = Skew im Sinn der Doku-Formel (1 + s*x)
    zeilen.append(dict(zeit=z, tag=g.tag.iloc[0], verfall=int(v), dte=int(dte), spx=S, vix=vix, iv_atm=a, iv_atm_je_vix=a / (vix / 100),
                       skew_s=b / a))
IV = pd.DataFrame(zeilen)
IV.to_csv(f'{AUS}/ketten_iv_skew.csv', index=False)
m = IV[(IV.dte >= 14) & (IV.dte <= 36)]
bericht['iv_atm_je_vix_median'] = float(m.iv_atm_je_vix.median())
bericht['iv_atm_je_vix_p10_p90'] = [float(m.iv_atm_je_vix.quantile(.1)), float(m.iv_atm_je_vix.quantile(.9))]
bericht['skew_s_median'] = float(m.skew_s.median())
bericht['skew_s_p10_p90'] = [float(m.skew_s.quantile(.1)), float(m.skew_s.quantile(.9))]

# ---- 3. Der konkrete Spread: ATM-Put (K1 = Kurs, auf 5 gerundet), Long-Put 10 Punkte tiefer --------------------------
def modell_kredit(S, vix, T, K1, K2, ivf, skew):
    c = dict(E2.STANDARD, ivf=ivf, skew=skew)
    mo = E2.Modell(c)
    return mo.put(S, K1, T, vix) - mo.put(S, K2, T, vix)

MODELLE = {'mein_Modell(0,766;+5,5)': (0.766, 5.5), 'ChatGPT-Referenz(1,0;0)': (1.0, 0.0), 'Markt-Skew(1,0;-3)': (1.0, -3.0)}
sp = []
for (z, v), g in P.groupby(['zeit', 'verfall']):
    dte = g.dte_exakt.iloc[0]
    if dte < 21 or dte > 32:
        continue
    S, vix = g.spx.iloc[0], g.vix.iloc[0]
    K1 = round(S / 5) * 5
    K2 = K1 - 10
    a = g[g.strike == K1]
    b = g[g.strike == K2]
    if a.empty or b.empty:
        continue
    a, b = a.iloc[0], b.iloc[0]
    mid = a.mid - b.mid
    nat = a.bid - b.ask                                  # Short zum Bid verkaufen, Long zum Ask kaufen
    halb = ((a.ask - a.bid) + (b.ask - b.bid)) / 2
    T = dte / 365.0
    t_iv = None
    # Preis aus den TWS-IV der beiden Strikes (Konsistenzprüfung der Datenquelle)
    mo = E2.Modell(dict(E2.STANDARD, ivf=1.0, skew=0.0))
    def bs(K, iv):
        mm = E2.Modell(dict(E2.STANDARD, sigma_min=iv, ivf=0.0, skew=0.0))
        return mm.put(S, K, T, 1.0)
    t_iv = bs(K1, a.tws_iv) - bs(K2, b.tws_iv)
    zeile = dict(zeit=z, tag=g.tag.iloc[0], verfall=int(v), dte=int(dte), spx=S, vix=vix, K1=K1, K2=K2, delta_markt=a.tws_delta,
                 bid1=a.bid, ask1=a.ask, bid2=b.bid, ask2=b.ask, mid=mid, natuerlich=nat, halbspanne=halb, aus_tws_iv=t_iv,
                 breite_kredit_mid=mid / 10, iv1=a.tws_iv, iv2=b.tws_iv,
                 skew_lokal=(b.tws_iv / a.tws_iv - 1) / np.log(K2 / K1))
    for nm, (ivf, sk) in MODELLE.items():
        zeile[nm] = modell_kredit(S, vix, T, K1, K2, ivf, sk)
    sp.append(zeile)
SP = pd.DataFrame(sp)
SP.to_csv(f'{AUS}/ketten_spread_vergleich.csv', index=False)
bericht['spreads'] = int(len(SP))
if len(SP):
    r = {}
    for nm in MODELLE:
        r[nm] = dict(fehler_zu_mid_mittel=float((SP[nm] - SP.mid).mean()), fehler_abs_mittel=float((SP[nm] - SP.mid).abs().mean()))
    r['aus_tws_iv'] = dict(fehler_zu_mid_mittel=float((SP.aus_tws_iv - SP.mid).mean()), fehler_abs_mittel=float((SP.aus_tws_iv - SP.mid).abs().mean()))
    bericht['modellfehler_punkte'] = r
    bericht['mid_kredit_mittel'] = float(SP.mid.mean())
    bericht['natuerlich_kredit_mittel'] = float(SP.natuerlich.mean())
    bericht['halbspanne_mittel'] = float(SP.halbspanne.mean())
    bericht['halbspanne_p10_p90'] = [float(SP.halbspanne.quantile(.1)), float(SP.halbspanne.quantile(.9))]
    bericht['skew_lokal_median'] = float(SP.skew_lokal.median())
    bericht['skew_lokal_p10_p90'] = [float(SP.skew_lokal.quantile(.1)), float(SP.skew_lokal.quantile(.9))]
    DV = E2.lade_daten()
    vx = SP.tag.map(lambda t: DV.vx.get(t, np.nan))
    ok = vx.notna()
    bericht['tage_mit_vx1_in_datei'] = sorted({str(t.date()) for t in SP.tag[ok]})
    if ok.any():
        bericht['vx1_je_vix_median'] = float((vx[ok] / SP.vix[ok]).median())
        bericht['iv_atm_k1_je_vx1_median'] = float((SP.iv1[ok] / (vx[ok] / 100)).median())
    bericht['iv_atm_k1_je_vix_median'] = float((SP.iv1 / (SP.vix / 100)).median())
    bericht['delta_short_markt_median'] = float(SP.delta_markt.median())
    # Abschlag 0,25 des Modells gegen den Markt: wie oft liegt (mid - 0,25) unter dem natürlichen Preis, also immer ausführbar?
    bericht['anteil_mid_minus_025_unter_natuerlich'] = float(((SP.mid - 0.25) <= SP.natuerlich).mean())
    bericht['anteil_mid_minus_025_ausfuehrbar_ueber_natuerlich'] = float(((SP.mid - 0.25) > SP.natuerlich).mean())
    tag = SP.groupby('tag').agg(n=('mid', 'size'), mid=('mid', 'mean'), natuerlich=('natuerlich', 'mean'), halbspanne=('halbspanne', 'mean'),
                                **{k.split('(')[0]: (k, 'mean') for k in MODELLE})
    tag.to_csv(f'{AUS}/ketten_spread_je_tag.csv')
    bericht['je_tag'] = {str(k.date()): {c: float(v) for c, v in row.items()} for k, row in tag.iterrows()}

# ---- 4. Zeitstempel: letzter Durchlauf je Tag ---------------------------------------------------------------------
letzt = K.groupby('datei').agg(erste=('zeit', 'min'), letzte=('zeit', 'max'), durchlaeufe=('durchlauf', 'nunique'))
bericht['zeitfenster'] = {k: [str(r.erste), str(r.letzte), int(r.durchlaeufe)] for k, r in letzt.iterrows()}

json.dump(bericht, open(f'{AUS}/ketten_bericht.json', 'w'), indent=1, ensure_ascii=False, default=float)
print(json.dumps(bericht, indent=1, ensure_ascii=False, default=float))
