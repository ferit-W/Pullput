# Umsetzungsplan Morgenroutine, Journal, Cockpit

Stand: 02.11.2026. Grundsatz laut Absprache: **Alles, was vorgeschlagen und nicht abgelehnt wurde, wird umgesetzt.** Die Kennungen beziehen sich auf drei Dokumente:

- `PRUEFBERICHT_Morgenroutine_v6.17.md`: F, V
- `KONZEPT_Ausbau_Archiv_KI.md`: J, C, A, T, K, U, W
- `auswertung/AMPEL_AUSWERTUNG.md`: AM

Die Reihenfolge folgt einer einfachen Regel: erst das, was heute Daten verfälscht, dann das Fundament (Prüfstand, Handelsplan, Archiv), dann neue Funktionen, zuletzt die Oberfläche. Jede Phase endet mit Tests und einem eigenen Commit. Nach jeder Phase gibt es eine kurze Zusammenfassung zum Prüfen.

## Grundsatz für Regeln

Jede neue Regel und jede Änderung an Ampel, Konsequenz-Zeile oder Schwellen wird **vorher** getestet: Die Regel wird festgelegt und eingecheckt, dann in `auswertung/` getrennt in zwei Zeiträumen geprüft und nur bei Verbesserung in beiden fest eingebaut. Alles andere kommt höchstens als klar gekennzeichneter Hinweis. Wo Zweifel bestehen, wird getestet, nicht geschätzt.

## Grundsatz für Erklärungen (Info-Pop-ups)

Jeder Baustein, ob neu oder überarbeitet, bekommt ein „i“-Pop-up mit vier festen Teilen:

1. **Ziel:** welche Frage der Baustein beantwortet
2. **Warum so:** welche Logik dahintersteckt, mit Bezug auf Lüddemann-Phasen, Handelsplan oder Testergebnis
3. **So liest du es:** Schwellen, Farben und was daraus folgt
4. **Beispiel:** ein echter Tag aus der Rückrechnung, etwa „19.03.2020: Breiten-Wende, danach +23 % in 20 Tagen“, oder ein typischer Fall

Wo es Testergebnisse gibt, steht die ehrliche Bilanz dabei, also Trefferquote, Fehlsignale und ob der Baustein getestet und bestanden ist oder nur ein Hinweis. Die bestehenden Erklärtexte werden auf dieses Muster umgestellt.

## Phase 1 · Fehler, die Daten verfälschen

- **J1** Bearbeiten überschreibt Stückzahl, FX und Risiko
- **J2** IB-Import legt Geisterpositionen an
- **J3** Kontobewegungen gehen nicht aufs Laufwerk
- **J4** Auto-Backup läuft nie
- **J6** älterer Tab überschreibt beim Schließen
- **J7** Vorschau rechnet mit anderem Risiko als die Buchung
- **J8** Kleinigkeiten
- **SH1–SH7** Stillhalter-Journal, siehe `PRUEFBERICHT_Stillhalter_v6.2.md`. SH1 (Reset löscht alle Werkzeuge) zuerst.
- **C1** Euro-Positionen im Cockpit falsch umgerechnet
- **C2** doppelte Datenkopie im Cockpit
- **F5 mit V10** Einstellungs-Sync schreibt bei jedem Lauf
- **F1** Anleihen-Erklärer
- **F6 mit V3** Uhr ohne XETRA-Feiertage
- **F7 bis F9, F11 bis F17, F19, F20** übrige Fehler aus dem Prüfbericht
- **V16** Selbsttest für die Rechenfunktionen, damit jede spätere Änderung abgesichert ist

## Phase 2 · Ampel neu und Handelsplan als Datei

- **W1** Handelsplan als eine Datei mit Versionsnummer. Alle Werkzeuge lesen daraus.
- **AM1** Breite über EMA200
- **AM4** neuer Zustand **VOREINSTIEG** mit Prüfliste
- **AM2** Risikostufe und Trendrichtung getrennt anzeigen
- **AM3** Panik-Score umdeuten
- **AM9** Hinweis „⚡ Panik-Wende möglich“. Nur als gekennzeichneter Hinweis, weil der Test nicht bestanden wurde.
- **AM5** Kreditspread als Anzeige. Quelle: FRED, wird in die Server-Allowlist aufgenommen.
- **AM6** ruhigere Anzeige bei Wechseln
- **AM7** Short-Seite mit Journal-Daten prüfen
- **AM8** Rückrechnung als Prüfstand: Jede Regeländerung läuft vorher durch `auswertung/`.

