# Ergebnis Robustheitsprüfung (Halbzeiten-Test), Stand 01.11.2026

**Urteil: Keine Variante erfüllt alle Punkte.** Die vorab nach festen Regeln auf Hälfte 1 gewählte Variante erreicht in
Hälfte 2 zwar 18,8 % Rendite, aber 22,8 % Drawdown (Grenze < 20 %). Damit ist Punkt 4 verfehlt.

## Gewählte Variante (nur aus Hälfte 1, 2007–2016)
Einstieg an jedem Handelstag zum Schlusskurs, wenn Vortagesschluss >= EMA 100 und weniger als 3 Positionen offen;
Bull-Put-Spread mit Short-Delta 0,8 (Modellfläche), Long 100 Punkte tiefer (mit Kurs skaliert), 21 Kalendertage,
bis Verfall gehalten, kein Stop, kein Take-Profit; max. Verlust je Position 1,10 % des Kontos; Zins 4 %.

## Ergebnisse (Einsatz fest 1,10 %, Drawdown täglich inkl. Intraday-Stress)

| Kosten | Hälfte | Einsatz | Rendite p. a. | Max. Drawdown | Grenzen erfüllt |
|---|---|---|---|---|---|
| SPX, Kostenmodell (0,25 Pkt Abschlag + 3,60 USD Gebühr je Spread) | 1 (2007–2016, Auswahl) | 1,10 % | 12,3 % | 18,1 % | ja |
| SPX, Kostenmodell (0,25 Pkt Abschlag + 3,60 USD Gebühr je Spread) | 2 (2017–2026, Test) | 1,10 % | 18,8 % | **22,8 %** | **nein** |
| SPX, 0,75 Pkt Abschlag + 3,60 USD | 1 | 1,10 % | 11,5 % | 18,4 % | nein |
| SPX, 0,75 Pkt Abschlag + 3,60 USD | 2 | 1,10 % | 17,7 % | 22,7 % | nein |
| SPX, 1,5 Pkt Abschlag (Demo-Fill) + 3,60 USD | 1 | 1,10 % | 10,3 % | 19,0 % | nein |
| SPX, 1,5 Pkt Abschlag (Demo-Fill) + 3,60 USD | 2 | 1,10 % | 16,2 % | 22,8 % | nein |
| XSP, Kostenmodell (0,5 Pkt + 36 USD je SPX-Äquivalent) | 1 | 1,10 % | 11,4 % | 18,7 % | nein |
| XSP, Kostenmodell (0,5 Pkt + 36 USD je SPX-Äquivalent) | 2 | 1,10 % | 17,7 % | 23,0 % | nein |

Maßgeblich ist Zeile 2 (vorab festgelegtes Kostenmodell). Die übrigen Kostenzeilen sind Empfindlichkeiten mit denselben
festen Parametern, keine weitere Auswahl. Drawdown in Hälfte 2: Hoch 03.01.2022, Tief 19.01.2023.

## Begründung, warum keine Variante es schafft
1. Vorab-Kontrolle innerhalb Hälfte 1 (Auswahl 2007–2011, Test 2012–2016, 4.200 Varianten): nur 55 Varianten (1,3 %)
   erreichen im Test Drawdown < 20 % und Rendite > 12 %; Median-Testrendite 7,2 %; Korrelation Auswahl- zu
   Testrendite 0,25. Die nach Regel gewählte Variante hatte im Test 31,8 % Drawdown.
2. Der auf eine Periode kalibrierte Einsatz führt in der anderen Periode regelmäßig zu höherem Drawdown
   (hier 18 % -> 22,8 %). Ein niedrigerer Einsatz senkt den Drawdown, drückt aber die Rendite in Hälfte 1 unter 12 %.
3. Stopps, Take-Profit, VIX-Filter, VIX-Größe, Drawdown-Skalierung, Trend- und VIX-Ausstiege verbessern das Verhältnis
   aus Rendite und Drawdown nicht (Runden 1–7, siehe STAND.md).
4. Weiteres Iterieren gegen Hälfte 2 würde die Vorgabe "genau einmal auswerten" verletzen.
5. Alle Optionspreise sind Modellpreise; das Ergebnis hängt stark am Prämienfaktor 0,766 (Faktor 0,85 senkt die
   frühere Spitzenvariante von 14,4 % auf 9,7 %).

Offenlegung: Hälfte 2 war aus früheren Runden bereits bekannt. Die Auswahl folgte aber ausschließlich der vor der
Auswertung festgeschriebenen Regel (siehe STAND.md, Commit "Auswahl auf Hälfte 1 festgeschrieben").

Dateien: ergebnisse in endauswertung.json, Raster in sel_h1.json, sel_inner.json, innen_test_alle.json.
