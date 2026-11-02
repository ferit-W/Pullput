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

- **S1 Setup-Test:** Einstieg im Rücksetzer einer Aktie in P3 an EMA20/50 nach mindestens 3 Korrekturkerzen, mit Stopp nach ATR. Wie oft und wie viel R pro Trade, getrennt nach Ampelzustand, Sektorphase und Voreinstieg? Damit bekommt T3 (Setup-Scanner) belegte Regeln.
- **S2 Ausstieg:** feste Ziele (CRV) gegen Nachziehen des Stopps (EMA20, Swing-Tief, ATR-Trailing). Welche Variante passt zum Trendhandel?
- **S3 Positionsgröße und Gesamtrisiko:** 0,25 % je Trade und maximal 10 Positionen. Welche Verlustserien und welcher Drawdown sind damit realistisch?

Alle drei gelten mit dem Vorbehalt der Survivorship-Verzerrung (nur heutige Mitglieder) und werden nach dem Grundsatz oben getestet.

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

1. **KI-Anbieter:** Gemini bleibt, Claude kommt dazu, oder beides wählbar? Bis zur Entscheidung baue ich die Server-Schicht so, dass beides möglich ist, und lasse Gemini als Standard.
2. **U6 Handy-Ansicht:** Dafür müsste der Server ins Heimnetz geöffnet werden, mit Passwortschutz. Ohne ausdrückliches Ja bleibt er nur auf dem eigenen Rechner erreichbar.
3. **W4 Broker-Abgleich:** Du bist noch unsicher. Das wird nicht gebaut, bis du es willst. Falls ja, kommt der Altbestand auf eine eigene Liste „nicht abgleichen“.
4. **Stillhalter-Journal:** Bitte `stillhalter_journal_v6.html` ins Repository laden, damit ich es genauso prüfen und anpassen kann.

## Noch nicht vollständig geprüft

- **Stillhalter-Journal:** die Datei fehlt im Repository.
- **Trading Journal, HTML-Teil:** Formulare und Bedienelemente, rund 900 Zeilen. Das JavaScript ist vollständig geprüft, der HTML-Teil nur automatisch (alle IDs und Klick-Funktionen vorhanden).
- **Echter Betrieb unter Windows mit Live-Daten:** Yahoo, CNN und Gemini sind aus der Prüfumgebung gesperrt. Live-Abrufe sind deshalb nur am Code geprüft, nicht im Lauf. Nach jeder Phase ist ein kurzer Probelauf bei dir nötig.

## Fortschritt

Wird nach jeder Phase hier fortgeschrieben.

- [ ] Phase 1 — erledigt und getestet: J1, J3, J4, J6 · offen: J2, J7, J8, C1, C2, F-Fehler, V3, V10, V16
- [ ] Phase 2
- [ ] Phase 3
- [ ] Phase 4
- [ ] Phase 5
- [ ] Phase 6
