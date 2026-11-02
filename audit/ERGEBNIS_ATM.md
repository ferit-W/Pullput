# Ergebnis ATM-Variante mit festem Einstiegsrhythmus (02.11.2026)

Regeln vor der Berechnung festgelegt: `audit/VORAB_REGELN_ATM.md` (Commit 9cc5ee9). Code: `audit/engine2.py`
(Schalter `zyklus`, `strike_modus='atm'`, `breite_fest`), `audit/atm_lauf.py`, `audit/atm_empfindlichkeit.py`.
Alle Werte: Modellsimulation ohne Marktpreise, ganze Kontrakte, Start 100.000 USD je Hälfte, EMA-200-Filter,
Einsatz 0,85 %, Kosten 1,80 USD je Kontrakt und Seite, Abschlag SPX 0,25 / XSP 0,05 Pkt, Zins 4 % auf den Kontowert.

## Ergebnisse (Rendite p. a. / max. Drawdown im Tagesdaten-Stress)
| Variante | H1 2007–2016 | H2 2017–2026 | Trades H1 / H2 | Trefferquote H1 / H2 |
|---|---|---|---|---|
| W-SPX-5 (Wochenzyklus, SPX, 5 Pkt) | 9,1 % / 17,9 % | 21,7 % / 22,8 % | 1.478 / 1.635 | 62,8 % / 63,7 % |
| W-SPX-10 | 10,2 % / 13,5 % | 27,4 % / 20,7 % | 1.473 / 1.635 | 66,9 % / 66,2 % |
| W-XSP-5 | 1,3 % / 8,5 % | 14,1 % / 12,8 % | 1.478 / 1.635 | 69,6 % / 72,8 % |
| W-XSP-10 | 2,7 % / 3,7 % | 6,3 % / 9,0 % | 1.150 / 1.250 | 69,8 % / 73,6 % |
| M-SPX-5 (Monatszyklus, SPX, 5 Pkt) | 10,5 % / 7,5 % | 16,0 % / 11,3 % | 334 / 370 | 64,6 % / 71,0 % |
| M-SPX-10 | 11,5 % / 7,2 % | 16,8 % / 10,0 % | 334 / 370 | 67,6 % / 71,3 % |
| M-XSP-5 | 6,9 % / 5,3 % | 16,6 % / 9,5 % | 334 / 370 | 73,3 % / 76,0 % |
| M-XSP-10 | 4,4 % / 3,6 % | 12,5 % / 5,6 % | 321 / 370 | 74,5 % / 79,2 % |

XSP-10: Ein Kontrakt riskiert bis rund 1.000 USD; bei 100.000 USD passt er oft nicht in 0,85 % (W: 328 / 385 Tage
ausgelassen). Ohne Cashzins wird W-XSP-10 in H1 gar nicht gehandelt.

## Kosten- und Zinsabhängigkeit (H1 / H2, Rendite p. a.)
| Variante | Referenz | Abschlag ×2 | Abschlag ×4 | ohne Cashzins |
|---|---|---|---|---|
| W-SPX-5 | 9,1 / 21,7 | 0,7 / 7,5 | −8,5 / −7,0 | 4,6 / 16,7 |
| W-SPX-10 | 10,2 / 27,4 | 6,2 / 20,2 | −2,2 / 7,7 | 6,1 / 21,8 |
| M-SPX-5 | 10,5 / 16,0 | 7,2 / 11,8 | 3,2 / 5,4 | 6,2 / 11,5 |
| M-SPX-10 | 11,5 / 16,8 | 10,1 / 15,0 | 6,9 / 10,0 | 6,7 / 12,0 |
| M-XSP-5 | 6,9 / 16,6 | 6,5 / 15,6 | 5,7 / 13,9 | 2,7 / 11,9 |
| M-XSP-10 | 4,4 / 12,5 | 4,3 / 12,1 | 4,0 / 11,7 | −0,4 / 7,9 |

Im Wochenzyklus mit SPX fressen Abschlag und Gebühren den Großteil: W-SPX-5 zahlt in H1 181.438 USD Kosten bei
62.221 USD Cashzins. Bei doppeltem Abschlag bleibt in H1 praktisch nichts.

## Modellabhängigkeit (H1 / H2, Rendite p. a. / DD)
| Variante | Referenz | Vol-Faktor 0,70 | Vol-Faktor 1,0 | Skew 0 | Skew −3 (marktübliche Richtung) |
|---|---|---|---|---|---|
| W-SPX-10 | 10,2/13,5 · 27,4/20,7 | 8,1/13,6 · 24,6/20,8 | 18,5/11,8 · 36,5/19,3 | 7,5/12,7 · 20,3/21,0 | 4,6/17,2 · 16,5/22,3 |
| M-SPX-10 | 11,5/7,2 · 16,8/10,0 | 10,4/6,3 · 15,8/10,5 | 14,0/7,4 · 21,6/10,1 | 6,5/5,3 · 10,1/9,1 | 4,5/8,9 · 7,7/7,5 |
| M-XSP-5 | 6,9/5,3 · 16,6/9,5 | 5,9/5,7 · 15,0/9,7 | 10,7/6,6 · 21,8/9,6 | 5,1/4,8 · 10,7/8,6 | 4,2/5,1 · 8,2/9,2 |

Alle 64 Kombinationen: `ergebnisse/vergleich_atm_empfindlichkeit.csv`.

## Einordnung
1. Der Monatszyklus hat in allen Szenarien deutlich niedrigere Drawdowns (3,6–11,3 % Referenz, höchstens 12,9 % im
   Zins-0-Szenario) als die bisherige Delta-0,8-Variante (19,3 % / 22,6 %).
2. Die Rendite ist eine Folge der Modellannahmen: Mit marktüblichem Skew (−3) liegt M-SPX-10 bei 4,5 % / 7,7 %
   inklusive 4 % Cashzins; das Optionsergebnis allein ist dann nahe null bis wenige Prozent.
3. Der Wochenzyklus ist in diesem Modell am schlechtesten belegt: VX1 als 30-Tage-Niveau passt nicht zu 1–4 Tagen
   Restlaufzeit, und die Ergebnisse kippen schon bei doppeltem Abschlag.
4. Keine Variante wurde ausgewählt oder nachjustiert. Die beste von acht über beide Hälften zu wählen, wäre
   eine Auswahl auf H2.
5. Offen: echte Geld-Brief-Spannen kurzlaufender ATM-Spreads, Listing der Freitags-Weeklys am Montag vor 2016
   (Annahme), XSP-Verfügbarkeit und -Kosten, historische Optionskurse.
