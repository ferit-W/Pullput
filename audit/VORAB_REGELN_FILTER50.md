# Vorab festgelegt: 50 Einstiegsfilter auf die ATM-Monatsstrategie (05.11.2026, vor jeder Berechnung)

Basis: M-SPX-10 (Short-Put am Kurs, Long 10 Punkte tiefer, Einstieg Mo–Do nach dem Monatsverfall, max. 4 Positionen, ganze
Kontrakte, EMA-200 und 0,85 % unverändert), 2007 bis 30.10.2026. Jeder Filter kommt **zusätzlich** zum EMA-200-Filter.
Alle Filter nutzen nur Daten bis zum Vortagesschluss (Kalenderfilter den Tag selbst). Fehlende Vorlaufwerte = nicht erlaubt.

## Preisannahmen (beide Läufe, keine Auswahl zwischen ihnen)
- **A (marktnah):** Faktor 0,766, Skew −6, Abschlag 0,25. Mid/Breite 0,363, nahe dem Wert der SPXW-Ketten (0,367).
- **B (ChatGPT-Referenz):** Faktor 1,0, Skew 0, Abschlag 0,25.

## Die 50 Filter
Trend und Momentum: T01 Schluss ≥ EMA 50 · T02 ≥ EMA 100 · T03 ≥ EMA 150 · T04 EMA 50 ≥ EMA 200 · T05 EMA 100 ≥ EMA 200 ·
T06 EMA 200 höher als vor 20 Tagen · T07 EMA 200 höher als vor 60 Tagen · T08 12-Monats-Rendite > 0 (252 Tage) · T09 6-Monats (126) > 0 ·
T10 3-Monats (63) > 0 · T11 1-Monats (21) > −3 % · T12 1-Monats > 0 · T13 Schluss ≥ SMA 50 · T14 Schluss ≥ 97 % des 20-Tage-Hochs.
Nähe zum Hoch: H01 höchstens 2 % unter dem 252-Tage-Hoch · H02 5 % · H03 10 % · H04 15 %.
Volatilität (VX1): V01 < 18 · V02 < 20 · V03 < 22 · V04 < 25 · V05 < 30 · V06 < 35 · V07 > 12 · V08 > 14 · V09 > 16 ·
V10 zwischen 15 und 25 · V11 ≤ 20-Tage-Mittel · V12 ≥ 20-Tage-Mittel · V13 5-Tage-Änderung < +15 % · V14 5-Tage-Änderung > −15 % ·
V15 realisierte 20-Tage-Vola < VX1/100 · V16 realisierte Vola < 15 % · V17 realisierte Vola < 20 %.
Kurzfristige Bewegung: P01 Vortagesrendite > −1 % · P02 Vortagesrendite > 0 · P03 5-Tage-Rendite > −2 % · P04 5-Tage-Rendite > 0 ·
P05 Schluss über dem 20-Tage-Tief.
Kalender: K01 nur Montag · K02 nur Dienstag · K03 nur Mittwoch · K04 nur Donnerstag · K05 nur Mo+Di · K06 nur Mi+Do ·
K07 nicht September/Oktober · K08 nur November bis April · K09 nicht Juni bis August · K10 nicht Januar.

## Bewertung (festgelegt)
- **Maß:** Nettogewinn je Spread in Punkten (nach Abschlag und Gebühren), nicht die Kontorendite, weil der Cashzins sie dominiert.
- **Test je Filter:** Auf der Trade-Liste der ungefilterten Strategie werden Trades, die der Filter zulässt, mit denen verglichen, die er
  streicht (Welch-t-Test auf Mittelwerten je Verfallstermin, damit gleichzeitige Einstiege nicht als unabhängig zählen).
- **Mehrfachtest:** Holm-Korrektur über alle 50 Filter bei α = 5 %. Zusätzlich wird gemeldet, wie viele Filter ohne Korrektur p < 5 % haben
  (zufällig erwartet: etwa 2,5 von 50).
- **Ein Filter gilt nur als „bestanden“,** wenn alle vier Punkte zutreffen: Holm-signifikant im Gesamtzeitraum, gleiches Vorzeichen des
  Vorteils in 2007–2016 und 2017–2026, mindestens 30 % der Trades bleiben, und beides (A und B) zeigt dasselbe.
- Jeder Filter wird zusätzlich als echter gefilterter Backtest gerechnet (Rendite, Drawdown, Trades). Es werden alle 50 Filter berichtet.
- Der gefilterte Backtest und der Trade-Vergleich dürfen leicht abweichen, weil Filter die freien Positionsplätze verschieben.
- Es wird kein Filter kombiniert oder nachjustiert. Die Liste ist mit diesem Commit abgeschlossen.
