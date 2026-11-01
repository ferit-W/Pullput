# Verifikation der Engine und der Variante (max. 4, EMA 200, Einsatz 0,85 %), Stand 01.11.2026

Skript: `verifikation.py`, Ergebnisse: `ergebnisse/verifikation.json`. Keine Auswahl, nur Kontrolle.

## Abgleich mit dem Originalcode – nicht möglich
Repository (einziges zugängliches: ferit-W/Pullput, ein Branch), GitHub-Codesuche und Uploads enthalten keinen früheren
Engine-Code. Geprüft werden kann nur die neu gebaute Engine.

## Prüfungen (22 von 23 bestanden)
- A Formeln: Put-Preis = Monte-Carlo (Abw. ≤ 0,32 %), Strike-Suche trifft Delta 0,8 exakt, Delta = numerische Ableitung.
- A4 **nicht bestanden**: Bei VX1 >= ~70 findet die Strike-Suche wegen des negativen Skews kein Delta 0,8.
  Kein Trade betroffen: Einstiege nur bis VX1 39,6, K1/S zwischen 1,02 und 1,11. Siehe F1.
- B Daten: keine doppelten Tage, 15 von 4.989 VX1-Tagen vorwärts gefüllt, OHLC konsistent, VX1-Datum korrekt
  zugeordnet (Korrelation Tagesrendite SPX zu VX1-Änderung: −0,72 am selben Tag, ±1 Tag nahe 0).
- C Unabhängiger Nachrechner aus dem Trade-Protokoll: Endkapital H1 409.853,11 und H2 666.227,20 USD auf den Cent gleich;
  alle 1.153 Trades regelkonform (Strikes, 21 Tage, EMA-Filter mit Vortagswerten, Settlement zum Schluss);
  nie mehr als 4 Positionen; Einsatz im Median 0,850 %.
- D Kein Blick in die Zukunft: Daten ab 01.06.2022 zufällig verändert -> Equity bis dahin identisch. Läufe deterministisch.
- F Alle 33.266 täglichen Bewertungen (Schluss und Intraday-Stress) liegen zwischen 0 und Spreadbreite.

## Empfindlichkeiten der festen Variante (Rendite p. a. / max. Drawdown inkl. Stress)
| Annahme | H1 2007–2016 | H2 2017–2026 |
|---|---|---|
| Kostenmodell (Referenz) | 15,2 % / 14,7 % | 21,3 % / 21,0 % |
| Zins nur auf Kontowert statt auf Cash inkl. Prämien | 14,8 % / 14,9 % | 20,9 % / 21,4 % |
| Abschlag 0,75 Pkt | 12,9 % / 15,1 % | 20,2 % / 21,2 % |
| Abschlag 1,5 Pkt (Demo-Fill) | 9,9 % / 15,8 % | 18,7 % / 21,5 % |
| XSP (0,5 Pkt + 36 USD je SPX-Äquiv.) | 12,6 % / 15,2 % | 20,1 % / 21,2 % |
| Kalibrierung Nr. 2 (2.800 / −5,5) | 15,0 % / 15,1 % | 21,0 % / 21,2 % |
| Kalibrierung Nr. 3 (2.650 / −6,0) | 15,8 % / 14,2 % | 22,1 % / 20,8 % |
| Kalibrierung Nr. 4 (2.700 / −6,0) | 15,6 % / 14,4 % | 21,8 % / 21,0 % |
| Drawdown nur aus Schlusskursen | 14,7 % | 20,9 % |
| Diagnose: Einsatz 0,80 % | 14,6 % / 13,7 % | 20,3 % / 19,6 % |
| Diagnose: Einsatz 0,90 % | 15,8 % / 15,7 % | 22,3 % / 22,4 % |

Die Diagnosezeilen dienen nur der Einordnung. Einen Einsatz von 0,80 % zu wählen, weil H2 dann unter 20 % liegt, wäre eine
Auswahl auf H2.

## Befund
1. Die Engine rechnet in sich korrekt; das Ergebnis 21,0 % Drawdown in H2 ist reproduzierbar.
2. Es ist robust gegen alle geprüften Kosten-, Zins- und Kalibrierungsvarianten: 20,8–21,5 %. Keine Annahme bringt es
   unter 20 %.
3. Der Drawdown (18.11.2021 bis 24.05.2023, Jahr 2022: −17,3 %) ist echt und kein Stress-Artefakt
   (nur Schlusskurse: 20,9 %).
4. Wirtschaftlich ist die Strategie ein gehebelter Long-SPX-Spread (beide Strikes meist über dem Kurs). Die Rendite
   hängt stark an Kosten und Modellpreisen: Demo-Fill 1,5 Pkt drückt H1 auf 9,9 %.