## Phase 2b · Das Handelssystem selbst prüfen (neu)

Bisher wurde nur die *Ampel* getestet, also das Marktumfeld, und das am S&P 500. Ob dein eigentlicher Einstieg in Einzelaktien einen Vorteil hat, ist noch offen. Die Daten der 489 S&P-500-Aktien von 2016 bis 2026 liegen dafür bereit.

- **S1 Setup-Test mit deinen drei Kriterien:** nicht „alle P3-Aktien“, sondern begrenzte Plätze (höchstens 10) und nur Kandidaten, die alle drei Kriterien erfüllen:
  1. Allzeithoch bzw. 52-Wochen-Hoch
  2. Platz bis zum Widerstand größer als der Stopp-Abstand, also ein ausreichendes Verhältnis von Ziel zu Risiko
  3. relative Stärke gegen den eigenen Sektor positiv
  Gemessen wird schrittweise, was jedes Kriterium beiträgt. Frühere Tests mit RSI und Momentum als Vorfilter brachten nichts. Ein ehrliches „bringt nichts“ ist deshalb ein mögliches und brauchbares Ergebnis.
- **S2 Ausstieg:** feste Ziele (CRV) gegen Nachziehen des Stopps (EMA20, Swing-Tief, ATR-Trailing). Welche Variante passt zum Trendhandel?
- **S3 Positionsgröße und Gesamtrisiko:** 0,25 % je Trade und maximal 10 Positionen. Welche Verlustserien und welcher Drawdown sind damit realistisch?

- **S4 52-Wochen-Ausbruch (Lüddemann-Trendhandel):** Einstieg, wenn eine Aktie ein neues 52-Wochen- oder Allzeithoch macht. Die Theorie dahinter: Über dem 52-Wochen-Hoch liegt niemand mehr im Minus, deshalb gibt es weniger Verkaufsdruck. Getestet wird gegen den Rücksetzer-Einstieg aus S1, getrennt nach Ampelzustand und Marktbreite. Die Forschung zur Nähe am 52-Wochen-Hoch (George & Hwang 2004) stützt den Gedanken für Einzelaktien.

Alle vier gelten mit dem Vorbehalt der Survivorship-Verzerrung (nur heutige Mitglieder) und werden nach dem Grundsatz oben getestet.

## Neu aufgenommen: Lücken auf dem Weg zur bestmöglichen Morgenroutine

