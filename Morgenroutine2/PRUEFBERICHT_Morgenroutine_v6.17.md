# Prüfbericht Morgenroutine v6.17 · Server 6.4 · REGELCHECK 1.2

Stand der Prüfung: 02.11.2026. An den Programmdateien wurde **nichts geändert**. Umgesetzt wird erst, wenn du die Vorschläge freigegeben hast.

**TL;DR:** Ich habe 20 Fehler gefunden. Keiner davon legt die Routine lahm, und Ampel, Phasen und Panik-Score rechnen richtig. Fünf Fehler haben aber spürbare Folgen:

- Der Anleihen-Erklärer kann den 10Y−2Y-Spread nie berechnen.
- Die Einstufung des KI-Kalenders stuft die EZB-Entscheidung als „niedrig“ ein, wenn vor dem Titel „Eurozone:“ steht. Termine ohne Länderangabe wie „Industrieproduktion“ verschwinden im Hintergrund.
- Die Zeitkorrektur schreibt ausländische Termine auf US-Zeiten um. Beispiel: Schweizer CPI 08:30 wird zu 14:30.
- Die Watchlist schreibt bei jedem Lauf Kursdaten in die Einstellungsdatei. Mit zwei Rechnern kommt deshalb nach fast jedem Lauf die Rückfrage „fremder Stand“.
- Die Uhr in der Kopfzeile kennt keine XETRA-Feiertage.

Danach folgen 16 Verbesserungsvorschläge, sortiert nach den Bereichen der Routine.

---

## Umfang und Vorgehen

Vollständig Zeile für Zeile gelesen:

- `ferit_morgenroutine_v6.html` (HTML, CSS, gesamtes JavaScript)
- `START_Morgenroutine_v6.py`
- `REGELCHECK.py`
- `START_Batch.bat`
- `Trading-Hub_v6.html`
- `AENDERUNGEN_v6.17.md`
- die Einstellungsdatei `daten/morgenroutine_settings.json` samt `.bak` und den fünf Wochen-Backups

Zusätzlich automatisch geprüft:

- JavaScript-Syntax aller vier HTML-Dateien mit Node
- Python-Syntax beider Skripte
- Gültigkeit aller sieben JSON-Dateien
- ob jede im Code angesprochene Element-ID und jede Klick-Funktion existiert

Alle diese Prüfungen waren fehlerfrei.

Getestet im echten Browser: Ich habe den Server aus einer Kopie gestartet, damit im Repository nichts geschrieben wird. Die Seite lief in Chromium. Die Verdachtsfälle habe ich direkt in der Seite nachgerechnet. Bei jedem Fehler steht, ob er **getestet** oder **aus dem Code abgeleitet** ist.

Nicht Zeile für Zeile geprüft habe ich `Trading_Journal_v6.html` und `depot_cockpit_v6.html`. Das sind eigene Werkzeuge und nicht Teil der Morgenroutine. Für sie gibt es nur die automatischen Prüfungen oben und eine Beobachtung bei F19.

Live-Kurse von Yahoo, CNN oder Gemini konnte ich aus der Prüfumgebung nicht abrufen. Aussagen, die echte Marktdaten bräuchten, sind deshalb als **Verdacht** gekennzeichnet.

---

## Teil A · Gefundene Fehler

Sortiert nach Auswirkung. Die Kennungen F1 bis F20 dienen dazu, dass du später einzelne Punkte freigeben oder ablehnen kannst.

### Mittlere Auswirkung

**F1 · Anleihen-Erklärer findet die 2-jährige Rendite nie** (getestet)
`ferit_morgenroutine_v6.html:2369–2375`
Der Erklärer sucht „2Y“ in `STATE.treasury`. Die 2-jährige Rendite liegt aber getrennt in `STATE.t2y`. Deshalb bekommt Gemini immer „Kurvenspread nicht berechenbar“, obwohl der Wert geladen ist. Außerdem gehen die Basispunkte ungerundet in den Prompt, zum Beispiel „+1.23456 bp“. Fehlt ein Wert, steht dort wörtlich „null bp“. Die KI rechnet also mit unvollständigen und unsauberen Eingaben.

**F2 · Länder-Präfix überstimmt die Liste der marktbewegenden Termine** (getestet)
`ferit_morgenroutine_v6.html:3747`
Die Prüfung auf Ländernamen läuft *vor* der Liste der marktbewegenden Termine. Getestet:

