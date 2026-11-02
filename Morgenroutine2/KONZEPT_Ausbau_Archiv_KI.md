# Ausbau-Konzept: Journale, Archiv, Trendhandel, KI

Stand: 02.11.2026. Ergänzt `PRUEFBERICHT_Morgenroutine_v6.17.md`. Am Programm ist noch **nichts geändert**. Umgesetzt wird erst nach deiner Freigabe.

**TL;DR:**

- **Trading Journal:** Es hat einen ernsten Fehler, den ich im Browser nachgestellt habe. Wer einen offenen Trade nur öffnet und speichert, etwa um die Marktphase nachzutragen, ändert dabei unbemerkt Stückzahl, Risiko und Kapitalbindung. Im Test wurden aus 7 Stück 5. Dazu kommen ein fehlerhafter IB-Import, Kontobewegungen, die nie auf dem Laufwerk landen, und ein Auto-Backup, das gar nicht läuft.
- **Depot-Cockpit:** Euro-Positionen rechnet es rund 8 % zu niedrig.
- **Stillhalter-Journal:** Es liegt nicht im Repository und konnte deshalb nicht geprüft werden.
- **Archiv:** Ein Tagesarchiv auf dem Laufwerk, das nie gekürzt wird. Es speichert alle Rohwerte, die Regelversion und automatisch, was danach am Markt passiert ist. Daraus entsteht auf Knopfdruck ein Bericht „Hat die Ampel funktioniert, wo waren Lücken?“. Der kursbasierte Teil lässt sich sogar sofort rückwirkend über rund 15 Jahre prüfen.
- **Trendhandel:** Neue Bausteine, darunter Marktbreite aus dem S&P 500, ein Positions-Monitor für offene Trades, ein Setup-Scanner sowie Tagesplan und Tagesrückblick.
- **KI als Trading-Partner:** Die KI gibt oben auf der Seite Lage, Ausblick, anstehende Termine (zum Beispiel US-Wahlen) und eine begründete Neigung wie „eher long“, gekennzeichnet als Meinung, mit Gegenargument und Rückfragemöglichkeit. Ihre Einschätzungen werden archiviert und später auf Treffsicherheit geprüft. Die Entscheidung bleibt bei dir.
- **Oberfläche:** Eine Startzeile, die alles in 5 Sekunden sagt, Reiter statt einer langen Seite, ein einheitliches Erscheinungsbild für alle Werkzeuge, Mini-Verläufe und eine Handy-Ansicht.
- **Weitere Vorschläge:** Handelsplan als eine Datei, vollständige Termine, „Trade vorbereiten“ direkt ins Journal, Broker-Abgleich, Monatsbericht, Update mit einem Klick.

---

## Teil A · Prüfung Trading Journal und Depot-Cockpit

Gelesen habe ich `Trading_Journal_v6.html` (das komplette JavaScript, rund 4.500 Zeilen) und `depot_cockpit_v6.html` vollständig. Einen Teil der Fälle habe ich im Browser an einer Kopie nachgestellt. Die Kennungen J und C dienen zur Freigabe.

### Trading Journal

**J1 · „Bearbeiten“ überschreibt Stückzahl, Risiko und FX-Kurs** (getestet, hohe Auswirkung)
`Trading_Journal_v6.html:3389–3455` und `:2157–2206`
`loadTradeForManagement()` schreibt die echte Stückzahl ins Formular und ruft danach `calculatePosition()` auf. Diese Funktion rechnet die Größe aus der *heutigen* Kontogröße neu und überschreibt das Feld. Das Sizing-FX-Feld wird gar nicht wiederhergestellt.

Im Test habe ich einen Trade mit 7 AAPL, Sizing-FX 1,09 und 64,22 € Risiko angelegt, nur die Marktphase nachgetragen und gespeichert. Danach stand im Journal: **5 Stück**, FX 1, **50 € Risiko**, Kapitalbindung 1.000 statt 1.400.

Betroffen sind alle offenen Trades, die je über „Bearbeiten → Änderungen speichern“ gelaufen sind. Bei geschlossenen Trades ändert sich über denselben Weg auch das R-Vielfache. Die Selbstkontrolle im Journal erkennt das nicht, weil die Werte danach in sich stimmig sind.

**J2 · IB/CapTrader-Import legt Geisterpositionen an** (aus dem Code, hohe Auswirkung)
`:5319–5495`
Eine Flex-Datei enthält Einstieg und Ausstieg als getrennte Zeilen. Der Import macht daraus zwei Trades:

- Die Kaufzeile bleibt für immer „offen“. Sie zählt in Slots, offenem Risiko und im REGELCHECK.
- Die Verkaufszeile wird ein eigener geschlossener Trade, dessen Einstiegskurs gleich dem Ausstiegskurs ist.

Der realisierte Gewinn wird außerdem in Dollar als „Euro“ gebucht, ohne FX. Die Selbstkontrolle meldet diese Trades danach als „Gewinn passt nicht zur Nachrechnung“.

**J3 · Kontobewegungen werden nicht aufs Laufwerk gesichert** (aus dem Code, mittlere Auswirkung)
`:5178`, `:5281`
Import und Löschen von Dividenden, Zinsen, Gebühren sowie Ein- und Auszahlungen speichern nur im Browser (`localDb.save()`), nicht über den Server. Folgen:

