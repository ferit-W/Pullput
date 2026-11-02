# Rückrechnung der Ampel 2007–2026: Hat sie funktioniert?

Stand: 02.11.2026. Ampel-Logik aus Morgenroutine v6.17, unverändert nachgebildet. An der Morgenroutine selbst wurde **nichts geändert**.

**TL;DR:**

- **Die Ampel ist ein guter Risikofilter, aber keine Renditeprognose.** Hätte man den S&P 500 nur nach Ampel gehalten (GO voll, CAUTION halb, STOP gar nicht), wäre der größte Verlust seit 2007 von −56 % auf −19 % gesunken. Die Rendite hätte sich aber ungefähr halbiert (4,1 % statt 8,7 % pro Jahr). Je Risikoeinheit war das Ergebnis praktisch gleich wie bei „Kaufen und halten“.
- **Lücke 1, sie springt zu oft:** rund 40 Wechsel pro Jahr, und ein Drittel aller Phasen dauert nur einen Tag.
- **Lücke 2, sie kommt zu spät zurück:** Nach Tiefpunkten verpasste sie große Teile der Erholung. 2020 zeigte sie 5 Monate lang kein GO, obwohl der Markt schon über 40 % gestiegen war. Grund ist die feste VIX-Grenze von 20.
- **Lücke 3, der Panik-Score wirkt verkehrt herum:** Je höher die Panik, desto *besser* liefen die Folgemonate. Als Warnsignal hat er außerdem nie den Ausschlag gegeben.
- **Lücke 4, die Short-Seite:** Wenn drei oder vier Indizes in P6 standen, stieg der S&P 500 in den folgenden 20 Tagen im Schnitt trotzdem.
- **Von sechs vorab festgelegten Verbesserungen hat nur eine in beiden Zeiträumen geholfen:** Marktbreite über der EMA200 statt über der EMA50.

---

## 1. Was genau gerechnet wurde

**Nachbildung.** `ampel_rueckrechnung.py` übernimmt `computeAmpel()`, `panikComponents()`, `luedePhase()`, die VIX-Termstruktur und `tagesKonsequenz()` 1:1 aus dem Programm. Die EMAs werden wie im Programm über ein Fenster von 2 Jahren gerechnet.

**Abgleich mit deinen echten Snapshots.** Für den 07.09. und den 09.09.2026 stimmt die Rückrechnung in jedem Punkt mit deinen gespeicherten History-Einträgen überein: Ampel, Phase jedes Index, Breite, Führung und VIX. Nur der Panik-Score weicht ab, weil damals deine manuellen Werte eingetragen waren.

**Zeitraum.** 02.07.2007 bis 08.09.2026, also 4.827 Handelstage mit den Einbrüchen 2008, 2011, 2015/16, 2018, 2020, 2022 und 2025.

**Daten.** Öffentliche Abzüge auf GitHub:

- SPY, QQQ, DIA, IWM
- 11 Sektor-ETFs
- VIX, VIX3M, VVIX
- CNN Fear & Greed ab 2011
- AAII-Bären
- NAAIM
- Put/Call-Ratio bis 2019
- High-Yield-Spread der US-Notenbank FRED

Alle URLs und Prüfsummen stehen in `ergebnisse/quellen.json`. Die Daten habe ich auf Lücken und Ausreißer geprüft. Ab 2011 weicht SPY nur an einem einzigen Tag um mehr als 1 % vom S&P-500-Datensatz im Repository ab.

**Vorsichtige Annahmen.** Jedes Signal entsteht aus dem Schlusskurs eines Tages. Umgesetzt wird es erst einen Tag später. Liquidität bringt keinen Zins: Das benachteiligt die Ampel leicht, weil sie im Schnitt 39 % der Zeit nicht investiert ist.

**Was fehlt.**

- Die Terminwoche (FOMC, Arbeitsmarktdaten, Quartalszahlen) ist nicht nachgebildet.
- Gemessen wird am S&P 500, nicht an deinen Einzelaktien-Trades.
- Fear & Greed vor 2021 stammt aus einer zusammengesetzten Fremdquelle.
- Die Put/Call-Ratio fehlt ab Oktober 2019. Das Programm rechnet dann ohne sie weiter, so wie bei einem leeren Feld.

---

## 2. Ergebnisse

### Wie oft welcher Zustand, und wie lange

