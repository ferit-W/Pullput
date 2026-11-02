#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  START_Morgenroutine_v6.py
#  Statischer Webserver  +  lokaler CORS-Proxy  auf Port 8765
#
#  Zweck:
#   1) Serviert die Morgenroutine ueber http://localhost:8765
#      -> loest das file:// null-origin CORS-Problem
#   2) Stellt /proxy?url=<encoded> bereit
#      -> holt Yahoo/CNN/CFTC SERVERSEITIG (kein Browser-CORS,
#         keine Rate-Limits fremder Proxies, kein null-origin)
#
#  Das Dashboard nutzt diesen Proxy automatisch als erste Option
#  (LOCAL_PROXY = 'http://localhost:8765/proxy?url=').
#
#  Start:  einfach START_Batch.bat doppelklicken
#          oder:  python START_Morgenroutine_v6.py
#  Stop:   STRG + C  im Konsolenfenster
# ============================================================

import os
import sys
import http.server
import socketserver
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import re as _re
import json
import threading
import time as _time
from concurrent.futures import ThreadPoolExecutor

PORT = 8765
INDEX_FILE = "ferit_morgenroutine_v6.html"
SERVER_VERSION = "6.4"
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# Hosts, die der Proxy weiterleiten darf (Allowlist gegen Missbrauch als offener Proxy)
ALLOWED_HOSTS = (
    "query1.finance.yahoo.com",
    "query2.finance.yahoo.com",
    "production.dataviz.cnn.io",
    "publicreporting.cftc.gov",
    # v15.15: "generativelanguage.googleapis.com" ENTFERNT — toter Eintrag.
    # Gemini braucht POST, dieser Proxy kann nur GET; das Dashboard ruft Gemini
    # ohnehin DIREKT im Browser auf (Google erlaubt CORS). Eintrag war nie nutzbar.
    "home.treasury.gov",   # 2Y-CMT-Yieldkurve (Build 15.7+) — XML/CSV, kein CORS am Server -> MUSS ueber Proxy
    # v6.0.2: Effective Federal Funds Rate der New Yorker Fed — offene JSON-Schnittstelle
    # ohne Schluessel. Daraus wird das aktuelle Zielband abgeleitet, damit es nicht
    # mehr von Hand im Code gepflegt werden muss.
    "markets.newyorkfed.org",
    # v6.19 (AM5): Kreditspread High Yield (BAMLH0A0HYM2) als CSV - nur Anzeige
    "fred.stlouisfed.org",
)

# ── v15.15: Persistenz auf dem Laufwerk (statt nur Browser-localStorage) ─────
#  POST /data/save?name=<x>   Body = JSON  -> speichert  ./daten/<x>.json  (atomar)
#                                            + ./daten/<x>.json.bak (vorheriger Stand)
#                                            + ./backups/<x>_<JJJJ>-W<KW>.json (1x pro Kalenderwoche)
#  GET  /data/load?name=<x>                -> liefert    ./daten/<x>.json
#  GET  /data/list                         -> listet alle gespeicherten Namen + Groesse + Datum
# ── v6.1: DATENORDNER EINSTELLBAR ───────────────────────────────────────────
# Bisher lagen "daten" und "backups" fest neben dem Programm. Wer die Programme
# lokal halten, die Daten aber in einen Cloud-Ordner legen will (damit Laptop und
# PC denselben Stand sehen), musste den ganzen Ordner verschieben.
#
# Zum Aendern gibt es zwei Wege — der erste hat Vorrang:
#
#   1) Datei "datenordner.txt" neben dieses Programm legen. Darin genau EINE Zeile
#      mit dem gewuenschten Pfad, zum Beispiel:
#         C:\Users\Ferit\OneDrive\Trading-Daten
#      Vorteil: Das Programm selbst bleibt unveraendert und wird bei einem Update
#      einfach ueberschrieben, ohne dass die Einstellung verloren geht.
#
#   2) Umgebungsvariable MORGENROUTINE_DATEN setzen.
#
# Ist nichts gesetzt oder der Pfad nicht anlegbar, bleibt es beim Ordner neben dem
# Programm — wie bisher. Es geht also nichts kaputt, wenn die Datei fehlt.
_BASIS = os.path.dirname(os.path.abspath(__file__))

def _lies_datenordner():
    # Weg 1: datenordner.txt
    try:
        cfg = os.path.join(_BASIS, "datenordner.txt")
        if os.path.isfile(cfg):
            with open(cfg, "r", encoding="utf-8-sig") as f:
                for zeile in f:
                    z = zeile.strip().strip('"').strip("'")
                    if z and not z.startswith("#"):
                        return os.path.expandvars(os.path.expanduser(z))
    except Exception:
        pass
    # Weg 2: Umgebungsvariable
    z = os.environ.get("MORGENROUTINE_DATEN", "").strip()
    if z:
        return os.path.expandvars(os.path.expanduser(z))
    return None

_ZIEL = _lies_datenordner()
_QUELLE = "Standard (neben dem Programm)"
if _ZIEL:
    try:
        # Beschreibbarkeit pruefen, BEVOR wir uns darauf verlassen — ein nicht
        # verbundenes Netzlaufwerk wuerde sonst erst beim Speichern auffallen,
        # also genau dann, wenn Daten verloren gehen koennten.
        os.makedirs(_ZIEL, exist_ok=True)
        _probe = os.path.join(_ZIEL, ".schreibtest")
        with open(_probe, "w") as f:
            f.write("ok")
        os.remove(_probe)
        _QUELLE = "eigener Pfad"
    except Exception as e:
        print(" !! Datenordner '%s' nicht nutzbar (%s)" % (_ZIEL, e))
        print(" !! Es wird der Standardordner neben dem Programm verwendet.")
        _ZIEL = None

DATA_DIR   = os.path.join(_ZIEL or _BASIS, "daten")
BACKUP_DIR = os.path.join(_ZIEL or _BASIS, "backups")

def _ensure_dirs():
    """v6.2: Beide Ordner anlegen. Wird beim Start und nach einer Pfadaenderung
    gerufen, damit der erste Speichervorgang nicht an einem fehlenden Ordner scheitert."""
    for d in (DATA_DIR, BACKUP_DIR):
        try:
            os.makedirs(d, exist_ok=True)
        except Exception as e:
            print(" !! Ordner '%s' nicht anlegbar: %s" % (d, e))
_NAME_RE = _re.compile(r"^[A-Za-z0-9_\-]{1,40}$")
# v6.4: ein Lock je Datensatzname. Zwei Speichervorgaenge desselben Namens (zwei
# offene Tabs, Debounce + manuelles Speichern) schrieben vorher in DIESELBE .tmp —
# beide oeffneten sie mit "wb", die Inhalte konnten sich vermischen, und os.replace
# haette dann ein kaputtes JSON an die Stelle der guten Datei gesetzt.
_save_locks = {}
_save_locks_guard = threading.Lock()

def _lock_fuer(name):
    with _save_locks_guard:
        lk = _save_locks.get(name)
        if lk is None:
            lk = _save_locks[name] = threading.Lock()
        return lk
MAX_SAVE_BYTES = 10 * 1024 * 1024   # 10 MB Obergrenze pro Datensatz
BACKUPS_KEEP = 26                   # pro Name max. 26 Wochen-Backups (halbes Jahr), aeltere werden geloescht

# ---- Yahoo quoteSummary: serverseitiges Crumb-/Cookie-Handling (im Browser nicht moeglich) ----
_BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
_cookiejar = http.cookiejar.CookieJar()

