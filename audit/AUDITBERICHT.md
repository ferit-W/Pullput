# Auditbericht Bull-Put-Spread SPX (max. 4, EMA 200, 0,85 %), Stand 01.11.2026

**Ergebnis:** Die bisherigen Zahlen beruhen zu 95 % auf Optionsverfällen, die es am Einstiegstag nicht gab. Mit
belegbar verfügbaren Monatsverfällen (V-M) erreicht die unveränderte Strategie im Modell 11,4 % / 19,3 % Drawdown
(H1) und 18,6 % / 22,6 % (H2). Mit 100.000 USD und echten SPX-Kontrakten ist sie ab 2017 nicht handelbar. Alle
Zahlen bleiben Modellsimulation: Es lagen keine historischen Optionskurse vor.

## 1. Ausgangsstand und Reproduktion
- Gesicherter Stand: Commit `160d408` (lokaler Tag `audit-ausgangsstand`, Push von Tags vom Server abgelehnt),
  SHA-256-Prüfsummen aller Dateien in `audit/pruefsummen_ausgangsstand.txt`.
- Reproduktion: `endauswertung.py` liefert bitgenau 15,17 % / 14,68 % (H1) und 21,30 % / 21,01 % (H2).
- Die neue Engine (`audit/engine2.py`) im Legacy-Modus trifft H1 auf den Cent (409.853,11 USD) und H2 bis zum
  vorletzten Tag exakt. Die Abweichung am letzten Tag ist Fehler F1.
- Kontrolltrade 03.01.2017: Mit VX1 = 13,79 liefert die Engine exakt die unabhängigen Werte (K1 2.320,19,
  K2 2.238,09, Kredit 52,62, n 0,28797, +358,96 USD). Die Datei enthält VX1 = 13,785, daraus folgen die im Regelwerk
  abgedruckten Werte (2.320,17 / 2.238,06 / 52,61 / +359,21 USD). Kein Rechenfehler.

## 2. Bestätigte Fehler

| Nr. | Fehler | Art | Wirkung (H1 / H2, Rendite p. a.) |
|---|---|---|---|
| F1 | Positionen mit Verfall nach Datenende wurden am letzten Datentag zum inneren Wert abgerechnet | Implementierung | 0 / +0,09 Pkt |
| F2 | Bepreisung immer mit 21/365, auch wenn der Verfall wegen Feiertag früher lag | Modell | +0,04 / +0,18 Pkt |
| F3 | Stress ohne die am Tag verfallenden Positionen; nur Kombination Tief + VX1-Hoch | Modell/Messung | DD H2 +0,03 Pkt |
| F4 | Cashzins auch auf vereinnahmte Prämien, ohne belegte Grundlage | Annahme | −0,33 / −0,38 Pkt |
| F5 | Strikes nicht auf das SPX-Raster gerundet | Modell | −0,24 / −0,07 Pkt, DD H1 +0,5 Pkt |
| F6 | VX1-Datumszuordnung seit 2025 an 14 Tagen nach Feiertagen falsch (veralteter Vortageswert) | Daten | 0 / +0,06 Pkt |
| F7 | Synthetische Verfälle: 95 % aller Trades nutzen Verfälle, die nicht als Monatsverfall existierten; 77 % (H1) bzw. 29 % (H2) auch nicht als Weekly | Handelbarkeit | siehe Abschnitt 4 |
| F8 | Bruchteilkontrakte: bei 100.000 USD passt ab 2017 kein SPX-Spread in 0,85 % Risiko | Handelbarkeit | siehe Abschnitt 5 |
| F9 | Regelwerk: „höchstens rund 3,4 % des Kontos“ ist falsch; das offene Maximalrisiko erreicht 3,58 % des aktuellen Kontowerts, der Drawdown hat keine Obergrenze | Dokumentation | – |
| F10 | Regelwerk nennt Skew „−5,5“ und in der Formel „+5,5“ | Dokumentation | – |
| F11 | Strike-Suche findet ab VX1 ≈ 70 kein Delta 0,8; alte Engine prüfte das nicht | Implementierung | keine (Einstiege nur bis VX1 39,6) |