- **N1 Gesamtrisiko über alle Werkzeuge** (gewünscht): Trend-Trades und Stillhalter zusammen, dazu Konzentration nach Sektor und Gleichlauf der Positionen. Die Frage lautet: Wie viel steht heute insgesamt auf dem Spiel, und hängt alles am selben Thema?
- **N2 Platz-Check bis zum Widerstand** (als Vorprüfung, die Entscheidung fällt in TradingView): Die Routine sucht über dem Kurs das nächste markante Hoch der letzten 12 Monate. Am Allzeithoch gibt es keins. Sie zeigt dann zum Beispiel „Platz bis 182,40 = 1,8 × Stopp-Abstand“. Es ist nur ein Vorsortierer, damit man nicht jeden Chart öffnen muss. Bringt er im Test (S1) nichts, fliegt er raus.
- **N3 Quartalszahlen für Positionen und Kandidaten** (gewünscht). Kommende Termine kommen wie bisher kostenlos aus Yahoo, je Titel. Für historische Termine (Backtest) gibt es laut Recherche keine verlässlich freie Quelle. Ein Anbieter wirbt mit einem Gratis-Kontingent, das muss vor einer Nutzung geprüft werden. Termin je Titel aus Yahoo. Warnung, wenn Zahlen innerhalb der Haltedauer oder vor dem nächsten Handelstag liegen.
- **N4 Zweite Datenquelle:** Die Yahoo-Schnittstelle ist inoffiziell und kann jederzeit ausfallen oder sich ändern. Recherche und Einbau eines Ersatzes, mindestens für Indizes und VIX.
- **N5 Deutscher Markt gleichwertig** (gewünscht), mit Liquiditätsfilter, weil viele MDAX- und SDAX-Werte dünn gehandelt sind. Entschieden: Die Schwelle ist in den Einstellungen anpassbar, Startwert 1 Mio. € Tagesumsatz im Schnitt der letzten 20 Tage. Höchstens 20 Vorschläge, sortiert nach Qualität. Angezeigt wird auch, wie viele Werte am Liquiditätsfilter gescheitert sind, damit man sieht, ob die Schwelle zu streng ist. Breite, neue Hochs und Tiefs sowie Phasen auch für DAX, MDAX und SDAX, nicht nur für die USA.
- **N6 Handy-App** (entschieden: beides, also App und Push): Die Morgenroutine wird als App auf dem Samsung installierbar, über „Zum Startbildschirm hinzufügen“ in Chrome (PWA), mit eigener, schlanker Handy-Ansicht. Dazu optional eine tägliche Push-Nachricht mit Ampel, Neigung des Trading-Partners, Terminen und Positionen mit Handlungsbedarf. Die funktioniert auch unterwegs, ohne den Server ins Internet zu öffnen. Die Variante wählst du.
- **N7 Recherche-Punkte:** gute, freie Quellen für historische Earnings-Termine (damit N3 auch im Backtest nutzbar wird) und für eine Datenquelle ohne Survivorship-Verzerrung.
- **N1 Ergänzung Bestände außerhalb der Journale:** Gold- und Silber-ETFs und Ähnliches, die nur bei CapTrader liegen, kommen bis zum Broker-Abgleich in eine kleine Liste „Sonstige Bestände“ (Symbol, Stückzahl, Art, etwa Rohstoff). Sie zählen bei Konzentration und Kapitalbindung mit, aber nicht ins Trading-Risiko.
- **N6 Technik nach Recherche:**
  - Eine echte installierbare Web-App braucht HTTPS. Im Heim-WLAN mit einfachem `http://192.168…` installiert Chrome sie nicht vollwertig. Möglich ist dann ein eigenes Zertifikat, das auf dem Handy als vertrauenswürdig eingetragen werden muss, oder ein kleines Android-Programm (APK), das die Seite anzeigt und per Datei installiert wird. Das APK ist der bequemere Weg und wird vor dem Bau geprüft.
  - Push über ntfy (kostenlos, eigene Android-App). Auf dem öffentlichen Dienst sind Themen-Namen öffentlich, deshalb sind dort nur ein langer Zufallsname und knappe Inhalte sinnvoll, oder ein eigener ntfy-Dienst. **Entschieden: Telegram-Bot**, den du einmal mit deinem Konto verbindest. Bot-Schlüssel und Chat-Kennung liegen nur auf dem PC in der Server-Konfiguration, nicht im Browser.

## Phase 3 · Archiv als Grundlage für die spätere Auswertung

- **A1** Tagesarchiv auf dem Laufwerk
- **A1b** Regelversion und Rohwerte
- **A1c** automatischer Nachlauf der Folgerenditen
- **A1d** Auswertungsbericht auf Knopfdruck
- **A2** Rückblick-Ansicht
- **A3** rückwirkend befüllen, die Skripte aus `auswertung/` sind die Grundlage
- **A4** Journal archivieren statt löschen
- **A5** Marktbild des Tages am Trade speichern

## Phase 4 · Unterstützung für den Trendhandel

- **T1** Marktbreite aus 600 Aktien
- **T2** Positions-Monitor
- **T3** Setup-Scanner
- **T4** Übernacht-Block
- **T5** Tagesplan und Abendrückblick
- **T6** Regeltreue-Auswertung
- **T7** Wochenvorbereitung
- **T8** Desktop-Alarme
- **W2** Termine regelbasiert (Verfall, Wahlen, verkürzte Tage)
- **W3** „Trade vorbereiten“ ins Journal
- **V1** Sentimentwerte mit Datum
- **V2** Abstand zur nächsten Schwelle
- **V4** laufende Tageskerze kennzeichnen
- **V5** YTD gegen Vorjahresschluss
- **V8** Alter der Pre-Market-Kurse prüfen
- **V9** doppelte Bestätigung im Drilldown
- **V11** KI-Check zwischenspeichern
- **V12** History-Farbstreifen
- **V13** Pflege-Übersicht

## Phase 5 · KI als Trading-Partner

