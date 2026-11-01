# Ergebnis Verbesserungsrunde, Stand 01.11.2026

**Urteil: Grenze knapp verfehlt.** Die nur auf Hälfte 1 gewählte Variante senkt den Drawdown in Hälfte 2 von 24,2 % auf
21,0 % und hebt die Rendite in beiden Hälften. Die Grenze von unter 20 % in Hälfte 2 erreicht sie nicht.

## Gewählte Variante (festgeschrieben vor der H2-Auswertung, Commit 63f0a66)
Bull-Put-Spread 21 Kalendertage, Short-Delta 0,8, Long 100 Pkt tiefer (skaliert), Einstieg zum Schluss, wenn
Vortagesschluss >= **EMA 200** und weniger als **4** Positionen offen; Einsatz **0,85 %** max. Verlust je Position;
Halten bis Verfall; Kosten 0,25 Pkt + 3,60 USD je Spread; Zins 4 %.

| Variante | Hälfte | Einsatz | Rendite p. a. | Max. Drawdown | Trades/Jahr | Grenzen erfüllt |
|---|---|---|---|---|---|---|
| Basis (max 3, EMA 100) | 1 (2007–2016) | 1,10 % | 12,3 % | 17,9 % | 40,8 | ja |
| Basis (max 3, EMA 100) | 2 (2017–2026) | 1,10 % | 20,2 % | 24,2 % | 45,3 | nein |
| **Neu (max 4, EMA 200)** | 1 (2007–2016, Auswahl) | 0,85 % | **15,2 %** | **14,7 %** | 55,1 | ja |
| **Neu (max 4, EMA 200)** | 2 (2017–2026, Test) | 0,85 % | **21,3 %** | **21,0 %** | 61,4 | **nein** |

Drawdown neu H2: Hoch 18.11.2021, Tief 24.05.2023.

## Wichtige Einschränkungen
1. Der frühere Engine-Code war nicht im Repository. Die Engine ist neu gebaut; Skew (−5,5) und Breiten-Referenz (2.750)
   wurden nur auf Hälfte 1 an die alten Basiszahlen kalibriert. Die Basis in H2 fällt hier strenger aus als früher
   (24,2 % statt 22,8 %), deshalb sind die Zahlen nicht 1:1 mit der alten Auswertung vergleichbar.
2. Der kalibrierte negative Skew ist marktunüblich. Hebel, die die Strikes verschieben (Delta, Breite, Laufzeit),
   ernten ein Modellartefakt (Runde 2: 31 % Rendite) und wurden deshalb ausgeschlossen.
3. Bei Skew 0 oder +3 hat die neue Variante dieselbe Rendite wie die Basis, aber rund 1 Pkt weniger Drawdown.
   Der Renditevorsprung hängt also am Modell, der Drawdown-Vorteil nicht.
4. Weiteres Iterieren gegen Hälfte 2 würde die Vorgabe verletzen; es wurde nicht nachjustiert.

Runde 4 (Drawdown-Bremse, VX1-Deckel, EMA-Steigung) brachte auf H1 keine Verbesserung >= 0,3 Pkt; Variante bleibt.

Verlauf: STAND.md. Daten: ergebnisse/*.json.
