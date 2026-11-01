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

## Schritt 6 – Runde 3 modellneutral (`runde3_h1.py`, `ergebnisse/runde3_*.json`), 1.500 Varianten, 53 getunt, 19 zulässig
- Gewinner nach Regel: max_pos 4, EMA 200, min_abstand 1, kein kurzer EMA, kein Risikodeckel; Einsatz 0,85 %.
  H1: 15,17 % / 14,68 % DD; Teile 2007–11: 11,0 % / 14,2 %, 2012–16: 19,8 % / 13,9 %.
- Skew-Probe H1 (Diagnose, keine Auswahl): skew 0: Basis 9,7/14,6 vs. neu 9,7/13,7; skew +3: 6,6/14,6 vs. 6,4/13,4.
  -> Drawdown-Vorteil ist modellunabhängig, der Renditevorsprung hängt am kalibrierten Modell.

## Schritt 7 – AUSWAHL FESTGESCHRIEBEN (vor H2-Auswertung)
tage 21, delta 0,8, breite 100 (Ref. 2.750), max_pos 4, ema 200, einsatz 0,85 %, Kosten 0,25 Pkt + 3,60 USD, Zins 4 %.

## Schritt 8 – Einmalige H2-Auswertung (`endauswertung.py`, `ergebnisse/endauswertung_neu.json`)
- Neu: H1 15,17 % / 14,68 %, H2 21,30 % / 21,01 % -> H2-Grenze verfehlt. Basis zum Vergleich: H2 20,23 % / 24,21 %.
- Kein Nachjustieren. Ergebnis siehe ERGEBNIS.md.

## Schritt 9 – Runde 4 (Nachfrage „weiter optimieren“), Regel festgeschrieben vor dem Lauf
- Offenlegung: H2-Ergebnis der Runde-3-Variante (21,0 % DD) ist bekannt. Jede neue H2-Auswertung ist ein zweiter Blick
  auf H2 und damit weniger beweiskräftig als der erste.
- Neue modellneutrale Hebel auf Basis der Runde-3-Struktur (21 T / 0,8 / 100): Drawdown-Bremse (Schwelle 5/8/10 %,
  Faktor 0,5/0,75), VX1-Deckel für Einstiege (25/30/35), EMA-Steigungsfilter (EMA > EMA vor 20 Tagen),
  max_pos 3/4/5, EMA 150/200.
- Regel unverändert: Einsatz so groß wie möglich bei H1-DD <= 15 %, H1-Rendite >= 12,5 %, Teil-DD < 17 %, höchste
  H1-Rendite. Zusätzlich: Ersetzt die Runde-3-Variante nur bei >= 0,3 Pkt mehr H1-Rendite, und die Median-Rendite
  der direkten Hebel-Nachbarn muss >= 90 % der eigenen sein.

## Schritt 10 – Runde 4 Ergebnis (`runde4_h1.py`, `ergebnisse/runde4_h1.json`, 336 Strukturen, 107 zulässig mit Plateau)
- Beste: VX1-Deckel 30 auf Runde-3-Struktur, 15,18 % / 14,68 % – nur +0,01 Pkt (Schwelle 0,3 Pkt) -> kein Ersatz.
- Drawdown-Bremse und EMA-Steigungsfilter senken bei auf 15 % DD normiertem Einsatz die H1-Rendite (14,3–15,0 %).
- Runde-3-Variante bleibt. Da keine neue Variante gewählt wurde, findet keine zweite H2-Auswertung statt.

## Schritt 11 – Verifikation (`verifikation.py`, `VERIFIKATION.md`, `ergebnisse/verifikation.json`)
- Originalcode nirgends auffindbar. 22/23 Prüfungen bestanden; A4 (Strike-Suche bei VX1 >= 70) ohne Auswirkung auf Trades.
- Ergebnis bestätigt: H2-Drawdown 21,0 %, Spanne über alle Kosten-/Zins-/Kalibrierungsannahmen 20,8–21,5 %.