- Am zweiten Rechner fehlen sie.
- Wird der Laufwerksstand übernommen, sind sie überschrieben.
- Der Kontostand, aus dem die Positionsgröße berechnet wird, aktualisiert sich erst bei der nächsten anderen Aktion.

Wer dieselbe Datei zweimal importiert, hat außerdem alles doppelt, weil es keine Dublettenprüfung gibt.

**J4 · Das Auto-Backup alle 15 Minuten läuft nie** (aus dem Code)
`:1730–1787`, Knopf `:997`
`startAutoBackupTimer()` und `checkAutoBackupRecovery()` werden nirgends aufgerufen. Der Knopf „🔄 Auto-Restore“ meldet deshalb immer „Kein Auto-Backup vorhanden“. Das Sicherheitsnetz, das die Kommentare beschreiben, gibt es nicht.

**J5 · „Archivieren“ löscht statt zu archivieren** (aus dem Code)
`:4571–4621`
Trades älter als ein Jahr werden als Datei heruntergeladen und aus Journal und Laufwerksdatei *entfernt*. Übrig bleibt nur eine Summe (Gewinn, R, Anzahl). Phasen-, Setup- und Wochentagsauswertungen verlieren damit genau die lange Historie, die du für den Rückblick willst.

**J6 · Ein älterer Tab überschreibt beim Schließen den Browserspeicher** (im Test beobachtet)
`:1790–1797`
Beim Schließen oder Neuladen speichert jeder Tab seinen eigenen Stand. Sind zwei Journal-Tabs offen, setzt der zuletzt geschlossene seinen älteren Stand in den Browserspeicher. Die Laufwerksdatei bleibt unberührt.

**J7 · Die Gewinnvorschau beim Schließen rechnet mit einem anderen Risiko als die Buchung** (aus dem Code)
`:4460–4513`
Die Vorschau teilt durch das neu berechnete Risiko aus dem Formular, die Buchung durch das gespeicherte. Der angezeigte R-Wert kann deshalb vom gebuchten abweichen. Die Prozentangabe bezieht sich aufs Startkapital, nicht auf den aktuellen Kontostand.

**J8 · Kleinere Punkte** (aus dem Code)

- Teilverkäufe bekommen immer das Datum „jetzt“ und lassen sich nicht nachtragen (`:3919`).
- Die Warnung „empfohlen max. N Positionen“ zählt auch Langfrist und Altbestand mit (`:4806–4812`).
- Das Formular startet mit 1,0 % Risiko, REGELCHECK prüft aber 0,25 % für Trend- und 0,40 % für Gap-Trades (`:804`).
- Nach dem Laufwerks-Sync wird die Liste der Kontobewegungen nicht neu gezeichnet (`:5292–5298`).
- Der KI-Coach hat ein fest eingestelltes Modell, schickt den Schlüssel in der Adresse und setzt die KI-Ausgabe ungefiltert ins HTML (`:1537–1650`).
- Im Titel steht „v6.0“.

### Depot-Cockpit

**C1 · Euro-Positionen werden mit dem Dollarkurs umgerechnet** (aus dem Code, mittlere Auswirkung)
`depot_cockpit_v6.html:90`, `:153`, `:166`
Die Währung gilt für das ganze Richtungs-Journal (Standard USD). Ein DAX-Wert oder ein Euro-Future ohne FX-Eintrag wird deshalb durch EUR/USD geteilt. Realisierter Gewinn und offenes Risiko dieser Positionen erscheinen rund 8 % zu niedrig, und der unrealisierte Gewinn wird für Euro-Titel gar nicht berechnet, weil das Cockpit einen Währungskonflikt meldet. Richtig wäre: Währung je Trade aus dem Symbol (`.DE`) oder aus einem eigenen Feld.

**C2 · Vollständige Kopie beider Journale im Browserspeicher** (aus dem Code)
`:65`
Das Cockpit legt alle Trades noch einmal ab. Das konkurriert mit dem Journal um dieselben rund 5 MB, vor deren Grenze das Journal selbst warnt.

**C3 · Versionsangaben passen nicht zusammen**
Im Kopf steht „v3.4“, im Titel „v6.1“. Der Stillhalter-Link läuft ins Leere (siehe F10 im ersten Bericht).

### Stillhalter-Journal

`stillhalter_journal_v6.html` liegt nicht im Repository. REGELCHECK und Depot-Cockpit lesen zwar `stillhalter_journal.json`, aber das Programm selbst konnte ich nicht prüfen. Wenn du die Datei hochlädst, prüfe ich sie genauso.

---

## Teil B · Langfrist-Archiv als Grundlage für eine spätere Auswertung

**Ziel:** Nach einigen Jahren sollen die gesammelten Daten ausgewertet werden, mit Programm und KI: Hat die Ampel funktioniert? Wo lag sie daneben, wo kam sie zu spät? War die Konsequenz-Zeile sinnvoll? Dafür muss das Archiv mehr enthalten als ein Tagebuch. Es braucht drei Dinge, die heute fehlen:

1. **Die Eingaben vollständig:** alle Rohwerte, aus denen die Ampel entsteht, nicht nur ihr Ergebnis.
2. **Die Regelversion:** Schwellen und Gewichte ändern sich über die Jahre. Ohne Versionsangabe vergleicht eine spätere Auswertung Äpfel mit Birnen.
3. **Was danach passiert ist:** Ob „GO“ richtig war, zeigt erst die Marktentwicklung der Folgetage.

**Heute** bewahrt die Morgenroutine wenig auf:

- höchstens 60 History-Karten, also etwa ein Quartal,
- die Kennzahlen des Vortags für 12 Tage,
- die KI-Texte für einen Tag bzw. eine Woche.

Was der VIX am 2. November 2025 war, wie die Ampel stand und was das Briefing sagte, lässt sich deshalb nicht nachschlagen.

**A1 · Tagesarchiv auf dem Laufwerk**
Nach jedem Lauf schreibt der Server einen vollständigen Tagesdatensatz in eine Jahresdatei, zum Beispiel `daten/archiv/morgenroutine_2026.json`. Darin stehen:

- Ampel, Konsequenz-Zeile und Panik-Score mit allen Einzelwerten
- VIX, VVIX, VIX9D, VIX3M und Termstruktur
- alle Indizes mit Kurs, EMAs, Phase und Trendstärke
- Sektoren, Rohstoffe, Renditen, Fed-Band und FOMC-Abstand
- Marktbreite
- Termine der Woche
- Gap-Liste, Watchlist und Regelcheck-Befund
- die KI-Texte im Wortlaut

Ein Eintrag je Tag. Läuft die Routine mehrmals am Tag, bleibt der erste Stand erhalten und spätere Läufe werden zusätzlich als „Nachträge“ angehängt. Die Datei wird nie gekürzt. Die bestehenden Wochen-Backups des Servers sichern sie mit.

- **Was es bringt:** Jeder Morgen ist dauerhaft nachlesbar, auch in Jahren noch.
- **Vorteil gegenüber heute:** Statt 60 Karten mit wenigen Zahlen gibt es ein vollständiges Protokoll ohne Ablaufdatum, das auf dem Laufwerk liegt und nicht im Browser.

**A1b · Regelversion und Rohwerte mitschreiben**
Jeder Tagesdatensatz enthält die Version der Ampel- und Konsequenzregeln (Schwellen, Gewichte) und alle Rohwerte. So lässt sich die Ampel später mit alten *und* neuen Regeln für jeden Tag neu berechnen.

- **Was es bringt:** Eine spätere Auswertung kann Regelvarianten fair vergleichen, etwa „hätte VIX 22 statt 20 als CAUTION-Grenze besser funktioniert?“.
- **Vorteil gegenüber heute:** Heute ist nach einer Regeländerung nicht mehr nachvollziehbar, welche Regel an welchem Tag galt.

**A1c · Nachlauf: Was ist danach passiert?**
Der Server ergänzt jeden Tag automatisch, sobald die Daten vorliegen:

- Veränderung von SPY, QQQ, IWM und DAX nach 1, 5, 20 und 60 Handelstagen
- größter Rücksetzer im selben Zeitraum
- VIX-Veränderung
- ob die Indexphase gewechselt hat

Gerechnet wird ausschließlich aus Kursen, ohne KI.

- **Was es bringt:** Jeder Ampeltag hat sein Ergebnis direkt daneben. Die spätere Auswertung muss nichts mehr nachträglich zusammensuchen.
- **Vorteil gegenüber heute:** Die Frage „War die Ampel richtig?“ wird überhaupt erst beantwortbar.

**A1d · Auswertungsbericht „Hat die Ampel funktioniert?“**
Ein Auswertungsskript rechnet die Zahlen, die KI schreibt daraus den Bericht. Die Zahlen kommen nie von der KI selbst. Ausgewertet wird:

- Ergebnis der Folgetage je Ampelzustand und je Konsequenz-Zeile
- **Lücken:** GO-Tage, nach denen der Markt deutlich fiel (Fehlalarme), und STOP-Tage, nach denen er stark stieg (verpasste Chancen)
- **Verzögerung:** Wie viele Tage nach einem Hoch bzw. Tief hat die Ampel gewechselt?
- welche Einzelsignale (VIX, Breite, Panik-Score, Phasen) am meisten beigetragen haben und welche nichts gebracht haben
- Vergleich mit einfachen Regeln, etwa „immer long“ oder „nur SPY über EMA200“: Bringt die Ampel mehr als eine simple Regel?
- deine echten Trades je Ampelzustand (aus dem Journal, siehe T6)

Was ehrlich dazugehört: Folgetage überlappen sich. Die Zahl unabhängiger Marktphasen ist auch nach Jahren klein, denn es gibt nur wenige echte Abwärtsphasen. Der Bericht nennt deshalb immer die Stichprobengröße und unterscheidet „deutlich“ von „Zufall nicht ausgeschlossen“.

- **Was es bringt:** Genau die Prüfung, die du beschreibst, auf Knopfdruck und wiederholbar.
- **Vorteil gegenüber heute:** Heute gibt es keine Möglichkeit, die Ampel gegen die Wirklichkeit zu prüfen.

**A2 · Rückblick-Ansicht**
Ein neuer Bereich „06 Rückblick“ bietet:

- einen Datumswähler
- die Schnellknöpfe „vor 1 Woche / 1 Monat / 1 Jahr“
- einen Vergleich „heute gegen damals“ nebeneinander
- Zeitreihen für VIX, Panik-Score, Marktbreite und Ampelfarbe als Streifen
- eine Suche wie „alle Tage mit VIX über 25“ oder „alle REVERSE-Tage“

- **Was es bringt:** Die Frage „Wie war das vor einem Jahr?“ ist mit einem Klick beantwortet.
- **Vorteil gegenüber heute:** Heute gibt es keinen Weg zurück hinter die letzten rund 60 Snapshots.

**A3 · Rückwirkend befüllen, soweit es ehrlich möglich ist**
Alles, was aus Kursen berechnet wird, lässt sich für vergangene Jahre aus Yahoo-Historien nachrechnen: VIX-Familie, Indexphasen, Sektorphasen, Renditen. Diese Tage werden als **„rekonstruiert“** markiert.

Nicht rekonstruierbar sind deine manuellen Sentimentwerte, die KI-Texte und Watchlist-Stände. Ob CNN eine Fear-&-Greed-Historie mitliefert, prüfe ich beim Umsetzen. Ich sage es dann, statt etwas zu erfinden.

- **Was es bringt:** Die Auswertung aus A1d muss nicht Jahre warten. Der kursbasierte Teil der Ampel (Phasen, VIX, Termstruktur, Breite der Sektoren) lässt sich sofort über rund 15 Jahre prüfen, inklusive 2018, 2020 und 2022.
- **Vorteil gegenüber heute:** Es gibt keine Lücke bis zum Start des Archivs, und die Kennzeichnung trennt gemessene von nachgerechneten Daten.
- **Grenze:** Ohne historische Sentimentwerte ist das eine vereinfachte Ampel. Das sage ich im Bericht auch so.

**A4 · Journal nicht mehr löschen, sondern archivieren**
Das bisherige „Archivieren“ (J5) wird durch eine Jahresdatei auf dem Laufwerk ersetzt. Alte Trades bleiben für alle Auswertungen erreichbar und werden nur aus der Tabellenansicht ausgeblendet.

- **Was es bringt:** Phasen- und Setup-Statistiken über alle Jahre.
- **Vorteil gegenüber heute:** Es geht keine Historie mehr verloren, und es entsteht kein Download, den man irgendwo ablegen muss.

**A5 · Trades mit dem Marktbild ihres Tages verknüpfen**
Beim Eröffnen eines Trades speichert das Journal Ampel, Konsequenz-Zeile, Indexphasen und VIX des Tages mit ab, aus dem Archiv und automatisch.

- **Was es bringt:** Zu jedem Trade ist sichtbar, wie der Markt beim Einstieg aussah.
- **Vorteil gegenüber heute:** Die Marktphase wird heute von Hand und oft gar nicht erfasst. Die Phasen-Auswertung hat deshalb Lücken.

---

## Teil C · Mehr Unterstützung für den Trendhandel am Morgen

**T1 · Echte Marktbreite aus dem S&P 500**
Die Kursabfrage des Gap-Scanners liefert für rund 600 US-Werte bereits den 50- und 200-Tage-Durchschnitt, das 52-Wochen-Hoch und -Tief und die Tagesveränderung. Ohne zusätzliche Abrufe ergeben sich daraus:

- der Anteil der Aktien über dem 50- und 200-Tage-Durchschnitt
- neue Hochs gegen neue Tiefs
- Anstieg gegen Rückgang

Alles wird im Archiv als Zeitreihe gespeichert.

- **Was es bringt:** Ein belastbares Breitenbild statt nur 11 Sektoren.
- **Vorteil gegenüber heute:** Die „Sektor-Breite 8/11“ ist grob. 600 Einzelwerte zeigen, ob ein Index von wenigen Schwergewichten getragen wird.
- **Hinweis:** Das sind einfache Durchschnitte von Yahoo, keine EMAs. Ich würde sie auch so beschriften.

**T2 · Positions-Monitor für offene Trades**
Im Tagesstart erscheinen die offenen Positionen aus dem Journal. Je Position:

- aktueller Kurs und Abstand zum Stopp in R und in ATR
- Phase des Titels heute gegen die Phase beim Einstieg
- Quartalszahlen vor dem nächsten Handelstag
- Hinweis „Stopp nachziehen möglich“, wenn das Kriterium aus deinem Handelsplan erfüllt ist, zum Beispiel ein neues Swing-Tief über dem Stopp oder EMA20 über dem Stopp

Es ist ein Hinweis, keine automatische Order.

- **Was es bringt:** Morgens siehst du sofort, welche Position Aufmerksamkeit braucht.
- **Vorteil gegenüber heute:** Der Regelcheck prüft nur die Journal-*Daten*. Mit dem aktuellen Markt verglichen werden die Positionen bisher nirgends.

**T3 · Setup-Scanner „Rücksetzer im Trend“**
Einmal täglich wird das Universum nach Titeln durchsucht, die alle diese Bedingungen erfüllen:

- in P3 (bzw. P6 für Short)
- Sektor in derselben Phase
- Korrektur über mindestens 3 Kerzen an EMA20 oder EMA50
- über dem Mindestkurs