- **V14** KI-Zugang über den lokalen Server, Schlüssel im Header und nicht im Browser
- **K0** Trading-Partner ganz oben mit Rückfragen
- **K1** strukturiertes Tagesbriefing
- **K2** Wochenausblick
- **K3** Fragen an Archiv und Journal
- **K4** Nachrichten-Scan der Positionen
- **K5** Journal-Coach mit Marktkontext
- **K6** Abendvergleich, wie gut die Einschätzungen waren
- **V6, V7** Land und Datum als Felder im KI-Kalender

## Phase 6 · Oberfläche

- **Zuerst:** eine anklickbare Vorschau mit Beispieldaten zur Freigabe
- **Danach:** U1 bis U5, U7, U8
- **V15** einheitliche Versionsangabe
- **W5** Monatsbericht
- **W6** Update mit einem Klick

## Offene Entscheidungen

Diese Punkte setze ich erst um, wenn du dich entschieden hast:

1. ~~KI-Anbieter~~ **entschieden:** Gemini und Claude wählbar, Gemini als Standard.
2. ~~N6 Handy-App~~ **entschieden:** beides, also App im Heim-WLAN und tägliche Push-Nachricht. Push über **Telegram-Bot** (entschieden).
3. **W4 Broker-Abgleich:** entschieden: **später**. Dann mit eigener Liste „Altbestand, nicht abgleichen“.
4. ~~Stillhalter-Journal~~ **erledigt:** Die Datei liegt im Repository und ist geprüft (`PRUEFBERICHT_Stillhalter_v6.2.md`).
5. ~~DAX-Optionen~~ **geklärt:** derzeit keine. Der Multiplikator 100 passt, im Formular kommt nur ein Hinweis.

## Noch nicht vollständig geprüft

- **Trading Journal, HTML-Teil:** Formulare und Bedienelemente, rund 900 Zeilen. Das JavaScript ist vollständig geprüft, der HTML-Teil nur automatisch (alle IDs und Klick-Funktionen vorhanden).
- **Echter Betrieb unter Windows mit Live-Daten:** Yahoo, CNN und Gemini sind aus der Prüfumgebung gesperrt. Live-Abrufe sind deshalb nur am Code geprüft, nicht im Lauf. Nach jeder Phase ist ein kurzer Probelauf bei dir nötig.

## Fortschritt

Wird nach jeder Phase hier fortgeschrieben.

- [x] Phase 1 — erledigt und in der Prüfumgebung getestet (02.11.2026):
  - Trading Journal v6.5: J1–J4, J6–J8 (J5 „Archivieren“ folgt als A4 in Phase 3)
  - Stillhalter-Journal v6.3: SH1–SH7
  - Depot-Cockpit v6.2: C1–C3
  - Morgenroutine v6.18: F1–F20, V3, V10
  - REGELCHECK: Rolls rückwärts erkannt, F16
  - V16: Selbsttest `tests/selbsttest.js` (36 Prüfungen, ohne Internet: `node tests/selbsttest.js`)
  - **Offen bei dir:** kurzer Probelauf unter Windows mit Live-Daten, vor allem:
    - IB-Import mit einer echten Flex-Datei; Spalte `Open/CloseIndicator` mit exportieren
    - Gap-Scanner vor 10:00 Uhr: Erscheint bei Pre-Market-Kursen „⚠ gestern“?
    - Alte Import-Fehler meldet die Selbstkontrolle als „Fehlerhafter IB-Import aus älterer Version“
  - Bewusst nicht geändert: Tailwind-Play-CDN im Journal (F19, zweiter Teil). Ein Umbau bräuchte einen Build-Schritt; das passt zum UI-Umbau in Phase 6.
