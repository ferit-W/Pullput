#!/usr/bin/env python3
"""Archiv-Werkzeug (Phase 3: A3 und A1d).

A3  befuellen(ordner)
    Traegt die Rueckrechnung 2007-2026 (ergebnisse/ampel_taeglich.csv,
    referenz_ampel_v2.csv, breite_taeglich.csv) in daten/archiv_JJJJ.json ein.
    Jeder Eintrag ist mit "quelle": "rueckrechnung" gekennzeichnet.
    Live-Eintraege der Morgenroutine werden NIE ueberschrieben: Ein Tag, der schon
    existiert, bleibt unveraendert (hoechstens fehlende Folgerenditen kommen dazu).

A1d bericht(ordner)
    Wertet alle Archivdateien aus und schreibt:
      daten/archiv_bericht.md     - lesbarer Bericht
      daten/archiv_ki_paket.csv   - kompakte Tabelle fuer eine KI
      daten/archiv_ki_frage.txt   - Vorschlag fuer die Frage an die KI
    Live-Tage und rueckgerechnete Tage werden getrennt ausgewiesen. Die
    Rueckrechnung ist der Massstab; die Live-Tage zeigen, ob die Ampel sich im
    echten Betrieb so verhaelt wie im Test.

Aufruf:  python3 archiv_werkzeug.py befuellen [datenordner]
         python3 archiv_werkzeug.py bericht   [datenordner]
Ohne Datenordner wird derselbe Ordner wie vom Server verwendet (datenordner.txt).
"""
import csv
import json
import math
import os
import sys
from datetime import datetime

HIER = os.path.dirname(os.path.abspath(__file__))
ERG = os.path.join(HIER, "ergebnisse")
ZUSTAENDE = ["GO", "VOREINSTIEG", "CAUTION", "STOP", "REVERSE"]


def _datenordner():
    sys.path.insert(0, os.path.dirname(HIER))
    try:
        import REGELCHECK
        return REGELCHECK.datenordner()
    except Exception:
        return os.path.join(os.path.dirname(HIER), "daten")


def _zahl(v):
    try:
        x = float(v)
        return None if math.isnan(x) else x
    except (TypeError, ValueError):
        return None


def _lese_csv(name):
    p = os.path.join(ERG, name)
    if not os.path.isfile(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return {r["date"][:10]: r for r in csv.DictReader(f)}


def _lade_archiv(ordner, jahr):
    p = os.path.join(ordner, "archiv_%s.json" % jahr)
    if not os.path.isfile(p):
        return {"jahr": int(jahr), "tage": {}}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _schreibe_archiv(ordner, jahr, daten):
    p = os.path.join(ordner, "archiv_%s.json" % jahr)
    if os.path.isfile(p):
        with open(p, "rb") as f:
            alt = f.read()
        with open(p + ".bak", "wb") as f:
            f.write(alt)
    tmp = p + ".tmp"
    daten["ts"] = int(datetime.now().timestamp() * 1000)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, sort_keys=True)
    os.replace(tmp, p)


def befuellen(ordner=None):
    ordner = ordner or _datenordner()
    os.makedirs(ordner, exist_ok=True)
    amp = _lese_csv("ampel_taeglich.csv")
    ref = _lese_csv("referenz_ampel_v2.csv")
    br = _lese_csv("breite_taeglich.csv")
    if not amp:
        return {"ok": False, "fehler": "ergebnisse/ampel_taeglich.csv fehlt"}
    je_jahr = {}
    for d, r in amp.items():
        e = {
            "quelle": "rueckrechnung",
            "version": "2026.11 · AM1+AM3+AM4",
            "label": (ref.get(d) or {}).get("ampel_v2") or None,
            "label_alt": r.get("ampel"),
            "p3": _zahl(r.get("p3")), "p6": _zahl(r.get("p6")), "n": _zahl(r.get("n")),
            "vix": _zahl(r.get("vix")), "term": r.get("term") or None,
            "panik": _zahl(r.get("panik")), "abdeckung": _zahl(r.get("abdeckung")), "fg": _zahl(r.get("fg")),
            "breite200": _zahl(r.get("breite200")), "breite50": _zahl(r.get("breite")),
            "rsBeat": _zahl(r.get("rsBeat")), "richtung": r.get("richtung") or None,
            "phasen": [{"s": k, "p": r.get("ph_" + k)} for k in ("SPY", "QQQ", "DIA", "IWM")],
            "kreditHY": _zahl(r.get("hy_oas")), "kreditHY63": _zahl(r.get("hy_chg63")),
            "spy_fwd5": _zahl(r.get("spy_fwd5")), "spy_fwd20": _zahl(r.get("spy_fwd20")),
            "spy_fwd60": _zahl(r.get("spy_fwd60")), "spy_maxdd20": _zahl(r.get("spy_maxdd20")),
        }
        b = br.get(d)
        if b:
            e.update({"aktien_p3_anteil": _zahl(b.get("P3_ANTEIL")), "aktien_nh": _zahl(b.get("NH")),
                      "aktien_nl": _zahl(b.get("NL")), "aktien_nhnl10": _zahl(b.get("NHNL10"))})
        je_jahr.setdefault(d[:4], {})[d] = e
    neu, unberuehrt, ergaenzt = 0, 0, 0
    for jahr, tage in sorted(je_jahr.items()):
        a = _lade_archiv(ordner, jahr)
        a.setdefault("tage", {})
        for d, e in tage.items():
            vorh = a["tage"].get(d)
            if vorh is None:
                a["tage"][d] = e
                neu += 1
            else:
                # Live-Eintrag bleibt; nur fehlende Folgerenditen ergaenzen
                add = {k: e[k] for k in ("spy_fwd5", "spy_fwd20", "spy_fwd60", "spy_maxdd20")
                       if vorh.get(k) is None and e.get(k) is not None}
                if add:
                    vorh.update(add)
                    ergaenzt += 1
                else:
                    unberuehrt += 1
        _schreibe_archiv(ordner, jahr, a)
    return {"ok": True, "neu": neu, "unberuehrt": unberuehrt, "ergaenzt": ergaenzt,
            "jahre": sorted(je_jahr), "ordner": ordner}