- **Anteil der Tage:** GO 44 %, CAUTION 33 %, STOP 22 %, REVERSE 1 %
- **Mittlere Dauer eines Zustands:** GO 9,5 Handelstage, CAUTION 4,2, STOP 6,4
- **Wechsel:** rund 40 pro Jahr. Ein Drittel aller Phasen dauert nur einen einzigen Tag.

### Was danach am Markt passierte (S&P 500, Folgetage)

**GO** (2.131 Tage)
- im Schnitt +0,34 % nach 20 Tagen, 64 % der Fälle positiv
- mittlerer Rückschlag in 20 Tagen −2,1 %, Rückschlag über 5 % in 11 % der Fälle

**CAUTION** (1.575 Tage)
- im Schnitt +0,92 % nach 20 Tagen, 68 % positiv
- mittlerer Rückschlag −2,5 %, über 5 % in 18 % der Fälle

**STOP** (1.064 Tage)
- im Schnitt +1,34 % nach 20 Tagen, 66 % positiv
- mittlerer Rückschlag −4,1 %, über 5 % in 31 % der Fälle

**REVERSE** (57 Tage in 10 Episoden)
- im Schnitt +3,6 % nach 20 Tagen und +12,7 % nach 60 Tagen
- mittlerer Rückschlag aber −6,3 %

**Einordnung:** Die Ampel erkennt **Risiko** zuverlässig. Bei STOP waren große Rückschläge fast dreimal so häufig wie bei GO. Sie sagt aber nicht die **Richtung** voraus. Nach STOP stieg der Markt im Schnitt sogar stärker als nach GO, weil auf Abverkäufe oft Erholungen folgen. Für einen Trendtrader heißt das: STOP schützt vor großen Schwankungen und Kurslücken, kostet aber Chancen.

### Die großen Einbrüche: wann reagierte die Ampel?

**2007 bis 2009** (−56,5 %)
- erstes STOP nach 23 Tagen, bei −7,2 %
- erstes GO 201 Tage nach dem Tief; bis dahin +64 % Erholung verpasst

**2015/16** (−14,4 %)
- erstes STOP nach 11 Tagen, bei −2,4 %
- erstes GO 42 Tage nach dem Tief; +13,7 % verpasst

**Februar 2018** (−10,2 %)
- erstes STOP nach 6 Tagen, bei −7,9 %; da waren 78 % des Rückgangs schon gelaufen
- erstes GO 11 Tage nach dem Tief; +4,9 % verpasst

**Herbst 2018** (−20,2 %)
- erstes STOP nach 15 Tagen, bei −7,3 %
- erstes GO 47 Tage nach dem Tief; +19,1 % verpasst

**Corona 2020** (−34,1 %)
- erstes STOP nach 3 Tagen, bei −4,7 %
- **kein GO bis zur vollen Erholung im August**

**2022** (−25,4 %)
- erstes STOP nach 13 Tagen, bei −8,3 %
- erstes GO 123 Tage nach dem Tief; +14,9 % verpasst

**Frühjahr 2025** (−19,0 %)
- erstes STOP nach 13 Tagen, bei −8,5 %
- erstes GO 28 Tage nach dem Tief; +19,8 % verpasst

**Einordnung:** Der Ausstieg kommt schnell, meist nach 3 bis 15 Handelstagen und bei 5 bis 8 % Verlust. Ein Trendsystem kann kaum früher reagieren. Der **Wiedereinstieg ist die eigentliche Schwäche**. 2020 hing die Ampel fünf Monate fest, weil der VIX über 20 blieb, obwohl Trend und Breite längst wieder positiv waren.

### Lücken

- **GO vor einem Rückschlag von mehr als 7 % in 20 Tagen:** 19 Episoden. Die meisten lagen direkt vor schnellen Schocks, etwa Ende Januar 2018, Februar 2020, Juli 2024 und Februar 2025. Das sind Ereignisse, die kein Trendsignal vorher sieht.
- **STOP vor einem Anstieg von mehr als 7 % in 20 Tagen:** 29 Episoden, typischerweise kurz nach dem Tief eines Abverkaufs, etwa März 2009, März 2020, Oktober 2022 und April 2025.

### Die einzelnen Auslöser

- **„p6 ≥ 2“, also zwei Indizes im Abwärtstrend:** der beste STOP-Auslöser. Er hat die tiefsten Rückschläge (−5,5 %) und die schwächsten Folgerenditen (+0,5 %).
- **„VIX > 28“ und „Breite < 3“:** Nach diesen Auslösern stieg der Markt im Schnitt um 1,5 bis 1,6 %. Sie zeigen Angst an, die sich oft wieder legt.
- **Panik-Score:** Er hat an keinem einzigen Tag allein STOP oder CAUTION ausgelöst. Immer war vorher schon ein anderes Signal da. Ohne ihn wäre die Ampel identisch gewesen.