Das Ergebnis ist eine sortierte Kandidatenliste mit Stopp-Vorschlag nach ATR, einer Positionsgröße nach deinem Risiko pro Trade und einem Kopier-Knopf für TradingView.

- **Was es bringt:** Kandidaten werden gesucht, nicht nur angezeigt.
- **Vorteil gegenüber heute:** Der Drilldown zeigt nur einen Sektor mit rund 20 Titeln, und das Einstiegskriterium „Korrektur an der EMA“ prüfst du von Hand.
- **Hinweis:** Das braucht pro Lauf einige hundert Kursabrufe. Deshalb läuft der Scanner einmal am Tag und das Ergebnis wird zwischengespeichert.

**T4 · Übernacht-Block**
Ein Block zeigt, was über Nacht passiert ist:

- US-Futures (ES, NQ)
- Asien-Schluss (Nikkei, Hang Seng)
- Öl, Bitcoin, EUR/USD

Als Kurzzeile oben, zum Beispiel „Übernacht: ES −0,6 %, Nikkei +1,1 %“.

- **Was es bringt:** Der Eröffnungs-Kontext ist auf einen Blick da.
- **Vorteil gegenüber heute:** Heute zeigt die Routine nur Tagesschlüsse. Die Bewegung seit gestern Abend fehlt.

**T5 · Tagesplan am Morgen und Tagesrückblick am Abend**
Morgens gibt es drei kurze Felder: Fokus, was ich heute nicht tue, maximale Anzahl neuer Positionen. Abends folgt ein Rückblick: Plan eingehalten? Welche Trades wurden eröffnet (automatisch aus dem Journal)? Eine Lehre des Tages. Beides geht ins Archiv.

- **Was es bringt:** Ein kurzes Tagebuch, das Disziplin messbar macht.
- **Vorteil gegenüber heute:** Die Routine beginnt den Tag, schließt ihn aber nicht ab. Notizen gibt es nur je Trade.

**T6 · Regeltreue-Auswertung**
Aus Archiv und Journal entsteht eine Auswertung:

- Ergebnis in R je Ampelzustand
- Trades gegen die Konsequenz-Zeile, etwa Long bei „nur Gaps & News“, und deren Ergebnis
- Trades in Terminwochen gegen ruhige Wochen

Die Aussagekraft der Stichprobe wird wie im Journal ehrlich gekennzeichnet.

- **Was es bringt:** Die Antwort auf die Frage: Lohnt es sich, der Ampel zu folgen?
- **Vorteil gegenüber heute:** Die Ampel wurde bisher nie gegen deine echten Ergebnisse geprüft.

**T7 · Wochenvorbereitung am Wochenende**
Am Samstag oder Sonntag zeigt die Routine:

- Wochenphasen der Indizes und Sektoren auf Wochenkerzen
- die Termine der kommenden Woche
- die Bilanz der vergangenen Woche aus dem Journal
- offene Positionen mit Quartalszahlen in der neuen Woche

- **Was es bringt:** Die Woche ist vorbereitet, bevor der Montag beginnt.
- **Vorteil gegenüber heute:** Am Wochenende zeigt die Routine dasselbe wie am Freitag.

**T8 · Benachrichtigung bei Alarm**
Wenn die Seite offen ist, meldet eine Desktop-Mitteilung des Browsers einen Alarm (VIX-Schwelle, Phasenwechsel, kritischer Regelcheck), auch wenn der Tab im Hintergrund liegt.

- **Was es bringt:** Wichtiges wird nicht übersehen.
- **Vorteil gegenüber heute:** Heute gibt es nur das Banner auf der Seite selbst.

---

## Teil D · KI: mehr Unterstützung, sauber begrenzt

### Was die KI heute tut

- Kurzbriefing (bis 560 Zeichen)
- Wochenkalender
- Fed-Konsens
- Anleihen-Erklärer
- Gap-Einordnung
- Watchlist-Check
- Journal-Coach

Die Aufrufe laufen jeder für sich: Keiner kennt die anderen, keiner kennt deine offenen Positionen, nichts wird dauerhaft gespeichert.

### Grundsatz: ein Trading-Partner mit eigener Meinung

Die KI soll wie ein erfahrener Kollege am Nebentisch arbeiten. Er sagt dir, wie die Lage ist, was in nächster Zeit ansteht und wohin er tendieren würde. Zum Beispiel: „Ich würde eher long bleiben, Trend intakt, saisonal ist ab Oktober Rückenwind“, oder „Vorsicht, nächste Woche sind US-Wahlen, das kann den Markt in beide Richtungen bewegen“. Entscheiden tust du.

Damit das ein guter Partner wird und kein überzeugend klingender Ratgeber, gelten vier Regeln:

1. **Meinung ja, aber als Meinung gekennzeichnet.** Jede Neigung kommt mit Begründung und einer ehrlichen Sicherheit (hoch, mittel, gering), dazu dem Gegenargument: „Was spräche dagegen?“
2. **Zahlen nur aus deinen Daten.** Kurse, Phasen und Ampel kommen aus der Routine. Recherchierte Fakten wie Termine oder Nachrichten kommen mit Quelle. Nichts wird erfunden.
3. **Widerspruch zu deinen Regeln wird offen angesagt.** Sieht die KI etwas anders als Ampel oder Konsequenz-Zeile, sagt sie das ausdrücklich, zum Beispiel: „Die Ampel sagt CAUTION, ich sehe aber …“. Sie stellt es nicht stillschweigend um.
4. **Jede Einschätzung wird archiviert und später bewertet** (K6, A1d). Nach einigen Monaten weißt du, ob der Partner etwas taugt oder ob die Ampel allein besser ist.

