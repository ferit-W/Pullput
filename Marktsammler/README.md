# Marktsammler v1.2.7

Sammelt nur (keine Orders). Statusseite: http://127.0.0.1:8770/  ·  TWS Paper Port 7497, Client-ID 80.

## Umstieg von v1.1
1. v1.1 beenden (Fenster schließen), den ganzen Ordner `daten` aus v1.1 in diesen Ordner kopieren.
2. `start_sammler.bat` doppelklicken. Er liest, was schon da ist, und holt nur das Fehlende (Tageskerzen und Stundenkerzen bleiben unangetastet).
3. Neue Watchlist-Zeilen eintragen und auf der Statusseite **Aktualisieren** drücken: Watchlist wird neu gelesen, fehlende und veraltete Kerzen werden nachgeholt, Werte ohne Kontrakt werden erneut versucht.

## Neu in v1.2
- Watchlist 844 Werte, Spalten: symbol;typ;boerse;waehrung;rth;gruppe;untergruppe;name;handelsklasse;multiplikator;stufen. gruppe = Aktie, Index, ETF, Future, Währung. untergruppe = Index/Bereich (S&P500, Nasdaq100, DAX, MDAX, SDAX, Branchen, Anleihen, Rohstoffe, Länder, Metalle, Energie, Agrar, Zinsen, Währungs-Futures, Devisenpaare ...), mehrere mit |. stufen = D (Tage), H (Stunden), M5 (5 Minuten).
- 5-Minuten-Kerzen (Ordner `fuenfminuten`) für 141 Leitwerte: Indizes, alle Futures, DAX, 30 US-Schwergewichte, wichtige ETFs, EUR/USD. Rückwärts bis 2 Jahre (`M5_JAHRE`). 30 Minuten und 10 Minuten bitte aus den 5-Minuten-Kerzen berechnen.
- Statusseite: Aktualisieren-Knopf, Vollständigkeit pro Gruppe und pro Index (Tage, Stunden, 5 Min). Zelle anklicken zeigt die fehlenden Werte mit Name, Grund und letzter Kerze.
- Laufzeit pro Kerzenlänge steht auf der Statusseite und in `daten\_laufzeit.csv`.
- Wartet nicht mehr 2,5 s bei Werten, die schon aktuell sind (Aktualisieren geht dadurch deutlich schneller).
- Stückgrößen der Historie passen sich selbst an, wenn die TWS ein Stück zu groß findet; bei einer Pacing-Meldung mitten in der Historie wird wiederholt statt die Historie abzuschneiden.
- Reihenfolge je Kerzenlänge: alles außer MDAX/SDAX, dann MDAX, zuletzt SDAX.
- Die SPX/SPXW-Optionskette ist unverändert (gleiche Dateien, Durchlaufnummer läuft weiter).

## Fehler aus v1.1, jetzt behoben
ES und CL standen in der Watchlist als Aktie (Eversource, Colgate) und als Future und schrieben in dieselbe Datei. Jetzt heißen die Future-Dateien `ES_FUT.csv` und `CL_FUT.csv`, deutsche Aktien mit US-Doppelgänger `DTE_DE.csv`, `MRK_DE.csv`, `NEM_DE.csv`, `SPG_DE.csv`. Die vermischten alten Dateien ES.csv und CL.csv werden beim ersten Start nach `daten\_kollision_sicherung` verschoben und beide Werte frisch geholt.

## Wichtig
- Kontrakte werden gegen die TWS geprüft. Findet sie ein Kürzel nicht (Eurex-/Xetra-Kürzel, Futures an NYBOT/EUREX), steht der Wert mit Grund in der Fehlend-Liste; mit der Spalte `boerse` korrigieren und Aktualisieren drücken. Ersatzbörsen werden automatisch probiert (IBIS-SMART, NYBOT-ICEUS, EUREX-DTB).
- Indexlisten: DAX Stand 22.09.2025, MDAX Stand 01/2023 (veraltet), SDAX Stand 12/2025 mit Kürzeln nach bestem Wissen; Nasdaq-100 und S&P 500 aktuell (29.10.2026). MDAX/SDAX bitte nach Fehlend-Liste bereinigen.
- Xetra-Kurse brauchen eine Marktdaten-Freigabe im Paper-Konto, sonst steht "keine Daten" mit TWS-Meldung in der Liste.
- Noch nicht enthalten (v1.3): Futures-Einzelkontrakte roh mit Kontraktmonat und Rolldatum, COT, Futures-Optionsketten. (Implied-Volatility-Historie: seit v1.2.7 für Aktien, ETFs und Indizes.)
- Nur in der Simulation getestet (`python sammler.py --sim`); gegen die echte TWS bitte Protokoll und Statusseite beobachten.

## Änderungen v1.2.1
- Warner Bros. Discovery (WBD) und Electronic Arts (EA) aus der Watchlist genommen (TWS kennt sie nicht unter diesem Kürzel). Mexikanischer-Peso-Future heißt bei IBKR MXP statt MXN.
- Fehlende Marktdaten-Berechtigung (z. B. Xetra/IBIS) wird nach drei Treffern je Börse erkannt, der Rest dieser Börse wird in diesem Lauf übersprungen und mit klarem Hinweis gelistet. Aktualisieren versucht es wieder.
- Umlaute in den TWS-Meldungen werden lesbar angezeigt.