Wirkungen F1–F6 schrittweise und kumulativ gemessen (Stufe A in `ergebnisse/vergleich.csv`).

## 3. Widerlegte Verdachtsfälle
- **Skew-Vorzeichen falsch implementiert:** widerlegt. Code: σ = 0,766·VX1/100·(1 − skew·ln(K/S)) mit skew = −5,5,
  das ist identisch mit der Doku-Formel (1 + 5,5·ln(K/S)). Es sind zwei Vorzeichenkonventionen (F10). Die neue
  Engine verwendet nur noch die Doku-Konvention (skew = +5,5).
- **Statische Arbitrage durch positiven Skew:** im relevanten Bereich widerlegt. Prüfung über K/S 0,90–1,15,
  VX1 10–71, 1–28 Tage (3.535 Punkte): Monotonie, Konvexität und Preisschranken überall eingehalten; nur bei
  VX1 71 und 28 Tagen ist die Put-Steigung größer als e^(−rT) (10 Punkte) – außerhalb aller Einstiege
  (`ergebnisse/preisflaeche.json`).
- **Blick in die Zukunft über Filter oder Datenlücken:** widerlegt. Filter nutzt nur Vortageswerte; Lücken werden nur
  vorwärts gefüllt; Test mit zufällig veränderten Zukunftsdaten lässt die Kontokurve davor unverändert.
- **Doppelte Verbuchung von Gebühren/Abschlag:** widerlegt. Gebühr einmal in Positionsgröße und Gutschrift, Abschlag
  einmal im Kredit; Bewertung offener Positionen ohne Abschlag (Tests `Gebuehren`).
- **Höhere Volatilität verschlechtert den Spread immer:** widerlegt. Bei VX1 10–20 senkt +1 VX1-Punkt den Wert des
  typischen Spreads (Vorteil Verkäufer), erst ab etwa VX1 25–30 erhöht er ihn. Deshalb nimmt der neue Stress das
  Schlechteste aus drei Kombinationen.

## 4. Handelbarkeit der Verfälle
Cboe-Primärquellen waren in dieser Sitzung gesperrt (Netzwerk). Einführungsdaten stammen aus Suchzusammenfassungen
(`VORAB_REGELN.md`). Regeln, Ersatzregel (14–28 Tage, nächster zu 21) und Varianten wurden **vor** der Berechnung
festgelegt und committet (Commit `478e6ad`).

| Zeitraum | Trades Original | ohne verfügbaren Verfall (V-W) | ohne verfügbaren Verfall (V-M) | 3. Freitag als PM statt AM gerechnet |
|---|---|---|---|---|
| H1 2007–2016 | 550 | 422 (76,7 %) | 523 (95,1 %) | 27 |
| H2 2017–2026 | 603 | 174 (28,9 %) | 574 (95,2 %) | 29 |

V-W betroffene Wochentage H1: Di 182, Do 114, Mi 78, Mo 48; H2: Di 114, Do 60. Der Beispieltrade 03.01.2017 →
Dienstag 24.01.2017 war nicht verfügbar (Dienstag-Weeklys erst ab April 2022).

## 5. Gegenüberstellung (Strategie unverändert, Kostenmodell, Start 100.000 USD je Hälfte)

| Stand | H1 Rendite / DD | H2 Rendite / DD | Trades H1 / H2 |
|---|---|---|---|
| A0 Ausgangsstand (engine.py) | 15,2 % / 14,7 % | 21,3 % / 21,0 % | 550 / 603 |
| A6 Modell korrigiert, Verfälle weiter synthetisch | 14,6 % / 15,4 % | 21,2 % / 21,4 % | 550 / 603 |
| B1 V-W: Weeklys ab Einführung (ungeprüfte Listing-Annahme) | 13,7 % / 15,2 % | 24,7 % / 21,5 % | 537 / 601 |
| **B2 V-M: nur Monatsverfälle (belegbar verfügbar)** | **11,4 % / 19,3 %** | **18,6 % / 22,6 %** | 379 / 413 |
| C1 SPX ganze Kontrakte, V-W | 12,9 % / 12,9 % | kein Trade (4,0 % Zins) | 367 / 0 |
| C2 SPX ganze Kontrakte, V-M | 11,5 % / 13,6 % | kein Trade (4,0 % Zins) | 266 / 0 |
| C3 XSP ganze Kontrakte, V-W (XSP-Verfälle ungeprüft) | 11,1 % / 14,8 % | 21,1 % / 20,0 % | 537 / 601 |
| C4 XSP ganze Kontrakte, V-M (XSP-Verfälle ungeprüft) | 10,2 % / 16,9 % | 16,0 % / 20,5 % | 379 / 413 |

