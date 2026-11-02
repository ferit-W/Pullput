# Phase 2b: Test des eigenen Handelssystems (S1–S4)

Stand: 02.11.2026. Die Regeln wurden vor der Auswertung festgelegt und eingecheckt (`system_test.py`, Commit da261a2). Danach wurde nichts angepasst. Die Rohergebnisse stehen in `ergebnisse/system_test.json`.

**Absprache:** Das Ergebnis ist eine Information, **kein Handelsstopp**. Ein „bringt nichts“ heißt nur, dass sich ein Kriterium in diesen Daten nicht messbar auszahlt.

## Kurzfassung

- **Der Rücksetzer-Einstieg in Phase 3 hatte in beiden Zeiträumen einen positiven Erwartungswert.** Ohne Filter waren es +0,22 R (2017–2021) und +0,10 R (2022–2026) je Trade.
- **„Platz bis zum Widerstand“ (K2) ist das einzige deiner drei Kriterien, das klar geholfen hat:** mit Ampel in allen vier Vergleichen und in beiden Zeiträumen.
- **„Relative Stärke gegen den Sektor“ (K3) war gemischt:** 2022–2026 in allen vier Vergleichen besser, 2017–2021 nur in zwei von vier.
- **„Nähe zum 52-Wochen-Hoch“ (K1) hat in allen Vergleichen geschadet.** Wichtig: Das ist nur eine Näherung für dein „Allzeithoch“, siehe Grenzen.
- **Nachziehende Stopps schlugen feste Ziele.** Mit festem Ziel bei CRV 2 oder 3 war 2022–2026 der Erwartungswert negativ.
- **Der 52-Wochen-Ausbruch (S4) war schwächer als der Rücksetzer-Einstieg.**
- **Verlustphasen sind lang:** 104,6 R Rückgang von September 2021 bis Mai 2023, längste Verlustserie 33 Trades. Bei 0,25 % Risiko sind das rund −26 %.

## Was getestet wurde

**Daten:** 488 heutige S&P-500-Aktien, 2016–2026, Sektor nach GICS. Geprüft wurde von 11/2017 bis 09/2026 in zwei Zeiträumen: A = 2017–2021, B = 2022–2026.

**Grundsignal (T):** Phase 3, an einem der 5 Vortage Schluss unter der EMA20, heute Schluss wieder darüber. Einstieg zur nächsten Eröffnung. Stopp am tiefsten Tief der letzten 10 Tage.

**Portfolio:** höchstens 10 Positionen, 0,25 % Risiko je Trade, 0,1 % Kosten je Trade. 20 Durchläufe mit zufälliger Auswahl, wenn mehr Kandidaten als freie Plätze da waren.

## S1: Was jedes Kriterium beiträgt

Erwartungswert je Trade in R, Zeitraum A / B, **mit Ampel** (keine neuen Einstiege bei STOP und REVERSE):

- T allein: 0,175 / 0,036
- T + K2 (Platz): **0,232 / 0,060**
- T + K3 (RS Sektor): 0,173 / 0,062
- T + K2 + K3: **0,239 / 0,094**. Das ist die beste Kombination mit Ampel.
- T + K1 (Hochnähe): 0,086 / −0,014
- T + K1 + K2 + K3, also alle drei: 0,174 / 0,069

Dieselben Werte **ohne Ampel**:

- T: 0,221 / 0,098
- T + K2: 0,278 / 0,089
- T + K2 + K3: 0,269 / 0,092
- alle drei: 0,240 / 0,079

Ohne Ampel ist K2 im Zeitraum B also nicht besser. Der Vorsprung von K2 ist damit deutlich, aber nicht in jeder Lesart.

**Beitrag der Kriterien** (in wie vielen von vier Vergleichen wurde der Erwartungswert besser, mit Ampel):

- K1: A 0/4, B 0/4
- K2: A 4/4, B 4/4
- K3: A 2/4, B 4/4

Die Trefferquote liegt bei allen Varianten zwischen 29 und 40 %. Der Vorteil kommt aus wenigen großen Gewinnern. Das ist typisch für Trendfolge.

## S2: Ausstieg

Auf T + K1 + K2 + K3 mit Ampel, Erwartungswert A / B:

- E1, Ziel CRV 2: 0,181 / **−0,004**
- E2, Ziel CRV 3: 0,250 / **−0,035**
- E3, Schluss unter EMA20: 0,110 / **−0,031**
- E4, Stopp auf das 10-Tage-Tief nachziehen: 0,174 / 0,069
- E5, ATR-Trailing (3 × ATR): **0,314** / 0,069

Nur die beiden nachziehenden Stopps E4 und E5 blieben in beiden Zeiträumen positiv. E5 war in A klar vorn und in B gleichauf mit E4.