- „EZB-Zinsentscheid“ wird zu **hoch**.
- „Eurozone: EZB-Zinsentscheid“ wird zu **niedrig** und landet eingeklappt im Hintergrund. Im Tagesstart erscheint der Termin dann nicht.
- „Deutschland: ifo-Geschäftsklima“ wird zu **niedrig**. Die Einträge ifo und ZEW in der Mittel-Liste greifen deshalb nur, wenn Gemini kein Land davorschreibt.

**F3 · „uk“ wird ohne Wortgrenze gesucht** (getestet)
`ferit_morgenroutine_v6.html:3734` und `:3747`
Das Muster für Großbritannien trifft jedes Wort, das „uk“ enthält: Industrieprod**uk**tion, Prod**uk**tivität, Bruttoinlandsprod**uk**t. Getestet: „Industrieproduktion“ wird als Ausland eingestuft und eingeklappt. Steht „USA:“ davor, greift zuerst die US-Erkennung. Ohne Präfix verschwindet der Termin.

**F4 · Die Uhrzeit-Korrektur wendet US-Zeiten auf ausländische Termine an** (getestet)
`ferit_morgenroutine_v6.html:3661–3724`
Die Tabelle mit festen New Yorker Uhrzeiten erkennt CPI, BIP/GDP, Einzelhandel und Ähnliches nur am Stichwort, nicht am Land. Getestet:

- „Schweiz: Verbraucherpreise (CPI)“ um 08:30 wird stillschweigend auf **14:30** „korrigiert“. Die richtige Zeit wird also falsch.
- „Eurozone GDP“ um 11:00 bekommt ein gelbes „?“ für eine angeblich abweichende Uhrzeit. Das ist ein Fehlalarm.

**F5 · Die Einstellungsdatei wird bei jedem Lauf neu geschrieben** (aus Code und Datei belegt)
`ferit_morgenroutine_v6.html:4040`, `:1408–1434`
`refreshWatch()` speichert die Watchlist mit allen Kursen, EMAs, Momentum- und Fundamentaldaten. Da die Watchlist zu den synchronisierten Schlüsseln gehört, löst jeder Lauf einen Schreibvorgang auf dem Server aus. Belegt durch `daten/morgenroutine_settings.json`: Dort stehen Kurs, EMA20/50/200, KGV und Marktkapitalisierung von AAPL und NDX1.DE.

Folgen:

- Arbeitest du an zwei Rechnern, erscheint nach fast jedem Lauf die Rückfrage „ACHTUNG — fremder Stand auf dem Laufwerk“. Sie kommt zeitversetzt, ohne erkennbaren Anlass.
- Antwortest du mit „OK“, überschreibt ein Rechner echte Änderungen des anderen.
- Datei und Wochen-Backups wachsen mit Kursdaten, die niemand zurückholen muss.

**F6 · Die Uhr in der Kopfzeile ignoriert XETRA-Feiertage** (Funktionen getestet, Anzeige aus dem Code)
`ferit_morgenroutine_v6.html:1571–1588`
Die Uhr prüft nur US-Feiertage. Die Funktion `xetraStatus()` gibt es, sie wird aber nur im Tagesstart-Block benutzt. Getestet am Ostermontag 2027: XETRA ist zu, die US-Börse offen. Die Uhr zeigt dann vormittags „🇩🇪 XETRA offen“. Das Gleiche passiert am 1. Mai, an Heiligabend und an Silvester, wenn die US-Börse handelt.

Dazu kommen zwei Ungenauigkeiten:

- „XETRA offen“ steht bis 18:00 statt bis 17:30.
- „US-Kernzeit“ steht schon ab 9:00 New Yorker Zeit, also eine halbe Stunde vor der Eröffnung. Der Kommentar im Code nennt das bewusst so.

### Geringe Auswirkung

**F7 · Der Export schreibt „Panik-Score: null“** (aus dem Code)
`ferit_morgenroutine_v6.html:4172`
Ist der Score wegen zu geringer Abdeckung unbestimmt, landet wörtlich „null“ im Markdown-Export statt „unbestimmt (x/100 erfasst)“.

**F8 · Nach dem Sync vom Laufwerk greift „KI beim Laden“ erst nach dem Neuladen** (aus dem Code)
`ferit_morgenroutine_v6.html:989`, `:4364–4371`
Der Sync übernimmt den Wert in den Browserspeicher. Die Variable `AI_AUTO` wurde aber schon vorher gelesen und wird nicht aktualisiert. Ebenso zeigt das FOMC-Textfeld nach dem Sync noch den alten Inhalt.

