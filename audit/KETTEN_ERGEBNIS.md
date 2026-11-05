# Marktpreis-Prüfung der ATM-Monatsstrategie mit SPXW-Ketten (05.11.2026)

Daten: `daten/ketten/kette_20261029/30/1102/1104/1105.csv` (85.128 Zeilen, nur SPXW, `datentyp` 3, 29.10.–05.11.2026, 5 Handelstage).
Skripte: `audit/ketten_analyse.py`, `audit/ketten_backtest.py`. Ergebnisse: `audit/ergebnisse/ketten_*`.
Kriterium „marktkonsistent“ (Mid-Prämie / Breite 0,34–0,40) wurde vor der Berechnung committet (Commit 9ac7e43).

## Was die Ketten zeigen (82 ATM-Put-Spreads, Short am Kurs, Long 10 Punkte tiefer, 21–32 Tage Restlaufzeit)
- Echter Mid-Credit im Mittel 3,67 Punkte (0,367 der Breite); natürlicher Preis (Short zum Bid, Long zum Ask) 3,01 Punkte.
- Halbspanne des Spreads im Mittel 0,66 Punkte (P10–P90: 0,45–0,89). Der angenommene Abschlag 0,25 liegt in allen 82 Fällen
  innerhalb der beobachteten Spanne (Fill zwischen Mid und natürlichem Preis nötig, nicht belegt).
- Modellcredit gegen echten Mid: altes Modell (0,766; Skew +5,5) +1,79 Punkte zu hoch; ChatGPT-Referenz (1,0; Skew 0) +1,12 zu hoch;
  Modell mit Skew −3: +0,56 zu hoch. Credit aus den TWS-Volatilitäten trifft den Mid auf 0,04 Punkte (Datenquelle in sich stimmig).
- Marktskew lokal am Spread: −7,4 (Form 1 + s·ln(K/S), P10–P90 −7,9 bis −6,6), d. h. der untere Strike hat die höhere Volatilität.
- ATM-IV / VIX = 0,79; ATM-IV / VX1 = 0,72 (nur 2 Tage, VX1 lag 11 % über VIX).
- Put-Mids im Strike nicht monoton: 115 von 45.017 Paaren (0,26 %).

## Sensitivität der Backtest-Rendite (M-SPX-10, ganze Kontrakte, 2007–30.10.2026)
Alle 30 Kombinationen: `ergebnisse/ketten_backtest_sensitivitaet.csv`. Reproduktion der ChatGPT-Referenz: Faktor 1,0, Skew 0, Abschlag 0,25 → 10,0 % / 10,1 % DD.
Marktkonsistente Kombinationen (Mid/Breite 0,34–0,40): 2,7 % bis 5,1 % Rendite p. a. inklusive 4 % Cashzins, Drawdown 7,6–10,1 %,
Gewinn je Spread −0,31 bis +0,31 Punkte (bei rund 3,7 Punkten Credit). Abschlag 0,25: 3,9–5,1 %; Abschlag 0,66: 2,7–3,5 %.

## Grenzen
- 5 Handelstage, ein Marktumfeld (SPX nahe Hoch, VIX 16–24); die Skew-Steigung und Prämienquote anderer Jahre (2008, 2020, 2022) sind nicht belegt.
- SPXW-PM-Kontrakte, nicht die SPX-AM-Monatsserie der Strategie. Die Ketten enthalten keine Klasse SPX.
- `datentyp` 3 (nach IB-Konvention verzögerte Kurse); Verzögerung gegenüber dem SPX-Wert nicht prüfbar.
- Auszahlungen sind echte SPX-Kurse, aber AM-Abrechnung mit Eröffnungskurs genähert (kein SOQ).
