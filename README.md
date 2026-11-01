# Pullput – Bull-Put-Spread SPX, Backtest und Audit

Modellsimulation (keine historischen Optionskurse). Prüfbericht: `audit/AUDITBERICHT.md`. Regelwerk: `audit/REGELWERK.md`.

## Voraussetzungen
Python 3.10 oder neuer mit `numpy` und `pandas`:

```bash
pip install numpy pandas
```

## Start (im Repository-Hauptordner)
Tests der korrigierten Engine (21 Tests, rund 2 s):

```bash
python3 -m unittest audit/test_engine2.py -v
```

Vollständige Audit-Auswertung (rund 15 s mit 4 Kernen), schreibt nach `audit/ergebnisse/` und `audit/konfiguration.json`:

```bash
python3 audit/lauf.py
```

Prüfung der Preisfläche und der Daten:

```bash
python3 audit/pruef_preisflaeche.py
```

```bash
python3 audit/pruef_daten.py
```

Ausgangsstand (alte Engine, unverändert):

```bash
python3 endauswertung.py
```

## Einzelne Variante rechnen

```bash
python3 -c "import sys; sys.path.insert(0,'audit'); import engine2 as E; r=E.backtest(E.lade_daten(), start='2017-01-01', ende='2026-12-31'); print(r['kennzahlen'])"
```

Standard (`engine2.STANDARD`) = korrigiertes Modell mit Monatsverfällen (V-M), 5-Punkte-Raster, Bruchteilkontrakte.
Schalter: `verfaelle` ('synthetisch' | 'monatlich' | 'weekly_annahme'), `ganze=True`, `produkt='XSP', skala=0.1, raster=1.0`,
`zins_cash`, `r_preis`, `q_div`, `slip`, `fee_kontrakt_seite`, `skew`, `vx_lag`. Legacy-Modus: `engine2.LEGACY` mit
`lade_daten('alt')`.

## Ausgaben in `audit/ergebnisse/`
| Datei | Inhalt |
|---|---|
| `vergleich.csv` | Kennzahlen aller Varianten und Szenarien je Zeitraum |
| `trades_<Variante>_<Zeitraum>.csv` | Trade-Protokoll (Einstieg, Verfall, Abrechnung, Strikes, Größe, Kredit, Ergebnis) |
| `konto_taeglich_<Variante>_<Zeitraum>.csv` | täglicher Kontowert, Cash, Verbindlichkeit, Stresswert, offenes Risiko, Zins |
| `jahre_<Variante>_<Zeitraum>.csv` | Jahresrenditen |
| `betroffene_trades.json` | Trades der Originalsimulation ohne historisch verfügbaren Verfall |
| `preisflaeche.json`, `datenpruefung.json` | Arbitrage- und Datenprüfung |

## Daten
`daten/SPX_1D.csv` (SPX-Tageskerzen), `daten/VX1_1D.csv` (VIX-Future vorderer Monat, ohne Rollanpassung).