**F9 · Zugriff auf eine Liste vor ihrer Definition beim ersten Aufruf** (aus dem Code)
`ferit_morgenroutine_v6.html:911`, `:1116–1122`, `:1391`
Beim allerersten Öffnen ruft `seedWatch()` die Funktion `saveLS()` auf. Diese fragt `MR_SYNC_KEYS` ab, das erst später im Skript entsteht. Das wirft intern einen Fehler. Der Fehler wird verschluckt, und `saveLS` meldet „nicht gespeichert“, obwohl gespeichert wurde. Heute folgenlos, aber es verdeckt Fehler.

**F10 · Das Stillhalter-Journal fehlt im Ordner** (aus dem Repository)
`Trading-Hub_v6.html:52`, `depot_cockpit_v6.html:56`
Hub-Kachel und Depot-Cockpit verlinken auf `stillhalter_journal_v6.html`. Diese Datei liegt nicht im Repository. Ein Klick zeigt die 404-Seite des Servers. Falls die Datei bei dir lokal existiert und nur nicht hochgeladen wurde, ist das kein Programmfehler.

**F11 · Veraltete oder widersprüchliche Texte** (aus dem Code)

- `:542` und `:972` nennen „START.bat“. Das Änderungsprotokoll meldet unter Punkt 15, das sei auf START_Batch.bat korrigiert. An diesen zwei Stellen fehlt die Korrektur.
- Info-Text Markt `:782`: „alles dazwischen ist ‚–‘“ stimmt seit v6.17 nicht mehr. Angezeigt wird zum Beispiel „P4 · kein Setup“.
- Info-Text Markt `:782` und Sektor-Kopf `:2490`: Dort steht, sortiert werde nach dem Abstand EMA50↔EMA200. Tatsächlich sortiert der Code nach einem Mischwert aus EMA50-Steigung, 0,25 × Abstand zur EMA200 und 0,25 × 1-Monats-Momentum (`:1230–1236`).
- Info-Text Werkzeuge `:836`: „Watchlist … lokal im Browser gespeichert“. Seit v6.11 wird sie auch auf dem Server gesichert.
- Info-Text Lagebild `:657` nennt nur GRÜN, GELB und ROT. Die Zustände REVERSE (violett) und WARTE fehlen.
- `START_Batch.bat:5` zeigt „v6.0“, `:83` spricht von „sieben Dateien“. Der Hub nennt sich v6.2. Der Server-Selbstcheck prüft nur die HTML-Version.

**F12 · Der Sektor-Tooltip nennt den falschen Spread** (aus dem Code)
`ferit_morgenroutine_v6.html:2495`
Bei Sektoren in P6 zeigt die Kachel den Abstand EMA20↔EMA200. Der Tooltip beschriftet den Wert trotzdem als „EMA50/200-Spread“.

**F13 · Das Wochenfenster ist länger als beschrieben** (aus dem Code)
`ferit_morgenroutine_v6.html:3437–3439`, `:3370`
Der Text sagt „nächsten fünf Handelstage“. Der Code zählt von heute bis heute + 7 Tage einschließlich. An einem Montag sind das sechs Handelstage, inklusive des folgenden Montags. Ein FOMC-Termin am nächsten Montag macht damit schon diese Woche „voll“.

**F14 · „Stärkster Sektor“ ist uneinheitlich definiert** (aus dem Code)
Briefing und Export nehmen die relative Stärke über einen Monat (`:3883`, `:4175`). Der History-Snapshot nimmt den Trendstärke-Mischwert (`:4079`). An einem Tag können deshalb zwei verschiedene „stärkste Sektoren“ dastehen.

**F15 · Toter Code und Reste** (aus Code und Datei)

- `MANUAL_CHECKS`, `CHECK` und `SK.check` (`:1106`, `:4151–4157`) werden nirgends mehr benutzt. `MANUAL_CHECKS` nennt außerdem „Risiko ≤ 0,5 %“, REGELCHECK prüft aber 0,25 %.
- In den gespeicherten Klappzuständen stehen Panels, die es nicht mehr gibt: `sp-panik`, `sp-cot`, `sp-check`.
- Die Klasse `mono` wird 14-mal benutzt, ist im CSS aber nie definiert. Sichtbar ist das nicht, weil die Grundschrift ohnehin Monospace ist.

