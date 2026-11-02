#!/usr/bin/env python3
"""Anbindung an den Marktsammler (CapTrader/TWS) als Kursquelle — N4 „zweite Datenquelle“.

Der Marktsammler (eigenes Programm, ab v1.2) schreibt je Wert eine Datei
  <Sammler>/daten/tageskerzen/<SCHLUESSEL>.csv   Spalten: zeit;open;high;low;close;volume
  (zeit = Datum JJJJ-MM-TT bei Tageskerzen; Stunden/5 Min. in UTC)
Der Schlüssel ist das TWS-Kürzel; bei doppelten Kürzeln bekommt der Future „_FUT“ und die
deutsche Aktie „_DE“ angehängt, Leerzeichen werden zu „_“ (BRK B → BRK_B). Diese Regel
wird hier aus der watchlist.csv des Sammlers nachgebildet — gleiche Logik wie dort.

Die Morgenroutine fragt Symbole im Yahoo-Format an (SPY, SAP.DE, ^GDAXI, ES=F). Dieses Modul
übersetzt sie, liest die Tageskerzen und prüft, ob sie aktuell sind. Nicht vorhandene oder
veraltete Werte meldet es zurück — dann holt die Morgenroutine wie bisher bei Yahoo.

Den Ordner des Sammlers trägt man in marktsammler_ordner.txt ein (oder in der Oberfläche).
Lesend, ändert am Sammler nichts.
"""
import csv
import datetime as dt
import os
import re

HIER = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HIER, "marktsammler_ordner.txt")

# Yahoo-Symbole ohne gleiches TWS-Kürzel → Schlüssel im Sammler
YAHOO_ZU_SAMMLER = {
    "^VIX": "VIX", "^GSPC": "SPX", "^NDX": "NDX", "^RUT": "RUT",
    "^GDAXI": "DAX", "^MDAXI": "MDAX", "^SDAXI": "SDAX", "^STOXX50E": "ESTX50",
    "ES=F": "ES_FUT", "NQ=F": "NQ", "CL=F": "CL_FUT", "GC=F": "GC", "SI=F": "SI", "HG=F": "HG",
}


def ordner_lesen():
    """Pfad aus marktsammler_ordner.txt. Akzeptiert den Programmordner oder seinen Unterordner daten."""
    try:
        with open(CFG, encoding="utf-8-sig") as f:
            p = f.read().strip().strip('"')
    except Exception:
        return None
    if not p:
        return None
    if os.path.isdir(os.path.join(p, "daten", "tageskerzen")):
        return p
    if os.path.isdir(os.path.join(p, "tageskerzen")):
        return os.path.dirname(os.path.normpath(p))
    return None


def ordner_setzen(pfad):
    pfad = (pfad or "").strip().strip('"')
    if pfad and not (os.path.isdir(os.path.join(pfad, "daten", "tageskerzen")) or os.path.isdir(os.path.join(pfad, "tageskerzen"))):
        return False, "Im Ordner gibt es weder daten\\tageskerzen noch tageskerzen"
    with open(CFG, "w", encoding="utf-8") as f:
        f.write(pfad)
    return True, ""


_INDEX = {"stamp": None, "keys": {}, "zeilen": []}


def _schluessel_index(root):
    """Nachbau der Schlüsselregel des Sammlers aus seiner watchlist.csv.
    Liefert {(symbol, waehrung, typ): schluessel} und die Zeilen (für Universum/Untergruppen)."""
    wl = os.path.join(root, "watchlist.csv")
    try:
        stamp = os.path.getmtime(wl)
    except OSError:
        return {}, []
    if _INDEX["stamp"] == (wl, stamp):
        return _INDEX["keys"], _INDEX["zeilen"]
    zeilen = []
    with open(wl, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f, delimiter=";"):
            z = {(k or "").strip(): (v or "").strip() for k, v in r.items()}
            if not z.get("symbol") or z["symbol"].startswith("#"):
                continue
            z["typ"] = (z.get("typ") or "STK").upper()
            z["sub"] = [x for x in (z.get("untergruppe") or "").split("|") if x]
            zeilen.append(z)
    zaehl = {}
    for z in zeilen:
        zaehl[z["symbol"]] = zaehl.get(z["symbol"], 0) + 1
    keys = {}
    for z in zeilen:
        suf = ("_FUT" if z["typ"] == "FUT" else "_DE" if z["typ"] == "STK" and z.get("waehrung") == "EUR" else "") if zaehl[z["symbol"]] > 1 else ""
        z["key"] = (z["symbol"] + suf).replace(" ", "_").replace("/", "_")
        keys[(z["symbol"], z.get("waehrung") or "USD", z["typ"])] = z["key"]
    _INDEX.update(stamp=(wl, stamp), keys=keys, zeilen=zeilen)
    return keys, zeilen