# ── Bericht ──────────────────────────────────────────────────────────────────────
def _alle_tage(ordner):
    tage = {}
    for fn in sorted(os.listdir(ordner)) if os.path.isdir(ordner) else []:
        if fn.startswith("archiv_") and fn.endswith(".json") and fn[7:11].isdigit():
            try:
                with open(os.path.join(ordner, fn), encoding="utf-8") as f:
                    tage.update(json.load(f).get("tage", {}))
            except Exception:
                pass
    return dict(sorted(tage.items()))


def _stat(werte):
    v = [x for x in werte if x is not None]
    if not v:
        return None
    return {"n": len(v), "mittel": sum(v) / len(v), "positiv": sum(1 for x in v if x > 0) / len(v)}


def _w(x, d=1):
    """Zahl lesbar, fehlend als Strich."""
    if x is None:
        return "–"
    try:
        return ("%.*f" % (d, float(x))).replace(".", ",")
    except (TypeError, ValueError):
        return str(x)


def _je_episode(liste, abstand_tage=30, n=10):
    """Je Episode nur den ersten (schlimmsten/stärksten) Tag — sonst füllt ein einziger
    Einbruch die ganze Liste mit Nachbartagen."""
    out = []
    for d, e in liste:
        t = datetime.strptime(d, "%Y-%m-%d")
        if all(abs((t - datetime.strptime(x, "%Y-%m-%d")).days) > abstand_tage for x, _ in out):
            out.append((d, e))
        if len(out) >= n:
            break
    return out


def _pct(x, d=1):
    return "–" if x is None else ("%+.*f %%" % (d, x * 100)).replace(".", ",")