### Der Panik-Score wirkt verkehrt herum

Folgerendite nach 60 Tagen je Panik-Stufe:

- ruhig (unter 20): +1,7 %
- normal: +2,8 %
- erhöht: +3,1 %
- hoch: +3,6 %
- extrem (72 und mehr): +5,4 %

Das deckt sich mit den Studien zu AAII und Fear & Greed (siehe Abschnitt 4): Extreme Angst war eher eine Einstiegschance als eine Warnung.

### Die Konsequenz-Zeile

- **„LONG normal“:** +0,34 % nach 20 Tagen
- **„KEINE neuen Positionen“:** +2,1 %
- **„SHORT normal“** (drei oder vier Indizes in P6): Der S&P 500 *stieg* danach im Schnitt um 1,3 %, in 60 % der Fälle. Für Short-Trades auf Indexebene war das kein tragfähiges Signal.
- **„SHORT reduziert“:** Hier fiel der Markt leicht (−0,2 %).

Für Short-Trades in **Einzelaktien** sagt das noch nichts. Das lässt sich erst mit deinen Journal-Daten prüfen.

---

## 3. Vorab festgelegte Verbesserungen im Test

Jede Variante habe ich vor der Auswertung festgelegt und dann getrennt in zwei Zeiträumen geprüft: 2007–2016 und 2017–2026. Als Verbesserung zählt eine Variante nur, wenn sie in **beiden** besser abschneidet. Maßstab ist die Rendite je Risiko (Sharpe-Kennzahl, ohne Zins).

Angegeben sind jeweils Sharpe 2007–2016 / Sharpe 2017–2026, der maximale Verlust und die Wechsel pro Jahr.

- **Kaufen und halten** (Vergleich): 0,30 / 0,78 · −56,5 % · 0 Wechsel
- **Ampel heute** (Ausgangspunkt): 0,24 / 0,71 · −19,3 % · 40 Wechsel
- **V1 Wechsel erst nach 2 Tagen Bestätigung:** 0,24 / 0,61 · −21,3 % · 21 Wechsel. Halbiert das Springen, kostet etwas.
- **V2 Breite über EMA200 statt EMA50:** **0,39 / 0,75** · −21,4 % · 31 Wechsel. **In beiden Zeiträumen besser.**
- **V3 zusätzlich Kreditspread-Warnung:** 0,43 / 0,68 · −19,3 % · 38 Wechsel. Nur 2007–2016 besser.
- **V4 ohne Panik-Score:** 0,24 / 0,71 · −19,3 % · 40 Wechsel. Identisch, der Score ist wirkungslos.
- **V5 VIX-Termstruktur statt fester VIX-Grenzen:** 0,22 / 0,91 · −21,8 % · 38 Wechsel. Nur 2017–2026 besser.
- **V6 Kombination V1+V2+V3:** 0,52 / 0,64 · −21,5 % · 17 Wechsel. Gemischt.
- **Einfach SPY über EMA200:** 0,18 / 0,86 · −25,9 % · 8 Wechsel. Gemischt.

Zur ehrlichen Einordnung:

- Die Unterschiede sind klein, und die Zahl unabhängiger Abwärtsphasen ist gering, gut sieben echte Einbrüche.
- Auch V2 ist deshalb ein Hinweis, kein Beweis.
- Die Tabelle misst den S&P 500, nicht deine Trades.

---

## 4. Recherche: Was es außerdem gibt

Die Suche hat überwiegend Praktiker-Analysen und Anbieterseiten gefunden, kaum begutachtete Forschung. Die Aussagen sind deshalb als Hinweise zu lesen.