DD = maximaler Drawdown im Tagesdaten-Stressszenario (kein beobachteter Intraday-Wert). Weitere Kennzahlen
(Trefferquote, Ø Gewinn/Verlust, Kosten, Zins, ausgelassene Tage, gebundenes Risiko) in `ergebnisse/vergleich.csv`.

Kennzahlen B2 (H1 / H2): Trefferquote 43,5 % / 49,9 %; Ø Gewinn 2.569 / 4.076 USD; Ø Verlust −1.381 / −2.464 USD;
Kosten 11.840 / 7.983 USD; Cashzins 71.204 / 115.434 USD; 190 / 217 Tage ohne passenden Verfall; offenes
Maximalrisiko höchstens 3,52 % / 3,53 % des aktuellen Kontowerts.

**Ganze Kontrakte:** Ein SPX-Spread riskierte über alle B2-Trades 495–2.799 USD in H1 (Median 1.630) und
1.012–7.596 USD in H2 (Median 3.579). Für 0,85 % braucht ein Median-Spread in H2 rund 421.000 USD Kontowert. C1/C2: in H1 wegen zu kleinen Kontos an 654 bzw. 351 Tagen ausgelassen, in H2 an allen Tagen mit erfülltem
Filter; tatsächliches Risiko je Einstieg in H1 0,43–0,85 % (C1) bzw. 0,44–0,85 % (C2), Median 0,74 % bzw. 0,73 %. XSP (Basis SPX/10, 1-Punkt-Raster):
Risiko je Einstieg 0,57–0,85 %, kein Trade ausgelassen. XSP-Verfügbarkeit vor 2022, XSP-Strikeraster und XSP-Kosten
sind nicht geprüft; XSP-Ergebnisse sind daher nur rechnerisch.

## 6. Empfindlichkeiten (Szenarioannahmen, Handelsregeln unverändert; Rendite / DD)

| Szenario | B1 H1 | B1 H2 | B2 H1 | B2 H2 |
|---|---|---|---|---|
| Referenz | 13,7 / 15,2 | 24,7 / 21,5 | 11,4 / 19,3 | 18,6 / 22,6 |
| ohne Cashzins (reines Optionsergebnis) | 9,3 / 18,9 | 19,9 / 26,1 | 7,1 / 26,5 | 14,1 / 28,1 |
| Zins 0 % (Cash und Bepreisung) | 16,0 / 18,3 | 29,7 / 23,5 | 13,2 / 21,2 | 21,2 / 25,2 |
| Zins 2 % (Cash und Bepreisung) | 15,1 / 15,6 | 27,3 / 22,6 | 12,4 / 19,7 | 19,8 / 24,2 |
| Dividende 2 % p. a. | 17,0 / 14,1 | 29,3 / 20,3 | 14,2 / 18,0 | 21,7 / 21,7 |
| Abschlag 0,5 Pkt | 12,6 / 15,3 | 24,1 / 21,6 | 10,6 / 19,5 | 18,2 / 22,7 |
| Abschlag 1,0 Pkt | 10,7 / 16,6 | 22,9 / 21,8 | 9,2 / 20,0 | 17,4 / 22,8 |
| Abschlag 1,5 Pkt | 8,9 / 18,1 | 21,8 / 22,0 | 7,9 / 20,4 | 16,6 / 22,9 |
| Gebühren verdoppelt | 13,5 / 15,2 | 24,6 / 21,5 | 11,3 / 19,3 | 18,6 / 22,7 |
| Gebühr auch bei Abrechnung | 13,6 / 15,3 | 24,6 / 21,5 | 11,4 / 19,3 | 18,6 / 22,7 |
| VX1 vom Vortag für Einstieg | 13,6 / 15,4 | 24,3 / 21,5 | 10,8 / 19,3 | 18,7 / 22,4 |
| Skew 0 (flach) | 9,6 / 13,5 | 17,1 / 19,7 | 9,6 / 17,4 | 14,8 / 19,2 |
| Skew −3 (marktübliche Richtung) | 6,7 / 14,0 | 12,8 / 19,1 | 7,2 / 17,9 | 11,4 / 18,5 |
| Cashzins inkl. Prämien | 14,0 / 15,0 | 25,0 / 21,2 | 11,7 / 18,9 | 19,0 / 22,3 |