**F16 · REGELCHECK: ein Name mit doppelter Bedeutung** (aus dem Code)
`REGELCHECK.py:169–190`
`kat` ist zuerst eine Funktion und wird dann in der Schleife mit einem Text überschrieben. Das funktioniert heute nur wegen der Reihenfolge. Wer die Funktion später weiter unten noch einmal braucht, bekommt einen Absturz.

**F17 · Kompilierte Python-Datei ist eingecheckt** (aus dem Repository)
`Morgenroutine2/__pycache__/REGELCHECK.cpython-314.pyc` liegt im Repository, obwohl `.gitignore` den Ordner `__pycache__` ausschließt. Die Datei wurde vor der Regel hinzugefügt.

**F18 · Gap-Scanner: Pre-Market-Kurse haben keine Altersprüfung** (aus dem Code, Teil davon nur ein Verdacht)
`START_Morgenroutine_v6.py:733–761`

- **Sicher:** Der Hinweis „⚠ gestern“ wird nur für Eröffnungskurse gesetzt, nie für Pre-Market-Kurse. Die US-Vorbörse beginnt um 4:00 New Yorker Zeit, also 10:00 deutscher Zeit. Ein Scan vorher kann einen Pre-Market-Kurs vom Vortag ohne Warnung als heutiges Gap zeigen.
- **Verdacht** (ohne Live-Daten nicht prüfbar): In der Vorbörse ist `regularMarketPreviousClose` bei Yahoo womöglich noch der Schluss von vorgestern. Das Gap würde dann die gesamte gestrige Tagesbewegung mitzählen. Prüfen lässt sich das einmalig, indem man ein Pre-Market-Gap im Scanner mit der Yahoo-Webseite vergleicht.

**F19 · Trading Journal lädt eine Bibliothek ohne Versionsnummer** (aus dem Code)
`Trading_Journal_v6.html:10` lädt `marked` ohne Version, also immer die neueste. Erscheint eine neue Hauptversion mit geänderter Schnittstelle, kann die Markdown-Anzeige im Journal ohne eigene Änderung ausfallen. `:7` nutzt außerdem das Tailwind-Play-CDN, das laut Tailwind nicht für den Dauerbetrieb gedacht ist.

**F20 · Der Rückfallwert für das Fed-Zielband ist veraltet** (aus dem Code)
`ferit_morgenroutine_v6.html:954`
`FED_BAND` steht auf dem Stand vom 17.06.2026. Seitdem gab es laut der eigenen Liste die Sitzungen am 16.09. und 28.10. Der Wert greift nur, wenn der Abruf bei der New Yorker Fed scheitert. Die Seite warnt dann selbst. Es ist trotzdem ein Pflegepunkt, der still veraltet.

---

## Teil B · Verbesserungsvorschläge nach Bereichen

Alle Fehler aus Teil A würde ich bei der Umsetzung mit beheben. Die folgenden Vorschläge gehen darüber hinaus. Jeder Vorschlag sagt, was er bringt und was der Vorteil gegenüber heute ist.

### 01 · Lagebild (Ampel, Panik-Score, Konsequenz-Zeile)

**V1 · Manuelle Sentiment-Werte bekommen ein Datum**
Beim Speichern von PCR, AAII-Bear und NAAIM wird das Datum mitgeschrieben. Werte älter als 10 Tage erscheinen im Streifen als „veraltet“ und zählen nicht mehr in den Score.

- **Was es bringt:** Der Panik-Score rechnet nur mit Werten, die zur aktuellen Woche passen.
- **Vorteil gegenüber heute:** Heute zählt ein vor Monaten eingetragener Wert unbemerkt mit. Diese drei Felder machen 36 von 100 Punkten aus, und die Anzeige „100/100 erfasst“ wirkt vollständig, obwohl sie veraltet ist.

**V2 · Abstand zur nächsten Ampelschwelle anzeigen**
Unter der Begründung steht eine Zeile wie „GO ab 3/4 in P3 (jetzt 2/4) · CAUTION ab VIX 20 (jetzt 19,1)“.

- **Was es bringt:** Du siehst sofort, wie nah die Lage an einem Wechsel ist.
- **Vorteil gegenüber heute:** Heute erklärt die Seite nur den aktuellen Zustand. Ob die Ampel morgen bei kleiner Bewegung kippt, musst du dir aus den Schwellen im Code selbst herleiten.