- **Kreditspreads (High-Yield):** Laut einer Strategen-Notiz von Credit Suisse aus 2018 hat eine Ausweitung 8 der vorangegangenen 9 Aktienhochs angekündigt, oft mit monatelangem Vorlauf. Im Test oben half das Signal nur 2007–2016.
- **Anteil der Aktien über dem 200-Tage-Durchschnitt:** in der Praxis verbreitet. Die genannten Schwellen (50, 60 oder 70 %) sind aber nirgends sauber getestet. Die eigene Variante V2 geht in diese Richtung und hat sich bewährt.
- **VIX-Termstruktur (VIX/VIX3M):** Sie zeigt kurzfristigen Stress, aber laut Anbieter selbst nicht den Boden. Das Ende der Backwardation fiel 2020 laut einer Quelle mit dem Tief zusammen. Das ist anekdotisch.
- **AAII-Bären:** ein schwaches bis mittleres Kontrarian-Signal bei extremer Angst, für 6 bis 12 Monate. Für kurze Zeiträume ist es kaum aussagekräftig. Das passt zum Ergebnis beim Panik-Score.
- **Zweig Breadth Thrust:** ein seltenes Signal für Erholungen nach einem Tief. Die starken Erfolgsquoten stammen aus Werbetexten, eine unabhängige Auswertung nennt nur sechs Signale seit 2010.
- **Gleitender Durchschnitt nach Faber:** Monatlich unter den 10-Monats-Durchschnitt heißt raus. In seiner Studie senkt das vor allem Schwankung und Verluste, ähnlich wie hier bei der Ampel.

---

## 5. Vorschläge für die Ampel

Kennungen AM1 bis AM8, zur Freigabe. Bei jedem steht, wie gut er belegt ist.

**AM1 · Breite über EMA200 statt EMA50** (getestet, in beiden Zeiträumen besser)
- **Was es bringt:** weniger Fehlalarme durch kurze Rücksetzer einzelner Sektoren.
- **Vorteil gegenüber heute:** Die EMA50-Breite schwankt stark und hat oft STOP ausgelöst, wenn der Markt kurz davor stand, sich wieder zu fangen.
- **Was es nicht ändert:** Den Zeitpunkt des ersten GO nach einem Tief. Der ist in allen sieben Einbrüchen identisch. Die Verbesserung kommt daher, dass 272 STOP-Tage, die allein wegen „Breite unter 3“ entstanden waren, großteils zu CAUTION werden (STOP-Anteil 22 % → 17 %). Für den früheren Wiedereinstieg ist AM4 zuständig. Die Indexphasen (P3/P6 mit EMA50/EMA200) bleiben unverändert.

**AM2 · Zwei Anzeigen statt einer: „Risiko“ und „Trendrichtung“** (folgt aus den Ergebnissen)
Die Ampel zeigt künftig getrennt:
- Risikostufe aus VIX, Breite und Kredit: niedrig, erhöht oder hoch
- Trendrichtung aus den Indexphasen: Long, neutral oder Short

- **Was es bringt:** Die Anzeige sagt, was sie wirklich messen kann.
- **Vorteil gegenüber heute:** Heute vermischt die Ampel beides. Ein STOP sieht aus wie „Markt fällt“, bedeutet laut Rückrechnung aber eher „Markt schwankt stark“.

**AM3 · Panik-Score umdeuten** (getestet: wirkungslos als Warnung, kontrarian in den Daten)
Der Score wird nicht mehr als Warnstufe verwendet, sondern als Hinweis „Angst hoch, Erholungschancen statistisch erhöht, aber mit großen Schwankungen“. Er sitzt damit neben dem REVERSE-Zustand.

- **Vorteil gegenüber heute:** Heute zählt er in die Warnung, ändert die Ampel aber nie, und seine Richtung ist umgekehrt zu dem, was die Daten zeigen.

**AM4 · Schnellerer Wiedereinstieg** (Hypothese, noch nicht getestet)
Feste VIX-Grenzen (20 und 28) durch relative ersetzen, etwa „VIX über seinem eigenen Jahresdurchschnitt“. Dazu ein Signal, das die Ampel nach einem STOP früher wieder öffnet: drei Indizes zurück in P3, Breite über EMA200 wieder über 6 und Termstruktur wieder in Contango.

- **Was es bringt:** Ziel ist, die 15 bis 60 % Erholung, die heute nach Tiefpunkten verpasst werden, zum Teil mitzunehmen.
- **Hinweis:** Das teste ich nur mit einer vorher festgelegten Regel und wieder getrennt in beiden Zeiträumen. Sonst passt man die Regel an die bekannten Tiefpunkte an.

**AM5 · Kreditspread als Zusatzanzeige** (gemischt getestet, in der Recherche gut belegt)
Eine eigene Kennzahl im Lagebild: High-Yield-Spread und seine Veränderung über 3 Monate. Ob er in die Ampel einfließt, entscheidet erst eine längere Beobachtung.