- [x] Phase 2 — erledigt und in der Prüfumgebung getestet (02.11.2026), Morgenroutine v6.19:
  - **AM1** Breite über EMA200, **AM3** Panik-Score aus der Regel (an 4.827 Tagen kein Unterschied), **AM4** Zustand VOREINSTIEG mit Prüfliste und 60-Tage-Rückschau aus den Kursreihen
  - **AM8** Prüfstand: Der Selbsttest vergleicht die Ampel der Seite an allen 4.827 Handelstagen 2007–2026 mit der Python-Rückrechnung (`auswertung/referenz_ampel_v2.py`). Ergebnis: identisch, davon 376 Tage VOREINSTIEG
  - **AM2** Trend und Risiko getrennt angezeigt · **AM6** „🆕 Wechsel“ wird gekennzeichnet, die Ampel selbst wartet nicht (die 2-Tage-Bestätigung hatte im Test Rendite gekostet)
  - **AM9** Hinweis „⚡ Panik-Wende möglich“ mit Prüfliste und ehrlicher Bilanz, ohne Einfluss auf Ampel und Größe. Die Breiten-Wende (B4) braucht Einzelaktien-Breite und folgt mit T1 in Phase 4
  - **AM5** Kreditspread High Yield (FRED) als Anzeige, Server-Allowlist erweitert
  - **W1** `handelsplan.json`: REGELCHECK und Journal lesen Risiko, Positionen usw. daraus. Die Morgenroutine zeigt die Version und warnt, wenn dort ungetestete Ampel-Werte stehen (sie werden nicht verwendet)
  - Info-Pop-ups mit Ziel / Warum so / So liest du es / Beispiel für Ampel, Voreinstieg, Panik-Wende, Trend/Risiko, Wechsel, Panik-Score, Breite, Kreditspread. Alle Beispielzahlen sind gegen die Rückrechnungsdaten geprüft
  - Tagesstand speichert jetzt Regelversion, Grundzustand, Trend, Risiko, Breite, Termstruktur, Voreinstieg, Panik-Wende und Kreditspread (Vorarbeit für das Archiv A1b)
  - **AM7** (Short-Seite mit Journal-Daten) wandert zu T6 in Phase 4: Die Journal-Trades speichern die Phase beim Einstieg noch nicht, das kommt mit A5 in Phase 3
  - **Offen bei dir:** Live-Probelauf: Erscheinen Kreditspread (FRED) und „Handelsplan 2026.11.1“ in der Zeile unter der Ampel? Steht im Journal 0,25 % als Vorgabe?
- [x] Phase 2b — Systemtest S1–S4 erledigt (02.11.2026), Ergebnisse in `auswertung/SYSTEM_TEST.md`. Kurz: Der Rücksetzer-Einstieg war in beiden Zeiträumen positiv. „Platz bis zum Widerstand“ half klar, „RS gegen Sektor“ gemischt, „Nähe zum 52-Wochen-Hoch“ (Näherung) schadete. Nachziehende Stopps waren besser als feste Ziele, der 52-Wochen-Ausbruch schwächer. Größter Rückgang 104,6 R (2021–2023). Kein Handelsstopp, nur Information. Folge: N2 Platz-Check bleibt im Plan, RS gegen Sektor nur als Anzeige.
- [x] Phase 3 — erledigt und in der Prüfumgebung getestet (02.11.2026):
  - **A1/A1b/A1c** Tagesarchiv `daten/archiv_JJJJ.json`: je Handelstag Zustand, Regelversion, Gründe, Konsequenz, alle Index-, Sektor- und Sentimentwerte. Der Server führt Einträge zusammen, statt sie zu ersetzen. Folgerenditen werden automatisch nachgetragen, exakt wie in der Rückrechnung (ab Schluss t+1)
  - **A2** Rückblick in der Morgenroutine: Datum wählen, blättern, sehen was danach geschah
  - **A3** Rückrechnung 2007–2026 per Knopf ins Archiv (4.827 Tage, gekennzeichnet als „nachgerechnet“, Live-Tage bleiben unberührt)
  - **A1d** Archiv-Bericht je Ampelzustand mit Lücken (grün vor Einbruch, rot vor Erholung) plus `archiv_ki_paket.csv` und `archiv_ki_frage.txt` für die Auswertung mit einer KI
  - **A4** Journal v6.6: „Archivieren“ verschiebt alte Trades nach `daten/trading_journal_archiv.json` statt sie zu löschen. Scheitert das Speichern, wird nichts entfernt. Dazu „📚 Langzeit“: Auswertung über Journal und Archiv je Jahr, Setup, Marktphase, Ampel beim Einstieg und Richtung
  - **A5** Jeder neue Trade speichert das Marktbild des Einstiegstags (Morgenroutine oder Archiv). Fehlt es, bleibt das Feld leer
  - **Offen bei dir:** einmal „⏪ Rückrechnung einspielen“ drücken. Nach ein paar Läufen prüfen, ob im Rückblick Live-Tage erscheinen
- [ ] Phase 4
- [ ] Phase 5
- [ ] Phase 6