def bericht(ordner=None):
    ordner = ordner or _datenordner()
    tage = _alle_tage(ordner)
    if not tage:
        return {"ok": False, "fehler": "keine Archivdateien in %s" % ordner}
    gruppen = {"live": {d: e for d, e in tage.items() if e.get("quelle") == "live"},
               "rueckrechnung": {d: e for d, e in tage.items() if e.get("quelle") == "rueckrechnung"}}
    L = ["# Archiv-Bericht Morgenroutine", "",
         "Erstellt: %s · Datenordner: `%s`" % (datetime.now().strftime("%d.%m.%Y %H:%M"), ordner), "",
         "Folgerenditen des S&P 500 (SPY) ab dem Schluss des Folgetags, wie in der Rückrechnung. "
         "„Rückschlag“ = tiefster Schluss der nächsten 20 Tage. Live-Tage und rückgerechnete Tage stehen getrennt; "
         "die Rückrechnung kennt keine Survivorship-Verzerrung auf Indexebene, die Live-Tage sind die echte Bewährungsprobe.", ""]
    for gname, g in gruppen.items():
        if not g:
            L += ["## %s" % ("Live-Tage" if gname == "live" else "Rückrechnung"), "", "Noch keine Einträge.", ""]
            continue
        ds = sorted(g)
        L += ["## %s (%d Tage, %s bis %s)" % ("Live-Tage" if gname == "live" else "Rückrechnung", len(ds), ds[0], ds[-1]), ""]
        for z in ZUSTAENDE:
            sub = [e for e in g.values() if e.get("label") == z]
            if not sub:
                continue
            s20 = _stat([e.get("spy_fwd20") for e in sub])
            s60 = _stat([e.get("spy_fwd60") for e in sub])
            dd = [e.get("spy_maxdd20") for e in sub if e.get("spy_maxdd20") is not None]
            tief = sum(1 for x in dd if x < -0.07) / len(dd) if dd else None
            L.append("- **%s**: %d Tage · nach 20 Tagen %s (%s positiv) · nach 60 Tagen %s · Rückschlag über 7 %% in %s der Fälle" % (
                z, len(sub), _pct(s20["mittel"]) if s20 else "–", ("%.0f %%" % (s20["positiv"] * 100)) if s20 else "–",
                _pct(s60["mittel"]) if s60 else "–", ("%.0f %%" % (tief * 100)) if tief is not None else "–"))
        # Lücken: großer Rückschlag, obwohl die Ampel GO/VOREINSTIEG zeigte
        verpasst_warnung = sorted([(d, e) for d, e in g.items() if e.get("label") in ("GO", "VOREINSTIEG")
                                   and (e.get("spy_maxdd20") or 0) < -0.07], key=lambda x: x[1]["spy_maxdd20"])
        verpasst_chance = sorted([(d, e) for d, e in g.items() if e.get("label") in ("STOP", "REVERSE")
                                  and (e.get("spy_fwd60") or 0) > 0.10], key=lambda x: -x[1]["spy_fwd60"])
        verpasst_warnung, verpasst_chance = _je_episode(verpasst_warnung), _je_episode(verpasst_chance)
        L += ["", "**Lücke 1 — grün, aber danach starker Rückschlag** (GO/VOREINSTIEG, Rückschlag über 7 % in 20 Tagen), je Episode der schlimmste Tag, höchstens zehn:"]
        L += ["- %s %s: Rückschlag %s · VIX %s · Breite %s · Termstruktur %s" % (
            d, e.get("label"), _pct(e.get("spy_maxdd20")), _w(e.get("vix")), _w(e.get("breite200"), 0), e.get("term") or "–") for d, e in verpasst_warnung] or ["- keine"]
        L += ["", "**Lücke 2 — rot, aber danach starke Erholung** (STOP/REVERSE, über +10 % in 60 Tagen), je Episode der stärkste Tag, höchstens zehn:"]
        L += ["- %s %s: +60 Tage %s · VIX %s · Breite %s · Panik %s" % (
            d, e.get("label"), _pct(e.get("spy_fwd60")), _w(e.get("vix")), _w(e.get("breite200"), 0), _w(e.get("panik"), 0)) for d, e in verpasst_chance] or ["- keine"]
        if gname == "live":
            ve = [e for e in g.values() if (e.get("voreinstieg") or {}).get("aktiv")]
            pw = [e for e in g.values() if e.get("panikWende")]
            s = _stat([e.get("spy_fwd20") for e in pw])
            L += ["", "**Hinweise im Live-Betrieb:** VOREINSTIEG an %d Tagen · Panik-Wende an %d Tagen%s" % (
                len(ve), len(pw), (", danach im Schnitt %s nach 20 Tagen" % _pct(s["mittel"])) if s else "")]
            # Phase 5 (K0, Regel 4): Wie gut lag der KI-Trading-Partner?
            kp = [(d, e) for d, e in g.items() if isinstance(e.get("ki_partner"), dict) and e.get("spy_fwd20") is not None]
            L += ["", "**KI-Trading-Partner — Neigung gegen den Verlauf** (S&P 500, 20 Tage ab Folgetag):"]
            if not kp:
                L += ["- noch keine bewertbaren Tage (eine Einschätzung braucht 21 Handelstage bis zur Bewertung)"]
            else:
                for n in ("eher long", "neutral", "eher defensiv", "eher short"):
                    sub = [e for _, e in kp if e["ki_partner"].get("neigung") == n]
                    if sub:
                        st = _stat([e.get("spy_fwd20") for e in sub])
                        L.append("- %s: %d Tage · danach %s · positiv in %.0f %%" % (n, len(sub), _pct(st["mittel"]), st["positiv"] * 100))
                gegen = [e for _, e in kp if e["ki_partner"].get("gegenRegel")]
                if gegen:
                    st = _stat([e.get("spy_fwd20") for e in gegen])
                    L.append("- Tage mit Widerspruch zur Ampel: %d · danach %s · positiv in %.0f %%" % (len(gegen), _pct(st["mittel"]), st["positiv"] * 100))
                treffer = sum(1 for _, e in kp if (e["ki_partner"].get("neigung") == "eher long" and e["spy_fwd20"] > 0)
                              or (e["ki_partner"].get("neigung") in ("eher defensiv", "eher short") and e["spy_fwd20"] < 0))
                gerichtet = sum(1 for _, e in kp if e["ki_partner"].get("neigung") != "neutral")
                if gerichtet:
                    L.append("- Trefferquote der gerichteten Neigungen: %d von %d (%.0f %%). Erst ab rund 50 Tagen aussagekräftig." % (treffer, gerichtet, treffer / gerichtet * 100))
            versionen = sorted({str(e.get("version")) for e in g.values() if e.get("version")}) or ["–"]
            L += ["", "Regelversionen im Zeitraum: " + ", ".join(versionen)]
        L.append("")
    L += ["## Hinweis", "",
          "Einzelne Jahre und wenige Einbrüche bestimmen diese Zahlen stark. Neue Regeln erst über `auswertung/` "
          "in zwei getrennten Zeiträumen prüfen (Grundsatz AM8), dann in den Handelsplan übernehmen.", ""]
    md = "\n".join(L)
    with open(os.path.join(ordner, "archiv_bericht.md"), "w", encoding="utf-8") as f:
        f.write(md)

    felder = ["datum", "quelle", "version", "label", "label_alt", "p3", "p6", "vix", "term", "breite200", "rsBeat",
              "panik", "fg", "kreditHY", "kreditHY63", "aktien_p3_anteil", "aktien_nhnl10", "trend", "risiko", "ki_neigung",
              "spy_fwd5", "spy_fwd20", "spy_fwd60", "spy_maxdd20"]
    with open(os.path.join(ordner, "archiv_ki_paket.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(felder)
        for d, e in tage.items():
            e = dict(e, ki_neigung=(e.get("ki_partner") or {}).get("neigung"))
            w.writerow([d] + [("" if e.get(k) is None else e.get(k)) for k in felder[1:]])
    frage = """Du bekommst die Datei archiv_ki_paket.csv (Semikolon, ein Handelstag je Zeile).
Sie enthält die Ampel meiner Morgenroutine (Spalte label) mit allen Eingangswerten und die
Folgerenditen des S&P 500 ab dem Folgetag (spy_fwd5/20/60, spy_maxdd20 = tiefster Stand der nächsten 20 Tage).
quelle = rueckrechnung: Regel nachträglich auf alte Daten gerechnet. quelle = live: so wurde es mir damals angezeigt.

Regeln (Regelwerk 2026.11):
- STOP bei 2+ US-Indizes in Phase 6, VIX > 28 oder Breite < 3 bei schwachem Trend
- CAUTION bei weniger als 3 Indizes in Phase 3, VIX >= 20, Breite < 6, enger Führung oder Backwardation
- GO bei 3+ Indizes in P3, VIX < 20, Breite >= 6 und keinem Index in P6
- VOREINSTIEG nach einem STOP (60 Tage), wenn 3 Indizes in P3, keiner in P6, 6 Sektoren über EMA200, VIX/VIX3M < 0,98
- REVERSE bei Fear&Greed <= 15, VIX > 30 und Backwardation

Bitte prüfe ehrlich und mit Zahlen:
1. Hat die Ampel funktioniert? Folgerenditen und Rückschläge je Zustand, getrennt nach live und rueckrechnung.
2. Wo lagen die Lücken? Zeiträume mit grüner Ampel vor starken Rückschlägen und mit roter Ampel vor starken Erholungen.
   Welche Eingangswerte hätten dort anders ausgesehen?
3. Weicht der Live-Betrieb von der Rückrechnung ab?
4. Welche Regeländerung würdest du testen? Nenne sie als vorab festgelegte Regel, die ich in zwei getrennten
   Zeiträumen prüfen kann, nicht als fertige Empfehlung.
Kennzeichne, was belegt ist und was Vermutung ist. Erfinde keine Zahlen.
"""
    with open(os.path.join(ordner, "archiv_ki_frage.txt"), "w", encoding="utf-8") as f:
        f.write(frage)
    return {"ok": True, "tage": len(tage), "live": len(gruppen["live"]), "rueckrechnung": len(gruppen["rueckrechnung"]),
            "dateien": ["archiv_bericht.md", "archiv_ki_paket.csv", "archiv_ki_frage.txt"], "bericht": md}


if __name__ == "__main__":
    was = sys.argv[1] if len(sys.argv) > 1 else "bericht"
    ordner = sys.argv[2] if len(sys.argv) > 2 else None
    r = befuellen(ordner) if was == "befuellen" else bericht(ordner)
    r.pop("bericht", None)
    print(json.dumps(r, ensure_ascii=False, indent=1))
