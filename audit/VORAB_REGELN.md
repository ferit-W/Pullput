# Vorab festgelegte Regeln für das Audit (vor jeder Ergebnisberechnung, 01.11.2026)

Diese Datei wird committet, bevor eine korrigierte Variante gerechnet wird. Keine dieser Regeln wird nach der Rendite gewählt.

## 1. Verfügbarkeit der Verfälle
Primärquellen (Cboe) waren in dieser Sitzung nicht abrufbar (Netzwerksperre). Verwendete Angaben stammen aus
Suchmaschinen-Zusammenfassungen der Cboe-Pressemitteilungen und sind als **nicht am Original geprüft** gekennzeichnet.

| Verfall | Ab (Listing-Beginn) | Abrechnung | Status der Angabe |
|---|---|---|---|
| Standard-Monatsverfall, 3. Freitag | ganzer Zeitraum | AM (Eröffnung) | Branchenstandard, nicht am Original geprüft |
| SPXW Freitag | vor 2007 | PM (Schluss) | nicht am Original geprüft |
| SPXW Mittwoch | 23.02.2016 | PM | Suchzusammenfassung Cboe IR / RG16-024 |
| SPXW Montag | 15.08.2016 | PM | Suchzusammenfassung, nur eine Quelle für das Tagesdatum |
| SPXW Dienstag | 18.04.2022 | PM | Suchzusammenfassung Cboe IR |
| SPXW Donnerstag | 11.05.2022 | PM | Suchzusammenfassung Cboe IR |

Unbekannt: wie weit Weeklys vor September 2022 im Voraus gelistet waren. Daher zwei Varianten:

- **V-M (konservativ):** nur Standard-Monatsverfälle (3. Freitag, AM). Diese waren bei jedem Einstieg sicher gelistet.
- **V-W (Annahme):** Monatsverfälle + Weeklys ab ihrem Listing-Beginn, mit der **ungeprüften Annahme**, dass jeder
  Weekly-Verfall mindestens 28 Kalendertage vorher handelbar war. Auf dem 3. Freitag gilt immer der AM-Monatsverfall.
- **Synthetisch (Original):** Einstieg + 21 Kalendertage, PM, bei Nicht-Handelstag der Handelstag davor.

## 2. Ersatzregel für die Verfallswahl (V-M und V-W)
Unter den am Einstiegstag verfügbaren Verfällen mit 14 bis 28 Kalendertagen Restlaufzeit wird der Verfall mit dem
geringsten Abstand zu 21 Tagen gewählt; bei Gleichstand der frühere. Gibt es keinen, wird nicht eröffnet.
Begründung: symmetrisches Fenster um die Ziellaufzeit, keine Renditeoptimierung.

## 3. Feiertage
- Monatsverfall auf Börsenfeiertag: Verfall am Handelstag davor, AM-Abrechnung zur Eröffnung dieses Tages.
- Freitag-Weekly auf Feiertag: Handelstag davor. Mo–Do-Weekly auf Feiertag: gilt als nicht gelistet.
- Handelstage = Tage mit SPX-Kurs; nach Datenende gelten Mo–Fr als Handelstage.

## 4. Abrechnung und Laufzeit
- PM: Schlusskurs SPX des Verfallstags. AM: Eröffnungskurs SPX des Verfallstags (Näherung für den SOQ-Wert;
  der echte SOQ weicht ab und liegt nicht vor).
- Restlaufzeit für die Bepreisung = tatsächliche Zeit bis zur Abrechnung: PM (Kalendertage)/365, AM
  (Kalendertage − 6,5/24)/365, jeweils gemessen ab Schluss 16:00 ET.

## 5. Strike-Raster und Kontrakte
- SPX: Strikes auf 5 Punkte gerundet (nächster Wert); Breite auf ein Vielfaches von 5, mindestens 5.
- XSP: Basis = SPX/10, Strikes auf 1 XSP-Punkt; Multiplikator 100.
- Ganze Kontrakte: n = abgerundet; passt kein Kontrakt, wird der Trade ausgelassen und gezählt.

## 6. Stress (Tagesdaten-Szenario, kein beobachteter Intraday-Wert)
Schlechtester Wert aus drei Kombinationen: (Tagestief, VX1-Schluss), (Tagestief, VX1-Hoch), (Schluss, VX1-Hoch).
PM-Positionen mit Verfall heute werden mit ihrem inneren Wert zum Tagestief einbezogen.

## 7. Zins und Kosten
- Korrigierter Standard: Cashzins nur auf den Kontowert (ohne vereinnahmte Prämien), 4 % p. a. wie bisher, weil
  historische Zinsreihen nicht abrufbar waren. Zusätzlich wird das Ergebnis **ohne Cashzins** berichtet.
- Gebühren: 1,80 USD je Kontrakt und Seite beim Einstieg (= 3,60 USD je Spread wie bisher), Abrechnung kostenlos.
  Grundlage der 3,60 USD ist nicht dokumentiert -> Szenarioannahme. Abschlag 0,25 Pkt je Spread -> Szenarioannahme.
- Dividende 0 % im Standard (keine Daten); 2 % p. a. als Szenario.

## 8. Strategie bleibt unverändert
Delta −0,80, Breite 100 × S / 2.750, Ziellaufzeit 21 T, max. 4 Positionen, max. 1 Einstieg/Tag, Vortagesschluss ≥ EMA 200,
Einsatz 0,85 %, Halten bis Verfall. Keine Optimierung in diesem Audit.
