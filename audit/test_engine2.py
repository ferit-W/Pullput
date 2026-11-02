"""Gezielte Tests der korrigierten Engine. Start: python3 -m unittest audit/test_engine2.py -v (im Repo-Hauptordner)."""
import math
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit('/', 2)[0])
sys.path.insert(0, __file__.rsplit('/', 1)[0])
import engine as E1  # noqa: E402
import engine2 as E2  # noqa: E402

D = E2.lade_daten()


class Kontrolltrade(unittest.TestCase):
    """Erster Trade H2 (03.01.2017) gegen die unabhängige Kontrollrechnung des Auftraggebers (VX1 = 13,79)."""

    def test_werte(self):
        m = E2.Modell(E2.STANDARD)
        S, vx, T = 2257.83, 13.79, 21 / 365
        K1, ok = m.strike_fuer_delta(S, T, vx, 0.8)
        K2 = K1 - 100 * S / 2750
        kr = m.put(S, K1, T, vx) - m.put(S, K2, T, vx) - 0.25
        n = 850 / ((K1 - K2 - kr) * 100 + 3.6)
        erg = n * (kr * 100 - 3.6) - n * 100 * (max(K1 - 2280.07, 0) - max(K2 - 2280.07, 0))
        self.assertTrue(ok)
        self.assertAlmostEqual(K1, 2320.19, delta=0.01)
        self.assertAlmostEqual(K2, 2238.09, delta=0.01)
        self.assertAlmostEqual(kr, 52.62, delta=0.01)
        self.assertAlmostEqual(n, 0.28797, delta=0.00001)
        self.assertAlmostEqual(erg, 358.96, delta=0.01)

    def test_datei_wert_vx(self):
        self.assertAlmostEqual(D.loc['2017-01-03', 'vx'], 13.785)


class Reproduktion(unittest.TestCase):
    def test_legacy_gleich_alte_engine_h1(self):
        a = E1.backtest(E1.lade_daten(), *E1.H1, max_pos=4, ema=200, einsatz=0.0085)
        b = E2.backtest(E2.lade_daten('alt'), **dict(E2.LEGACY, start=E1.H1[0], ende=E1.H1[1]))
        self.assertAlmostEqual(a['kurve'][-1], b['kennzahlen']['endkapital'], places=4)
        self.assertAlmostEqual(a['dd'], b['kennzahlen']['max_drawdown_stress'], places=10)


class Gebuehren(unittest.TestCase):
    def test_einmalige_verbuchung(self):
        r = E2.backtest(D, start='2017-01-01', ende='2017-03-31')
        for q in r['trades']:
            self.assertAlmostEqual(q['gutschrift'], q['n'] * (q['kredit'] * 100 - 3.6), places=6)
            self.assertAlmostEqual(q['ergebnis'], q['gutschrift'] - q['zahlung'], places=6)
            self.assertAlmostEqual(q['risiko'], q['n'] * (q['maxl'] * 100 + 3.6), places=6)
            self.assertAlmostEqual(q['kredit'], q['mid'] - 0.25, places=9)

    def test_risiko_gleich_einsatz(self):
        r = E2.backtest(D, start='2017-01-01', ende='2018-12-31')
        for q in r['trades']:
            self.assertAlmostEqual(q['risiko'] / q['E_ein'], 0.0085, places=9)