**K0 · Trading-Partner als eigenes Feld ganz oben**
Ganz oben auf der Seite steht ein kurzer Absatz im Gesprächston:

- Lage in zwei Sätzen
- Meine Neigung: eher long, eher abwarten oder eher short, mit Sicherheit und Begründung
- Was in den nächsten Tagen und Wochen ansteht: FOMC, Arbeitsmarktdaten, Wahlen, Großer Verfall, Quartalszahlen deiner Positionen
- Saisonale Lage aus den Lüddemann-Fenstern und der Saisonalität der Sektoren, die schon in der Routine stehen
- Was spräche dagegen?

Darunter gibt es ein Eingabefeld für Rückfragen, etwa „Und was heißt das für meine NVDA-Position?“. Die KI antwortet im Kontext aller Daten des Tages.

Der Partner kennt deinen Handelsplan (P3/P6, Risiko je Trade, Slots) und deine Statistik aus dem Journal. Seine Hinweise passen deshalb zu deiner Art zu handeln, etwa: „Du hast an CAUTION-Tagen bisher meist verloren.“

- **Was es bringt:** Genau der Partner, den du beschreibst: Lage, Ausblick und eine begründete Neigung in einer Minute Lesezeit.
- **Vorteil gegenüber heute:** Das heutige Briefing hat 560 Zeichen, keine Meinung, keinen Ausblick und keine Rückfragen, und es kennt weder deine Positionen noch deine Regeln.

**K1 · Strukturiertes Tagesbriefing statt Kurztext**
Die KI bekommt in einem einzigen Aufruf:

- alle Werte des Tages
- offene Positionen und Regelcheck
- Termine
- den Vortag
- denselben Tag vor einem Jahr aus dem Archiv

Sie liefert feste Abschnitte:

1. Lage in drei Sätzen
2. Handelstag nach deinen Regeln (übernommen aus der Konsequenz-Zeile, mit Begründung)
3. Was sich seit gestern geändert hat
4. Positionen mit Handlungsbedarf
5. Risiken heute (Termine, Quartalszahlen)
6. Ausblick auf die nächsten 5 Handelstage
7. Vergleich mit vor einem Jahr

- **Was es bringt:** Ein echtes Morgen-Memo, das alles verbindet.
- **Vorteil gegenüber heute:** Heute bekommt das Briefing nur die Ampelwerte und kennt weder Positionen, Termine noch Historie.

**K2 · Wochenausblick am Wochenende**
Zusammenfassung der Woche, Lage der Phasen, Termine mit Einordnung und Fragen an dich für die Vorbereitung. Gehört zu T7.

**K3 · Fragen an die Routine**
Ein Eingabefeld, zum Beispiel:

- „Wann stand der VIX zuletzt über 25, und wie lief die Ampel danach?“
- „Wie liefen meine Trades an CAUTION-Tagen?“

Die Zahlen rechnet das Programm aus Archiv und Journal. Die KI formuliert nur die Antwort und nennt die Datenbasis.

- **Was es bringt:** Das Archiv wird ohne eigene Auswertungen nutzbar.
- **Vorteil gegenüber heute:** Heute ist so eine Frage nur von Hand beantwortbar.

**K4 · Nachrichten-Scan für offene Positionen und Watchlist**
Einmal morgens, mit Websuche: Gibt es zu meinen Positionen Neuigkeiten seit gestern? Jede Meldung kommt mit Quelle und Link, und „nichts gefunden“ ist eine erlaubte Antwort.

- **Was es bringt:** Keine Überraschung durch eine Meldung zu einer gehaltenen Aktie.
- **Vorteil gegenüber heute:** Der KI-Check der Watchlist läuft heute nur auf Klick und nicht für offene Positionen.

**K5 · Journal-Coach mit Marktkontext**
Wie der heutige Coach, aber mit dem Archiv-Kontext je Trade aus A5. Beispiele: „Deine Verlierer häufen sich bei VIX über 20“, „Ausbrüche in P2 laufen schlechter als Rücksetzer in P3“. Die Aussagekraft der Stichprobe wird immer mitgenannt.

**K6 · Tagesrückblick am Abend**
Ein kurzer Vergleich: Was hat das Morgenbriefing erwartet, was ist passiert (Indexschluss, VIX)? Daraus wird mit der Zeit messbar, wie brauchbar die KI-Einschätzungen sind.

### Welche KI?

**Gemini bleibt nutzbar.** Ich würde den KI-Zugang aber in den lokalen Server verlegen und den Anbieter wählbar machen. Dann liegt der Schlüssel nicht mehr im Browser und nicht in einer URL, alle Aufrufe werden zentral protokolliert und archiviert, und ein Wechsel des Anbieters ist eine Einstellung statt einer Programmänderung.

