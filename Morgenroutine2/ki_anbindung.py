#!/usr/bin/env python3
"""KI-Anbindung über den lokalen Server (Phase 5: K0, K-Punkte; behebt J8/SH7 „Schlüssel in der Adresse“).

Bisher rief die Morgenroutine Gemini direkt aus dem Browser auf, mit dem Schlüssel in der
Adresse. Jetzt liegen die Schlüssel nur auf dem PC in ki_schluessel.json (neben dem Programm,
nicht im Repository) und der Server stellt die Anfrage. Wählbar: Gemini (Standard) oder Claude.

Gemini: REST-Schnittstelle von Google, Schlüssel im Kopf x-goog-api-key (nicht in der Adresse).
Claude: offizielles Python-SDK `anthropic` (einmalig: pip install anthropic), Modell
        claude-opus-5-5. Bei einer Ablehnung durch die Sicherheitsfilter springt serverseitig
        ein Ersatzmodell ein (fallbacks="default"); eine endgültige Ablehnung wird gemeldet.
"""
import json
import os
import urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
DATEI = os.path.join(HIER, "ki_schluessel.json")
CLAUDE_MODELL = "claude-opus-5-5"
GEMINI_STANDARD = "gemini-2.5-flash"
GEMINI_ERSATZ = {"gemini-2.5-pro": ["gemini-2.5-flash"], "gemini-3.1-pro-preview": ["gemini-2.5-pro", "gemini-2.5-flash"],
                 "gemini-2.5-flash": ["gemini-flash-latest"], "gemini-flash-latest": ["gemini-2.5-flash"]}


class KIFehler(Exception):
    pass


def lade():
    try:
        with open(DATEI, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def speichere(neu):
    d = lade()
    for k in ("gemini", "claude"):
        if k in neu and isinstance(neu[k], str):
            v = neu[k].strip()
            if v:
                d[k] = v
            else:
                d.pop(k, None)
    if neu.get("standard") in ("gemini", "claude"):
        d["standard"] = neu["standard"]
    if isinstance(neu.get("gemini_modell"), str) and neu["gemini_modell"]:
        d["gemini_modell"] = neu["gemini_modell"]
    tmp = DATEI + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, DATEI)
    return status()


def status():
    d = lade()
    try:
        import anthropic  # noqa: F401
        sdk = True
    except ImportError:
        sdk = False
    return {"ok": True, "gemini": bool(d.get("gemini")), "claude": bool(d.get("claude")), "claude_sdk": sdk,
            "standard": d.get("standard", "gemini"), "gemini_modell": d.get("gemini_modell", GEMINI_STANDARD),
            "claude_modell": CLAUDE_MODELL}


def _gemini(prompt, suche, max_tokens, schluessel, modell):
    letzter = ""
    for m in [modell] + GEMINI_ERSATZ.get(modell, []):
        url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % m
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.2}}
        if suche:
            body["tools"] = [{"google_search": {}}]
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": schluessel})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise KIFehler("Gemini-Schlüssel ungültig")
            letzter = "Gemini HTTP %s" % e.code
            continue
        except Exception as e:
            letzter = "Gemini: %s" % e
            continue
        cand = (d.get("candidates") or [{}])[0]
        text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts", []))
        if text.strip():
            return text, m
        letzter = "Gemini: leere Antwort (%s)" % cand.get("finishReason", "?")
    raise KIFehler(letzter or "Gemini: kein Modell erreichbar")


def _claude(prompt, suche, max_tokens, schluessel):
    try:
        import anthropic
    except ImportError:
        raise KIFehler("Für Claude einmalig im Programmordner ausführen: pip install anthropic")
    client = anthropic.Anthropic(api_key=schluessel, timeout=300.0)
    werkzeuge = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}] if suche else []
    nachrichten = [{"role": "user", "content": prompt}]
    try:
        for _ in range(4):   # Websuche kann die Antwort unterbrechen (pause_turn) — dann fortsetzen
            antwort = client.beta.messages.create(
                model=CLAUDE_MODELL, max_tokens=max_tokens, messages=nachrichten,
                output_config={"effort": "medium"},
                betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                **({"tools": werkzeuge} if werkzeuge else {}))
            if antwort.stop_reason == "pause_turn":
                nachrichten = nachrichten + [{"role": "assistant", "content": antwort.content}]
                continue
            break
    except anthropic.AuthenticationError:
        raise KIFehler("Claude-Schlüssel ungültig")
    except anthropic.RateLimitError:
        raise KIFehler("Claude: Anfragegrenze erreicht, später erneut versuchen")
    except anthropic.APIStatusError as e:
        raise KIFehler("Claude: Fehler %s" % e.status_code)
    except anthropic.APIConnectionError:
        raise KIFehler("Claude: keine Verbindung")
    if antwort.stop_reason == "refusal":
        raise KIFehler("Claude hat die Anfrage abgelehnt")
    text = "".join(b.text for b in antwort.content if getattr(b, "type", "") == "text")
    if not text.strip():
        raise KIFehler("Claude: leere Antwort (%s)" % antwort.stop_reason)
    return text, antwort.model


def frage(prompt, anbieter=None, suche=False, max_tokens=8192):
    d = lade()
    anbieter = anbieter or d.get("standard", "gemini")
    if anbieter == "claude":
        if not d.get("claude"):
            raise KIFehler("Kein Claude-Schlüssel hinterlegt")
        text, modell = _claude(prompt, suche, max(1024, min(int(max_tokens or 8192), 16000)), d["claude"])
    else:
        if not d.get("gemini"):
            raise KIFehler("Kein Gemini-Schlüssel hinterlegt")
        text, modell = _gemini(prompt, suche, max(1024, min(int(max_tokens or 8192), 32000)), d["gemini"], d.get("gemini_modell", GEMINI_STANDARD))
    return {"ok": True, "text": text, "anbieter": anbieter, "modell": modell}