# ── v6.3 FIX (WEITERLEITUNGEN UMGINGEN DIE ALLOWLIST) ────────────────────────
# urllib folgt HTTP-Weiterleitungen (301/302/307/308) automatisch. Die Allowlist
# wurde nur gegen die URSPRUENGLICHE Adresse geprueft. Haette ein erlaubter Host
# auf einen fremden weitergeleitet, haette der Proxy die fremde Antwort geholt
# und ausgeliefert — die Allowlist war damit weniger hart, als ihr Kommentar
# versprach. Jetzt wird jedes Weiterleitungsziel erneut gegen ALLOWED_HOSTS
# geprueft; ein fremdes Ziel bricht mit HTTP 403 ab.
class _AllowlistRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        p = urllib.parse.urlparse(newurl)
        if p.scheme != "https" or (p.hostname or "") not in ALLOWED_HOSTS:
            raise urllib.error.HTTPError(newurl, 403, "redirect target not allowed: %s" % (p.hostname or "?"), headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

_opener = urllib.request.build_opener(_AllowlistRedirect, urllib.request.HTTPCookieProcessor(_cookiejar))
# Gleicher Schutz fuer den allgemeinen Proxy-Pfad (der ohne Cookie-Jar arbeitet).
_proxy_opener = urllib.request.build_opener(_AllowlistRedirect)
_crumb = {"value": None}
# CookieJar selbst ist intern threadsafe (RLock). Dieser Lock serialisiert nur das
# Crumb-Holen/-Verwerfen, damit beim parallelen Gap-Scan nicht mehrere Threads
# gleichzeitig ein Crumb anfordern (oder eins verwerfen, das ein anderer gerade liest).
_crumb_lock = threading.Lock()
_SYM_RE = _re.compile(r"^[A-Za-z0-9.\^=\-]{1,20}$")

# ── Gap-Scanner Universum ───────────────────────────────────────────────
# US = S&P 500 (verifizierte Konstituenten; deckt NASDAQ-100-Schwergewichte ab).
# DE = DAX 40 (kuratiert, Stand Wissen; ungueltige Ticker ueberspringt Yahoo automatisch).
SP500_SYMS = "MMM,AOS,ABT,ABBV,ACN,ADBE,AMD,AES,AFL,A,APD,ABNB,AKAM,ALB,ARE,ALGN,ALLE,LNT,ALL,GOOGL,GOOG,MO,AMZN,AMCR,AEE,AEP,AXP,AIG,AMT,AWK,AMP,AME,AMGN,APH,ADI,AON,APA,APO,AAPL,AMAT,APP,APTV,ACGL,ADM,ARES,ANET,AJG,AIZ,T,ATO,ADSK,ADP,AZO,AVB,AVY,AXON,BKR,BALL,BAC,BAX,BDX,BRK-B,BBY,TECH,BIIB,BLK,BX,XYZ,BNY,BA,BKNG,BSX,BMY,AVGO,BR,BRO,BF-B,BLDR,BG,BXP,CHRW,CDNS,CPT,CPB,COF,CAH,CCL,CARR,CVNA,CASY,CAT,CBOE,CBRE,CDW,COR,CNC,CNP,CF,CRL,SCHW,CHTR,CVX,CMG,CB,CHD,CIEN,CI,CINF,CTAS,CSCO,C,CFG,CLX,CME,CMS,KO,CTSH,COHR,COIN,CL,CMCSA,FIX,CAG,COP,ED,STZ,CEG,COO,CPRT,GLW,CPAY,CTVA,CSGP,COST,CRH,CRWD,CCI,CSX,CMI,CVS,DHR,DRI,DDOG,DVA,DECK,DE,DELL,DAL,DVN,DXCM,FANG,DLR,DG,DLTR,D,DPZ,DASH,DOV,DOW,DHI,DTE,DUK,DD,ETN,EBAY,SATS,ECL,EIX,EW,EA,ELV,EME,EMR,ETR,EOG,EPAM,EQT,EFX,EQIX,EQR,ERIE,ESS,EL,EG,EVRG,ES,EXC,EXE,EXPE,EXPD,EXR,XOM,FFIV,FDS,FICO,FAST,FRT,FDX,FIS,FITB,FSLR,FE,FISV,F,FTNT,FTV,FOXA,FOX,BEN,FCX,GRMN,IT,GE,GEHC,GEV,GEN,GNRC,GD,GIS,GM,GPC,GILD,GPN,GL,GDDY,GS,HAL,HIG,HAS,HCA,DOC,HSIC,HSY,HPE,HLT,HD,HON,HRL,HST,HWM,HPQ,HUBB,HUM,HBAN,HII,IBM,IEX,IDXX,ITW,INCY,IR,PODD,INTC,IBKR,ICE,IFF,IP,INTU,ISRG,IVZ,INVH,IQV,IRM,JBHT,JBL,JKHY,J,JNJ,JCI,JPM,KVUE,KDP,KEY,KEYS,KMB,KIM,KMI,KKR,KLAC,KHC,KR,LHX,LH,LRCX,LVS,LDOS,LEN,LII,LLY,LIN,LYV,LMT,L,LOW,LULU,LITE,LYB,MTB,MPC,MAR,MRSH,MLM,MAS,MA,MKC,MCD,MCK,MDT,MRK,META,MET,MTD,MGM,MCHP,MU,MSFT,MAA,MRNA,TAP,MDLZ,MPWR,MNST,MCO,MS,MOS,MSI,MSCI,NDAQ,NTAP,NFLX,NEM,NWSA,NWS,NEE,NKE,NI,NDSN,NSC,NTRS,NOC,NCLH,NRG,NUE,NVDA,NVR,NXPI,ORLY,OXY,ODFL,OMC,ON,OKE,ORCL,OTIS,PCAR,PKG,PLTR,PANW,PSKY,PH,PAYX,PYPL,PNR,PEP,PFE,PCG,PM,PSX,PNW,PNC,POOL,PPG,PPL,PFG,PG,PGR,PLD,PRU,PEG,PTC,PSA,PHM,PWR,QCOM,DGX,Q,RL,RJF,RTX,O,REG,REGN,RF,RSG,RMD,RVTY,HOOD,ROK,ROL,ROP,ROST,RCL,SPGI,CRM,SNDK,SBAC,SLB,STX,SRE,NOW,SHW,SPG,SWKS,SJM,SW,SNA,SOLV,SO,LUV,SWK,SBUX,STT,STLD,STE,SYK,SMCI,SYF,SNPS,SYY,TMUS,TROW,TTWO,TPR,TRGP,TGT,TEL,TDY,TER,TSLA,TXN,TPL,TXT,TMO,TJX,TKO,TTD,TSCO,TT,TDG,TRV,TRMB,TFC,TYL,TSN,USB,UBER,UDR,ULTA,UNP,UAL,UPS,URI,UNH,UHS,VLO,VEEV,VTR,VLTO,VRSN,VRSK,VZ,VRTX,VRT,VTRS,VICI,V,VST,VMC,WRB,GWW,WAB,WMT,DIS,WBD,WM,WAT,WEC,WFC,WELL,WST,WDC,WY,WSM,WMB,WTW,WDAY,WYNN,XEL,XYL,YUM,ZBRA,ZBH,ZTS".split(",")
DAX_SYMS = "ADS.DE,AIR.DE,ALV.DE,BAS.DE,BAYN.DE,BEI.DE,BMW.DE,BNR.DE,CBK.DE,CON.DE,1COV.DE,DTG.DE,DB1.DE,DBK.DE,DHL.DE,DTE.DE,ENR.DE,EOAN.DE,FRE.DE,HNR1.DE,HEI.DE,HEN3.DE,IFX.DE,MBG.DE,MRK.DE,MTX.DE,MUV2.DE,P911.DE,PAH3.DE,QIA.DE,RHM.DE,RWE.DE,SAP.DE,SHL.DE,SIE.DE,SRT3.DE,SY1.DE,VNA.DE,VOW3.DE,ZAL.DE".split(",")
NQ100_SYMS = "ADBE,AMD,ABNB,ALNY,GOOGL,GOOG,AMZN,AEP,AMGN,ADI,AAPL,AMAT,APP,ARM,ASML,ADSK,ADP,AXON,BKR,BKNG,AVGO,CDNS,CHTR,CTAS,CSCO,CCEP,CTSH,CMCSA,CEG,CPRT,COST,CRWD,CSX,DDOG,DXCM,FANG,DASH,EA,EXC,FAST,FER,FTNT,GEHC,GILD,HON,IDXX,INSM,INTC,INTU,ISRG,KDP,KLAC,KHC,LRCX,LIN,LITE,MAR,MRVL,MELI,META,MCHP,MU,MSFT,MSTR,MDLZ,MPWR,MNST,NFLX,NVDA,NXPI,ORLY,ODFL,PCAR,PLTR,PANW,PAYX,PYPL,PDD,PEP,QCOM,REGN,ROP,ROST,SNDK,STX,SHOP,SBUX,SNPS,TMUS,TTWO,TSLA,TXN,TRI,VRSK,VRTX,WMT,WBD,WDC,WDAY,XEL,ZS".split(",")
US_SYMS = list(dict.fromkeys(SP500_SYMS + NQ100_SYMS))  # S&P 500 vereinigt mit NASDAQ-100, dedupliziert



def _yget(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": _BROWSER_UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://finance.yahoo.com/",
    })
    return _opener.open(req, timeout=timeout)


