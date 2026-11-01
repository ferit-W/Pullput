# Zwischenstände – Verbesserung der Basisvariante (21 T, Delta 0,8, 100 Pkt, max. 3, EMA 100, 1,10 %)

## Schritt 0 – Ausgangslage (01.11.2026)
- Repository war leer; früherer Engine-Code und STAND.md fehlen. Engine neu aufgebaut (`engine.py`).
- Regeln aus ERGEBNIS_vorher.md übernommen. Kosten immer: 0,25 Pkt Abschlag + 3,60 USD je Spread. Zins 4 %.
- Unbekannte Modelldetails als Parameter: IV = 0,766 × VX1 × (1 − skew·ln(K/S)), Breite = 100 × S / breite_ref.

## Schritt 1 – Kalibrierung nur auf Hälfte 1 (`kalibrierung.py`, `ergebnisse/kalibrierung_h1.json`)
- Ziel: Basisvariante H1 = 12,3 % / 18,1 %. Bestes Paar: breite_ref = 2.750, skew = −5,5 → 12,25 % / 17,86 %, 40,8 Trades/J (alt 40,5).
- Achtung: negativer Skew (Vol steigt über Spot) ist marktunüblich. Die Rekonstruktion bildet die alten Zahlen nach,
  nicht zwingend reale Optionspreise.

## Schritt 2 – Validierung der Rekonstruktion an der Basisvariante (einmalig, keine Auswahl)
- H1: 12,25 % / 17,86 % (alt 12,3 / 18,1). H2: 20,23 % / 24,21 % (alt 18,8 / 22,8), DD-Tief 19.01.2023 wie alt.
- Engine ist in H2 ~1,4 Pkt strenger beim Drawdown -> vorsichtige Seite. Ab jetzt keine H2-Auswertung bis zur Festschreibung.

## Schritt 3 – Auswahlregel (festgeschrieben vor Sicht auf Raster-Ergebnisse)
1. Struktur: höchstes Rendite/Drawdown-Verhältnis (MAR) auf H1 bei konstantem Gesamtrisiko 3,3 %.
2. Plateau-Pflicht: Median-MAR der direkten Rasternachbarn (ein Parameter, ein Schritt) >= 85 % des eigenen MAR.
3. Einsatz: größter Wert (Schritt 0,05 %), bei dem H1-Drawdown <= 15,0 % bleibt (5 Pkt Puffer, weil der Drawdown
   außerhalb der Auswahlperiode erfahrungsgemäß steigt – Punkt 2 der alten Auswertung).
4. Pflicht bei diesem Einsatz: H1-Rendite >= 12,5 %; in beiden H1-Teilen (2007–2011, 2012–2016) Drawdown < 17 %.
5. Unter allen Kandidaten, die 2–4 erfüllen: höchste H1-Rendite. H2 wird danach genau einmal gerechnet.

## Schritt 4 – Runde 1 Strukturraster H1 (`suche_h1.py`, `ergebnisse/runde1_h1.json`, 3.840 Varianten)
- Spitze nach MAR: 14 Tage, Delta 0,6, breite Spreads, 6 Positionen – aber MAR wird vom 4-%-Zins verzerrt
  (5 % Rendite bei 1 % DD). Korrektur der Regel (nur H1 betroffen, H2 weiter unberührt): zusätzlich Rangliste nach
  (Rendite − 4 %)/DD; die Top 40 beider Listen gehen ins Einsatz-Tuning (Regelpunkte 2–5 unverändert).

## Schritt 5 – Runde 2 Ergebnis verworfen (Modellartefakt)
- Einsatz-Tuning der Top-76 (`ergebnisse/runde2_auswahl_h1.json`): Spitze 21 T / Delta 0,6 / 50 Pkt / EMA 200 mit
  31,4 % bei 14,9 % DD auf H1. Alle Spitzen am Rasterrand Delta 0,6.
- Skew-Probe H1 (Basis vs. Spitze): skew −5,5: 12,3/17,9 vs. 31,4/14,9; skew 0: 9,7/14,6 vs. 15,1/16,4;
  skew +3: 6,6/14,6 vs. 9,0/18,2. Der Vorsprung kommt aus dem marktunüblichen negativen Skew (Long-Put billig).
- Konsequenz: Delta, Breite, Laufzeit bleiben auf dem Kalibrierungspunkt (0,8 / 100 / 21). Gesucht wird nur über
  modellneutrale Portfolio-/Timing-Hebel. Regelpunkte 2–5 aus Schritt 3 gelten weiter.
