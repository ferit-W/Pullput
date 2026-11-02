#!/usr/bin/env python3
"""Lädt die öffentlichen Kurs- und Sentimentdaten für die Ampel-Rückrechnung.

Alle Quellen sind öffentliche GitHub-Repositories Dritter (Yahoo-/CBOE-/CNN-/AAII-/
NAAIM-Abzüge). Qualität und Vollständigkeit liegen NICHT in unserer Hand; das
Skript prüft deshalb Datumsbereich und Lücken und schreibt eine Quellenliste mit
Prüfsummen. Aufruf: python3 daten_laden.py <zielordner>
"""
import hashlib, json, sys, urllib.request, os

RAW = "https://raw.githubusercontent.com/{}/HEAD/{}"
QUELLEN = {
    # Indizes (Schlusskurse)
    "SPY":   ("flytothejy/market-data", "data/SPY.csv"),
    "QQQ":   ("flytothejy/market-data", "data/QQQ.csv"),
    "DIA":   ("nohseongmin/stonks-atlas", "data/us/DIA.csv"),
    "IWM":   ("nohseongmin/stonks-atlas", "data/us/IWM.csv"),
    # Volatilität
    "VIX":   ("flytothejy/market-data", "data/VIX.csv"),
    "VIX3M": ("flytothejy/market-data", "data/VIX3M.csv"),
    "VVIX":  ("smallfishmacro-Git/market-dashboard", "data/barchart/CBOE_Vvolatility_$VVIX.csv"),
    # Sentiment
    "FG":    ("whit3rabbit/fear-greed-data", "fear-greed.csv"),
    "AAII":  ("alecsmith/sentiment", "data/aaii_sentiment.csv"),
    "NAAIM": ("riverfjs/notification", "data/macro/naaim.csv"),
    "PCR":   ("achl0902-web/back-testing", "qld/data/macro/CBOE_EQUITYPC.csv"),
    # Kredit: ICE BofA US High Yield OAS (FRED BAMLH0A0HYM2)
    "HYOAS": ("viki-m13/bonds", "data/fred/BAMLH0A0HYM2.csv"),
}
for s in ["XLK","XLC","XLY","XLF","XLV","XLI","XLP","XLE","XLB","XLU","XLRE"]:
    QUELLEN[s] = ("kittycapital/sector-chart", f"data/history/{s}.csv")

def main(ziel):
    os.makedirs(ziel, exist_ok=True)
    meta = {}
    for k, (repo, pfad) in QUELLEN.items():
        url = RAW.format(repo, pfad.replace("$", "%24"))
        data = urllib.request.urlopen(url, timeout=60).read()
        open(os.path.join(ziel, k + ".csv"), "wb").write(data)
        meta[k] = {"url": url, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        print(k, len(data))
    json.dump(meta, open(os.path.join(ziel, "quellen.json"), "w"), indent=1)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "rohdaten")