def _get_crumb(force=False):
    with _crumb_lock:
        if _crumb["value"] and not force:
            return _crumb["value"]
        # Cookies setzen (mehrere Quellen als Fallback)
        for prime in ("https://fc.yahoo.com/", "https://finance.yahoo.com/"):
            try:
                _yget(prime, timeout=10).read()
            except Exception:
                pass
        try:
            c = _yget("https://query2.finance.yahoo.com/v1/test/getcrumb", timeout=10).read().decode("utf-8", "ignore").strip()
            if c and len(c) < 64 and "<" not in c:
                _crumb["value"] = c
                return c
        except Exception:
            pass
        return None


def breite_aus_quotes(quotes):
    """v6.19 (T1): Breitenkennzahlen aus v7/quote-Datensaetzen. Rein rechnend (testbar).
    Liefert (kennzahlen, earnings-termine)."""
    n = ueber50 = ueber200 = p3 = nh = nl = auf = ab = 0
    termine = []
    for q in quotes:
        px = q.get("regularMarketPrice")
        s50, s200 = q.get("fiftyDayAverage"), q.get("twoHundredDayAverage")
        if not (px and s50 and s200):
            continue
        n += 1
        ueber50 += px > s50
        ueber200 += px > s200
        p3 += (px > s50 > s200)
        hi, lo = q.get("fiftyTwoWeekHigh"), q.get("fiftyTwoWeekLow")
        dh, dl = q.get("regularMarketDayHigh") or px, q.get("regularMarketDayLow") or px
        nh += bool(hi and dh >= hi)
        nl += bool(lo and dl <= lo)
        chg = q.get("regularMarketChangePercent") or 0
        auf += chg > 0
        ab += chg < 0
        et = q.get("earningsTimestamp") or q.get("earningsTimestampStart")
        if et:
            termine.append({"s": q.get("symbol"), "t": et})
    pct = lambda x: round(x / n * 100, 1) if n else None
    return ({"n": n, "ueber50": pct(ueber50), "ueber200": pct(ueber200), "p3": pct(p3),
             "nh": pct(nh), "nl": pct(nl), "steigend": auf, "fallend": ab}, termine)


_BREITE_CACHE = {"ts": 0, "daten": None}


