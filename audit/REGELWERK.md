# Regelwerk Bull-Put-Spread SPX (max. 4, EMA 200, 0,85 %) – korrigierter Stand, exakt wie `audit/engine2.py`

Stand 01.11.2026. Standardkonfiguration = `engine2.STANDARD` (V-M, SPX, 5-Punkte-Raster). Modellsimulation ohne
Marktpreisvalidierung. Abweichende Varianten sind am Ende aufgeführt.

## 1. Handelsregeln (unverändert gegenüber dem Ausgangsstand)
| Regel | Wert |
|---|---|
| Instrument | SPX-Indexoptionen, europäisch, bar abgerechnet, Multiplikator 100 |
| Position | Bull-Put-Spread: Short-Put K1, Long-Put K2 < K1 |
| Short-Put | Put-Delta −0,80 im Modell |
| Breite | 100 × SPX / 2.750 Punkte |
| Ziellaufzeit | 21 Kalendertage |
| Trendfilter | SPX-Schluss Vortag ≥ EMA 200 des Vortags (α = 2/201, Start = erster Schluss 1980) |
| Positionen | höchstens 4 offen, höchstens 1 Einstieg je Handelstag |
| Einsatz | maximaler Verlust inkl. Einstiegsgebühren = 0,85 % des Kontowerts vor dem Einstieg |
| Ausstieg | Halten bis Verfall; kein Stop, kein Take-Profit, kein vorzeitiger Ausstieg |

## 2. Verfallswahl (Modellkorrektur, vorab festgelegt)
1. Verfügbare Verfälle (V-M): Standard-Monatsverfall am 3. Freitag; ist er kein Handelstag, der Handelstag davor.
   Abrechnung AM zum Eröffnungskurs des Verfallstags (Näherung für den SOQ).
2. Wahl: Verfall mit 14 bis 28 Kalendertagen Restlaufzeit, der am nächsten an 21 Tagen liegt; bei Gleichstand der
   frühere. Gibt es keinen, wird an diesem Tag nicht eröffnet.
3. Restlaufzeit für die Bepreisung ab Schluss (16:00 ET): AM (Kalendertage − 6,5/24) / 365, PM Kalendertage / 365.

## 3. Strikes und Preise
- Volatilität: σ(K) = max(0,05; 0,766 × VX1/100 × (1 + 5,5 × ln(K/S))). VX1 = Schluss des VIX-Futures am Einstiegstag.
- Preis: Black-Scholes-Put mit r = 4 %, Dividendenrendite q = 0, σ = σ(K) des jeweiligen Strikes.
- K1: Bisektion über ln(K/S) ∈ [−1; 1], 60 Schritte, bis Put-Delta e^(−qT)·(N(d1) − 1) = −0,80. Weicht das Delta
  danach um mehr als 0,0001 ab, wird nicht eröffnet. K1 wird auf das nächste Vielfache von 5 gerundet.
- Breite w = max(5; 100 × S / 2.750 auf ein Vielfaches von 5 gerundet). K2 = K1 − w.
- Kredit = P(K1) − P(K2) − 0,25 Punkte. Max. Verlust je Spread = w − Kredit. Kredit ≤ 0 oder max. Verlust ≤ 0:
  kein Einstieg.

## 4. Positionsgröße
- Risiko je Spread R = (w − Kredit) × 100 + 2 × 1,80 USD.
- Anzahl n = 0,0085 × E / R mit E = Cash − Modellwert aller offenen Spreads zum Schluss, nach den Abrechnungen des Tages.
- Modellrechnung mit Bruchteilen. Für echte Ausführung: n abrunden; ist n = 0, entfällt der Trade.
- Das offene Maximalrisiko ist nicht auf 3,4 % begrenzt: Es bezieht sich auf den Kontowert zum jeweiligen Einstieg und
  erreichte im Test 3,53 % des aktuellen Kontowerts. Der Drawdown über mehrere Verlustserien hat keine Obergrenze.