class Kalender(unittest.TestCase):
    k = E2.Kalender(D.index)

    def test_karfreitag_monatsverfall(self):
        # 3. Freitag April 2014 = Karfreitag 18.04.2014 (kein SPX-Handel) -> Donnerstag 17.04.2014
        self.assertFalse(self.k.handelstag(pd.Timestamp('2014-04-18')))
        kand = self.k.kandidaten(pd.Timestamp('2014-03-27'), 'monatlich', 14, 28)
        self.assertIn((pd.Timestamp('2014-04-17'), 'AM'), kand)

    def test_synthetisch_feiertag(self):
        r = E2.backtest(D, start='2014-03-20', ende='2014-04-30', verfaelle='synthetisch')
        for q in r['trades']:
            self.assertTrue(self.k.handelstag(q['verfall']))
            self.assertLessEqual(q['verfall'], q['ziel'])

    def test_dienstag_2017_nicht_verfuegbar(self):
        kand = self.k.kandidaten(pd.Timestamp('2017-01-03'), 'weekly_annahme', 14, 28)
        self.assertNotIn(pd.Timestamp('2017-01-24'), [v for v, _ in kand])
        self.assertTrue(all(v.weekday() in (0, 2, 4) for v, _ in kand))

    def test_dienstag_2022_verfuegbar(self):
        kand = self.k.kandidaten(pd.Timestamp('2022-06-01'), 'weekly_annahme', 14, 28)
        self.assertIn(1, [v.weekday() for v, _ in kand])

    def test_ersatzregel_naechster_zu_21(self):
        r = E2.backtest(D, start='2010-01-01', ende='2010-12-31', verfaelle='monatlich')
        for q in r['trades']:
            self.assertTrue(14 <= q['dte'] <= 28)
            self.assertEqual(q['abr'], 'AM')
            self.assertEqual(q['verfall'], self.k.vorheriger(self.k.dritter_freitag(q['verfall'].year, q['verfall'].month)))


class FehlendeWerte(unittest.TestCase):
    def test_vx_zuordnung_feiertage_2025(self):
        # Kerze mit Zeitstempel So 19.01.2025 23 Uhr UTC gehört zum Handelstag Di 21.01.2025 (Mo = Feiertag)
        self.assertAlmostEqual(D.loc['2025-01-21', 'vx'], 16.45)
        self.assertFalse(D.loc['2025-01-21', 'vx_gefuellt'])
        self.assertEqual(int(D.loc['2007':].vx_gefuellt.sum()), 1)   # nur 06.08.2008 ohne VX1-Kerze

    def test_vx_nur_aus_vergangenheit(self):
        gef = D[D.vx_gefuellt & (D.index >= '2007-01-01')]
        self.assertGreater(len(gef), 0)
        for t in gef.index:
            i = D.index.get_loc(t)
            j = i - 1
            while D.vx_gefuellt.iloc[j]:
                j -= 1
            self.assertEqual(D.vx.iloc[i], D.vx.iloc[j])

    def test_kein_blick_in_die_zukunft(self):
        d2 = D.copy()
        cut = d2.index.searchsorted(pd.Timestamp('2020-06-01'))
        rng = np.random.default_rng(3)
        cols = ['open', 'high', 'low', 'close', 'vx', 'vx_high']
        d2.iloc[cut:, [d2.columns.get_loc(x) for x in cols]] *= rng.uniform(0.7, 1.3, size=(len(d2) - cut, len(cols)))
        a = E2.backtest(D, start='2019-01-01', ende='2021-12-31', verfaelle='weekly_annahme')['tage']
        b = E2.backtest(d2, start='2019-01-01', ende='2021-12-31', verfaelle='weekly_annahme')['tage']
        k = (a.index < '2020-06-01').sum()
        # Stresswert am Schnitttag hängt nur vom Schnitttag selbst ab; Kontowerte davor müssen identisch sein
        np.testing.assert_allclose(a.kontowert.values[:k], b.kontowert.values[:k], atol=1e-6)


class DeltaSuche(unittest.TestCase):
    def test_delta_genau(self):
        m = E2.Modell(E2.STANDARD)
        for vx in (10, 20, 39.6):
            K, ok = m.strike_fuer_delta(3000, 21 / 365, vx, 0.8)
            self.assertTrue(ok)
            self.assertAlmostEqual(m.put_delta(3000, K, 21 / 365, vx), -0.8, places=6)

    def test_nicht_gefunden_wird_erkannt(self):
        K, ok = E2.Modell(E2.STANDARD).strike_fuer_delta(3000, 21 / 365, 80, 0.8)
        self.assertFalse(ok)


class GanzeKontrakte(unittest.TestCase):
    def test_abrunden_und_auslassen(self):
        r = E2.backtest(D, start='2007-01-01', ende='2016-12-31', ganze=True, raster=5.0)
        k = r['kennzahlen']
        for q in r['trades'] + r['offen']:
            self.assertEqual(q['n'], int(q['n']))
            self.assertLessEqual(q['risiko'], 0.0085 * q['E_ein'] + 1e-6)
        self.assertGreater(k['tage_konto_zu_klein'], 0)

    def test_raster(self):
        r = E2.backtest(D, start='2017-01-01', ende='2017-06-30', raster=5.0)
        for q in r['trades']:
            self.assertAlmostEqual(q['K1'] % 5, 0, places=9)
            self.assertAlmostEqual(q['w'] % 5, 0, places=9)


