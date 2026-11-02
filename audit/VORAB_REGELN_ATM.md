# Vorab festgelegte Regeln: ATM-Variante mit festem Einstiegsrhythmus (02.11.2026, vor jeder Berechnung)

Auftrag: „At the money, 5 bzw. 10 Punkte Breite, XSP oder SPX, Einstieg nach dem Verfall Mo, Di, Mi, Do; alle 4
Einstiege laufen bis zum Verfall.“ Offen ist, welcher Verfall gemeint ist; beide Lesarten werden gerechnet.

## Gemeinsame Regeln
- Short-Put K1 = SPX- bzw. XSP-Schluss, gerundet auf das nächste Strike-Raster (SPX 5 Pkt, XSP 1 Pkt).
- Long-Put K2 = K1 − Breite; Breite 5 oder 10 Punkte **des jeweiligen Produkts** (XSP 5 Pkt = 50 SPX-Pkt Gegenwert).
- Einstieg zum Schlusskurs; höchstens 1 Einstieg je Handelstag, höchstens 4 offen; halten bis Verfall.
- Unverändert aus dem Regelwerk: Trendfilter Vortagesschluss ≥ EMA 200, Einsatz 0,85 % des Kontowerts inkl.
  Gebühren, Kosten 1,80 USD je Kontrakt und Seite, Abschlag SPX 0,25 Pkt / XSP 0,05 Pkt, Zins 4 % auf den Kontowert,
  Preismodell und Stress wie `engine2.STANDARD`.
- Kein Einstieg am Verfallstag selbst. Fällt ein Einstiegstag auf einen Feiertag, entfällt er (kein Nachholen).
- Hauptergebnis: ganze Kontrakte (abgerundet), Start 100.000 USD je Hälfte. Bruchteile nur als Modellreferenz.

## Lesart W (Wochenzyklus)
- Einstiegstage: Mo–Do einer Woche. Verfall: Freitag derselben Woche (PM-Weekly; ist es der 3. Freitag, der
  AM-Monatsverfall). Freitag-Feiertag: Handelstag davor; liegt dieser auf dem Einstiegstag, kein Einstieg.
- Restlaufzeiten 1–4 Tage. Annahme (nicht am Original geprüft): Freitags-Weeklys waren ab 2007 spätestens am Montag
  der Verfallswoche gelistet.

## Lesart M (Monatszyklus)
- Einstiegstage: Mo–Do der Kalenderwoche direkt nach der Woche des Monatsverfalls (3. Freitag).
- Verfall: nächster Monatsverfall (3. Freitag, AM; Feiertag: Handelstag davor). Restlaufzeit rund 3–4 Wochen.

## Auswertung
8 Varianten (W/M × SPX/XSP × 5/10), jeweils H1, H2, Gesamt. Es wird keine Variante ausgewählt oder nachjustiert.
Zusätzlich eine Abschlags-Empfindlichkeit (×2, ×4). H2 ist für diese neue Struktur noch nicht gesehen, wird aber
mitgerechnet; eine Auswahl der besten von 8 über beide Hälften wäre keine unabhängige Prüfung.

## Bekannte Modellgrenze vorab
VX1 (30-Tage-Volatilitätsniveau) als Volatilität für Optionen mit 1–4 Tagen Restlaufzeit ist eine grobe Näherung;
kurzfristige Volatilität und Wochenend-/Ereigniseffekte sind nicht abgebildet.
