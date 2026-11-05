# Ergebnis: 50 Einstiegsfilter auf M-SPX-10 (05.11.2026)

Regeln vor der Berechnung: `audit/VORAB_REGELN_FILTER50.md` (Commit 0e11fb9). Skript: `audit/filter50.py`. Rohdaten: `audit/ergebnisse/filter50.csv`,
`filter50_zusammenfassung.json`. Zeitraum 2007 bis 30.10.2026, 704 Trades der Basis, ca. 235 Verfallstermine.

## Ergebnis
- **Kein Filter bestanden.** Ohne Mehrfachtest-Korrektur hat keiner der 50 Filter p < 5 % (bei reinem Zufall wären etwa 2,5 zu erwarten),
  in beiden Preisannahmen. Nach Holm-Korrektur ist keiner signifikant.
- Basis Annahme A (marktnah, Mid/Breite 0,363): 5,0 % Rendite, 9,3 % Drawdown, Edge 0,30 Punkte je Spread.
- Basis Annahme B (ChatGPT-Referenz): 10,0 % Rendite, 10,1 % Drawdown, Edge 1,30 Punkte je Spread.
- Kleinster p-Wert: V08 „VX1 > 14“ (A: p = 0,097, B: 0,183) – und das in die falsche Richtung (Filter schadet).
- Beste Richtung in beiden Annahmen: V11 „VX1 ≤ 20-Tage-Mittel“ (kein Einstieg nach Vola-Anstieg): Vorteil +0,83 bzw. +0,80 Punkte je Spread,
  gleiches Vorzeichen in beiden Hälften, p = 0,14 bzw. 0,15, Holm 1,0. Das ist mit 50 Tests nicht von Zufall zu unterscheiden.

## Trennschärfe
Der Standardfehler des Unterschieds liegt bei etwa 0,55–0,95 Punkten je Spread. Nachweisbar wären damit erst Vorteile von grob 1,5 Punkten
oder mehr bei einem Credit von 3,7 Punkten. Kleinere echte Effekte kann diese Datenmenge nicht trennen: „kein Signal“ heißt nicht „sicher kein Effekt“.

## Beobachtung zu Rendite und Drawdown
Filter, die Trades streichen, senken meist die Rendite, weil das nicht investierte Geld nur 4 % Cashzins bringt, und den Drawdown. Beispiele (A):
K04 „nur Donnerstag“: 4,5 % Rendite, 1,9 % Drawdown, 25 % der Trades. Das ist keine bessere Strategie, sondern weniger Risiko bei weniger Einsatz.