class Handler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    # v15.15: Host-Header-Check gegen DNS-Rebinding.
    # Eine fremde Webseite koennte sonst (via Domain, die auf 127.0.0.1 aufloest)
    # den Proxy und die /data-Endpunkte aus dem Browser des Nutzers ansprechen.
    def _host_ok(self):
        host = (self.headers.get("Host") or "").split(":")[0].strip().lower()
        return host in ("localhost", "127.0.0.1")

    # CORS-Header auf ALLE Antworten (auch statische Dateien & Fehler).
    # v15.15: nicht mehr pauschal "*", sondern nur noch localhost-Origins.
    # Das Dashboard/die Journale laufen ueber diesen Server (same-origin) und
    # brauchen gar kein CORS; der Header bleibt nur als Komfort fuer lokale Tests.
    # ── v6.4 FIX (FREMDE WEBSEITEN KONNTEN DATEN UEBERSCHREIBEN) ─────────────
    # Der Host-Check oben schuetzt nur gegen DNS-Rebinding. Eine beliebige Webseite,
    # die im selben Browser offen ist, konnte aber direkt an http://localhost:8765
    # senden: fetch(..., {method:'POST', mode:'no-cors', body:'{...}'}) ist ein
    # "einfacher" Request ohne Vorabpruefung — der Host-Header lautet dabei korrekt
    # "localhost:8765" und ging durch. Damit liessen sich Journale ueberschreiben
    # (die .bak haette nur EINEN Stand gerettet) oder der Datenordner umbiegen.
    # Browser senden bei jedem POST einen Origin-Header. Erlaubt sind nur die
    # eigenen Seiten auf diesem Port. Ohne Origin (curl, Python-Skripte) bleibt es
    # erlaubt — das ist kein Browser-Angriffsweg.
    _EIGENE_ORIGINS = ("http://localhost:%d" % PORT, "http://127.0.0.1:%d" % PORT)

    def _origin_ok(self):
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        return origin in self._EIGENE_ORIGINS

    def end_headers(self):
        origin = self.headers.get("Origin") or ""
        # v6.4: nur noch die eigenen Seiten (vorher jeder localhost-Port, also auch
        # jede andere lokal laufende Anwendung).
        if origin in self._EIGENE_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self):
        if not self._host_ok() or not self._origin_ok():
            self.send_error(403, "forbidden host/origin")
            return
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if not self._host_ok():
            self.send_error(403, "forbidden host header")
            return
        # v6.2: Aktuellen Datenordner abfragen — damit ihn die Oberflaeche anzeigen kann.
        if self.path.startswith("/config/datadir"):
            return self._send_json({
                "ok": True, "pfad": os.path.dirname(DATA_DIR),
                "daten": DATA_DIR, "backups": BACKUP_DIR,
                "quelle": _QUELLE, "programm": _BASIS,
                "dateien": sorted(os.listdir(DATA_DIR)) if os.path.isdir(DATA_DIR) else []
            })
        if self.path.startswith("/data/load"):
            return self._data_load()
        if self.path.startswith("/data/list"):
            return self._data_list()
        if self.path.startswith("/regelcheck"):
            return self._regelcheck()
        if self.path.startswith("/archiv/bericht"):
            return self._archiv_werkzeug("bericht")
        # v6.19 (W1): Handelsplan als Datei - alle Werkzeuge lesen dieselben Regeln
        if self.path == "/handelsplan" or self.path.startswith("/handelsplan?"):
            fp = os.path.join(DIRECTORY, "handelsplan.json")
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    return self._send_json({"ok": True, "plan": json.load(f)})
            except FileNotFoundError:
                return self._send_json({"ok": False, "fehler": "handelsplan.json fehlt im Programmordner"})
            except Exception as e:
                return self._send_json({"ok": False, "fehler": "handelsplan.json unlesbar: %s" % e})
        if self.path == "/ping" or self.path.startswith("/ping?"):
            return self._ping()
        if self.path.startswith("/quote?"):
            return self._quote()
        if self.path.startswith("/proxy?") or self.path.startswith("/proxy/"):
            return self._proxy()
        if self.path.startswith("/gapscan"):
            return self._gapscan()
        if self.path.startswith("/breite"):
            return self._breite()
        if self.path.startswith("/gapdetail"):
            return self._gapdetail()
        # v15.15: lokale .html-Dateien (Journale, Cockpit, Hub) SAME-ORIGIN ausliefern.
        # Nur der reine Dateiname zaehlt (kein Pfad, kein Traversal), nur *.html,
        # nur wenn die Datei wirklich im Server-Ordner liegt.
        name = os.path.basename(urllib.parse.unquote(urllib.parse.urlparse(self.path).path))
        if name.lower().endswith(".html") and _re.match(r"^[A-Za-z0-9_\-\. ()]{1,80}$", name):
            fp = os.path.join(DIRECTORY, name)
            if os.path.isfile(fp):
                return self._serve_html(fp)
            # v15.16: FEHLENDE .html NICHT mehr still durch das Dashboard ersetzen —
            # das machte Tippfehler/Umbenennungs-Probleme unsichtbar. Stattdessen klare Meldung
            # inkl. Liste der tatsaechlich vorhandenen HTML-Dateien im Ordner.
            try:
                vorhanden = sorted(fn for fn in os.listdir(DIRECTORY) if fn.lower().endswith(".html"))
            except Exception:
                vorhanden = []
            body = ("<html><head><meta charset='utf-8'><title>404</title></head><body style='font-family:Consolas,monospace;background:#0b0f14;color:#e8eef5;padding:40px'>"
                    "<h2 style='color:#e05252'>Datei nicht gefunden: %s</h2>"
                    "<p>Der Server sucht sie in:<br><b>%s</b></p>"
                    "<p>Vorhandene HTML-Dateien in diesem Ordner:</p><ul>%s</ul>"
                    "<p>Entweder die Datei exakt so benennen wie oben angefragt, oder den Link im Trading-Hub anpassen.</p>"
                    "<p><a style='color:#d4a44c' href='/Trading-Hub_v6.html'>&larr; zur&uuml;ck zum Hub</a></p></body></html>"
                    % (name, DIRECTORY, "".join("<li><a style='color:#4a90d9' href='/%s'>%s</a></li>" % (fn, fn) for fn in vorhanden))).encode("utf-8")
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except Exception:
                pass
            return
        # ALLES andere -> Dashboard. Das Cockpit ist self-contained (keine weiteren lokalen
        # Dateien noetig), daher liefert JEDER unbekannte Pfad direkt das Dashboard.
        # Kein super().do_GET(), kein Verzeichnis-Listing, kein 404 mehr moeglich.
        return self._serve_dashboard()

    def do_POST(self):
        if not self._host_ok():
            self.send_error(403, "forbidden host header")
            return
        if not self._origin_ok():
            print(" !! POST von fremder Seite abgewiesen: %s -> %s" % (self.headers.get("Origin"), self.path.split("?")[0]))
            self.send_error(403, "forbidden origin")
            return
        if self.path.startswith("/data/save"):
            return self._data_save()
        if self.path.startswith("/archiv/tage"):
            return self._archiv_tage()
        if self.path.startswith("/archiv/befuellen"):
            return self._archiv_werkzeug("befuellen")
        if self.path.startswith("/config/datadir"):
            return self._set_datadir()
        self.send_error(404, "unknown POST endpoint")

    def _set_datadir(self):
        """v6.2: Datenordner aus der Oberflaeche setzen.

        Der Weg ueber datenordner.txt bleibt bestehen — diese Route schreibt genau
        diese Datei, damit beide Wege denselben Zustand ergeben und die Einstellung
        einen Neustart ueberlebt.

        Bewusste Entscheidungen:
        · Vorhandene Daten werden NICHT automatisch verschoben. Ein Programm, das
          im Hintergrund Dateien zwischen Ordnern bewegt, kann bei einem Abbruch
          beides beschaedigen. Stattdessen wird zurueckgemeldet, was im alten Ordner
          liegt — verschieben tut der Nutzer selbst, mit dem Explorer.
        · Der Pfad wird auf Beschreibbarkeit geprueft, bevor er uebernommen wird.
        · Die Aenderung wirkt sofort; ein Neustart ist nicht noetig.
        """
        global DATA_DIR, BACKUP_DIR, _QUELLE
        try:
            laenge = int(self.headers.get("Content-Length") or 0)
            if laenge <= 0 or laenge > 8192:
                self.send_error(400, "bad length"); return
            roh = self.rfile.read(laenge)
            obj = json.loads(roh.decode("utf-8"))
            pfad = (obj.get("pfad") or "").strip().strip('"').strip("'")
        except Exception as e:
            self.send_error(400, "bad json: %s" % e); return

        alt_daten = DATA_DIR
        alte_dateien = sorted(os.listdir(alt_daten)) if os.path.isdir(alt_daten) else []

        # Leerer Pfad = zurueck auf den Ordner neben dem Programm
        if not pfad:
            try:
                cfg = os.path.join(_BASIS, "datenordner.txt")
                if os.path.isfile(cfg):
                    os.remove(cfg)
            except Exception:
                pass
            DATA_DIR   = os.path.join(_BASIS, "daten")
            BACKUP_DIR = os.path.join(_BASIS, "backups")
            _QUELLE = "Standard (neben dem Programm)"
            _ensure_dirs()
            return self._send_json({"ok": True, "pfad": _BASIS, "daten": DATA_DIR,
                                    "quelle": _QUELLE, "vorherDateien": alte_dateien,
                                    "vorherOrdner": alt_daten})

        ziel = os.path.expandvars(os.path.expanduser(pfad))
        if not os.path.isabs(ziel):
            return self._send_json({"ok": False, "fehler":
                "Bitte einen vollstaendigen Pfad angeben, z.B. C:\\Users\\Ferit\\OneDrive\\Trading-Daten"}, 400)

        # Beschreibbarkeit mit einer echten Testdatei pruefen — nicht nur nachsehen,
        # ob der Ordner existiert. Ein nicht verbundenes Netzlaufwerk faellt sonst
        # erst beim Speichern auf, also genau dann, wenn Daten verloren gehen koennten.
        try:
            os.makedirs(ziel, exist_ok=True)
            probe = os.path.join(ziel, ".schreibtest")
            with open(probe, "w") as f:
                f.write("ok")
            os.remove(probe)
        except Exception as e:
            return self._send_json({"ok": False, "fehler":
                "Ordner nicht nutzbar: %s" % e}, 400)

        try:
            with open(os.path.join(_BASIS, "datenordner.txt"), "w", encoding="utf-8") as f:
                f.write("# Von der Morgenroutine gesetzt. Zeile aendern oder Datei loeschen,\n")
                f.write("# um wieder den Ordner neben dem Programm zu verwenden.\n")
                f.write(ziel + "\n")
        except Exception as e:
            return self._send_json({"ok": False, "fehler":
                "Einstellung nicht speicherbar: %s" % e}, 400)

        DATA_DIR   = os.path.join(ziel, "daten")
        BACKUP_DIR = os.path.join(ziel, "backups")
        _QUELLE = "eigener Pfad"
        _ensure_dirs()
        print(" >> Datenordner geaendert auf: %s" % DATA_DIR)
        return self._send_json({"ok": True, "pfad": ziel, "daten": DATA_DIR,
                                "quelle": _QUELLE, "vorherOrdner": alt_daten,
                                "vorherDateien": alte_dateien})

    def _serve_dashboard(self):
        self._serve_html(os.path.join(DIRECTORY, INDEX_FILE))

    def _serve_html(self, path):
        try:
            with open(path, "rb") as f:
                body = f.read()
        except Exception as e:
            self.send_error(404, "HTML %s nicht lesbar: %s" % (os.path.basename(path), e))
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    # ── v15.15: Persistenz-Endpunkte ─────────────────────────────────────────
    def _data_name(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        name = (params.get("name", [""])[0] or "").strip()
        if not _NAME_RE.match(name):
            self.send_error(400, "bad name (erlaubt: A-Z a-z 0-9 _ - / max 40 Zeichen)")
            return None
        return name

    def _send_json(self, obj, code=200):
        payload = obj if isinstance(obj, bytes) else json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        try:
            self.wfile.write(payload)
        except Exception:
            pass

    def _data_save(self):
        try:
            name = self._data_name()
            if not name:
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = 0
            if length <= 0:
                return self.send_error(400, "empty body")
            if length > MAX_SAVE_BYTES:
                return self.send_error(413, "body too large (max %d MB)" % (MAX_SAVE_BYTES // 1024 // 1024))
            raw = self.rfile.read(length)
            try:
                json.loads(raw.decode("utf-8"))   # nur validieren — gespeichert wird das Original
            except Exception as e:
                return self.send_error(400, "body ist kein gueltiges JSON: %s" % e)

            os.makedirs(DATA_DIR, exist_ok=True)
            os.makedirs(BACKUP_DIR, exist_ok=True)
            target = os.path.join(DATA_DIR, name + ".json")
            with _lock_fuer(name):
                return self._data_save_locked(name, target, raw)
        except Exception as e:
            try:
                self.send_error(500, "save error: %s" % e)
            except Exception:
                pass

    def _archiv_tage(self):
        """v6.19 (A1): Tagesarchiv. POST /archiv/tage?jahr=JJJJ, Body {"tage": {"JJJJ-MM-TT": {...}}}.

        Die Eintraege werden in daten/archiv_JJJJ.json ZUSAMMENGEFUEHRT statt die Datei
        zu ersetzen: Ein Rechner ergaenzt seinen Tag, ein anderer traegt spaeter die
        Folgerenditen nach - keiner ueberschreibt den anderen. Je Tag werden die Felder
        zusammengefuehrt (neue Werte gewinnen, vorhandene Felder bleiben).
        Gespeichert wird ueber denselben Weg wie /data/save: .bak, atomar, Wochen-Backup.
        """
        try:
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            jahr = (params.get("jahr", [""])[0] or "").strip()
            if not _re.match(r"^(19|20)\d\d$", jahr):
                return self.send_error(400, "jahr fehlt oder ungueltig")
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = 0
            if length <= 0 or length > MAX_SAVE_BYTES:
                return self.send_error(400, "Body leer oder zu gross")
            try:
                neu = json.loads(self.rfile.read(length).decode("utf-8"))
                tage = neu.get("tage") if isinstance(neu, dict) else None
                if not isinstance(tage, dict):
                    raise ValueError("Feld 'tage' fehlt")
            except Exception as e:
                return self.send_error(400, "ungueltiges JSON: %s" % e)
            name = "archiv_" + jahr
            os.makedirs(DATA_DIR, exist_ok=True)
            os.makedirs(BACKUP_DIR, exist_ok=True)
            target = os.path.join(DATA_DIR, name + ".json")
            with _lock_fuer(name):
                alt = {"jahr": int(jahr), "tage": {}}
                if os.path.isfile(target):
                    try:
                        with open(target, "r", encoding="utf-8") as f:
                            alt = json.load(f)
                    except Exception:
                        return self._send_json({"ok": False, "error": "archiv_%s.json unlesbar - nichts geaendert" % jahr}, code=500)
                alt.setdefault("tage", {})
                geaendert = 0
                for tag, eintrag in tage.items():
                    if not (isinstance(tag, str) and _re.match(r"^\d{4}-\d{2}-\d{2}$", tag) and tag.startswith(jahr)):
                        continue
                    if not isinstance(eintrag, dict):
                        continue
                    ziel = alt["tage"].get(tag) or {}
                    ziel.update(eintrag)
                    alt["tage"][tag] = ziel
                    geaendert += 1
                alt["ts"] = int(_time.time() * 1000)
                raw = json.dumps(alt, ensure_ascii=False, sort_keys=True).encode("utf-8")
                return self._data_save_locked(name, target, raw)
        except Exception as e:
            try:
                self.send_error(500, "archiv error: %s" % e)
            except Exception:
                pass

    def _data_save_locked(self, name, target, raw):
        try:

            # 1) Vorherigen Stand als .bak sichern (Schutz gegen kaputte Einzel-Speicherung)
            if os.path.isfile(target):
                try:
                    with open(target, "rb") as f_old:
                        old = f_old.read()
                    with open(target + ".bak", "wb") as f_bak:
                        f_bak.write(old)
                except Exception:
                    pass

            # 2) Atomar schreiben: erst .tmp, dann os.replace (kein halb geschriebenes JSON moeglich)
            tmp = "%s.%d.%d.tmp" % (target, os.getpid(), threading.get_ident())   # v6.4: eindeutig je Thread
            with open(tmp, "wb") as f:
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, target)

            # 3) Wochen-Backup: 1x pro ISO-Kalenderwoche beim ERSTEN Save der Woche
            #    (laeuft immer dann, wenn der PC ohnehin an ist — kein Nacht-Job noetig)
            iso = _time.strftime("%G-W%V")     # z.B. 2026-W27
            wk = os.path.join(BACKUP_DIR, "%s_%s.json" % (name, iso))
            made_backup = False
            if not os.path.isfile(wk):
                with open(wk, "wb") as f:
                    f.write(raw)
                made_backup = True
                # ── v6.0.1 FIX (BACKUPS LOESCHTEN SICH GEGENSEITIG) ─────────────
                # Vorher wurde per startswith(name + "_") gefiltert. Damit fing eine
                # Datei "trading_journal" auch die Sicherungen von "trading_journal_test"
                # mit ein. Sortiert wird alphabetisch: nach dem gemeinsamen Praefix
                # steht "2026-W30.json" gegen "test_2026-W30.json", und "2" kommt vor "t".
                # Die ECHTEN Sicherungen rutschten damit an den Anfang der Liste —
                # geloescht wird aber vorne ([:-BACKUPS_KEEP]), behalten wird hinten.
                # Ergebnis: Das Speichern von "trading_journal" haette seine eigenen
                # Wochensicherungen geloescht, waehrend die der Testdatei blieben.
                # Neu: exaktes Muster Name_JJJJ-WKW.json, andere Namen bleiben unberuehrt.
                try:
                    pat = _re.compile(r"^%s_\d{4}-W\d{2}\.json$" % _re.escape(name))
                    mine = sorted(fn for fn in os.listdir(BACKUP_DIR) if pat.match(fn))
                    for fn in mine[:-BACKUPS_KEEP]:
                        os.remove(os.path.join(BACKUP_DIR, fn))
                except Exception:
                    pass

            self._send_json({"ok": True, "name": name, "bytes": len(raw),
                             "weeklyBackup": made_backup, "week": iso})
        except Exception as e:
            try:
                self.send_error(500, "save error: %s" % e)
            except Exception:
                pass

    def _data_load(self):
        try:
            name = self._data_name()
            if not name:
                return
            target = os.path.join(DATA_DIR, name + ".json")
            if not os.path.isfile(target):
                return self._send_json({"ok": False, "error": "not found", "name": name}, code=404)
            with open(target, "rb") as f:
                self._send_json(f.read())
        except Exception as e:
            try:
                self.send_error(500, "load error: %s" % e)
            except Exception:
                pass

    def _data_list(self):
        try:
            out = []
            if os.path.isdir(DATA_DIR):
                for fn in sorted(os.listdir(DATA_DIR)):
                    if fn.endswith(".json"):
                        fp = os.path.join(DATA_DIR, fn)
                        st = os.stat(fp)
                        out.append({"name": fn[:-5], "bytes": st.st_size,
                                    "geaendert": _time.strftime("%Y-%m-%d %H:%M", _time.localtime(st.st_mtime))})
            self._send_json({"ok": True, "count": len(out), "items": out})
        except Exception as e:
            try:
                self.send_error(500, "list error: %s" % e)
            except Exception:
                pass

    def _regelcheck(self):
        """v6.4: REGELCHECK direkt in der Morgenroutine anzeigen.
        Bisher musste man das Skript separat starten — also tat man es selten.
        Das Skript wird hier nur importiert und mit dem AKTUELLEN Datenordner des
        Servers aufgerufen; Regeln und Logik bleiben ausschliesslich in REGELCHECK.py."""
        try:
            import importlib.util
            pfad = os.path.join(DIRECTORY, "REGELCHECK.py")
            if not os.path.isfile(pfad):
                return self._send_json({"ok": False, "fehler": "REGELCHECK.py liegt nicht im Programmordner"}, 404)
            spec = importlib.util.spec_from_file_location("regelcheck_mod", pfad)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if not hasattr(mod, "analyse"):
                return self._send_json({"ok": False, "fehler": "REGELCHECK.py zu alt (Version 1.2 noetig)"}, 501)
            erg = mod.analyse(DATA_DIR)
            erg.pop("_bericht", None)
            return self._send_json(erg)
        except Exception as e:
            try:
                self._send_json({"ok": False, "fehler": "regelcheck: %s" % e}, 500)
            except Exception:
                pass

    def _archiv_werkzeug(self, was):
        """v6.19 (A3/A1d): auswertung/archiv_werkzeug.py mit dem AKTUELLEN Datenordner.
        was = "befuellen" (Rueckrechnung einspielen, Live-Tage bleiben) oder "bericht"."""
        try:
            import importlib.util
            pfad = os.path.join(DIRECTORY, "auswertung", "archiv_werkzeug.py")
            if not os.path.isfile(pfad):
                return self._send_json({"ok": False, "fehler": "auswertung/archiv_werkzeug.py fehlt"}, 404)
            spec = importlib.util.spec_from_file_location("archiv_werkzeug_mod", pfad)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            with _lock_fuer("archiv_werkzeug"):
                erg = mod.befuellen(DATA_DIR) if was == "befuellen" else mod.bericht(DATA_DIR)
            return self._send_json(erg)
        except Exception as e:
            try:
                self._send_json({"ok": False, "fehler": "archiv: %s" % e}, 500)
            except Exception:
                pass

    def list_directory(self, path):
        # Sicherheitsnetz: NIE ein Verzeichnis-Listing zeigen -> immer das Dashboard ausliefern.
        # Faengt jeden Weg ab, auf dem "/" doch bei der Standard-Auslieferung landet.
        self._serve_dashboard()
        return None

    def _ping(self):
        body = b'{"ok":true,"service":"morgenroutine-proxy"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def _quote(self):
        try:
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            symbol = (params.get("symbol", [""])[0]).strip()
            if not _SYM_RE.match(symbol):
                self.send_error(400, "bad symbol")
                return
            modules = "price,summaryDetail,calendarEvents,defaultKeyStatistics"
            body = None
            for attempt in (0, 1):
                crumb = _get_crumb(force=(attempt == 1))
                if not crumb:
                    continue
                url = ("https://query2.finance.yahoo.com/v10/finance/quoteSummary/%s?modules=%s&crumb=%s"
                       % (urllib.parse.quote(symbol), modules, urllib.parse.quote(crumb)))
                try:
                    body = _yget(url, timeout=15).read()
                    break
                except urllib.error.HTTPError as e:
                    if e.code in (401, 403):
                        _crumb["value"] = None
                        continue
                    raise
            if not body:
                self.send_error(502, "quoteSummary unavailable")
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            try:
                self.send_error(502, "quote error: %s" % e)
            except Exception:
                pass

    def _batch_quote(self, symbols):
        """v7/quote fuer eine Symbol-Liste (<=50), mit Crumb-Retry. Gibt result-Liste oder []."""
        qs = ",".join(symbols)
        for attempt in (0, 1):
            crumb = _get_crumb(force=(attempt == 1))
            if not crumb:
                continue
            url = ("https://query1.finance.yahoo.com/v7/finance/quote?symbols=%s&crumb=%s"
                   % (urllib.parse.quote(qs), urllib.parse.quote(crumb)))
            try:
                raw = _yget(url, timeout=20).read()
                data = json.loads(raw.decode("utf-8", "ignore"))
                return (data.get("quoteResponse", {}) or {}).get("result", []) or []
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    _crumb["value"] = None
                    continue
                return []
            except Exception:
                return []
        return []


    def _breite(self):
        """v6.19 (T1): Marktbreite aus Einzelaktien - S&P 500 und DAX.

        Nutzt dieselbe Kursabfrage wie der Gap-Scanner (v7/quote, 50er-Pakete), also
        keine zusaetzliche Datenquelle. Yahoo liefert 50- und 200-Tage-DURCHSCHNITTE
        (einfach, nicht exponentiell); der Anteil "in P3" ist deshalb eine Naeherung an
        die EMA-Definition der Rueckrechnung. Ergebnis 10 Minuten zwischengespeichert.
        """
        try:
            jetzt = _time.time()
            if _BREITE_CACHE["daten"] and jetzt - _BREITE_CACHE["ts"] < 600:
                return self._send_json(_BREITE_CACHE["daten"])
            jobs = []
            for markt, syms in (("US", SP500_SYMS), ("DE", DAX_SYMS)):
                for i in range(0, len(syms), 50):
                    jobs.append((markt, syms[i:i + 50]))

            def _run(job):
                mk, batch = job
                try:
                    return mk, self._batch_quote(batch)
                except Exception:
                    return mk, []
            with ThreadPoolExecutor(max_workers=4) as ex:
                res = list(ex.map(_run, jobs))
            out = {}
            for markt in ("US", "DE"):
                quotes = [q for mk, qs in res if mk == markt for q in qs]
                out[markt], out[markt + "_earnings"] = breite_aus_quotes(quotes)
            daten = {"ok": True, "ts": int(jetzt * 1000), "maerkte": out}
            _BREITE_CACHE.update(ts=jetzt, daten=daten)
            return self._send_json(daten)
        except Exception as e:
            try:
                self._send_json({"ok": False, "fehler": "breite: %s" % e}, 500)
            except Exception:
                pass

    def _gapscan(self):
        """Scannt SP500_SYMS + DAX_SYMS auf Open-vs-PrevClose-Gaps >= threshold (Default 5%)."""
        try:
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            try:
                thr = abs(float(params.get("threshold", ["5"])[0]))
            except Exception:
                thr = 5.0
            if thr < 0.1:
                thr = 0.1
            mode = (params.get("src", ["auto"])[0] or "auto").lower()
            if mode not in ("auto", "pre", "open"):
                mode = "auto"
            out = []
            scanned = 0
            quoted = 0

            # Jobs sammeln: (Markt, 50er-Batch). US-Universum ist gross (~600 Symbole -> ~13 Batches),
            # frueher strikt sequenziell (bis zu 13 x 20s). Jetzt parallel mit kleinem Pool:
            # 4 Worker -> grob 4x schnellere Wandzeit, ohne Yahoo mit zu vielen Calls zu reizen.
            jobs = []
            for market, syms in (("US", US_SYMS), ("DE", DAX_SYMS)):
                for i in range(0, len(syms), 50):
                    jobs.append((market, syms[i:i+50]))
            scanned = sum(len(b) for _, b in jobs)

            # Jeder Job liefert (market, [quotes]); Fehler eines Batches bleiben isoliert ([]).
            def _run(job):
                mk, batch = job
                try:
                    return mk, self._batch_quote(batch)
                except Exception:
                    return mk, []

            results = []
            with ThreadPoolExecutor(max_workers=4) as ex:
                results = list(ex.map(_run, jobs))

            # Verarbeitung NACH dem Netzwerk-Teil (rein CPU, deterministisch, Reihenfolge egal -> wird sortiert)
            for market, quotes in results:
                for q in quotes:
                        pc = q.get("regularMarketPreviousClose")
                        sym = q.get("symbol")
                        if not (pc and pc > 0):
                            continue
                        state = (q.get("marketState") or "").upper()
                        pm = q.get("preMarketPrice")
                        op = q.get("regularMarketOpen")
                        ref = None
                        src = ""
                        if mode == "pre":
                            if pm:
                                ref, src = pm, "Pre"
                        elif mode == "open":
                            if op and op > 0:
                                ref, src = op, "Open"
                        elif state in ("REGULAR", "POST"):
                            # Auto: Boerse offen/Nachboerse -> heutiger Eroeffnungs-Gap
                            if op and op > 0:
                                ref, src = op, "Open"
                            elif pm:
                                ref, src = pm, "Pre"
                        else:
                            # Auto: PRE/PREPRE/CLOSED (US vormittags DE-Zeit) -> Pre-Market bevorzugen
                            if pm:
                                ref, src = pm, "Pre"
                            elif op and op > 0:
                                ref, src = op, "Open"
                        if not ref:
                            continue
                        # v6.18 FIX (F18, Verdachtsteil): Fuer ein Pre-Market-Gap ist die Basis der
                        # letzte regulaere Schluss. Vor der Eroeffnung ist das regularMarketPrice.
                        # regularMarketPreviousClose kann in der Vorboerse noch der Schluss von
                        # VORGESTERN sein - dann zaehlte das Gap die ganze gestrige Bewegung mit.
                        # Waehrend der Handelszeit bleibt es bei regularMarketPreviousClose.
                        rmp = q.get("regularMarketPrice")
                        if src == "Pre" and state not in ("REGULAR", "POST") and rmp and rmp > 0:
                            pc = rmp
                        quoted += 1
                        gap = (ref - pc) / pc * 100.0
                        if abs(gap) >= thr:
                            vol = q.get("regularMarketVolume")
                            av = q.get("averageDailyVolume3Month")
                            qt = q.get("regularMarketTime")
                            # Build 15.14: "Open" aus einer Session, die >16 h zurueckliegt, ist GESTERN
                            # (typisch: DE-Titel vor XETRA-Eroeffnung, US-Titel am fruehen Morgen).
                            old = bool(src == "Open" and qt and (_time.time() - qt) > 16 * 3600)
                            # v6.18 FIX (F18): Auch Pre-Market-Kurse auf Alter pruefen. Die US-Vorboerse
                            # beginnt 4:00 New York = 10:00 deutscher Zeit; ein Scan davor kann einen
                            # Pre-Market-Kurs vom Vortag zeigen - bisher ohne Warnung.
                            pmt = q.get("preMarketTime")
                            if src == "Pre" and pmt and (_time.time() - pmt) > 16 * 3600:
                                old = True
                            out.append({
                                "symbol": sym,
                                "name": q.get("shortName") or q.get("longName") or sym,
                                "market": market,
                                "gap": round(gap, 2),
                                "src": src,
                                "ref": ref,
                                "prevClose": pc,
                                "avgVol": av,
                                "vol": vol,
                                "rvol": (round(vol / av, 2) if vol and av else None),
                                "exchange": q.get("fullExchangeName") or q.get("exchange"),
                                "state": state,
                                "qTime": qt,
                                "old": old,
                            })
            out.sort(key=lambda x: -abs(x["gap"]))
            payload = json.dumps({"ok": True, "threshold": thr, "scanned": scanned,
                                  "quoted": quoted, "count": len(out), "mode": mode, "gaps": out}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            try:
                self.wfile.write(payload)
            except Exception:
                pass
        except Exception as e:
            try:
                self.send_error(502, "gapscan error: %s" % e)
            except Exception:
                pass

    def _gapdetail(self):
        """Detail fuer EINEN Treffer: ATR(14) aus Tageshistorie + letzte Tage + gap-relevante News."""
        try:
            import datetime as _dt
            import time as _tm
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            sym = (params.get("symbol", [""])[0] or "").strip()
            if not sym or not _SYM_RE.match(sym):
                return self.send_error(400, "bad symbol")
            out = {"ok": True, "symbol": sym, "atr": None, "days": [], "news": [], "newsTotal": 0}
            # --- Tageshistorie (v8/chart) -> ATR + letzte Tage ---
            try:
                url = ("https://query1.finance.yahoo.com/v8/finance/chart/%s?range=3mo&interval=1d"
                       % urllib.parse.quote(sym))
                ch = json.loads(_yget(url, timeout=20).read().decode("utf-8", "ignore"))
                res = (ch.get("chart", {}).get("result") or [None])[0]
                if res:
                    ts = res.get("timestamp") or []
                    qd = (res.get("indicators", {}).get("quote") or [{}])[0]
                    hi, lo, cl = qd.get("high") or [], qd.get("low") or [], qd.get("close") or []
                    rows = []
                    for i in range(len(ts)):
                        if i < len(cl) and cl[i] is not None and i < len(hi) and hi[i] is not None and i < len(lo) and lo[i] is not None:
                            rows.append((ts[i], hi[i], lo[i], cl[i]))
                    trs = []
                    for j in range(1, len(rows)):
                        h, l, pc2 = rows[j][1], rows[j][2], rows[j - 1][3]
                        trs.append(max(h - l, abs(h - pc2), abs(l - pc2)))
                    # ── v6.0.1 FIX (ATR-METHODE WICH VOM REST DER SUITE AB) ─────
                    # Hier lief ein einfacher Durchschnitt der letzten 14 True Ranges.
                    # Der Client rechnet dagegen ueberall Wilder-Glaettung: SMA der
                    # ersten 14 als Startwert, danach a = (a*13 + tr) / 14.
                    # Ein Volatilitaetsausschlag, der 18 Tage zurueckliegt, wirkt beim
                    # Client noch nach, fiel hier aber nach genau 14 Tagen schlagartig
                    # heraus — Gap-Popup und Dashboard zeigten dann verschiedene ATR.
                    # Jetzt identisch zur JS-Funktion atr().
                    if len(trs) >= 14:
                        a = sum(trs[:14]) / 14.0
                        for _i in range(14, len(trs)):
                            a = (a * 13.0 + trs[_i]) / 14.0
                        out["atr"] = round(a, 4)
                    elif trs:
                        out["atr"] = round(sum(trs) / len(trs), 4)
                    last = rows[-6:]
                    for k in range(len(last)):
                        t, h, l, c = last[k]
                        prevc = last[k - 1][3] if k > 0 else (rows[-7][3] if len(rows) >= 7 else c)
                        chg = round((c - prevc) / prevc * 100.0, 2) if prevc else 0.0
                        out["days"].append({"date": _dt.datetime.fromtimestamp(t, _dt.timezone.utc).strftime("%d.%m."),
                                            "close": round(c, 2), "chg": chg})
            except Exception:
                pass
            # --- News (v1/search), zeitgefiltert (~72h), neueste zuerst, Top 3 ---
            try:
                nurl = ("https://query1.finance.yahoo.com/v1/finance/search?q=%s&newsCount=12&quotesCount=0"
                        % urllib.parse.quote(sym))
                nd = json.loads(_yget(nurl, timeout=15).read().decode("utf-8", "ignore"))
                allnews = nd.get("news") or []
                out["newsTotal"] = len(allnews)
                cutoff = _tm.time() - 72 * 3600
                fresh = [{"title": it.get("title") or "", "publisher": it.get("publisher") or "",
                          "time": it.get("providerPublishTime") or 0, "link": it.get("link") or ""}
                         for it in allnews if (it.get("providerPublishTime") or 0) >= cutoff]
                fresh.sort(key=lambda x: -x["time"])
                out["news"] = fresh[:3]
            except Exception:
                pass
            payload = json.dumps(out).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            try:
                self.wfile.write(payload)
            except Exception:
                pass
        except Exception as e:
            try:
                self.send_error(502, "gapdetail error: %s" % e)
            except Exception:
                pass

    def _proxy(self):
        try:
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            target = params.get("url", [None])[0]
            if not target and self.path.startswith("/proxy/"):
                # Pfadform /proxy/https://... (Route existiert -> Handler muss sie auch koennen)
                target = urllib.parse.unquote(self.path[len("/proxy/"):])
            if not target:
                self.send_error(400, "missing url parameter")
                return

            parsed = urllib.parse.urlparse(target)
            host = parsed.hostname or ""
            if parsed.scheme != "https":
                self.send_error(403, "scheme not allowed: %s" % parsed.scheme)
                return
            if host not in ALLOWED_HOSTS:
                self.send_error(403, "host not allowed: %s" % host)
                return

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
            }
            if "yahoo.com" in host:
                headers["Referer"] = "https://finance.yahoo.com/"
                headers["Origin"] = "https://finance.yahoo.com"
            req = urllib.request.Request(target, headers=headers)
            # 25 s: das Treasury-Jahres-XML ist gross und der Server dort traege
            # ── v6.0.3 FIX (UNBEGRENZTES LESEN) ─────────────────────────────
            # resp.read() ohne Argument liest, was auch immer die Gegenseite sendet,
            # vollstaendig in den Speicher. Bei einer fehlkonfigurierten oder
            # kompromittierten Quelle in der Allowlist kann das den Rechner
            # lahmlegen — der Server laeuft mit voller Nutzerberechtigung.
            # 20 MB reichen fuer alles, was hier legitim geholt wird: das groesste
            # Objekt ist die Treasury-Jahres-XML mit wenigen MB.
            MAX_BODY = 20 * 1024 * 1024
            with _proxy_opener.open(req, timeout=25) as resp:   # v6.3: Redirect-geprueft
                body = resp.read(MAX_BODY + 1)
                if len(body) > MAX_BODY:
                    self.send_error(502, "upstream response too large (>20 MB)")
                    return
                ctype = resp.headers.get("Content-Type", "application/json")

            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        except urllib.error.HTTPError as e:
            self.send_error(e.code, "upstream HTTP %s" % e.code)
        except Exception as e:
            try:
                self.send_error(502, "proxy error: %s" % e)
            except Exception:
                pass

    # ruhigere Konsole: nur Proxy-Treffer kurz anzeigen
    # v15.15: mit ECHTEM Status (vorher stand auch bei 403/502 "ok" da)
    def log_message(self, fmt, *args):
        try:
            line = fmt % args
        except Exception:
            return
        if "/proxy" in line:
            m = _re.search(r'"\s*(\d{3})\s', line) or _re.search(r"\s(\d{3})\s*(?:-|$)", line)
            code = m.group(1) if m else "?"
            sys.stdout.write("  proxy: ok\n" if code == "200" else "  proxy: HTTP %s\n" % code)


def main():
    # Konsolen-Ausgabe gegen Encoding-Crashes haerten (Windows cmd ist oft cp850/cp437):
    # ohne dies wirft print() mit Sonderzeichen einen UnicodeEncodeError -> Server startet nicht.
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    os.chdir(DIRECTORY)
    # SO_REUSEADDR AUS (wichtig unter Windows!): verhindert, dass sich ein
    # zweiter Server still neben einen bereits laufenden (Zombie) setzt.
    # Haengt noch ein alter Server am Port -> Start schlaegt LAUT fehl.
    socketserver.ThreadingTCPServer.allow_reuse_address = False
    # Daemon-Threads: haengende Requests (z.B. langsames Treasury-XML) blockieren STRG+C nicht
    socketserver.ThreadingTCPServer.daemon_threads = True
    try:
        httpd = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler)
    except OSError as e:
        # Port belegt -> es laeuft bereits ein (alter) Server. Welchen Build liefert er aus?
        old_build = "unbekannt"
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/%s" % (PORT, INDEX_FILE), timeout=4) as r:
                _h = r.read().decode("utf-8", "ignore")
            m = _re.search(r"Build (\d+\.\d+)", _h)
            if m:
                old_build = "Build " + m.group(1)
        except Exception:
            pass
        print("\n" + "!" * 64)
        print(" PORT %d IST BELEGT - es laeuft bereits ein Server (liefert: %s)." % (PORT, old_build))
        print(" Das ist fast sicher ein ALTES Konsolenfenster mit einem alten Ordner.")
        print("")
        print(" LOESUNG (sicher): PC einmal NEU STARTEN, dann diese .bat erneut.")
        print(" Oder manuell:")
        print("  1) cmd ALS ADMINISTRATOR oeffnen")
        print("  2) netstat -ano | findstr :8765   ->  PID(s) ablesen")
        print("  3) taskkill /F /PID <pid>          ->  fuer JEDE PID")
        print("  4) START_Batch.bat erneut starten.")
        print("!" * 64)
        try:
            input("\nEnter zum Schliessen...")
        except (EOFError, KeyboardInterrupt):
            pass
        return

    root_url = "http://localhost:%d/" % PORT
    # v15.17: Wenn ein Trading-Hub im Ordner liegt, beim Start DAS Hub oeffnen (Zentrale).
    # Ohne Hub-Datei weiterhin das Dashboard. Cache-Buster -> immer frisch, kein haengender Tab.
    hub = "Trading-Hub_v6.html" if os.path.isfile(os.path.join(DIRECTORY, "Trading-Hub_v6.html")) else ""
    open_url = "%s%s?t=%d" % (root_url, hub, int(_time.time()))
    # Selbst-Check: welchen Build enthaelt die HTML in DIESEM Ordner?
    idx_path = os.path.join(DIRECTORY, INDEX_FILE)
    try:
        with open(idx_path, "r", encoding="utf-8", errors="ignore") as f:
            _html = f.read()
        m = _re.search(r"Build (\d+\.\d+)", _html)
        if m:
            html_status = "Build %s gefunden [OK]" % m.group(1)
        else:
            html_status = "ALTE/UNBEKANNTE DATEI [!] kein 'Build x.y' gefunden -> falsche HTML in diesem Ordner"
    except FileNotFoundError:
        html_status = "NICHT GEFUNDEN [!] %s liegt nicht in diesem Ordner" % INDEX_FILE

    print("=" * 64)
    print(" Morgenroutine - Server laeuft   >>> SERVER-VERSION %s (ROOT-MODUS) <<<" % SERVER_VERSION)
    print("=" * 64)
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)
    except Exception:
        pass
    print(" Dashboard : %s   (oeffnet automatisch)" % root_url)
    print(" Proxy     : http://localhost:%d/proxy?url=..." % PORT)
    # v6.1: Herkunft mit ausgeben — sonst sieht man beim Start nicht, ob die
    # eigene Einstellung ueberhaupt gegriffen hat.
    print(" Daten     : %s" % DATA_DIR)
    print("             Quelle: %s%s" % (_QUELLE,
          "  <- datenordner.txt aendern, um ihn zu verschieben" if _QUELLE.startswith("Standard") else ""))
    print(" Backups   : %s   (1x pro Kalenderwoche, %d Wochen Vorrat)" % (BACKUP_DIR, BACKUPS_KEEP))
    print(" Ordner    : %s" % DIRECTORY)
    print(" HTML-Datei: %s" % html_status)
    print(" Beenden   : STRG + C")
    print("=" * 64)
    print(" Sieht die Zeile oben NICHT 'SERVER-VERSION %s' -> du startest eine ALTE .py." % SERVER_VERSION)
    print("=" * 64)
    if "[!]" in html_status:
        print(" >> Lege die neue %s GENAU in diesen Ordner" % INDEX_FILE)
        print(" >> (oben bei 'Ordner') und ueberschreibe die alte. Dann Browser Strg+Shift+R.")
        print("=" * 64)
    if "onedrive" in DIRECTORY.lower():
        print(" !! WARNUNG: Dieser Ordner liegt in OneDrive.")
        print(" !! OneDrive liefert oft ALTE/zwischengespeicherte Dateien aus und")
        print(" !! erzeugt Konflikt-Kopien -> du siehst dann eine veraltete Version.")
        print(" !! Lege das Cockpit besser in einen LOKALEN Ordner, z.B. C:\\Morgenroutine")
        print(" !! (NICHT unter OneDrive/Desktop).")
        print("=" * 64)
    try:
        import webbrowser
        webbrowser.open(open_url)
    except Exception:
        pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer beendet.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
