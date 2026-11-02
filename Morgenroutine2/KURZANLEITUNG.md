# Kurzanleitung: Einrichten auf dem PC

Stand: 02.11.2026 · Morgenroutine v6.19 · Journal v6.7 · Stillhalter v6.4 · Cockpit v6.3 · Hub v6.3 · Marktsammler v1.2.7

## 1. Dateien übernehmen

- Den Ordner `Morgenroutine2` an die bisherige Stelle kopieren. `daten/` und `backups/` vorher sichern. Die Programmdateien überschreiben sie nicht.
- Neu im Ordner: `handelsplan.json`, `sektoren.json`, `setup_scanner.py`, `marktsammler.py`, `ki_anbindung.py`, `telegram_bot.py`, `auswertung/`, `tests/`.
- `START_Batch.bat` starten. Im Fenster muss **SERVER-VERSION 6.19** stehen.

## 2. Marktsammler auf v1.2.7

- Im Marktsammler-Ordner `sammler.py`, `README.md` und `start_sammler.bat` durch die Dateien aus `Marktsammler/` ersetzen. `daten/` bleibt, wie es ist.
- Starten. Die Statusseite zeigt die neue Karte **IV-Tageswerte**. Beim ersten Lauf holt der Sammler die IV-Historie, danach täglich nur das Fehlende.
- In der Morgenroutine unter **⚙ → Marktsammler-Ordner** den Ordner eintragen, in dem `sammler.py` liegt.

## 3. KI (optional)

- Unter **⚙ → KI**: den Gemini-Schlüssel eintragen und auf Wunsch den Claude-Schlüssel. Als Anbieter ist Gemini voreingestellt.
- Für Claude einmalig im Programmordner ausführen:

```bash
pip install anthropic
```

- Die Schlüssel liegen danach nur in `ki_schluessel.json` auf diesem PC und nicht mehr im Browser.

## 4. Telegram (Handy)

1. In Telegram **@BotFather** anschreiben, `/newbot` senden und einen Namen vergeben. Du bekommst ein Token.
2. Das Token unter **⚙ → Telegram** eintragen und speichern.
3. Deinem Bot `/start` schicken. Er antwortet mit deiner Chat-ID.
4. Die Chat-ID eintragen, speichern und auf **Test senden** drücken.

Danach kommt nach dem ersten Lauf des Tages die Zusammenfassung. Mit `/lage` und `/positionen` fragst du jederzeit nach.

## 5. Einmalig

- **📚 Archiv & Rückblick → ⏪ Rückrechnung einspielen**: trägt 2007 bis 2026 ins Archiv ein.
- Im **Cockpit → ⚖ Gesamtrisiko** die Gold- und Silber-ETFs als „Sonstige Bestände“ eintragen.
- Unter **⚙ → Desktop-Mitteilungen erlauben**.

## 6. Prüfen nach dem ersten Lauf

- **Diagnose → Pflege-Übersicht:** Alles sollte ✓ zeigen. Bei „Marktsammler“ steht, wie viele Werte aus dem Sammler und wie viele aus Yahoo kamen.
- **Setup-Scanner ▶ Scannen:** Prüfen, ob „Volumen-Einheit ungeprüft“ erscheint.
- **Unter der Ampel:** Die Aktien-Breite sollte rund 500 S&P-Werte zeigen.
- **Selbsttest:** im Ordner `Morgenroutine2` ausführen. Erwartet: „63 bestanden, 0 fehlgeschlagen“.

```bash
node tests/selbsttest.js
```