**Claude als Alternative oder Ergänzung.** Die folgenden Angaben stammen aus der aktuellen Modellübersicht, die ich vorhin abgerufen habe. Preise gelten je 1 Million Token für Eingabe / Ausgabe:

- **Claude Opus 5.5** (`claude-opus-5-5`), 4 $ / 20 $: für Tagesbriefing, Wochenausblick und Journal-Coach, also überall, wo viele Zahlen verbunden und sorgfältig begründet werden müssen.
- **Claude Sonnet 5.5** (`claude-sonnet-5-5`), 2 $ / 10 $: für häufige Aufgaben wie den Nachrichten-Scan.
- **Claude Haiku 5.5** (`claude-haiku-5-5`), 0,10 $ / 0,50 $ bei Eingaben bis 100.000 Token: für einfache Einordnungen, zum Beispiel die Wichtigkeit von Terminen.

Für die Recherche gibt es eine eingebaute Websuche (`web_search`), die je Suche zusätzlich abgerechnet wird. Den aktuellen Suchpreis prüfe ich vor der Umsetzung. Was ein Tag kostet, rechne ich nach den ersten Läufen aus den tatsächlich verbrauchten Token aus. Eine Schätzung vorab würde ich dir nicht als Zahl verkaufen.

Wiederkehrende Teile der Anfrage (Regeln, Erklärung der Kennzahlen) lassen sich zwischenspeichern. Das senkt die Kosten bei mehreren Aufrufen am selben Morgen.

**Meine Einschätzung ohne Werbung:** Für deinen Zweck ist nicht das Modell der größte Hebel, sondern dass die KI alle Daten auf einmal bekommt und die Antworten archiviert werden (K1, A1). Das bringt mit Gemini wie mit Claude den größten Sprung.

---

## Teil E · Oberfläche: übersichtlicher und ruhiger

**Ausgangslage:** Die Morgenroutine ist eine lange Seite mit fünf Abschnitten, vielen Erklärtexten und mehreren Schaltern pro Block. Journal, Cockpit und Hub haben drei verschiedene Gestaltungen: Papier mit Serifenschrift, Tailwind-Weiß und Dunkelblau. Wichtige Antworten wie „Darf ich heute?“, „Was steht an?“ und „Wo muss ich handeln?“ verteilen sich über die ganze Seite.

**U1 · Eine Startzeile, die in 5 Sekunden alles sagt**
Oben steht fest eine schmale Zeile mit:

- Ampel und Konsequenz-Zeile
- Neigung des Trading-Partners
- Termine heute
- Anzahl Positionen mit Handlungsbedarf
- Börsenstatus

Jedes Element ist anklickbar und springt zum Detail.

- **Vorteil gegenüber heute:** Die Antwort steht oben, die Belege darunter. Heute muss man scrollen und zusammensetzen.

**U2 · Reiter statt einer langen Seite**
Die Inhalte verteilen sich auf: Heute · Markt · Kandidaten · Positionen · Kalender · Rückblick · Einstellungen. Der Reiter „Heute“ enthält nur das Tägliche, alles andere ist einen Klick entfernt.

- **Vorteil gegenüber heute:** Weniger Scrollen. Die Seite zeigt, was man braucht, und nicht alles auf einmal.

**U3 · Details eingeklappt, Erklärungen als kleines „?“**
Die langen Erklärtexte, etwa im Treasury-Block oder bei der Konsequenz-Zeile, öffnen sich nur bei Bedarf. In der Normalansicht stehen Zahl und Farbe.

- **Vorteil gegenüber heute:** Ruhigeres Bild. Die Erklärungen bleiben erhalten, stören aber nicht mehr.

**U4 · Ein Erscheinungsbild für alle Werkzeuge**
Morgenroutine, Journal, Cockpit und Hub bekommen dieselben Farben, Schriften und Bausteine, mit Hell- und Dunkelmodus überall gleich. Die Farbsprache ist fest: Grün für Long/gut, Rot für Short/Gefahr, Gelb für Vorsicht. Dazu eine gemeinsame Kopfzeile, über die man zwischen den Werkzeugen wechselt.

- **Vorteil gegenüber heute:** Man findet sich überall sofort zurecht, statt zwischen drei Stilen zu springen. Die Bibliothek für Tailwind vom CDN (F19) entfällt dabei.

**U5 · Mini-Verläufe statt nur Zahlen**
Bei VIX, Panik-Score, Marktbreite und jedem Index gibt es eine kleine Linie der letzten 20 Tage direkt neben der Zahl.

- **Vorteil gegenüber heute:** Man sieht auf einen Blick, ob ein Wert steigt oder fällt. Heute gibt es nur den Wert und das Delta zum Vortag.

**U6 · Handy- und Tablet-Ansicht**
Eine schlanke Ansicht mit Startzeile, Trading-Partner und Positionen, im Heimnetz über den lokalen Server erreichbar.

- **Vorteil gegenüber heute:** Die Lage morgens am Handy prüfen, ohne den PC hochzufahren.
- **Hinweis:** Der Server lauscht heute bewusst nur auf dem eigenen Rechner. Für das Handy müsste er ins Heimnetz geöffnet werden, mit Passwortschutz. Das würde ich nur auf deinen Wunsch hin umsetzen.