### Tagesstart (Börsenstatus, Termine heute, Regelcheck)

**V3 · Uhr und „Heute“-Zeile aus einer Quelle, laufend aktualisiert**
Die Kopfzeile nutzt dieselbe Börsenstatus-Funktion wie der Tagesstart, also mit XETRA-Feiertagen und 17:30 Schluss. Die „Heute“-Zeile wird im 30-Sekunden-Takt der Uhr mit aktualisiert.

- **Was es bringt:** Kopfzeile und Tagesstart sagen immer dasselbe. Das behebt F6.
- **Vorteil gegenüber heute:** Heute rechnen zwei Stellen getrennt und widersprechen sich an XETRA-Feiertagen. Bleibt die Seite über Nacht offen, zeigt „Heute“ den Vortag, bis du neu lädst.

### 02 · Markt (Indizes, Rohstoffe & FX, Treasury & Fed)

**V4 · Laufende Tageskerze kennzeichnen**
Ist die letzte Tageskerze noch nicht abgeschlossen (DAX nach 9:00, US nach 15:30 deutscher Zeit), bekommt die Phase den Zusatz „vorläufig“.

- **Was es bringt:** Du erkennst, ob eine Phase auf einem Schlusskurs oder auf einem Zwischenstand beruht.
- **Vorteil gegenüber heute:** Der Code-Kommentar sagt „Tagesschluss-basiert“. Während der Handelszeit liefert Yahoo als letzte Kerze aber den laufenden Kurs. Eine Phase kann im Tagesverlauf wechseln, ohne dass das sichtbar ist.

**V5 · YTD gegen den Jahresschluss des Vorjahres rechnen**
Die Jahresveränderung der Renditen bezieht sich auf den letzten Schluss des Vorjahres statt auf den ersten Handelstag des neuen Jahres.

- **Was es bringt:** Die Zahl entspricht der üblichen Definition und ist mit Finanzseiten vergleichbar.
- **Vorteil gegenüber heute:** Heute fehlt die Bewegung des ersten Handelstags im Januar in der YTD-Zahl.

### 03 · News & Termine (KI-Kalender)

**V6 · Land als eigenes Feld vom Modell anfordern**
Der Prompt verlangt je Termin ein Feld `"land"` (US, EU, DE, CH, …). Region, Wichtigkeit und Zeitkorrektur richten sich zuerst nach diesem Feld, die Stichwörter im Titel dienen nur noch als Rückfall.

- **Was es bringt:** Die Fehler F2, F3 und F4 werden an der Wurzel behoben, nicht nur einzeln geflickt.
- **Vorteil gegenüber heute:** Heute hängt die Einstufung an der Schreibweise des Titels. Ob Gemini „Eurozone:“ davorschreibt oder nicht, entscheidet, ob die EZB-Sitzung als marktbewegend gilt.

**V7 · Termine mit Datum statt Wochentagskürzel anfordern**
Der Prompt verlangt `"datum":"2026-11-04"` zusätzlich zu `"day"`.

- **Was es bringt:** Die Zuordnung zum Tag ist eindeutig. Die Umrechnung bei der Zeitumstellung trifft den richtigen Tag, und der Tagesstart zeigt verlässlich die heutigen Termine.
- **Vorteil gegenüber heute:** Das Abfragefenster umfasst acht Kalendertage, also kommt „Mo“ zweimal vor. Ein Kalender vom Wochenbeginn ordnet „Mo“ am Donnerstag dem nächsten Montag zu.

### 04 · Action (Sektoren, Gap-Scanner, Saisonkalender)

**V8 · Gap-Scanner prüft das Alter der Pre-Market-Kurse**
Der Server nutzt `preMarketTime` und markiert Pre-Market-Kurse vom Vortag wie heute schon die Eröffnungskurse. Vor 10:00 deutscher Zeit erscheint ein Hinweis, dass die US-Vorbörse noch nicht läuft.

- **Was es bringt:** Keine Gaps von gestern als heutige Kandidaten. Das behebt F18 im sicheren Teil.
- **Vorteil gegenüber heute:** Heute bekommen nur Eröffnungskurse das „⚠ gestern“.

**V9 · Drilldown zeigt die doppelte Bestätigung**
In den Listen der 10 stärksten und 10 schwächsten Aktien wird markiert, wenn Aktie *und* Sektor-ETF in derselben Phase stehen, also beide P3 oder beide P6.