## S3: Verlustserien und Rückgang

Variante T + K1 + K2 + K3, mit Ampel, Ausstieg E4. Grundlage sind 1.379 Trades, nachgeprüft mit einem eigenen Skript.

- **Größter Rückgang:** −104,6 R, von 09/2021 bis 05/2023. Bei 0,25 % Risiko sind das −26 %, auch in der Tageswertung (−26,3 %).
- **Längste Verlustserie:** 33 Trades in Folge, zusammen −31,7 R.
- **Neu gemischte Reihenfolge (Monte Carlo, 95-%-Wert):** längste Serie 22, Rückgang −14 %. Die echte Reihenfolge war deutlich schlechter als der Zufall. **Die Verluste häufen sich in Bärenphasen** (2022: −39,8 R bei 26 % Treffern). Bei mehreren gleichzeitigen Positionen verlieren alle zugleich.
- **Summe über alle Trades:** +245,5 R. Starke Jahre waren 2017, 2019, 2024 und 2025, schwache 2020 bis 2022.

**Einordnung:** Für einen Rücksetzer-Ansatz mit 30–35 % Treffern sind 20 bis 30 Verlierer in Folge und monatelange Durststrecken Teil des normalen Verlaufs. Schon bei 1 % Risiko je Trade wäre derselbe Verlauf ein Rückgang von über 60 % gewesen.

## S4: 52-Wochen-Ausbruch (Lüddemann-Trendhandel)

Einstieg bei Schluss über dem höchsten Hoch der 252 Vortage, in Phase 3. Stopp, Ausstieg und Portfolio wie oben, mit Ampel.

- **Ausbruch:** 0,085 / **−0,020** R
- **Ausbruch + RS Sektor:** 0,057 / −0,019 R
- **Vergleich, Rücksetzer mit allen drei Kriterien:** 0,174 / 0,069 R

**Aufgeteilt nach Ampel beim Signal** (alle Signale, ohne Platzbegrenzung):

- **Rücksetzer:** GO 0,026 · CAUTION 0,090 · VOREINSTIEG 0,083 · STOP 0,043 · REVERSE −0,226
- **Ausbruch:** GO −0,003 · CAUTION 0,049 · VOREINSTIEG −0,038 · STOP −0,087 · REVERSE −0,801

**Nach Marktbreite** (Anteil der Aktien in Phase 3):

- Rücksetzer: ab 50 % +0,078, unter 50 % +0,027
- Ausbruch: −0,006 bzw. +0,015

Auffällig: Beide Einstiege liefen bei **GO am schwächsten** und bei CAUTION am besten. Das passt zum bisherigen Bild: Wenn alles ruhig und grün ist, sind die leichten Gewinne oft schon gemacht.

## Grenzen

- **Survivorship:** Nur heutige Mitglieder sind enthalten. Absolute Ergebnisse sind zu gut, Vergleiche zwischen Varianten sind belastbarer.
- **Vergleich mit Kaufen und Halten:** Der SPY hatte im selben Zeitraum eine Sharpe-Kennzahl von 0,74, gut 13 % pro Jahr und −34 % größten Verlust. Keine Variante hat das übertroffen. Bei 0,25 % Risiko ist aber auch nicht durchgehend das ganze Kapital investiert.
- **K1 ist nur eine Näherung:** „52-Wochen-Hoch in den letzten 30 Tagen“ ist nicht dasselbe wie dein Blick auf das Allzeithoch im Chart. Mit 10 Jahren Daten lässt sich ein echtes Allzeithoch nicht sauber bestimmen.
- **Mechanische Regeln:** Dein Chartbild, die Lage im Kontext und die Auswahl in TradingView sind nicht abgebildet. Gemessen wird, ob die Kriterien als Regel einen Vorteil haben, nicht deine Trades.
- **Ausbruch:** Der Stopp am 10-Tage-Tief ist beim Ausbruch eher eng. Ein anderer Stopp kann dort anders ausfallen. Er wurde bewusst nicht nachträglich probiert.
- **Viele Varianten:** Bei so vielen gleichzeitig getesteten Varianten sind Unterschiede unter etwa 0,05 R kein Befund.

## Was daraus für die Morgenroutine folgt

- **N2 Platz-Check** bleibt im Plan (Phase 4). Er ist das einzige Kriterium mit klarem Testbeleg.
- **RS gegen den Sektor** wird als Information angezeigt, nicht als Filter.
- **Hochnähe** bekommt kein eigenes Werkzeug. Das Allzeithoch siehst du ohnehin im Chart.
- **Die Werte aus S3** (Verlustserien, Rückgang) kommen ins Info-Pop-up beim Risiko. Damit ist eine Serie von 20 Verlierern als „im Rahmen“ erkennbar und nicht als Systembruch.
