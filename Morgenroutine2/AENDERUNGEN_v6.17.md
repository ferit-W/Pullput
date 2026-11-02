# Morgenroutine v6.17 · Server 6.4 · REGELCHECK 1.2

Stand 06.10.2026. Ersetzt werden nur vier Dateien: ferit_morgenroutine_v6.html, START_Morgenroutine_v6.py, REGELCHECK.py, Trading-Hub_v6.html.
Die Ordner `daten/` und `backups/` bleiben unberührt. Nach dem Kopieren das Server-Fenster schließen und START_Batch.bat neu starten. Die Konsole muss dann „SERVER-VERSION 6.4“ und „Build 6.17“ zeigen.

## Behobene Fehler

### Server 6.4
1. **Fremde Webseiten konnten Daten überschreiben (Sicherheit).** Der Host-Check wirkte nur gegen DNS-Rebinding. Ein „einfacher“ POST von einer beliebigen geöffneten Webseite an localhost:8765 kam durch. Damit ließen sich Journale überschreiben oder der Datenordner umbiegen. Jetzt nimmt der Server POST-Anfragen aus dem Browser nur noch von den eigenen Seiten an (Origin localhost:8765 / 127.0.0.1:8765). Abgewiesene Versuche erscheinen in der Konsole.
2. **CORS** wurde vorher für jede lokale Anwendung auf jedem Port freigegeben, jetzt nur noch für Port 8765.
3. **Gleichzeitiges Speichern** desselben Datensatzes, etwa aus zwei offenen Tabs, schrieb in dieselbe .tmp-Datei. Das konnte ein kaputtes JSON erzeugen. Jetzt gibt es eine Sperre je Datensatz und eine eindeutige Temp-Datei. Getestet mit 25 parallelen Speichervorgängen: Ergebnis gültig, keine Reste.

### REGELCHECK 1.2
4. **Altbestand wurde wie Trading geprüft:** „kein Stopp“ als KRITISCH, Zählung aufs Slot-Limit und ins offene Risiko. Altbestand ist jetzt ausgenommen, genau wie im Journal.
5. **AKJ zählte auf das Trend-Limit** von 10 Positionen. Für das Slot-Limit zählt jetzt nur noch die Kategorie Trading. Stopp- und Risikoprüfung gelten weiter für AKJ.
6. Farben in der Windows-Konsole werden jetzt aktiviert statt abgeschaltet.

### Morgenroutine v6.17
7. **Konsequenz-Zeile ohne Farbe:** `--t1/--t2/--t3/--grn/--amb` wurden an etwa 30 Stellen benutzt, waren aber nie definiert. Dadurch fehlten Farbrahmen und Ampelfarbe des wichtigsten Blocks. Die Variablen sind jetzt als Aliase auf die bestehende Palette definiert, Dunkelmodus inklusive.
8. **„Nur Gaps & News“ wurde grün gezeichnet:** Der Vergleich prüfte auf `'nur GAP/News'`, gesetzt wird aber `'nur Gaps und News'`. Jetzt erscheint die Zeile gelb, mit Kurztext „Nur Gaps & News · klein“.
9. **Zeitumstellung:** „8:30 ET = 14:30“ galt als ganzjährig. Vom 26. bis 30.10.2026 stimmt das nicht. Die US-Daten kommen dann um 13:30, die **FOMC-Entscheidung am 28.10. um 19:00**. Die alte Korrektur hätte richtige Zeiten auf falsche „korrigiert“. Zeiten werden jetzt in New Yorker Zeit geführt und für den konkreten Tag umgerechnet. Das gilt auch für „halber Tag · Schluss …“ in der Kopfzeile.
10. **Sync-Lücken:** Alarm-Schwellen, Klappzustände, KI-Automatik, „FOMC zurücksetzen“ und „History löschen“ schrieben am Server-Sync vorbei. Jetzt laufen alle über den zentralen Speicherweg.
11. **FOMC-Liste lief am 09.12.2026 aus.** Ergänzt sind alle 8 Termine 2027 und der 26.01.2028, laut federalreserve.gov (abgerufen 06.10.2026).
12. **Öffentliche Proxys trotz laufendem Server:** Ein Tippfehler in der Watchliste löste bisher vier fremde Proxys mit je 9 s Wartezeit aus und färbte den Proxy-Chip rot. Läuft der lokale Server, gilt jetzt seine Antwort. Getestet: Ein Lauf ohne Yahoo-Zugriff endet in 6 s statt nach Minuten.
13. **„Morgenroutine komplett ✓“ ohne einen einzigen Kurs:** Die Meldung erschien trotzdem, und der Datenstand wurde auf „gerade eben“ gesetzt. Jetzt kommt in dem Fall eine Fehlermeldung, und der Stand bleibt alt.
14. **Saisonfenster am letzten Tag** zeigte „endet in 365 Tagen“.
15. Banner und Hub nannten Dateinamen, die es nicht gibt (START_Morgenroutine.bat). Jetzt steht dort START_Batch.bat.
16. Versionsanzeige vereinheitlicht: Titel, Kopf, „Build 6.17“ für den Server-Selbstcheck und Fußzeile (stand noch auf v15.16).

## Neu: Unterstützung für den Tagesstart
- **Block „🧭 Tagesstart“** direkt unter dem Lagebild, lädt sofort beim Öffnen:
  - Börsenstatus **NYSE und XETRA** mit Handelszeiten in deutscher Zeit. Feiertage und halbe Tage werden gerechnet.
  - **Termine von heute:** FOMC, Arbeitsmarktdaten, eigene Termine, Watchlist-Earnings und die marktbewegenden Einträge des KI-Kalenders, sofern schon geladen. Dafür wird kein zusätzlicher KI-Aufruf gemacht.
  - **Regelcheck der offenen Positionen:** dieselbe Prüfung wie REGELCHECK.py. Kritische Befunde stehen rot, Warnungen gelb, Hinweise sind eingeklappt. Er wird nach jedem Lauf und per „↻ prüfen“ aktualisiert. Neuer Server-Endpunkt `/regelcheck`, die Regeln stehen weiterhin nur in REGELCHECK.py.
- **Autostart (optional):** in den Einstellungen unter „Beim Öffnen“. Die Routine startet selbst, wenn die Daten älter als 60 Min sind. Die Einstellung wird mit dem Server synchronisiert. Standard bleibt aus.
- **Tastenkürzel:** `R` startet die Routine, `G` öffnet den Gap-Scanner und scannt.
- **Ampel im Tab-Titel**, z. B. „🟡 CAUTION · Morgenroutine“.
- **Übergangsphasen mit Kürzel:** P1, P2, P4 und P5 heißen jetzt „P4 · kein Setup“ statt „– · neutral“. Das gilt für Indizes, Rohstoffe, Watchlist und Chart. Das 6-Phasen-Popup ist an die tatsächliche Rechenlogik angeglichen.

## Bewusst nicht geändert
- Keine Änderung an Ampel-Schwellen, Panik-Gewichten, Phasenlogik oder Sektor-Drilldown.
- Trading Journal, Depot-Cockpit und START_Batch.bat sind unverändert.