**U7 · Einstellungen als eigene Seite mit Pflegebereich**
Gemini-Schlüssel, Datenordner, FOMC-Termine, Alarme, Handelsplan-Werte und Pflegehinweise (V13) stehen zusammen auf einer Seite statt in einer ausklappbaren Leiste.

- **Vorteil gegenüber heute:** Alle Einstellungen sind an einem Ort und nicht in Leisten, eigenen Terminfeldern und Code verteilt.

**U8 · Schnellsuche für Ticker**
Ein Ticker in die Suche getippt zeigt auf einer Karte: Chart mit Phase, deine Trades in diesem Wert aus dem Journal, Quartalszahlen, Watchlist-Status und den Knopf „Trade vorbereiten“.

- **Vorteil gegenüber heute:** Alles zu einem Wert an einer Stelle, statt Journal, Watchlist und Chart einzeln zu öffnen.

Wenn du möchtest, baue ich vor der Umsetzung eine anklickbare Vorschau der neuen Oberfläche mit Beispieldaten. Dann kannst du das Aussehen beurteilen, bevor ich am echten Programm etwas ändere.

---

## Teil F · Weitere Vorschläge

**W1 · Handelsplan als eine Datei**
Alle Regeln stehen an einer Stelle:

- Risiko je Trade
- Slots
- Ampelschwellen
- Panik-Gewichte
- Mindestkurs
- DTE-Grenze

Morgenroutine, Journal, REGELCHECK und KI lesen alle diese eine Datei, und jede Änderung bekommt automatisch eine neue Versionsnummer (A1b).

- **Vorteil gegenüber heute:** Heute stehen die Regeln an mehreren Stellen und widersprechen sich, zum Beispiel 1,0 % Risiko im Journal gegen 0,25 % im REGELCHECK (J8).

**W2 · Termine regelbasiert vervollständigen**
Ergänzt werden alle Termine, die nach festen Regeln entstehen:

- großer Verfall (dritter Freitag), Quartalsverfall (Hexensabbat)
- US-Wahltermine
- Index-Neugewichtungen
- verkürzte Handelstage

Wahltermine pflegst du einmal im Jahr in eine Liste, so wie bisher die FOMC-Termine.

- **Vorteil gegenüber heute:** Solche Termine fehlen heute. Ob die KI sie im Wochenkalender erwähnt, ist Zufall.

**W3 · „Trade vorbereiten“ von der Morgenroutine ins Journal**
Aus einem Kandidaten, einem Gap oder der Ticker-Suche öffnet ein Knopf das Journal mit vorausgefülltem Formular: Symbol, Richtung, Stopp nach ATR, Größe nach Risiko, Marktphase, Setup. Das Marktbild des Tages wird automatisch übernommen (A5).

- **Vorteil gegenüber heute:** Weniger Abtippen, weniger Tippfehler, und Marktphase und Kontext sind immer erfasst.

**W4 · Täglicher Abgleich mit dem Broker**
IB bietet einen Flex-Web-Service, über den sich Positionen und Ausführungen automatisch abholen lassen. Ob CapTrader diesen Zugang für dein Konto freigibt, prüfe ich vor der Umsetzung. Falls ja, vergleicht die Routine jeden Morgen die offenen Positionen im Journal mit denen beim Broker.

- **Vorteil gegenüber heute:** Der monatliche Abgleich von Hand entfällt, und fehlende oder doppelte Positionen fallen am selben Tag auf.

**W5 · Monatsbericht automatisch**
Zum Monatsende entsteht ein Bericht mit:

- Ampelverlauf
- deine Trades und Regeltreue
- Treffsicherheit des Trading-Partners
- Auffälligkeiten

Gespeichert wird er im Archiv als lesbare Datei.

- **Vorteil gegenüber heute:** Eine regelmäßige Rückschau, ohne sie selbst zusammenzustellen.

**W6 · Update mit einem Klick und Versionsprüfung**
Neue Programmversionen lassen sich aus dem Repository einspielen. Der Server prüft dabei, ob alle Dateien zusammenpassen (V15), und legt vorher eine Sicherung an.

- **Vorteil gegenüber heute:** Laut Änderungsprotokoll werden heute vier Dateien von Hand kopiert, und eine vergessene Datei fällt nicht auf.

---

## Freigabe

Zur Auswahl stehen:

- **Fehler:** J1 bis J8 und C1 bis C3, zusätzlich zu F1 bis F20 und V1 bis V16 aus dem ersten Bericht
- **Archiv:** A1 bis A5, inklusive A1b bis A1d für die spätere Auswertung der Ampel
- **Trendhandel:** T1 bis T8
- **KI:** K0 (Trading-Partner) bis K6, dazu die Frage, ob Gemini bleibt, Claude dazukommt oder beides wählbar wird
- **Oberfläche:** U1 bis U8, auf Wunsch zuerst als anklickbare Vorschau
- **Weitere:** W1 bis W6

Mein Vorschlag für die Reihenfolge, falls du eine willst:

1. J1 bis J3, weil diese Fehler Daten verfälschen
2. A1 und A2, weil jeder Tag ohne Archiv verloren ist
3. danach T2, T1 und K1

Für das Stillhalter-Journal brauche ich die Datei `stillhalter_journal_v6.html`.
