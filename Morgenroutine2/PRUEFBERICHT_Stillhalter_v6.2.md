# Prüfbericht Stillhalter-Journal v6.2

Stand: 02.11.2026. Geprüft wurde `stillhalter_journal_v6.html` (hochgeladen als `stillhalter_journal_v6_1.html`), vollständig Zeile für Zeile. Die JavaScript-Syntax ist fehlerfrei. Die Kennungen SH dienen zur Umsetzung in Phase 1. An der Datei selbst ist noch nichts geändert, sie liegt nur unter dem Namen im Repository, den Hub und Cockpit erwarten.

**TL;DR:** Das Journal ist sorgfältig gebaut: Selbstkontrolle, Roll-Ketten, Wheel-Berechnung und Euro-Umrechnung sind größtenteils sauber. Ein Fehler ist gefährlich: Der Knopf „⚠ Reset“ löscht nicht nur das Stillhalter-Journal, sondern die Browserdaten **aller** Werkzeuge. Dazu kommen fünf mittlere und einige kleine Fehler.

## Fehler

**SH1 · „⚠ Reset“ löscht alle Werkzeuge** (hoch, aus dem Code)
`localStorage.clear()` (Zeile 151) leert den gesamten Browserspeicher für `localhost:8765`. Den teilen sich Morgenroutine, Trading Journal, Cockpit und Stillhalter-Journal. Weg wären unter anderem:

- der Gemini-Schlüssel und die Einstellungen der Morgenroutine
- die Browserkopie des Trading Journals samt Synchronisations-Zeitstempel
- die Zwischenspeicher aller Werkzeuge

Die Laufwerksdateien bleiben erhalten, aber die Rückfrage „ALLE Daten löschen?“ lässt nicht erkennen, dass auch die anderen Werkzeuge betroffen sind. Richtig wäre: nur die eigenen Schlüssel `soj4_*` löschen.

**SH2 · Close-Typ geändert, Status bleibt alt** (mittel, aus dem Code)
`saveTrade()` (Zeilen 989–999): Wird bei einer geschlossenen Position der Close-Typ korrigiert, zum Beispiel von „Buy to Close“ auf „Expired“, übernimmt das Programm den neuen Close-Typ, lässt aber den alten Status stehen. Status und Close-Typ widersprechen sich danach. Die Folgen:

- Die Selbstkontrolle rechnet mit dem falschen P&L-Muster und meldet Fehlalarme.
- Ein nachträglich als „Assigned“ korrigierter Trade erscheint nicht im Wheel.

**SH3 · Roll-Verknüpfung geht beim Bearbeiten verloren** (mittel, aus dem Code)
Beim Bearbeiten wird die Position neu zusammengesetzt, aber ohne `rolledTo`, also den Zeiger auf die Anschlussposition. Die Kette im Journal selbst bleibt sichtbar, weil sie auch rückwärts gelesen wird. **REGELCHECK prüft aber nur `rolledTo`** (`REGELCHECK.py:315`) und meldet deshalb fälschlich „Roll ohne Nachfolger“. Das gilt auch für alle Rolls aus der Zeit vor v6.0, die diesen Zeiger nie hatten. Behebung an beiden Stellen: Zeiger beim Bearbeiten erhalten, und REGELCHECK erkennt den Nachfolger auch rückwärts über `rolledFrom`.

**SH4 · Risiko-Seite mischt Dollar und Euro** (mittel, aus dem Code)
`rRisk()` (Zeilen 1080–1117) ist bei der Euro-Umstellung in v6.1.1 vergessen worden:

- Die Kontogröße (in Euro erfasst) wird mit Dollarzeichen angezeigt.
- Das offene Risiko (bereits in Euro) erscheint ebenfalls mit Dollarzeichen.
- Das Risiko je Basiswert steht in Dollar und wird durch die Euro-Kontogröße geteilt. Die Prozente liegen dadurch rund 8 % zu hoch.

**SH5 · Dauerwarnung bei Covered Calls und Strangles** (gering bis mittel, aus dem Code)
Die Selbstkontrolle (Prüfung 9) meldet jeden offenen Covered Call und jeden Strangle als „ohne berechenbares Risiko“. Beim Covered Call ist das normal, weil die Aktien den Call decken. Die Warnung steht damit dauerhaft da und verdeckt echte Befunde.

Beim **Short Strangle** ist das Risiko nach oben unbegrenzt, fließt aber mit 0 ins Kontorisiko ein. Das sollte ausdrücklich als „unbegrenzt“ angezeigt werden.

**SH6 · Monatsziel in Euro gegen Prämien in Dollar** (gering, aus dem Code)
Das Feld heißt „Monatl. Ziel (€)“, verglichen werden aber Dollar-Prämien (Zeilen 709–712).

**SH7 · Kleinere Punkte** (aus dem Code)

- „Wieder öffnen“ lässt Assignment-Daten, FX-Kurs und Close-Notiz stehen (Zeile 1030).
- Wird ein Glied einer Roll-Kette gelöscht, bleiben die Zeiger der Nachbarn auf eine nicht mehr vorhandene Position stehen.
- Der Hinweis beim Einpflegen von Altbestand nennt das Feld „UL-Preis“, es heißt aber „Kaufkurs“ (Zeile 1310).
- Im Kopf steht „v6.1“, im Titel „v6.2“.
- Der KI-Coach schickt das ganze Portfolio mit allen Notizen an Gemini und den Schlüssel in der Adresse. Das wird mit Phase 5 über den lokalen Server gelöst.
- Optionen in Euro werden mit Multiplikator 100 gerechnet. Für Eurex-Aktienoptionen stimmt das. Für DAX-Optionen (ODAX, Multiplikator 5) wäre es falsch. Bitte kurz bestätigen, ob du DAX-Optionen handelst.

## Was gut gelöst ist

- Selbstkontrolle mit P&L-Nachrechnung
- Schutz vor Assignment bei barabgerechneten Indizes
- Roll-Ketten mit Netto-Credit über die ganze Kette
- Wheel-Einstand inklusive Adjustments
- Rückfrage, wenn ein anderer Rechner die Datei geändert hat
- Datumsangaben in lokaler Zeit

Diese Punkte bleiben unverändert.