def aufloesen(yahoo_sym, root=None):
    """Yahoo-Symbol → Dateischlüssel im Sammler oder None."""
    root = root or ordner_lesen()
    if not root:
        return None
    s = (yahoo_sym or "").strip().upper()
    if s in YAHOO_ZU_SAMMLER:
        return YAHOO_ZU_SAMMLER[s]
    keys, _ = _schluessel_index(root)
    if s.endswith(".DE"):
        sym = s[:-3]
        return keys.get((sym, "EUR", "STK"))
    sym = s.replace("-", " ")
    return keys.get((sym, "USD", "STK"))


def letzter_handelstag(heute=None):
    """Wie im Sammler: letzter Werktag vor heute (die heutige Kerze ist noch offen)."""
    d = (heute or dt.date.today()) - dt.timedelta(days=1)
    while d.weekday() > 4:
        d -= dt.timedelta(days=1)
    return d


def tageskerzen(key, root=None, n=None):
    """Liste [(datum, open, high, low, close, volume)] aufsteigend; leere Liste, wenn nicht vorhanden."""
    root = root or ordner_lesen()
    if not root or not key:
        return []
    p = os.path.join(root, "daten", "tageskerzen", key + ".csv")
    if not os.path.isfile(p):
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            try:
                out.append((r["zeit"][:10], float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), float(r["volume"] or 0)))
            except (KeyError, ValueError, TypeError):
                continue
    out.sort()
    return out[-n:] if n else out


def kerzen_fuer(yahoo_sym, n=520, root=None):
    """Antwort für die Morgenroutine: gleiche Form wie deren fetchYahoo (closes, highs, lows, times),
    dazu 'frisch' (letzte Kerze mindestens vom letzten Handelstag) und 'quelle'."""
    root = root or ordner_lesen()
    if not root:
        return {"ok": False, "grund": "kein Sammler-Ordner eingetragen"}
    key = aufloesen(yahoo_sym, root)
    if not key:
        return {"ok": False, "grund": "Symbol nicht im Sammler"}
    k = tageskerzen(key, root, n)
    if len(k) < 2:
        return {"ok": False, "grund": "keine Tageskerzen", "key": key}
    letzte = k[-1][0]
    frisch = letzte >= letzter_handelstag().isoformat()
    zeit = lambda d: int(dt.datetime.strptime(d, "%Y-%m-%d").replace(hour=20, tzinfo=dt.timezone.utc).timestamp())
    return {"ok": True, "quelle": "marktsammler", "key": key, "frisch": frisch, "letzte": letzte,
            "times": [zeit(x[0]) for x in k], "opens": [x[1] for x in k], "highs": [x[2] for x in k],
            "lows": [x[3] for x in k], "closes": [x[4] for x in k], "volumes": [x[5] for x in k]}


def universum(root=None, gruppen=("S&P500", "DAX", "MDAX", "SDAX")):
    """Aktien des Sammlers je Index: {'US': [yahoo-symbole], 'DE': [...]}. Für den Setup-Scanner."""
    root = root or ordner_lesen()
    if not root:
        return {"US": [], "DE": []}
    _, zeilen = _schluessel_index(root)
    us, de = [], []
    for z in zeilen:
        if z["typ"] != "STK" or (z.get("gruppe") or "") != "Aktie":
            continue
        sub = set(z["sub"])
        if "S&P500" in sub and "S&P500" in gruppen:
            us.append(z["symbol"].replace(" ", "-"))
        elif sub & {"DAX", "MDAX", "SDAX"} & set(gruppen) and z.get("waehrung") == "EUR":
            de.append(z["symbol"] + ".DE")
    return {"US": us, "DE": de}


def status(root=None):
    root = root or ordner_lesen()
    if not root:
        return {"ok": False, "eingetragen": False}
    td = os.path.join(root, "daten", "tageskerzen")
    try:
        dateien = [f for f in os.listdir(td) if f.endswith(".csv")]
    except OSError:
        dateien = []
    spy = tageskerzen("SPY", root, 1)
    return {"ok": True, "eingetragen": True, "ordner": root, "dateien": len(dateien),
            "spy_letzte": spy[-1][0] if spy else None,
            "frisch": bool(spy and spy[-1][0] >= letzter_handelstag().isoformat())}
