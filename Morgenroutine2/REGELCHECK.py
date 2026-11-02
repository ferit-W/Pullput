#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REGELCHECK 1.2 - prueft die offenen Positionen gegen die eigenen Handelsregeln.

Aufruf (im Ordner der Morgenroutine):
    python REGELCHECK.py

Liest daten/trading_journal.json und daten/stillhalter_journal.json und meldet,
wo die offenen Positionen von den Regeln aus dem Handelsplan abweichen.

Was dieses Skript NICHT ist:
  · Es ist kein Ersatz fuer die Selbstkontrolle in den Journalen. Die prueft, ob
    die DATEN in sich stimmig sind (Rechenfehler, fehlende Felder). Dieses Skript
    prueft, ob das HANDELN den Regeln folgt. Zwei verschiedene Fragen.
  · Es ist kein Ersatz fuer den monatlichen Abgleich gegen CapTrader. Beide pruefen
    nur, was in den eigenen Dateien steht.
  · Es aendert NICHTS. Es liest und meldet.

Alle Regeln stehen unten im Block REGELN und sind dort aenderbar, ohne den
uebrigen Code anzufassen.
"""

import json
import os
import sys
from datetime import datetime, date

# ─────────────────────────────────────────────────────────────────────────────
#  REGELN - hier anpassen, wenn sich der Handelsplan aendert
# ─────────────────────────────────────────────────────────────────────────────
REGELN = {
    # Risiko je Position, in Prozent des Kontos
    "risiko_trend_pct":   0.25,   # Trend-Handel
    "risiko_gap_pct":     0.40,   # Gap- und News-Handel
    "risiko_akj_fix":     100.0,  # AKJ: fixer Eurobetrag statt Prozentsatz
    "risiko_toleranz":    0.20,   # 20 % Abweichung nach oben werden geduldet

    # Gleichzeitige Positionen im Trend-Handel (Backtest-Konfiguration)
    "max_positionen":     10,

    # Optionen: ab dieser Restlaufzeit wird das Rollen faellig
    "dte_warnung":        21,

    # Universum
    "mindestkurs":        10.0,   # USD bzw. EUR
    # v1.1: "earnings_abstand" ENTFERNT. Die Regel (7 Tage Abstand zu Quartalszahlen)
    # stand hier, wurde aber nirgends geprueft — das Journal fuehrt kein Earnings-Datum.
    # Eine Regel, die im Regelblock steht und nie greift, taeuscht Kontrolle vor.
    # Sie steht weiter im Handelsplan und wird beim Einstieg von Hand geprueft.

    # Index-Optionen, die bar abgerechnet werden - dort ist kein Assignment moeglich
    "bar_abgerechnet":    {"SPX", "NDX", "RUT", "VIX", "XSP", "DJX", "XEO", "OEX"},
}


# v1.4 (W1): Werte aus handelsplan.json uebernehmen, damit Journal, Morgenroutine und
# REGELCHECK dieselben Regeln verwenden. Fehlt die Datei oder ist sie unlesbar, gelten
# die Werte oben - der Lauf meldet das in der Uebersicht.
HANDELSPLAN = {"version": None, "fehler": None}

def lade_handelsplan(pfad=None):
    pfad = pfad or os.path.join(os.path.dirname(os.path.abspath(__file__)), "handelsplan.json")
    try:
        with open(pfad, "r", encoding="utf-8") as f:
            plan = json.load(f)
    except FileNotFoundError:
        HANDELSPLAN.update(version=None, fehler="handelsplan.json nicht gefunden - eingebaute Werte")
        return
    except Exception as e:
        HANDELSPLAN.update(version=None, fehler="handelsplan.json unlesbar (%s) - eingebaute Werte" % e)
        return
    zuordnung = [
        (("risiko", "trend_pct"), "risiko_trend_pct"),
        (("risiko", "gap_pct"), "risiko_gap_pct"),
        (("risiko", "akj_fix_eur"), "risiko_akj_fix"),
        (("risiko", "toleranz"), "risiko_toleranz"),
        (("positionen", "max_trend"), "max_positionen"),
        (("optionen", "dte_warnung"), "dte_warnung"),
        (("universum", "mindestkurs"), "mindestkurs"),
    ]
    for (block, feld), schluessel in zuordnung:
        wert = (plan.get(block) or {}).get(feld)
        if isinstance(wert, (int, float)) and not isinstance(wert, bool):
            REGELN[schluessel] = int(wert) if isinstance(REGELN[schluessel], int) else float(wert)
    HANDELSPLAN.update(version=plan.get("version"), fehler=None)

lade_handelsplan()

# ─────────────────────────────────────────────────────────────────────────────

ROT, GELB, GRUEN, GRAU, AUS = "\033[91m", "\033[93m", "\033[92m", "\033[90m", "\033[0m"
if os.name == "nt" and not os.environ.get("WT_SESSION"):
    # v1.2: Windows 10/11-Konsolen koennen ANSI-Farben, muessen sie aber erst
    # einschalten (os.system("") aktiviert den VT-Modus). Klappt das nicht — sehr
    # alte Konsole —, wird ohne Farben ausgegeben.
    try:
        os.system("")
    except Exception:
        ROT = GELB = GRUEN = GRAU = AUS = ""

BASIS = os.path.dirname(os.path.abspath(__file__))


def datenordner():
    """Denselben Ordner verwenden wie der Server - inklusive datenordner.txt."""
    try:
        cfg = os.path.join(BASIS, "datenordner.txt")
        if os.path.isfile(cfg):
            with open(cfg, "r", encoding="utf-8-sig") as f:
                for zeile in f:
                    z = zeile.strip().strip('"').strip("'")
                    if z and not z.startswith("#"):
                        return os.path.join(os.path.expandvars(os.path.expanduser(z)), "daten")
    except Exception:
        pass
    z = os.environ.get("MORGENROUTINE_DATEN", "").strip()
    if z:
        return os.path.join(os.path.expandvars(os.path.expanduser(z)), "daten")
    return os.path.join(BASIS, "daten")


def lade(pfad):
    if not os.path.isfile(pfad):
        return None, "Datei nicht gefunden"
    try:
        with open(pfad, "r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as e:
        return None, str(e)


def zahl(v, standard=None):
    try:
        f = float(v)
        return f if f == f else standard   # NaN abfangen
    except Exception:
        return standard


def tage_bis(iso):
    """Kalendertage bis zum Datum. Bewusst ueber date, nicht ueber UTC -
    sonst liegt das Ergebnis in Mitteleuropa abends einen Tag daneben."""
    if not iso:
        return None
    try:
        d = datetime.strptime(str(iso)[:10], "%Y-%m-%d").date()
        return (d - date.today()).days
    except Exception:
        return None


class Bericht:
    def __init__(self):
        self.eintraege = []
        self.infos = []          # v1.2: Uebersichtszeilen, statt direkt zu drucken

    def info(self, text):
        self.infos.append(text)

    def add(self, stufe, bereich, text, hinweis=""):
        self.eintraege.append((stufe, bereich, text, hinweis))

    def kritisch(self, *a): self.add("kritisch", *a)
    def warnung(self, *a):  self.add("warnung", *a)
    def hinweis(self, *a):  self.add("hinweis", *a)

    def ausgeben(self):
        farbe = {"kritisch": ROT, "warnung": GELB, "hinweis": GRAU}
        zeichen = {"kritisch": "!!", "warnung": " !", "hinweis": " ·"}
        for stufe in ("kritisch", "warnung", "hinweis"):
            teil = [e for e in self.eintraege if e[0] == stufe]
            if not teil:
                continue
            print()
            print("%s%s  %s (%d)%s" % (farbe[stufe], zeichen[stufe], stufe.upper(), len(teil), AUS))
            for _, bereich, text, hinweis in teil:
                print("   %s[%s]%s %s" % (GRAU, bereich, AUS, text))
                if hinweis:
                    print("        %s%s%s" % (GRAU, hinweis, AUS))
        return sum(1 for e in self.eintraege if e[0] == "kritisch")


# ─────────────────────────────────────────────────────────────────────────────
#  Prueflauf: Richtungs-Journal
# ─────────────────────────────────────────────────────────────────────────────
def pruefe_trades(daten, b):
    trades = daten.get("trades") if isinstance(daten, dict) else None
    if not isinstance(trades, list):
        b.kritisch("Journal", "Die Datei enthaelt keine Trade-Liste - Format unerwartet.")
        return

    konten = {k.get("id"): k for k in (daten.get("accounts") or []) if isinstance(k, dict)}
    offen = [t for t in trades if isinstance(t, dict) and str(t.get("status", "")).lower() == "open"]

    # ── v1.2 FIX (ALTBESTAND WURDE WIE TRADING GEPRUEFT) ─────────────────────
    # Das Journal kennt vier Kategorien: Trading, AKJ, Langfrist, Altbestand.
    # Hier wurde nur "Langfrist" ausgesondert. Altbestand-Positionen haben bewusst
    # keinen Trading-Stopp (das Journal nimmt sie von der Stopp-Pruefung aus) —
    # REGELCHECK meldete sie trotzdem als KRITISCH, zaehlte sie aufs Slot-Limit und
    # rechnete sie ins offene Trading-Risiko. Ebenso zaehlte AKJ auf das Limit des
    # Trend-Handels, obwohl AKJ einen eigenen Zaehler hat.
    # v1.3 FIX (F16): Funktion hiess wie die Schleifenvariable weiter unten und wurde
    # dort mit einem Text ueberschrieben. Jetzt eindeutiger Name.
    def kategorie_von(t):
        return str(t.get("category") or "Trading")
    trading   = [t for t in offen if kategorie_von(t) in ("Trading", "AKJ")]   # aktive Regeln
    trend     = [t for t in trading if kategorie_von(t) == "Trading"]           # nur fuers Slot-Limit
    langfrist = [t for t in offen if kategorie_von(t) == "Langfrist"]
    altbest   = [t for t in offen if kategorie_von(t) == "Altbestand"]

    b.info("%d offene Positionen (%d Trading, %d AKJ, %d Langfrist, %d Altbestand)"
           % (len(offen), len(trend), len(trading) - len(trend), len(langfrist), len(altbest)))

    # ── Positionsgrenze ─────────────────────────────────────────────────────
    if len(trend) > REGELN["max_positionen"]:
        b.warnung("Slots", "%d gleichzeitige Trend-Positionen - der Plan sieht %d vor."
                  % (len(trend), REGELN["max_positionen"]),
                  "Der Backtest lief mit %d. Mehr Positionen heisst nicht mehr Ertrag, "
                  "sondern duennere Ueberwachung je Position." % REGELN["max_positionen"])

    for t in trading:
        nr = t.get("tradeNumber") or t.get("id") or "?"
        name = t.get("productName") or "?"
        kennung = "#%s %s" % (nr, name)
        kat = kategorie_von(t)
        setup = str(t.get("setup", "") or "")

        # ── Stopp vorhanden und auf der richtigen Seite ──────────────────────
        sl = zahl(t.get("slPrice"))
        ein = zahl(t.get("entryPrice"))
        richtung = str(t.get("direction", "Long"))
        if sl is None or sl == 0:
            b.kritisch("Stopp", "%s: kein Stopp hinterlegt." % kennung,
                       "Plan: kein Einstieg ohne vorher festgelegten Stopp.")
        elif ein is not None:
            if richtung == "Long" and sl >= ein:
                b.kritisch("Stopp", "%s: Long, aber Stopp (%.2f) liegt ueber dem Einstieg (%.2f)."
                           % (kennung, sl, ein))
            if richtung == "Short" and sl <= ein:
                b.kritisch("Stopp", "%s: Short, aber Stopp (%.2f) liegt unter dem Einstieg (%.2f)."
                           % (kennung, sl, ein))

        # ── Risiko gegen die Regel ──────────────────────────────────────────
        risiko = zahl(t.get("maxRiskEuro"))
        konto = zahl((konten.get(t.get("accountId")) or {}).get("balance"))
        if risiko is None or risiko <= 0:
            b.warnung("Risiko", "%s: kein Risikobetrag erfasst." % kennung,
                      "Ohne ihn laesst sich das R-Vielfache spaeter nicht auswerten.")
        elif kat == "AKJ":
            grenze = REGELN["risiko_akj_fix"] * (1 + REGELN["risiko_toleranz"])
            if risiko > grenze:
                b.warnung("Risiko", "%s (AKJ): %.0f EUR Risiko - vorgesehen sind fix %.0f EUR."
                          % (kennung, risiko, REGELN["risiko_akj_fix"]))
        elif konto and konto > 0:
            pct = risiko / konto * 100
            soll = REGELN["risiko_gap_pct"] if "GAP" in setup.upper() else REGELN["risiko_trend_pct"]
            if pct > soll * (1 + REGELN["risiko_toleranz"]):
                b.kritisch("Risiko", "%s: %.2f %% des Kontos - erlaubt sind %.2f %%."
                           % (kennung, pct, soll),
                           "%.0f EUR Risiko bei %.0f EUR Konto." % (risiko, konto))
        else:
            # v1.1 FIX: Vorher wurde die Prozent-Pruefung hier STILL uebersprungen —
            # eine Position mit unbekanntem Konto oder Konto ohne Saldo galt damit als
            # regelkonform, obwohl nichts geprueft wurde. Jetzt wird es gesagt.
            b.warnung("Risiko", "%s: Konto '%s' unbekannt oder ohne Saldo - Risikoanteil nicht pruefbar."
                      % (kennung, t.get("accountId") or "?"),
                      "Konto im Journal anlegen bzw. Saldo eintragen.")

        # ── Universum ───────────────────────────────────────────────────────
        if ein is not None and 0 < ein < REGELN["mindestkurs"]:
            b.warnung("Universum", "%s: Einstieg bei %.2f - unter dem Mindestkurs von %.0f."
                      % (kennung, ein, REGELN["mindestkurs"]))

        # ── Marktphase erfasst? ─────────────────────────────────────────────
        if not str(t.get("marketPhase", "") or "").strip():
            b.hinweis("Phase", "%s: keine Marktphase erfasst." % kennung,
                      "Ohne sie faellt die Position aus der Phasen-Auswertung heraus.")

        # ── Richtung gegen Phase ────────────────────────────────────────────
        ph = str(t.get("marketPhase", "") or "")
        if ph.startswith("P3") and richtung == "Short":
            b.warnung("Richtung", "%s: Short in einer als P3 erfassten Phase." % kennung,
                      "Plan: P3 ist die Long-Seite, P6 die Short-Seite.")
        if ph.startswith("P6") and richtung == "Long":
            b.warnung("Richtung", "%s: Long in einer als P6 erfassten Phase." % kennung)

    # ── Langfrist: darf keinen Trading-Stopp mitschleppen ───────────────────
    for t in langfrist:
        nr = t.get("tradeNumber") or t.get("id") or "?"
        if zahl(t.get("maxRiskEuro"), 0) > 0:
            b.hinweis("Langfrist", "#%s %s traegt noch einen Risikobetrag."
                      % (nr, t.get("productName") or "?"),
                      "Langfrist zaehlt nicht ins offene Trading-Risiko - der Wert verzerrt die Summe.")

    # ── Gesamtes offenes Risiko ─────────────────────────────────────────────
    summe = sum(zahl(t.get("maxRiskEuro"), 0) or 0 for t in trading)
    kontos = {k for k in (t.get("accountId") for t in trading) if k}
    basis = sum(zahl((konten.get(k) or {}).get("balance"), 0) or 0 for k in kontos)
    if basis > 0:
        b.info("Offenes Trading-Risiko: %.0f EUR = %.2f %% des Kontos" % (summe, summe / basis * 100))
        b.hinweis("Risiko gesamt", "%.2f %% des Kontos stehen gleichzeitig auf dem Spiel."
                  % (summe / basis * 100),
                  "Der Plan setzt hier bewusst keine feste Grenze - Ueberblick behalten "
                  "und Barreserven halten.")


# ─────────────────────────────────────────────────────────────────────────────
#  Prueflauf: Stillhalter-Journal
# ─────────────────────────────────────────────────────────────────────────────
def pruefe_optionen(daten, b):
    trades = daten.get("trades") if isinstance(daten, dict) else None
    if not isinstance(trades, list):
        b.kritisch("Stillhalter", "Die Datei enthaelt keine Positionsliste - Format unerwartet.")
        return

    offen = [t for t in trades if isinstance(t, dict) and str(t.get("status", "")).upper() == "OPEN"]
    b.info("%d offene Optionspositionen" % len(offen))

    for t in offen:
        ul = t.get("underlying") or "?"
        strat = t.get("strategy") or "?"
        kennung = "%s %s" % (ul, strat)

        # ── Restlaufzeit ────────────────────────────────────────────────────
        d = tage_bis(t.get("expiry"))
        if d is None:
            b.warnung("Verfall", "%s: kein oder unlesbares Verfallsdatum." % kennung)
        elif d < 0:
            b.kritisch("Verfall", "%s: Verfall war vor %d Tagen, Position steht noch auf offen."
                       % (kennung, -d),
                       "Verfaelscht Delta und Margin - Zustand nachtragen.")
        elif d <= REGELN["dte_warnung"]:
            b.warnung("Verfall", "%s: noch %d Tage Restlaufzeit." % (kennung, d),
                      "Plan: ab %d Tagen rollen oder schliessen." % REGELN["dte_warnung"])

        # ── Praemie erfasst ─────────────────────────────────────────────────
        pr = zahl(t.get("premium"))
        if pr is None or pr <= 0:
            b.warnung("Praemie", "%s: keine oder negative Eroeffnungspraemie erfasst." % kennung)

        # ── Barabgerechnete Indizes ─────────────────────────────────────────
        if str(ul).upper() in REGELN["bar_abgerechnet"] and zahl(t.get("assignmentShares"), 0):
            b.kritisch("Assignment", "%s: Aktien-Einbuchung bei einem barabgerechneten Index."
                       % kennung, "Das ist technisch nicht moeglich - Buchung pruefen.")

    # ── Verwaiste Rolls ─────────────────────────────────────────────────────
    gerollt = [t for t in trades if isinstance(t, dict) and str(t.get("status", "")).upper() == "ROLLED"]
    ids = {t.get("id") for t in trades if isinstance(t, dict)}
    for t in gerollt:
        nachfolger = t.get("rolledTo")
        # v1.3 FIX (SH3): Nachfolger auch rückwärts über rolledFrom erkennen — ältere
        # Rolls (vor Journal v6.0) und bearbeitete Positionen haben kein rolledTo.
        rueckwaerts = any(isinstance(x, dict) and x.get("rolledFrom") == t.get("id") for x in trades)
        if (not nachfolger or nachfolger not in ids) and not rueckwaerts:
            b.warnung("Roll", "%s %s: als gerollt gebucht, aber ohne Nachfolger."
                      % (t.get("underlying") or "?", t.get("expiry") or ""),
                      "Verzerrt das aggregierte Risiko.")


def analyse(ordner=None):
    """v1.2: Prueflauf ohne Bildschirmausgabe — liefert ein Dict.
    Wird vom Server (/regelcheck) fuer die Anzeige in der Morgenroutine genutzt;
    main() nutzt dieselbe Funktion, damit es nur EINE Pruefung gibt."""
    ordner = ordner or datenordner()
    lade_handelsplan()      # v1.4: bei jedem Lauf neu, damit Aenderungen ohne Neustart greifen
    b = Bericht()
    teile = {}
    for schluessel, datei, fn in (("journal", "trading_journal.json", pruefe_trades),
                                  ("stillhalter", "stillhalter_journal.json", pruefe_optionen)):
        d, fehler = lade(os.path.join(ordner, datei))
        vorher = len(b.infos)
        if fehler:
            teile[schluessel] = {"gefunden": False, "fehler": fehler, "infos": []}
        else:
            fn(d, b)
            teile[schluessel] = {"gefunden": True, "fehler": None, "infos": b.infos[vorher:]}
    return {
        "ok": True,
        "version": "1.4",
        "ordner": ordner,
        "handelsplan": {"version": HANDELSPLAN.get("version"), "fehler": HANDELSPLAN.get("fehler")},
        "stand": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "teile": teile,
        "befunde": [{"stufe": e[0], "bereich": e[1], "text": e[2], "hinweis": e[3]} for e in b.eintraege],
        "kritisch": sum(1 for e in b.eintraege if e[0] == "kritisch"),
        "warnung": sum(1 for e in b.eintraege if e[0] == "warnung"),
        "hinweis": sum(1 for e in b.eintraege if e[0] == "hinweis"),
        "_bericht": b,      # nur fuer main(); vor JSON-Ausgabe entfernen
    }


def main():
    ordner = datenordner()
    print()
    print("REGELCHECK - offene Positionen gegen die Handelsregeln")
    print("=" * 62)
    print("Datenordner: %s" % ordner)
    print("Stand      : %s" % datetime.now().strftime("%d.%m.%Y %H:%M"))

    erg = analyse(ordner)
    b = erg["_bericht"]
    hp = erg["handelsplan"]
    print("Handelsplan: %s" % (("Version " + str(hp["version"])) if hp["version"] else (GELB + str(hp["fehler"]) + AUS)))
    gefunden = 0
    for titel, schl in (("RICHTUNGS-JOURNAL", "journal"), ("STILLHALTER-JOURNAL", "stillhalter")):
        teil = erg["teile"][schl]
        print()
        print(titel)
        if not teil["gefunden"]:
            print("   %s(%s)%s" % (GRAU, teil["fehler"], AUS))
        else:
            gefunden += 1
            for z in teil["infos"]:
                print("   " + z)

    if not gefunden:
        print()
        print("%sKeine Journaldateien gefunden.%s" % (GELB, AUS))
        print("Laeuft der Server, und stimmt der Datenordner? "
              "Er steht in datenordner.txt bzw. in den Einstellungen der Morgenroutine.")
        return 2

    print()
    print("=" * 62)
    kritische = b.ausgeben()

    print()
    if not b.eintraege:
        print("%sOhne Befund - die offenen Positionen entsprechen den Regeln.%s" % (GRUEN, AUS))
    elif kritische:
        print("%s%d kritische(r) Befund(e) - vor dem naechsten Einstieg klaeren.%s" % (ROT, kritische, AUS))
    else:
        print("%sKeine kritischen Befunde.%s" % (GRUEN, AUS))

    print()
    print("%sDieses Skript prueft nur, was in den Journaldateien steht.%s" % (GRAU, AUS))
    print("%sOb die Zahlen mit CapTrader uebereinstimmen, zeigt nur der monatliche Abgleich.%s" % (GRAU, AUS))
    print()
    return 1 if kritische else 0


def _warten():
    """v1.1: Bei Doppelklick unter Windows schloss sich das Fenster sofort nach dem
    Bericht — man konnte nichts lesen. Wird das Skript aus einer Konsole gestartet
    oder die Ausgabe umgeleitet (z.B. in eine Datei), stoert die Pause nicht:
    dann ist stdin keine Konsole und wir warten nicht."""
    try:
        if sys.stdin is not None and sys.stdin.isatty() and sys.stdout.isatty():
            input("Enter zum Schliessen...")
    except Exception:
        pass


if __name__ == "__main__":
    try:
        code = main()
    except KeyboardInterrupt:
        code = 130
    except Exception as e:
        print("\nUnerwarteter Fehler: %s" % e)
        code = 3
    _warten()
    sys.exit(code)
