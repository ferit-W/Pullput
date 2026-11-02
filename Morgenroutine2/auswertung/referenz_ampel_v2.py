"""Referenz für den Einbau der neuen Ampel (AM1 + AM3 + AM4) in die Morgenroutine.

Erzeugt aus ergebnisse/ampel_taeglich.csv für jeden Handelstag 2007–2026 die Ampel,
wie sie in der Rückrechnung getestet wurde:
  AM1  Breite = Sektoren über EMA200
  AM3  Panik-Score ohne Einfluss auf die Ampel (Test V4: identisch)
  AM4  VOREINSTIEG nach einem STOP in den letzten 60 Handelstagen

Die Datei ergebnisse/referenz_ampel_v2.csv dient dem Selbsttest der Morgenroutine:
Die JavaScript-Fassung muss an jedem Tag dasselbe Ergebnis liefern.

Aufruf: python3 referenz_ampel_v2.py
"""
import os
import pandas as pd
from ampel_auswertung import neu_ampel
from am4_voreinstieg_test import voreinstieg

hier = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(hier, "ergebnisse", "ampel_taeglich.csv"), parse_dates=["date"]).set_index("date")

mit_panik = voreinstieg(df, neu_ampel(df, breite_col="breite200", panik_aktiv=True))
ohne_panik = voreinstieg(df, neu_ampel(df, breite_col="breite200", panik_aktiv=False))
abw = int((mit_panik != ohne_panik).sum())
print("Tage:", len(df), "· Abweichungen mit/ohne Panik-Score:", abw)

aus = df[["p3", "p6", "n", "vix", "fg", "breite200", "breiteTot", "rsBeat", "rsTot", "term"]].copy()
aus["ampel_v2"] = ohne_panik
aus.to_csv(os.path.join(hier, "ergebnisse", "referenz_ampel_v2.csv"))
print(aus["ampel_v2"].value_counts().to_dict())
