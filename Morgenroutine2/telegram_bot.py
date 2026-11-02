#!/usr/bin/env python3
"""Telegram-Anbindung (Phase 6, N6): Tagesnachricht aufs Handy und Abfrage unterwegs.

Einrichtung (einmalig):
  1. In Telegram @BotFather anschreiben, /newbot, Namen vergeben → Bot-Schlüssel (Token).
  2. Token in der Morgenroutine unter ⚙ eintragen und speichern.
  3. Dem eigenen Bot in Telegram /start schicken → er antwortet mit deiner Chat-ID.
  4. Chat-ID unter ⚙ eintragen, „Test senden“.

Danach:
  • Nach jedem Lauf der Morgenroutine schickt der Server die Zusammenfassung (einmal je Tag,
    auf Wunsch abschaltbar).
  • /lage und /positionen liefern jederzeit den letzten Stand, /hilfe die Befehle.
  • Der Bot antwortet nur der eingetragenen Chat-ID. Fremden nennt er nur deren eigene Chat-ID.
Schlüssel und Chat-ID liegen nur in telegram.json auf diesem PC (nicht im Repository).
Der Server muss laufen; das Handy braucht keinen Zugang zum PC — alles läuft über Telegram.
"""
import datetime as dt
import json
import os
import threading
import time
import urllib.parse
import urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HIER, "telegram.json")
_STAND = {"lage": None, "positionen": None, "ts": None}
_LAUF = {"thread": None, "stopp": False}
_LOCK = threading.Lock()


def lade():
    try:
        with open(CFG, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _schreibe(d):
    tmp = CFG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, CFG)


def status():
    d = lade()
    return {"ok": True, "token": bool(d.get("token")), "chat_id": d.get("chat_id") or None,
            "auto": d.get("auto", True), "zuletzt_gesendet": d.get("zuletzt_gesendet"),
            "abfrage_laeuft": bool(_LAUF["thread"] and _LAUF["thread"].is_alive())}


def speichere(neu):
    d = lade()
    if isinstance(neu.get("token"), str) and neu["token"].strip():
        d["token"] = neu["token"].strip()
    if "chat_id" in neu:
        c = str(neu.get("chat_id") or "").strip()
        if c:
            d["chat_id"] = c
        else:
            d.pop("chat_id", None)
    if "auto" in neu:
        d["auto"] = bool(neu["auto"])
    _schreibe(d)
    starte_abfrage()
    return status()


def _api(methode, daten, timeout=20):
    d = lade()
    if not d.get("token"):
        raise RuntimeError("kein Telegram-Token eingetragen")
    url = "https://api.telegram.org/bot%s/%s" % (d["token"], methode)
    req = urllib.request.Request(url, data=json.dumps(daten).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def senden(text, chat_id=None):
    d = lade()
    chat = chat_id or d.get("chat_id")
    if not chat:
        raise RuntimeError("keine Chat-ID eingetragen — dem Bot /start schicken")
    teile = [text[i:i + 3900] for i in range(0, len(text), 3900)] or [""]
    for t in teile:
        r = _api("sendMessage", {"chat_id": chat, "text": t, "disable_web_page_preview": True})
        if not r.get("ok"):
            raise RuntimeError("Telegram: %s" % r.get("description", "Fehler"))
    return True


def stand_setzen(lage, positionen, auto_senden=True):
    """Von der Morgenroutine nach jedem Lauf. Sendet die Lage einmal je Kalendertag, wenn 'auto'."""
    with _LOCK:
        _STAND.update(lage=lage, positionen=positionen, ts=dt.datetime.now().strftime("%d.%m. %H:%M"))
    d = lade()
    heute = dt.date.today().isoformat()
    if auto_senden and d.get("auto", True) and d.get("token") and d.get("chat_id") and d.get("zuletzt_gesendet") != heute:
        senden(lage)
        d["zuletzt_gesendet"] = heute
        _schreibe(d)
        return "gesendet"
    return "gespeichert"


def _antwort(text, chat):
    d = lade()
    befehl = (text or "").strip().split()[0].lower() if text else ""
    befehl = befehl.split("@")[0]
    if str(chat) != str(d.get("chat_id") or ""):
        return "Deine Chat-ID: %s\nIn der Morgenroutine unter ⚙ „Telegram“ eintragen, dann antworte ich hier." % chat
    with _LOCK:
        s = dict(_STAND)
    if befehl in ("/lage", "/start"):
        return s["lage"] or "Noch kein Stand — die Morgenroutine ist heute noch nicht gelaufen."
    if befehl in ("/positionen", "/pos"):
        return s["positionen"] or "Noch kein Stand zu den Positionen."
    return "Befehle:\n/lage – Ampel, Konsequenz, Termine, Hinweise\n/positionen – offene Trades mit Hinweisen\n/hilfe – diese Liste\n(Stand: %s)" % (s["ts"] or "–")


def _abfrage_schleife():
    offset = None
    while not _LAUF["stopp"]:
        if not lade().get("token"):
            time.sleep(30)
            continue
        try:
            daten = {"timeout": 50, "allowed_updates": ["message"]}
            if offset is not None:
                daten["offset"] = offset
            r = _api("getUpdates", daten, timeout=60)
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                m = u.get("message") or {}
                chat = (m.get("chat") or {}).get("id")
                if chat is None or not m.get("text", "").startswith("/"):
                    continue
                try:
                    senden(_antwort(m.get("text"), chat), chat_id=chat)
                except Exception:
                    pass
        except Exception:
            time.sleep(15)


def starte_abfrage():
    if not lade().get("token"):
        return False
    if _LAUF["thread"] and _LAUF["thread"].is_alive():
        return True
    _LAUF["stopp"] = False
    t = threading.Thread(target=_abfrage_schleife, daemon=True, name="telegram")
    _LAUF["thread"] = t
    t.start()
    return True