class XSP(unittest.TestCase):
    def test_xsp_filter_und_trades(self):
        a = E2.backtest(D, start='2017-01-01', ende='2017-12-31', raster=5.0)
        b = E2.backtest(D, start='2017-01-01', ende='2017-12-31', produkt='XSP', skala=0.1, raster=1.0)
        self.assertGreater(b['kennzahlen']['trades'], 0)
        self.assertEqual(a['kennzahlen']['tage_filter_aus'], b['kennzahlen']['tage_filter_aus'])

    def test_spx_kontrakt_zu_gross_2017(self):
        r = E2.backtest(D, start='2017-01-01', ende='2017-12-31', raster=5.0, ganze=True)
        self.assertEqual(r['kennzahlen']['trades'], 0)
        self.assertGreater(r['kennzahlen']['tage_konto_zu_klein'], 0)


class ZyklusATM(unittest.TestCase):
    k = E2.Kalender(D.index)
    T = staticmethod(pd.Timestamp)

    def test_woche_normal(self):
        for tag in ('2017-01-09', '2017-01-10', '2017-01-11', '2017-01-12'):
            self.assertEqual(self.k.zyklus_verfall(self.T(tag), 'woche'), (self.T('2017-01-13'), 'PM'))
        self.assertIsNone(self.k.zyklus_verfall(self.T('2017-01-13'), 'woche'))

    def test_woche_dritter_freitag_am(self):
        self.assertEqual(self.k.zyklus_verfall(self.T('2017-01-17'), 'woche'), (self.T('2017-01-20'), 'AM'))

    def test_woche_karfreitag(self):
        self.assertEqual(self.k.zyklus_verfall(self.T('2014-04-16'), 'woche'), (self.T('2014-04-17'), 'AM'))
        self.assertIsNone(self.k.zyklus_verfall(self.T('2014-04-17'), 'woche'))

    def test_monat(self):
        for tag in ('2017-01-23', '2017-01-26'):
            self.assertEqual(self.k.zyklus_verfall(self.T(tag), 'monat'), (self.T('2017-02-17'), 'AM'))
        self.assertIsNone(self.k.zyklus_verfall(self.T('2017-01-30'), 'monat'))
        self.assertIsNone(self.k.zyklus_verfall(self.T('2017-01-17'), 'monat'))

    def test_atm_strikes_und_breite(self):
        r = E2.backtest(D, start='2017-01-01', ende='2017-03-31', zyklus='woche', strike_modus='atm', breite_fest=10, ganze=True)
        self.assertGreater(len(r['trades']), 0)
        for q in r['trades']:
            self.assertEqual(q['K1'], round(q['S_ein'] / 5) * 5)
            self.assertEqual(q['K1'] - q['K2'], 10)
            self.assertLess(q['ein_datum'], q['verfall'])
            self.assertTrue(q['ein_datum'].weekday() <= 3)
            self.assertEqual(q['n'], int(q['n']))


class Bewertung(unittest.TestCase):
    def test_verfall_innerer_wert_und_grenzen(self):
        m = E2.Modell(E2.STANDARD)
        self.assertEqual(m.put(3000, 3100, 0.0, 20), 100.0)
        for T in (1 / 365, 7 / 365, 21 / 365):
            for vx in (10, 20, 40):
                v = m.put(3000, 3120, T, vx) - m.put(3000, 3010, T, vx)
                self.assertTrue(0 <= v <= 110 * math.exp(-0.04 * T) + 1e-9)

    def test_offene_positionen_bewertung_konsistent(self):
        r = E2.backtest(D, start='2017-01-01', ende='2017-02-28')
        tl = r['tage']
        np.testing.assert_allclose(tl.kontowert, tl.cash - tl.verbindlichkeit, atol=1e-6)


if __name__ == '__main__':
    unittest.main()