- **Was es bringt:** Der Top-down-Gedanke „starker Sektor → starke Aktie“ ist direkt ablesbar.
- **Vorteil gegenüber heute:** Heute musst du die Sektorphase oben und die Aktienphase unten selbst abgleichen.

### 05 · Werkzeuge (Watchlist, History, Diagnose)

**V10 · Watchlist trennt Einstellungen von Kursdaten**
In die synchronisierte Einstellungsdatei kommen nur Ticker, Name und Gap-Kontext. Kurse, EMAs und Fundamentaldaten bleiben im lokalen Zwischenspeicher.

- **Was es bringt:** Der Server-Sync schreibt nur bei echten Änderungen. Das behebt F5.
- **Vorteil gegenüber heute:** Keine Rückfragen „fremder Stand“ nach jedem Lauf, keine überschriebenen Änderungen zwischen zwei Rechnern und kleinere Backups.

**V11 · KI-Check der Watchlist zwischenspeichern**
Das Ergebnis wird 24 Stunden mit Zeitstempel gespeichert und nach dem Neuladen wieder angezeigt.

- **Was es bringt:** Die Einschätzung bleibt erhalten, und du siehst, von wann sie ist.
- **Vorteil gegenüber heute:** Heute ist sie nach dem Neuladen weg, und ein erneuter Klick kostet wieder Token.

**V12 · History als Farbstreifen**
Über den Karten steht ein schmaler Streifen mit den Ampelfarben der letzten bis zu 60 Tage.

- **Was es bringt:** Regimewechsel und ihre Dauer sind auf einen Blick erkennbar.
- **Vorteil gegenüber heute:** Heute musst du Karte für Karte durchgehen, um zu sehen, seit wann die Lage so ist.

**V13 · Pflege-Übersicht in der Diagnose**
Ein Block zeigt alle Daten, die von Hand gepflegt werden, mit Stand und Ablaufdatum:

- FOMC-Liste (reicht bis …)
- Fed-Band-Rückfallwert
- Saisonquelle (Stand 04/2024)
- Holdings je Sektor
- manuelle Sentimentwerte

- **Was es bringt:** Alle jährlichen und wöchentlichen Pflegepunkte stehen an einer Stelle.
- **Vorteil gegenüber heute:** Heute stehen sie verstreut im Code und fallen erst auf, wenn sie schon veraltet sind, siehe F20.

### Einstellungen, Server und Start

**V14 · Gemini-Schlüssel im Header statt in der Adresse**
Der Schlüssel wird als Header `x-goog-api-key` übertragen statt als `?key=` in der URL.

- **Was es bringt:** Der Schlüssel taucht nicht mehr in Adresszeilen, Netzwerkprotokollen oder Fehlermeldungen auf.
- **Vorteil gegenüber heute:** Die Funktion bleibt gleich, der Schlüssel ist weniger sichtbar.

**V15 · Einheitliche Versionsangabe**
Batch-Datei, Hub und Server-Selbstcheck lesen dieselbe Versionsnummer. Der Selbstcheck prüft zusätzlich, ob REGELCHECK.py und der Hub zur Version passen.

- **Was es bringt:** Beim Start siehst du in einer Zeile, ob alle Dateien zusammengehören.
- **Vorteil gegenüber heute:** Heute stehen v6.0, v6.2, 6.4 und 6.17 nebeneinander. Eine vergessene Datei beim Update fällt nicht auf.

**V16 · Kleiner Selbsttest für die Rechenfunktionen**
Eine Testdatei für Node prüft ohne Internet:

- Phasenlogik und Ampel
- Feiertage und Halbtage
- Zeitumrechnung New York → Berlin
- Makro-Einstufung mit den Testtiteln aus diesem Bericht

- **Was es bringt:** Fehler wie F2 bis F4 fallen vor dem Einsatz auf, nicht erst am Handelstag.
- **Vorteil gegenüber heute:** Das Änderungsprotokoll beschreibt Tests, die einmalig von Hand liefen. Bei der nächsten Änderung prüft sie niemand erneut.

---

## Freigabe

Antworte am einfachsten mit den Kennungen, zum Beispiel:

- „alle“
- „alle Fehler, dazu V1, V3, V6, V10“
- „alles außer V12 und V16“

Bewusst **nicht** angefasst, solange du es nicht ausdrücklich willst:

- Ampelschwellen
- Gewichte des Panik-Scores
- Phasenlogik
- Handelsregeln in REGELCHECK