Die Rendite hängt stärker an Modellannahmen (Zins in der Bepreisung, Dividende, Skew) als an Kosten. Ohne Cashzins
liegt der Drawdown in allen vier Fällen über 18 %, in H2 über 26 %.

## 7. Daten und Zeitstempel
- Sommerzeit: VX1-Sessions beginnen 22 Uhr UTC (Sommer) bzw. 23 Uhr UTC (Winter), SPX-Kerzen 13:30 bzw. 14:30 UTC;
  die Zuordnung „+3 Stunden“ trifft beide Fälle. Ausnahme seit 2025: F6.
- Fehlende VX1-Werte ab 2007 nach Korrektur: 1 Tag (06.08.2008), vorwärts gefüllt.
- VX1-Rollregel: Endlosreihe ohne Rollanpassung. An 238 berechneten Rolltagen (Tag nach VX-Verfall) ist die
  ungeklärte VX1-Änderung im Mittel nicht größer als sonst (0,44 gegen 0,51 Punkte). VX1 ist ein Future auf den
  30-Tage-VIX zum Future-Verfall, keine Volatilität der gehandelten Optionslaufzeit; das bleibt eine Näherung.
- Uhrzeit des VX1-Schlusskurses gegenüber SPX 16:00 ET ist aus den Daten nicht prüfbar. Szenario „VX1 vom Vortag“
  ändert die Rendite um −0,6 bis +0,1 Pkt.
- AM-Abrechnung mit dem SPX-Eröffnungskurs genähert (echter SOQ liegt nicht vor).

## 8. Überoptimierung und Git-Historie
- Commit `63f0a66` (Festschreibung der Parameter, 17:34:03 UTC) liegt vor `ba33f4c` (erstes Hinzufügen von
  `endauswertung.py` und H2-Ergebnis, 17:34:23 UTC). Git belegt die Reihenfolge der Commits, nicht der Rechnungen.
- H2 war vor der Auswahl schon bekannt: Der Auftraggeber nannte H2-Zahlen der Basis, und Commit `59ee49a` enthält
  die H2-Validierung der Basisvariante. Runde 4 und alle Audit-Rechnungen fanden nach Sicht auf H2 statt.
- Folge: Kein H2-Ergebnis dieses Audits ist ein unabhängiger Test. In diesem Audit wurde nichts optimiert;
  Einsatz 0,85 % und alle Handelsregeln sind unverändert.

## 9. Offene Einschränkungen
1. Keine historischen SPX-Optionskurse: alle Ergebnisse sind Modellsimulation; die Kalibrierung auf alte
   Strategieergebnisse ist keine Validierung gegen Marktpreise.
2. Cboe-Primärquellen, historische Zinsen (FRED), VIX-Spot (Cboe) nicht abrufbar (Netzwerksperre der Sitzung).
3. Listing-Horizont der Weeklys vor September 2022 unbekannt; V-W beruht auf einer ungeprüften Annahme.
4. Zins 4 % und Dividende 0 % fest; beide verschieben die Ergebnisse um mehrere Punkte (Abschnitt 6).
5. Gebühren (3,60 USD je Spread) und Abschlag (0,25 Pkt) sind Szenarioannahmen ohne dokumentierte Grundlage.
6. Ausführung exakt zum Schlusskurs mit Modell-Mittelkurs minus Abschlag; keine Orderbuch- oder Fill-Daten.