## Änderungen v1.2.2
- Historie mit bis zu 4 gleichzeitigen Anfragen (`PARALLEL` oben in sammler.py, jeder Wert immer nur in einer Anfrage). Das Aktualisieren der Tageskerzen für alle Werte dauert damit grob ein Viertel. Bei Pacing-Meldungen der TWS bremst der Sammler wie bisher selbst; wenn das oft im Protokoll steht, `PARALLEL` auf 2 oder 3 senken.
- Fehlermeldungen der TWS werden jetzt dem richtigen Wert zugeordnet (wichtig bei parallelen Anfragen).
- Die Watchlist ist unverändert gegenüber v1.2.1 (842 Werte). Zeigt die Statusseite 844 Werte, liegt noch die alte Watchlist aus v1.2 im Ordner: die `watchlist.csv` aus diesem ZIP kopieren und Aktualisieren drücken.

## Änderungen v1.2.7
- **Implizite Volatilität als Tageswert** (neuer Ordner `daten/iv_tage`, gleiches Dateiformat wie die Tageskerzen; Wert als Dezimalzahl, 0,25 = 25 %). Quelle ist der TWS-Datentyp `OPTION_IMPLIED_VOLATILITY` (30-Tage-IV, auf ein Jahr hochgerechnet).
- Jeder Wert mit Tageskerzen vom Typ Aktie/ETF oder Index bekommt die Stufe IV automatisch — die Watchlist muss nicht geändert werden. Futures und Devisen bekommen keine IV: Die TWS bietet diesen Datentyp dafür nicht an.
- Erster Lauf: so weit zurück wie die TWS liefert (5 Jahre, bei Fehlermeldung 2 Jahre, 1 Jahr, 6 Monate). Danach täglich nur die Differenz, eine Abfrage je Wert, direkt nach den Tageskerzen.
- Statusseite: Karte „IV-Tageswerte“ und Spalte IV in Vollständigkeit und Werteliste.
- Die Morgenroutine (ab v6.19) liest daraus IV, IV-Rang und IV-Perzentil für Stillhalter-Journal, Watchlist und Positions-Monitor.
- Getestet in der Simulation (`python sammler.py --sim --sim-hist`). Gegen die echte TWS bitte beim ersten Lauf das Protokoll ansehen: Meldet die TWS für einzelne Werte „no data“, stehen sie mit Grund in der Fehlend-Liste (Spalte IV).

## Änderungen v1.2.6
- Watchlist: 5-Minuten-Kerzen jetzt auch für alle ETFs, alle Nasdaq-100-Aktien und alle Indizes (vorher 141 Werte). Zum Übernehmen `watchlist.csv` kopieren und auf der Statusseite Aktualisieren drücken.

## Änderungen v1.2.5
- 5-Minuten-Kerzen in zwei Stufen: Zuerst nur die letzten 3 Monate (`M5_ERST`) für alle Werte, das sind etwa 4-mal weniger Abfragen als vorher und alle Werte sind schnell nutzbar. Erst danach, nach allem anderen, holt der Sammler die 5-Minuten-Kerzen bis 2 Jahre zurück (`M5_JAHRE`), Wert für Wert, jederzeit unterbrechbar (Optionszeit, Stopp, Aktualisieren) und mit Fortsetzung. Was die TWS nicht weiter zurück hat, merkt er sich in `daten/_tiefe.json`.
- Das tägliche Update bleibt eine einzige Abfrage je Wert.

## Änderungen v1.2.4
- Schneller: 8 statt 4 gleichzeitige Arbeiter (`PARALLEL`), Pause zwischen zwei Abfragen 0,6 s statt 2,5 s (`HIST_PAUSE`). Bei einer Pacing-Meldung der TWS bremst der Sammler selbst bis auf 15 s und baut die Pause danach schnell wieder ab (vorher blieb sie nach einer einzigen Meldung stundenlang hoch).
- Das Protokoll zeigt jetzt je Stunden-/5-Minuten-Wert: Anzahl Abfragen, Sekunden je Abfrage, Stückgröße, aktuelle Pause. Damit sieht man sofort, ob die TWS selbst langsam antwortet.

## Änderungen v1.2.3
- Behoben: Bei Futures (Dauer-Kontrakt) hat der Sammler die Historie rückwärts mit Enddatum geholt. Das erlaubt die TWS nicht (Meldung 10339) und trennt dann die Verbindung ("Socket disconnect"), im Protokoll 211 Mal. Jetzt holt er bei Futures genau ein Stück ab jetzt, in der größten Stückgröße, die die TWS liefert. Die tiefe Futures-Historie kommt später aus den Einzelkontrakten (v1.3).
- Meldungen wie "not supported" lassen die Stückgröße der Aktien nicht mehr schrumpfen.
- Fehlende Berechtigung wird auch für Devisenpaare (IDEALPRO) nach drei Treffern erkannt und der Rest übersprungen.