## 5. Tagesablauf (Reihenfolge im Code)
1. Cashzins: Kontowert des Vortags × (1,04^(Kalendertage/365) − 1).
2. AM-Abrechnung zur Eröffnung: Zahlung n × 100 × (max(K1 − O, 0) − max(K2 − O, 0)), O = SPX-Eröffnung.
3. Stresswert (Tagesdaten-Szenario): schlechtester Kontowert aus (Tagestief, VX1-Schluss), (Tagestief, VX1-Hoch),
   (Schluss, VX1-Hoch); heute verfallende PM-Positionen mit innerem Wert.
4. PM-Abrechnung zum Schluss (nur in Varianten mit PM-Verfällen).
5. Kontowert E zum Schluss bewerten.
6. Einstiegsregeln prüfen und gegebenenfalls eröffnen: Cash += n × (Kredit × 100 − 3,60).
7. Kontowert neu bewerten; Höchststand und Drawdown fortschreiben.

## 6. Kosten, Zins, Messung
- Gebühr 1,80 USD je Kontrakt und Seite beim Einstieg (3,60 USD je Spread), Abrechnung kostenlos; Abschlag 0,25 Pkt.
  Beides Szenarioannahmen ohne dokumentierte Broker-Grundlage.
- Cashzins 4 % p. a. nur auf den Kontowert (nicht auf vereinnahmte Prämien). Historische Zinsen lagen nicht vor.
- Drawdown = 1 − min(Kontowert, Stresswert) / bisheriger Höchststand des Kontowerts zum Schluss. Kein beobachteter
  Intraday-Wert.
- Rendite p. a. = (Endwert / Startwert)^(365,25 / Kalendertage) − 1; offene Spreads mit Modellwert.

## 7. Daten
- SPX-Tageskerzen; Handelstage = Tage mit SPX-Kurs.
- VX1: Handelstag = erster SPX-Handelstag am oder nach (Zeitstempel UTC + 3 h). Fehlende Werte werden nur aus der
  Vergangenheit fortgeschrieben (ab 2007: 1 Tag).

## 8. Varianten im Code
| Schalter | Wirkung |
|---|---|
| `verfaelle='weekly_annahme'` (V-W) | zusätzlich PM-Weeklys ab Listing-Beginn Fr (2005), Mi 23.02.2016, Mo 15.08.2016, Di 18.04.2022, Do 11.05.2022; ungeprüfte Annahme: ≥ 28 Tage vorher handelbar; Mo–Do-Feiertage ohne Verfall |
| `verfaelle='synthetisch'` | Ausgangsstand: Einstieg + 21 Tage, PM, bei Nicht-Handelstag der Tag davor |
| `ganze=True` | ganze Kontrakte, abgerundet, Auslassen bei n = 0 |
| `produkt='XSP', skala=0.1, raster=1.0` | XSP: Basis SPX/10, 1-Punkt-Raster (XSP-Verfügbarkeit und -Kosten ungeprüft) |
| `LEGACY` + `lade_daten('alt')` | bildet `engine.py` exakt nach (bis auf den behobenen Datenende-Fehler) |

## 9. Ergebnisse (Start je Hälfte 100.000 USD; Rendite p. a. / max. Drawdown im Stressszenario)
| Variante | H1 2007–2016 | H2 2017–2026 |
|---|---|---|
| Standard V-M, Bruchteile | 11,4 % / 19,3 % | 18,6 % / 22,6 % |
| V-W (Annahme), Bruchteile | 13,7 % / 15,2 % | 24,7 % / 21,5 % |
| SPX V-M, ganze Kontrakte | 11,5 % / 13,6 % (266 Trades) | kein Trade |
| XSP V-M, ganze Kontrakte (ungeprüft) | 10,2 % / 16,9 % | 16,0 % / 20,5 % |

H2 war vor allen diesen Rechnungen bekannt und ist kein unabhängiger Test. Details: `audit/AUDITBERICHT.md`.