- **Vorteil gegenüber heute:** Der Kreditmarkt fehlt bisher völlig.

**AM6 · Weniger Springen** (getestet: V1 halbiert die Wechsel, kostet aber etwas)
Statt der Ampel selbst wird nur die Anzeige beruhigt. Ein Wechsel erscheint als „Wechsel angekündigt“ und gilt erst ab dem zweiten Tag. Die gerechnete Ampel bleibt unverändert.

- **Vorteil gegenüber heute:** Kein Hin und Her im Tagesrhythmus, ohne die Signalqualität zu verändern.

**AM7 · Short-Seite neu prüfen** (Befund: auf Indexebene schwach)
Die Konsequenz-Zeile „SHORT normal“ hat auf den S&P 500 bezogen nicht funktioniert. Bevor ich etwas ändere, würde ich deine Short-Trades aus dem Journal je Phase auswerten (T6 aus dem Konzept). Einzelaktien in P6 können sich anders verhalten als der Index.

**AM8 · Rückrechnung als festen Prüfstand behalten**
Die Skripte bleiben im Repository. Jede künftige Regeländerung wird vor dem Einbau gegen dieselben 19 Jahre geprüft und im Archiv mit Versionsnummer festgehalten (A1b).

- **Vorteil gegenüber heute:** Regeln wurden bisher nach Gefühl angepasst. Künftig gibt es für jede Änderung eine Messung.

---

## 6. Dateien

Alles liegt in `Morgenroutine2/auswertung/`:

- `daten_laden.py` lädt alle Rohdaten aus den öffentlichen Quellen
- `ampel_rueckrechnung.py` bildet die Ampel nach und schreibt `ergebnisse/ampel_taeglich.csv` (ein Eintrag je Tag mit Ampel, Gründen, allen Eingangswerten und den Folgerenditen)
- `ampel_auswertung.py` erzeugt alle Kennzahlen in `ergebnisse/auswertung.json`
- `ergebnisse/annahmen.json` und `ergebnisse/quellen.json` enthalten die Annahmen sowie die Quellen mit Prüfsummen

Die Rohdaten selbst sind nicht eingecheckt, weil sie Abzüge Dritter sind. Sie lassen sich mit `daten_laden.py` jederzeit neu holen.

## Quellen der Recherche

- [Sentimentrader: Optimismus bei schwacher Breite](https://sentimentrader.com/blog/stocks-are-seeing-high-optimism-during-an-unhealthy-environment)
- [MarketBeat: S&P 500 Breitensignal](https://www.marketbeat.com/articles/sp-500-market-breadth-signal-sounding-2023-01-25/)
- [LuxAlgo: Anteil Aktien über 20/50/200-Tage-Linie](https://www.luxalgo.com/library/concept/percent-stocks-above-20-50-200-day-ma/)
- [Globe and Mail: Kreditspreads und Marktspitzen (Credit Suisse)](https://www.theglobeandmail.com/globe-investor/inside-the-market/stock-volatility-a-historic-sign-of-the-end-to-bull-market-rallies/article37909498/)
- [Interactive Brokers Campus: Kreditspreads und VIX](https://www.interactivebrokers.com/campus/?p=219911)
- [eco3min: HY-Spread als Frühindikator](https://eco3min.fr/en/us-hy-credit-spread-leading-indicator-dataset/)
- [thetrading.tools: VIX-Termstruktur](https://www.thetrading.tools/manuals/vix-term-structure)
- [thetrading.tools: Backwardation](https://www.thetrading.tools/concepts/backwardation)
- [Faber: A Quantitative Approach to Tactical Asset Allocation (Kopie)](https://www.scribd.com/doc/116881446/SSRN-id962461)
- [Schaeffer's: AAII-Bären als Kontrarian-Indikator](https://www.schaeffersresearch.com/content/analysis/2025/09/24/aaii-bearish-tilt-could-be-a-reliable-contrarian-indicator)
- [Option Alpha: Aussagekraft von Anleger-Sentiment](https://optionalpha.com/podcast/predictive-power-of-investor-sentiment)
- [AAII Sentiment Survey](https://www.aaii.com/o/sentimentsurvey)
- [thetrading.tools: Zweig Breadth Thrust](https://www.thetrading.tools/zweig-breadth-thrust)
- [Nasdaq: Zweig Breadth Thrust](https://www.nasdaq.com/articles/rare-zweig-breadth-thrust-indicator-suggests-hefty-gains-ahead)
