"""Marktsammler v1.2.6: eigenständiges Programm nur zum Sammeln, mit Statusseite im Browser (http://127.0.0.1:8770/).

Tagesplan (Rechnerzeit, Deutschland):
  außerhalb 15:25-22:10 (und am Wochenende): Historie holen = Tageskerzen für alle Werte der watchlist.csv, danach Stundenkerzen.
                                              Beim ersten Lauf die ganze Historie, später nur die Differenz seit dem letzten Stand.
  15:25-22:10 an Börsentagen:                 SPX/SPXW-Optionskette in Durchläufen (gleiches Format wie bisher: daten/kette_JJJJMMTT.csv).
Nur lesend, es werden keine Orders gesendet. Historie-Abfragen belegen keine Marktdaten-Leitungen, die Optionsphase bleibt unter dem Limit.

Start: start_sammler.bat  (TWS muss laufen, API aktiv, Port 7497 Paper)     Test ohne TWS: python sammler.py --sim
Vorhandene Datenordner einfach in "daten" hineinkopieren: der Sammler macht dort weiter (Optionsdateien werden angehängt, Kerzen nur ergänzt).
"""
import asyncio, csv, datetime as dt, importlib, json, math, os, random, re, shutil, sys, threading, time, traceback, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------ Einstellungen
HOST, PORT, CLIENT_ID = "127.0.0.1", 7497, 80     # Paper 7497, Live 7496; Client-ID 80 (Trader nutzen 79, alter Sammler 78)
HTTP_PORT = 8770
MARKTDATENTYP = 1             # 1 live, fällt automatisch auf 3 (verzögert) zurück
MAX_LEITUNGEN = 100           # Marktdaten-Leitungen laut Konto (TWS: Konto-Verwaltung). Optionsblock plus 2 (SPX, VIX) bleibt darunter
BLOCK = 90                    # Optionskontrakte gleichzeitig; muss + 2 <= MAX_LEITUNGEN sein
WARTE = 7.0                   # Sekunden Wartezeit je Optionsblock
PAUSE_MIN = 20                # Minuten Pause zwischen zwei Optionsdurchläufen
OPT_FENSTER = ("15:25", "22:10")   # Rechnerzeit; nur Mo-Fr
MAX_DTE = 200; BAND_PUT, BAND_CALL = 0.12, 0.10; ATM_BAND = 0.015
NAH = (25, 50); SCHRITT_NAH, SCHRITT_FERN = 5, 25
NUR_FREITAG_UND_MONAT = True
KLASSEN = ("SPXW", "SPX")
ALT_BOERSEN = {"IBIS": [("SMART", "IBIS")], "NYBOT": [("ICEUS", None)], "ICEUS": [("NYBOT", None)], "EUREX": [("DTB", None)]}   # Ersatz-Börsen, falls die TWS den Kontrakt unter der ersten nicht findet
PARALLEL = 8                  # gleichzeitige Historie-Anfragen (jeder Wert immer nur einer gleichzeitig); die TWS erlaubt bis ca. 50 offene, bei Pacing-Meldungen bremst der Sammler selbst
HIST_PAUSE = 0.6              # Sekunden Pause je Arbeiter zwischen zwei Historie-Abfragen; wird bei Pacing-Meldungen der TWS automatisch länger (bis 15 s) und danach rasch wieder kürzer
TAGES_JAHRE = 25              # erster Lauf: so viele Jahre Tageskerzen
STUNDEN_JAHRE = 2             # erster Lauf: so weit zurück Stundenkerzen (die TWS liefert, so viel sie hat; es wird bis zum Ende der Daten geholt)
M5_ERST = 0.25                # erster Lauf: Fünf-Minuten-Kerzen zunächst nur so viele Jahre zurück (0,25 = 3 Monate), damit alle Werte schnell nutzbar sind
M5_JAHRE = 2                  # danach, nach allem anderen und unterbrechbar: Fünf-Minuten-Kerzen so weit zurück vertiefen
RETRY_TAGE = 2                # Werte ohne Daten/Kontrakt werden frühestens nach so vielen Tagen erneut versucht (Aktualisieren-Button: sofort)
BLOECKE = {"H": ["3 M", "1 M", "2 W"], "M5": ["1 M", "2 W", "1 W", "3 D"]}   # Stückgrößen, bei Fehlermeldung der TWS automatisch eine Stufe kleiner
BLOCK_TAGE = {"1 Y": 365, "6 M": 180, "3 M": 90, "1 M": 30, "2 W": 14, "1 W": 7, "3 D": 3, "1 D": 1}
BLOCK_STUFE = {"H": 0, "M5": 0}
FUT_LEITER = {"H": ["3 M", "1 M", "2 W", "1 W"], "M5": ["1 M", "2 W", "1 W", "3 D"]}   # Dauer-Futures: ein Stück ab jetzt (kein Enddatum erlaubt), größte Stückgröße zuerst
FUT_STUFE = {"H": 0, "M5": 0}
STUFEN = {"D": ("Tageskerzen", "tageskerzen"), "H": ("Stundenkerzen", "stundenkerzen"), "M5": ("5-Minuten-Kerzen", "fuenfminuten")}
REIHENFOLGE = ("D", "H", "M5")
DATEN = os.path.join(HERE, "daten")
WATCHLIST = os.path.join(HERE, "watchlist.csv")
SIM = "--sim" in sys.argv
if SIM: STUNDEN_JAHRE, M5_JAHRE, M5_ERST = 0.02, 0.02, 0.005
OPT_SPALTEN = ["zeit", "durchlauf", "spx", "vix", "klasse", "verfall", "dte", "art", "strike", "bid", "ask", "last", "volumen", "oi", "tws_iv", "tws_delta", "datentyp"]
KERZ_SPALTEN = ["zeit", "open", "high", "low", "close", "volume"]

# ------------------------------------------------------------ Zustand für die Statusseite
LOCK = threading.Lock()
ST = dict(verbunden=False, phase="Start", pause=False, stopp=False, datentyp=None, job="", hist=dict(D=[0, 0], H=[0, 0], M5=[0, 0]), aktualisieren=False, laufzeit={}, opt=dict(durchlauf=0, kontrakte=[0, 0], zeilen_heute=0, letzte="", leitungen=0),
          letzter_wert=None, fehler="", symbole={}, pausensek=HIST_PAUSE, start=time.time(), naechste_phase="")
LOGZ = []

def log(*a):
    z = " ".join([dt.datetime.now().strftime("%H:%M:%S")] + [str(x) for x in a]); print(z, flush=True)
    with LOCK: LOGZ.append(z); del LOGZ[:-80]
    try:
        with open(os.path.join(HERE, "sammler.log"), "a", encoding="utf-8") as f: f.write(dt.date.today().isoformat() + " " + z + "\n")
    except Exception: pass

def setze(**kw):
    with LOCK: ST.update(kw)

def windows_schutz():
    if os.name != "nt": return
    try:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
        k = ctypes.windll.kernel32; h = k.GetStdHandle(-10); m = ctypes.c_uint32()
        if k.GetConsoleMode(h, ctypes.byref(m)): k.SetConsoleMode(h, (m.value & ~0x0040) | 0x0080)
    except Exception as e: log("Windows-Schutz nicht aktiv:", e)

# ------------------------------------------------------------ Dateien
class KontraktFehler(Exception): pass
GRUPPEN = ["Aktie", "Index", "ETF", "Future", "Währung"]
HLOCK = threading.Lock(); HINWEISE = {}; NAMEN = {}; TIEFE = {}; PLAN = []; PERM = {}   # PERM: fehlende Marktdaten-Berechtigung je Börse

def _json_lesen(name):
    try:
        with open(os.path.join(DATEN, name), encoding="utf-8") as f: return json.load(f)
    except Exception: return {}

def _json_schreiben(name, d):
    try:
        tmp = os.path.join(DATEN, name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, os.path.join(DATEN, name))
    except Exception as e: log("Konnte", name, "nicht speichern:", e)

def hinweis_setzen(st, key, grund):
    with HLOCK:
        HINWEISE[st + "|" + key] = dict(grund=str(grund)[:160], zeit=dt.datetime.now().isoformat(timespec="seconds")); _json_schreiben("_hinweise.json", HINWEISE)

def hinweis_aktiv(st, key):
    for k in (st + "|" + key, "*|" + key):
        h = HINWEISE.get(k)
        if h and (dt.datetime.now() - dt.datetime.fromisoformat(h["zeit"])).days < RETRY_TAGE: return True
    return False

def hinweis_text(st, key):
    h = HINWEISE.get(st + "|" + key) or HINWEISE.get("*|" + key)
    return h["grund"] if h else ""

def watchlist_lesen():
    """Spalten: symbol;typ;boerse;waehrung;rth;gruppe;untergruppe;name;handelsklasse;multiplikator;stufen (alte v1.1-Dateien mit weniger Spalten gehen weiter)."""
    if not os.path.exists(WATCHLIST): return []
    plan = []; gesehen = set()
    with open(WATCHLIST, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f, delimiter=";"):
            z = {(k or "").strip(): (v or "").strip() for k, v in r.items()}
            if not z.get("symbol") or z["symbol"].startswith("#"): continue
            z["typ"] = (z.get("typ") or "STK").upper()
            if (z["typ"], z["symbol"], z.get("boerse")) in gesehen: continue
            gesehen.add((z["typ"], z["symbol"], z.get("boerse")))
            g = z.get("gruppe") or ""; sub = [x for x in (z.get("untergruppe") or "").split("|") if x]
            if g == "S&P500": g = "Aktie"; sub = sub or ["S&P500"]
            z["gruppe"] = g or {"STK": "Aktie", "IND": "Index", "FUT": "Future", "CASH": "Währung"}.get(z["typ"], "Aktie"); z["sub"] = sub
            z["rth"] = z.get("rth") or ("0" if z["typ"] in ("FUT", "CASH") else "1")
            z["stufen"] = [x for x in re.split(r"[,|\s]+", z.get("stufen") or "D,H") if x in STUFEN]
            plan.append(z)
    zaehl = {}
    for z in plan: zaehl[z["symbol"]] = zaehl.get(z["symbol"], 0) + 1
    # Gleiches Kürzel mehrfach (z. B. ES = Eversource / E-mini S&P, CL = Colgate / Rohöl, DTE = DTE Energy / Deutsche Telekom): Future bekommt _FUT, deutsche Aktie _DE im Dateinamen
    for z in plan:
        suf = ("_FUT" if z["typ"] == "FUT" else "_DE" if z["typ"] == "STK" and z.get("waehrung") == "EUR" else "") if zaehl[z["symbol"]] > 1 else ""
        z["key"] = z["symbol"] + suf
        z["name"] = z.get("name") or NAMEN.get(z["key"], "")
    return plan

def kerz_datei(art, key):
    ordner = os.path.join(DATEN, STUFEN[art][1]); os.makedirs(ordner, exist_ok=True)
    return os.path.join(ordner, key.replace(" ", "_").replace("/", "_") + ".csv")

def kerzen_lesen(datei):
    d = {}
    if os.path.exists(datei):
        with open(datei, encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter=";"): d[r["zeit"]] = [r["open"], r["high"], r["low"], r["close"], r["volume"]]
    return d

def kerzen_schreiben(datei, d):
    tmp = datei + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";"); w.writerow(KERZ_SPALTEN)
        for k in sorted(d): w.writerow([k] + d[k])
    os.replace(tmp, datei)

def stand(art, key):
    """(erste Kerze, letzte Kerze, Anzahl) ohne die ganze Datei zu parsen."""
    datei = kerz_datei(art, key)
    if not os.path.exists(datei): return (None, None, 0)
    try:
        with open(datei, "rb") as f:
            f.readline(); erste = f.readline().decode("utf-8", "ignore").split(";")[0].strip()
            if not erste: return (None, None, 0)
            f.seek(0, 2); size = f.tell(); f.seek(max(0, size - 2000)); tail = f.read().decode("utf-8", "ignore").splitlines()
            letzte = next((x.split(";")[0] for x in reversed(tail) if x.strip()), None)
            f.seek(0); n = sum(chunk.count(b"\n") for chunk in iter(lambda: f.read(1 << 20), b"")) - 1
        return (erste, letzte, max(0, n))
    except Exception: return (None, None, 0)

def kollision_sichern(plan):
    """v1.1 hat Aktie und Future mit gleichem Kürzel (ES, CL) in dieselbe Datei geschrieben. Diese vermischten Dateien werden einmalig beiseitegelegt und neu geholt."""
    sich = os.path.join(DATEN, "_kollision_sicherung")
    for z in plan:
        if not z["key"].endswith("_FUT"): continue
        marke = os.path.join(sich, "erledigt_" + z["symbol"] + ".txt")
        if os.path.exists(marke): continue
        for st in STUFEN:
            alt = kerz_datei(st, z["symbol"])
            if os.path.exists(alt):
                ziel = os.path.join(sich, STUFEN[st][1]); os.makedirs(ziel, exist_ok=True); shutil.move(alt, os.path.join(ziel, os.path.basename(alt)))
                log("Kollision %s: vermischte Datei %s nach _kollision_sicherung verschoben, wird neu geholt" % (z["symbol"], os.path.basename(alt)))
        os.makedirs(sich, exist_ok=True)
        with open(marke, "w", encoding="utf-8") as f: f.write("erledigt " + dt.datetime.now().isoformat(timespec="seconds"))

def plan_laden():
    global PLAN
    plan = watchlist_lesen(); kollision_sichern(plan); sym = {}
    for z in plan:
        s = {"symbol": z["symbol"], "typ": z["typ"], "gruppe": z["gruppe"], "name": z["name"], "sub": z["sub"]}
        for st in REIHENFOLGE:
            if st in z["stufen"]: s[st] = list(stand(st, z["key"]))
        sym[z["key"]] = s
    with LOCK: ST["symbole"] = sym
    PLAN = plan; return plan

def kette_datei(): return os.path.join(DATEN, "kette_%s.csv" % dt.date.today().strftime("%Y%m%d"))

def letzter_durchlauf(datei):
    if not os.path.exists(datei): return 0
    n = 0
    try:
        with open(datei, "rb") as f:
            f.seek(0, 2); size = f.tell(); f.seek(max(0, size - 4000)); tail = f.read().decode("utf-8", "ignore").splitlines()
        for z in reversed(tail):
            p = z.split(";")
            if len(p) > 2 and p[1].isdigit(): n = int(p[1]); break
    except Exception: pass
    return n

# ------------------------------------------------------------ Quellen
def dritter_freitag(d): return d.weekday() == 4 and 15 <= d.day <= 21

def strike_auswahl(strikes, spot, dte):
    step = SCHRITT_NAH if NAH[0] <= dte <= NAH[1] else SCHRITT_FERN; out = []
    for K in sorted(strikes):
        rel = K / spot - 1
        if abs(rel) <= ATM_BAND:
            if K % (SCHRITT_NAH if abs(rel) <= 0.006 else step) == 0: out += [(K, "P"), (K, "C")]
        elif -BAND_PUT <= rel < -ATM_BAND and K % step == 0: out.append((K, "P"))
        elif ATM_BAND < rel <= BAND_CALL and K % step == 0: out.append((K, "C"))
    return out

def verfaelle_waehlen(chains, heute):
    res = []
    for klasse, exps in chains.items():
        for e in exps:
            d = dt.datetime.strptime(e, "%Y%m%d").date(); dte = (d - heute).days
            if dte < 1 or dte > MAX_DTE: continue
            if NUR_FREITAG_UND_MONAT and not (d.weekday() == 4 or (klasse == "SPX" and dritter_freitag(d))): continue
            res.append((klasse, e, dte))
    return sorted(res, key=lambda x: (x[2], x[0]))

class IBQuelle:
    def __init__(s):
        asyncio.set_event_loop(asyncio.new_event_loop())
        try: s.ibx = importlib.import_module("ib_async")
        except ImportError: s.ibx = importlib.import_module("ib_insync")
        s.ib = s.ibx.IB(); s.typ = MARKTDATENTYP; s.pacing = False; s.hist_fehler = None; s.cache = {}; s.fehler_con = {}; s.fehler_zeit = 0
        s.ib.errorEvent += s._fehler
    def _fehler(s, reqId, code, msg, *a):
        msg = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), msg)   # TWS liefert Umlaute als \u00fc
        if code in (2104, 2106, 2107, 2108, 2119, 2158, 2103, 2105, 2157): return
        if code == 162 and "pacing" in msg.lower(): s.pacing = True
        if code in (162, 165, 200, 321, 366, 354, 10167):
            s.hist_fehler = (code, msg); s.fehler_zeit = time.time(); con = getattr(a[0], "conId", None) if a else None
            if con: s.fehler_con[con] = (code, msg)
        if code in (1100, 1101, 1102, 502, 504): log("TWS-Meldung", code, msg)
        else: log("TWS", code, msg[:140])
    def verbinden(s):
        s.ib.connect(HOST, PORT, clientId=CLIENT_ID, timeout=20); s.ib.reqMarketDataType(s.typ)
        s.spx = s.ibx.Index("SPX", "CBOE"); s.vix = s.ibx.Index("VIX", "CBOE"); s.ib.qualifyContracts(s.spx, s.vix); s.t_spx = s.t_vix = None
    def basis_starten(s):
        if s.t_spx is not None: return
        s.t_spx = s.ib.reqMktData(s.spx, "", False, False); s.t_vix = s.ib.reqMktData(s.vix, "", False, False); s.ib.sleep(4)
        for neu in (3, 4):
            if s._gueltig(s.t_spx): break
            log("Keine Echtzeitdaten, wechsle auf Datentyp", neu)
            s.ib.cancelMktData(s.spx); s.ib.cancelMktData(s.vix); s.typ = neu; s.ib.reqMarketDataType(neu); s.ib.sleep(1)
            s.t_spx = s.ib.reqMktData(s.spx, "", False, False); s.t_vix = s.ib.reqMktData(s.vix, "", False, False); s.ib.sleep(5)
    def basis_stoppen(s):
        if s.t_spx is None: return
        try: s.ib.cancelMktData(s.spx); s.ib.cancelMktData(s.vix)
        except Exception: pass
        s.t_spx = s.t_vix = None
    @staticmethod
    def _gueltig(t): return any(v is not None and v == v and v > 0 for v in (t.last, t.close, t.bid, t.ask))
    @staticmethod
    def _preis(t):
        for v in (t.last, t.bid, t.close):
            if v is not None and v == v and v > 0: return float(v)
        try:
            m = t.marketPrice()
            if m == m and m > 0: return float(m)
        except Exception: pass
        return None
    def basis(s):
        sp = s._preis(s.t_spx); vx = s._preis(s.t_vix)
        if sp is None: raise RuntimeError("Kein SPX-Kurs von der TWS")
        return sp, vx
    def ketten(s):
        res = {}
        for c in s.ib.reqSecDefOptParams("SPX", "", "IND", s.spx.conId):
            if c.exchange not in ("SMART", "CBOE") or c.tradingClass not in KLASSEN: continue
            r = res.setdefault(c.tradingClass, {"exps": set(), "strikes": set()}); r["exps"] |= set(c.expirations); r["strikes"] |= set(c.strikes)
        return res
    def block(s, auftraege):
        ibx = s.ibx; cs = []; neu = []
        for kl, e, K, a in auftraege:
            c = s.cache.get((kl, e, K, a))
            if c is None: c = ibx.Option("SPX", e, float(K), a, "SMART", tradingClass=kl, currency="USD"); neu.append(c)
            cs.append(c)
        if neu: s.ib.qualifyContracts(*neu)
        for (kl, e, K, a), c in zip(auftraege, cs):
            if c.conId: s.cache[(kl, e, K, a)] = c
        ts = [s.ib.reqMktData(c, "100,101,106", False, False) if c.conId else None for c in cs]
        s.ib.sleep(WARTE); out = []
        for (kl, e, K, a), c, t in zip(auftraege, cs, ts):
            if t is None: out.append(dict(bid=None, ask=None, last=None, volumen=None, oi=None, tws_iv=None, tws_delta=None)); continue
            ok = lambda x: x if (x is not None and x == x and x > 0) else None
            g = t.modelGreeks; oi = t.callOpenInterest if a == "C" else t.putOpenInterest
            out.append(dict(bid=ok(t.bid), ask=ok(t.ask), last=ok(t.last), volumen=(t.volume if t.volume == t.volume else None), oi=(oi if oi == oi else None),
                            tws_iv=(g.impliedVol if g and g.impliedVol else None), tws_delta=(g.delta if g and g.delta is not None else None)))
            s.ib.cancelMktData(c)
        return out
    # --- Historie
    async def vertrag(s, z):
        ibx = s.ibx; k = z["key"]
        if k in s.cache: return s.cache[k]
        t = z["typ"]; w = z.get("waehrung") or "USD"; ex0 = z.get("boerse") or "SMART"
        for ex, prim in [(ex0, None)] + ALT_BOERSEN.get(ex0, []):
            if t == "STK": c = ibx.Stock(z["symbol"], ex, w, primaryExchange=prim) if prim else ibx.Stock(z["symbol"], ex, w)
            elif t == "IND": c = ibx.Index(z["symbol"], ex, w)
            elif t == "CASH": c = ibx.Forex(z["symbol"])
            else:
                c = ibx.ContFuture(z["symbol"], ex, currency=w)
                if z.get("handelsklasse"): c.tradingClass = z["handelsklasse"]
                if z.get("multiplikator"): c.multiplier = z["multiplikator"]
            try: q = [x for x in (await s.ib.qualifyContractsAsync(c) or []) if x]
            except Exception as e: log("Kontrakt-Prüfung", z["symbol"], ex, repr(e)[:100]); q = []
            if q: break
        else: raise KontraktFehler("Kontrakt nicht gefunden: %s (%s)" % (z["symbol"], ex0))
        s.cache[k] = c
        if not z.get("name"):
            try:
                det = await s.ib.reqContractDetailsAsync(c)
                if det and det[0].longName:
                    z["name"] = NAMEN[k] = det[0].longName; _json_schreiben("_namen.json", NAMEN)
                    with LOCK: ST["symbole"].setdefault(k, {})["name"] = z["name"]
            except Exception: pass
        return c
    async def hist(s, z, art, ende, dauer, rth):
        """Liefert Ergebnis (dict zeit -> [open, high, low, close, volume]; UTC-ISO bei Stunden/Minuten, Datum bei Tagen) samt Fehlermeldung dieser Anfrage."""
        if z["typ"] == "FUT" and ende:   # Dauer-Futures erlauben kein Enddatum: die TWS meldet 10339 und trennt die Verbindung
            d = Ergebnis(); d.fehler = (10339, "Enddatum bei Dauer-Futures nicht erlaubt"); return d
        c = await s.vertrag(z); s.fehler_con.pop(c.conId, None); tag = art == "D"; t0 = time.time()
        bars = await s.ib.reqHistoricalDataAsync(c, endDateTime=ende, durationStr=dauer, barSizeSetting={"D": "1 day", "H": "1 hour", "M5": "5 mins"}[art],
                                                 whatToShow="MIDPOINT" if z["typ"] == "CASH" else "TRADES", useRTH=bool(rth), formatDate=1 if tag else 2, keepUpToDate=False, timeout=90)
        d = Ergebnis()
        for b in bars or []:
            k = b.date.isoformat() if tag else b.date.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
            d[k] = [b.open, b.high, b.low, b.close, b.volume]
        if not d:
            d.fehler = s.fehler_con.pop(c.conId, None) or (s.hist_fehler if time.time() - s.fehler_zeit < 3 and s.fehler_zeit >= t0 - 1 else None)
            d.pacing = bool(d.fehler and "pacing" in d.fehler[1].lower())
        return d
    def run(s, coro): return s.ib.run(coro)
    async def apause(s, sek): await asyncio.sleep(sek)
    def pause(s, sek): s.ib.sleep(sek)
    def trennen(s):
        try: s.ib.disconnect()
        except Exception: pass

class SimQuelle:
    """Künstliche Daten zum Testen ohne TWS."""
    def __init__(s): s.rng = random.Random(3); s.typ = 3; s.spot = 7700.0; s.vix = 17.5; s.t_spx = None; s.loop = asyncio.new_event_loop()
    def verbinden(s): log("Simulation: keine TWS-Verbindung")
    def basis_starten(s): s.t_spx = 1
    def basis_stoppen(s): s.t_spx = None
    def basis(s): s.spot *= 1 + s.rng.gauss(0, .001); return s.spot, s.vix
    def ketten(s):
        h = dt.date.today(); ex = {(h + dt.timedelta(days=i)).strftime("%Y%m%d") for i in range(1, 200) if (h + dt.timedelta(days=i)).weekday() == 4}
        stk = set(range(5000, 10000, 5)); return {"SPXW": {"exps": ex, "strikes": stk}, "SPX": {"exps": set(), "strikes": stk}}
    def block(s, au):
        out = []
        for kl, e, K, a in au:
            dte = max(1, (dt.datetime.strptime(e, "%Y%m%d").date() - dt.date.today()).days); m = (s.spot - K) if a == "P" else (K - s.spot)
            p = max(m, 0) + 0.15 * s.vix * math.sqrt(dte) * math.exp(-abs(m) / 400); out.append(dict(bid=round(p * .99, 2), ask=round(p * 1.01, 2), last=None, volumen=0, oi=100, tws_iv=0.18, tws_delta=-0.3))
        return out
    def run(s, coro): return s.loop.run_until_complete(coro)
    async def apause(s, sek): await asyncio.sleep(min(sek, 0.002))
    async def hist(s, z, art, ende, dauer, rth):
        await asyncio.sleep(0)
        if z["typ"] == "FUT" and ende: d = Ergebnis(); d.fehler = (10339, "Enddatum bei Dauer-Futures nicht erlaubt"); return d
        if z["symbol"].startswith("XXX"): raise KontraktFehler("Kontrakt nicht gefunden: " + z["symbol"])
        d = Ergebnis(); p = 100.0
        if art == "D":
            t0 = dt.date.today()
            for i in range(40): p *= 1 + s.rng.gauss(0, .01); d[(t0 - dt.timedelta(days=40 - i)).isoformat()] = [round(p, 2), round(p * 1.01, 2), round(p * .99, 2), round(p, 2), 1000]
        else:
            end = dt.datetime.strptime(ende, "%Y%m%d-%H:%M:%S") if ende else jetzt_utc(); schritt = 60 if art == "H" else 5
            for i in range(200): p *= 1 + s.rng.gauss(0, .003); d[(end - dt.timedelta(minutes=schritt * (200 - i))).strftime("%Y-%m-%dT%H:%M:%S")] = [round(p, 2), round(p * 1.01, 2), round(p * .99, 2), round(p, 2), 1000]
        return d
    def pause(s, sek): time.sleep(min(sek, 0.02))
    def trennen(s): pass

# ------------------------------------------------------------ Historie
def jetzt_utc(): return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)

def letzter_handelstag(heute):
    """Letzter Werktag vor heute (die heutige Kerze ist noch unvollständig). Feiertage zählen nicht, dann kostet es nur eine leere Abfrage."""
    d = heute - dt.timedelta(days=1)
    while d.weekday() > 4: d -= dt.timedelta(days=1)
    return d

def dauer_text(tage, jahre):
    tage = max(1, tage)
    if tage <= 30: return "%d D" % max(2, tage)
    if tage <= 330: return "%d M" % math.ceil(tage / 30)
    if tage <= 365: return "1 Y"
    return "%d Y" % max(1, min(int(math.ceil(jahre)), math.ceil(tage / 365)))

def jahre_von(st): return {"D": TAGES_JAHRE, "H": STUNDEN_JAHRE, "M5": M5_ERST}[st]

def dauer_tage(dauer):
    return int(dauer.split()[0]) if dauer.endswith(" D") else BLOCK_TAGE.get(dauer, 3)

class Ergebnis(dict):
    """Kerzen einer Anfrage samt Fehlermeldung der TWS (code, text), falls es eine gab."""
    fehler = None; pacing = False

def groessenfehler(f):
    """True, wenn die Fehlermeldung (code, text) auf ein zu großes Stück hindeutet (nicht auf fehlende Daten, Berechtigung oder Pacing)."""
    if not f: return False
    code, msg = f; m = msg.lower()
    if any(x in m for x in ("no data", "no security definition", "not subscribed", "permission", "pacing", "not supported")): return False
    return code in (162, 321, 366)

async def rueckwaerts(q, z, st, rth, bis, erste_dauer=None, max_bloecke=400, ende0=""):
    """Holt von jetzt rückwärts in Stücken, bis die älteste Kerze <= bis (ISO-Text) ist oder keine Daten mehr kommen. Rückgabe (Kerzen, Anzahl Anfragen, letzte Fehlermeldung)."""
    leiter = BLOECKE[st]; neu = {}; ende = ende0; anf = 0; leer = 0; dauer = erste_dauer; pacing_wdh = 0; fehler = None
    for _ in range(max_bloecke):
        if dauer is None: dauer = leiter[BLOCK_STUFE[st]]
        blk = await q.hist(z, st, ende, dauer, rth); anf += 1
        if blk.fehler: fehler = blk.fehler
        if not blk:
            if blk.pacing and pacing_wdh < 6:   # sonst würde die Historie hier still abgeschnitten
                pacing_wdh += 1; setze(pausensek=min(15.0, ST["pausensek"] * 2)); log("Pacing bei", z["symbol"], st, "- warte 15 s und wiederhole"); await q.apause(15); continue
            if groessenfehler(blk.fehler) and BLOCK_STUFE[st] < len(leiter) - 1:
                BLOCK_STUFE[st] += 1; log("%s: Stück zu groß, nutze jetzt %s" % (STUFEN[st][0], leiter[BLOCK_STUFE[st]])); dauer = None; continue
            leer += 1
            if leer >= 2 or not neu or blk.fehler: break
            ende = (dt.datetime.fromisoformat(min(neu)) - dt.timedelta(days=dauer_tage(dauer))).strftime("%Y%m%d-%H:%M:%S"); dauer = None; await q.apause(ST["pausensek"]); continue
        leer = 0; neu.update(blk); ae = min(blk)
        if ae <= bis: break
        ende_neu = dt.datetime.fromisoformat(ae).strftime("%Y%m%d-%H:%M:%S")
        if ende_neu == ende: break
        ende = ende_neu; dauer = None
        if ST["pausensek"] > HIST_PAUSE: setze(pausensek=max(HIST_PAUSE, ST["pausensek"] * .93))
        await q.apause(ST["pausensek"])
    return neu, anf, fehler

def fut_stufenfehler(f):
    """Fehler, bei dem eine kleinere Stückgröße für Dauer-Futures sinnvoll ist (nicht: fehlende Berechtigung, Kontrakt oder Daten)."""
    if not f: return False
    code, msg = f; m = msg.lower()
    if any(x in m for x in ("permission", "no security definition", "pacing", "no data", "not subscribed")): return False
    return code in (162, 321, 366)

async def fut_holen(q, z, st, rth, tage=None):
    """Dauer-Futures (CONTFUT): Die TWS erlaubt kein Enddatum, also genau ein Stück ab jetzt. Die Stückgröße merkt sich der Sammler für alle Futures; die tiefe Historie kommt später aus den Einzelkontrakten.
    Rückgabe wie rueckwaerts: (Kerzen, Anzahl Anfragen, letzte Fehlermeldung)."""
    leiter = FUT_LEITER[st]; anf = 0; fehler = None; pacing_wdh = 0
    while anf < 12:
        if tage is not None and tage <= (7 if st == "M5" else 28): dauer = "%d D" % max(2, tage)
        else: dauer = leiter[FUT_STUFE[st]]
        blk = await q.hist(z, st, "", dauer, rth); anf += 1
        if blk.fehler: fehler = blk.fehler
        if blk: return dict(blk), anf, fehler
        if blk.pacing and pacing_wdh < 6:
            pacing_wdh += 1; setze(pausensek=min(15.0, ST["pausensek"] * 2)); log("Pacing bei", z["symbol"], st, "- warte 15 s und wiederhole"); await q.apause(15); continue
        if fut_stufenfehler(blk.fehler) and dauer == leiter[FUT_STUFE[st]] and FUT_STUFE[st] < len(leiter) - 1:
            FUT_STUFE[st] += 1; log("%s (Dauer-Futures): %s nicht möglich, versuche %s" % (STUFEN[st][0], dauer, leiter[FUT_STUFE[st]])); await q.apause(ST["pausensek"]); continue
        break
    return {}, anf, fehler

async def hist_job(q, z, st):
    """Holt die fehlende Strecke für einen Wert. Rückgabe (neue Kerzen, Anzahl Anfragen, letzte Fehlermeldung); ist alles aktuell, kostet es keine Anfrage."""
    key = z["key"]; rth = int(z.get("rth") or 1); datei = kerz_datei(st, key); alt = kerzen_lesen(datei); heute = dt.date.today(); anf = 0; neu = {}; f = None
    if st == "D":
        if alt:
            ld = dt.date.fromisoformat(max(alt)[:10])
            if ld >= letzter_handelstag(heute): return 0, 0, None
            r = await q.hist(z, "D", "", dauer_text((heute - ld).days + 3, TAGES_JAHRE), rth)
        else: r = await q.hist(z, "D", "", "%d Y" % TAGES_JAHRE, rth)
        neu = dict(r); f = r.fehler; anf = 1
    else:
        if alt:
            letzt = dt.datetime.fromisoformat(max(alt))
            if letzt.date() >= letzter_handelstag(heute): return 0, 0, None
            tage = (jetzt_utc() - letzt).days + 2
            erste = "%d D" % max(2, tage) if tage <= BLOCK_TAGE[BLOECKE[st][BLOCK_STUFE[st]]] else None
            if z["typ"] == "FUT": neu, anf, f = await fut_holen(q, z, st, rth, tage)
            else: neu, anf, f = await rueckwaerts(q, z, st, rth, max(alt), erste_dauer=erste)
        else:
            grenze = (jetzt_utc() - dt.timedelta(days=365 * jahre_von(st))).strftime("%Y-%m-%dT%H:%M:%S")
            if z["typ"] == "FUT": neu, anf, f = await fut_holen(q, z, st, rth)
            else: neu, anf, f = await rueckwaerts(q, z, st, rth, grenze)
    if not neu: return 0, anf, f
    vorher = len(alt); alt.update(neu); kerzen_schreiben(datei, alt); return len(alt) - vorher, anf, f

async def vertiefen_job(q, z):
    """Fünf-Minuten-Kerzen eines Werts weiter in die Vergangenheit holen (bis M5_JAHRE). Rückgabe (neue Kerzen, Anfragen, Fehler)."""
    key = z["key"]; datei = kerz_datei("M5", key); alt = kerzen_lesen(datei)
    if not alt or TIEFE.get(key): return 0, 0, None
    grenze = (jetzt_utc() - dt.timedelta(days=365 * M5_JAHRE)).strftime("%Y-%m-%dT%H:%M:%S")
    if min(alt) <= grenze: return 0, 0, None
    ende = dt.datetime.fromisoformat(min(alt)).strftime("%Y%m%d-%H:%M:%S")
    neu, anf, f = await rueckwaerts(q, z, "M5", int(z.get("rth") or 1), grenze, ende0=ende)
    if neu: vorher = len(alt); alt.update(neu); kerzen_schreiben(datei, alt)
    if not f and min(alt) > grenze: TIEFE[key] = 1; _json_schreiben("_tiefe.json", TIEFE)   # die TWS hat nicht mehr
    return len(neu), anf, f

async def vertiefen_arbeiten(q, todo):
    warteschlange = list(todo)
    async def arbeiter_task():
        while True:
            if ST["stopp"] or ST["aktualisieren"] or opt_zeit(): return "abbruch"
            while ST["pause"] and not ST["stopp"]: await q.apause(1)
            if not warteschlange: return None
            z = warteschlange.pop(0); t_job = time.time(); setze(job="5-Minuten-Kerzen tiefer holen: %s, bis zu %d parallel" % (z["symbol"], PARALLEL))
            try:
                n, a, f = await vertiefen_job(q, z); z["_tief"] = True
                if a: log("5-Minuten-Kerzen tiefer %s: %d Abfragen in %.0f s, %d Kerzen" % (z["symbol"], a, time.time() - t_job, n)); await q.apause(ST["pausensek"])
            except KontraktFehler: z["_tief"] = True
            except Exception as e:
                log("FEHLER beim Vertiefen", z["symbol"], repr(e)); z["_tief"] = True
                if hasattr(q, "ib") and not q.ib.isConnected(): raise
    res = await asyncio.gather(*[arbeiter_task() for _ in range(PARALLEL)])
    return "abbruch" if "abbruch" in res else None

def sortiert(plan):
    """DAX zuerst, MDAX danach, SDAX zuletzt; alles andere in Watchlist-Reihenfolge davor."""
    def prio(z):
        sub = set(z["sub"])
        return 2 if "SDAX" in sub and not sub & {"DAX", "MDAX"} else 1 if "MDAX" in sub and "DAX" not in sub else 0
    return sorted(plan, key=prio)

def laufzeit_log(st, werte, anf, sek):
    with LOCK: ST["laufzeit"][st] = dict(werte=werte, anfragen=anf, sekunden=round(sek), pro_anfrage=round(sek / anf, 2) if anf else 0)
    try:
        datei = os.path.join(DATEN, "_laufzeit.csv"); neu = not os.path.exists(datei)
        with open(datei, "a", encoding="utf-8") as f:
            if neu: f.write("datum;stufe;werte;anfragen;sekunden;sek_pro_anfrage\n")
            f.write("%s;%s;%d;%d;%.0f;%.2f\n" % (dt.datetime.now().isoformat(timespec="seconds"), st, werte, anf, sek, sek / anf if anf else 0))
    except Exception: pass

async def bearbeite(q, st, z, zaehler):
    """Ein Wert in einer Kerzenlänge. Läuft bis zu PARALLEL-mal gleichzeitig, jeder Wert aber nur in einem Arbeiter."""
    key = z["key"]; a = 0
    if hinweis_aktiv("*", key) or (hinweis_aktiv(st, key) and not os.path.exists(kerz_datei(st, key))):
        z["_fertig_" + st] = True
        with LOCK: ST["hist"][st][0] += 1
        return
    if PERM.get(z.get("boerse"), 0) >= 3 and z["typ"] in ("STK", "CASH"):   # Berechtigung für diese Börse fehlt: Rest überspringen statt jede Anfrage einzeln scheitern zu lassen
        hinweis_setzen(st, key, "keine Marktdaten-Berechtigung für %s (übersprungen)" % z.get("boerse")); z["_fertig_" + st] = True
        with LOCK: ST["hist"][st][0] += 1
        return
    setze(job="%s: %s (%s), bis zu %d parallel" % (STUFEN[st][0], z["symbol"], z["typ"], PARALLEL))
    try:
        t_job = time.time(); n, a, f = await hist_job(q, z, st); z["_fertig_" + st] = True; zaehler["werte"] += 1
        if st != "D" and a >= 3: log("%s %s: %d Abfragen in %.0f s (%.1f s je Abfrage), %d neue Kerzen, Stück %s, Pause %.1f s" % (STUFEN[st][0], z["symbol"], a, time.time() - t_job, (time.time() - t_job) / a, n, (FUT_LEITER if z["typ"] == "FUT" else BLOECKE)[st][(FUT_STUFE if z["typ"] == "FUT" else BLOCK_STUFE)[st]], ST["pausensek"]))
        if n == 0 and a > 0 and not os.path.exists(kerz_datei(st, key)):
            hinweis_setzen(st, key, ("TWS %s: %s" % f) if f else "keine Daten von der TWS")
            if f and "permission" in f[1].lower(): PERM[z.get("boerse")] = PERM.get(z.get("boerse"), 0) + 1
        x = stand(st, key)
        with LOCK: ST["symbole"].setdefault(key, {})[st] = list(x); ST["hist"][st][0] += 1; ST["letzter_wert"] = time.time()
    except KontraktFehler as e:
        log("KONTRAKT:", z["symbol"], e); hinweis_setzen("*", key, e)
        for x in REIHENFOLGE: z["_fertig_" + x] = True
        with LOCK: ST["hist"][st][0] += 1
    except Exception as e:
        log("FEHLER bei", z["symbol"], st, repr(e)); z["_fehler_" + st] = z.get("_fehler_" + st, 0) + 1
        if z["_fehler_" + st] >= 2:
            z["_fertig_" + st] = True; hinweis_setzen(st, key, "Fehler: " + repr(e)); setze(fehler="%s %s: %s" % (z["symbol"], st, e))
        if hasattr(q, "ib") and not q.ib.isConnected(): raise
    zaehler["anf"] += a
    if getattr(q, "pacing", False):
        setze(pausensek=min(15.0, ST["pausensek"] * 2)); log("Pacing-Meldung der TWS: Pause jetzt %.1f s" % ST["pausensek"]); q.pacing = False
    elif a > 0: setze(pausensek=max(HIST_PAUSE, ST["pausensek"] * .8))
    if a > 0: await q.apause(ST["pausensek"])

async def stufe_arbeiten(q, st, todo, zaehler):
    """Arbeitet die Werte einer Kerzenlänge mit PARALLEL Arbeitern ab. Rückgabe "abbruch", wenn vorzeitig beendet (Optionszeit, Stopp, Aktualisieren)."""
    warteschlange = list(todo)
    async def arbeiter_task():
        while True:
            if ST["stopp"] or ST["aktualisieren"] or opt_zeit(): return "abbruch"
            while ST["pause"] and not ST["stopp"]: await q.apause(1)
            if not warteschlange: return None
            await bearbeite(q, st, warteschlange.pop(0), zaehler)
    res = await asyncio.gather(*[arbeiter_task() for _ in range(PARALLEL)])
    return "abbruch" if "abbruch" in res else None

def historie_phase(q, plan):
    """Arbeitet die Aufträge ab, bis die Optionszeit beginnt, der Stopp kommt, Aktualisieren gedrückt wird oder alles fertig ist. Rückgabe True, wenn alles erledigt."""
    for st in REIHENFOLGE:
        alle = [z for z in plan if st in z["stufen"]]
        todo = [z for z in sortiert(alle) if not z.get("_fertig_" + st)]
        with LOCK: ST["hist"][st] = [len(alle) - len(todo), len(alle)]
        t0 = time.time(); zaehler = dict(anf=0, werte=0)
        res = q.run(stufe_arbeiten(q, st, todo, zaehler))
        if zaehler["anf"]: laufzeit_log(st, zaehler["werte"], zaehler["anf"], time.time() - t0)
        if res == "abbruch": return False
    todo = [z for z in sortiert(plan) if "M5" in z["stufen"] and z["typ"] != "FUT" and not z.get("_tief") and not hinweis_aktiv("*", z["key"])]
    if todo and q.run(vertiefen_arbeiten(q, todo)) == "abbruch": return False
    setze(job="Historie fertig")
    return True

# ------------------------------------------------------------ Auswertung für die Statusseite
def sym_status(key, st, ltag):
    s = ST["symbole"].get(key, {}).get(st); h = hinweis_text(st, key)
    if s and s[1] and s[1][:10] >= ltag: return "ok", s[1][:10], ""
    if s and s[1]: return "alt", s[1][:10], h
    return ("fehler" if h else "fehlt"), "", h

def uebersicht_bauen():
    ltag = letzter_handelstag(dt.date.today()).isoformat(); zeilen = {}
    for z in PLAN:
        for kat, n in [("g", z["gruppe"])] + [("u", x) for x in z["sub"]]:
            r = zeilen.setdefault((kat, n), dict(kat=kat, name=n, werte=0, stufen={})); r["werte"] += 1
            for st in z["stufen"]:
                v = r["stufen"].setdefault(st, [0, 0]); v[0] += 1
                if sym_status(z["key"], st, ltag)[0] == "ok": v[1] += 1
    g = sorted([r for r in zeilen.values() if r["kat"] == "g"], key=lambda r: GRUPPEN.index(r["name"]) if r["name"] in GRUPPEN else 99)
    return g + sorted([r for r in zeilen.values() if r["kat"] == "u"], key=lambda r: r["name"])

def fehlend_liste(kat, name, st):
    ltag = letzter_handelstag(dt.date.today()).isoformat(); out = []
    for z in PLAN:
        if st not in z["stufen"]: continue
        if not ((kat == "g" and z["gruppe"] == name) or (kat == "u" and name in z["sub"])): continue
        status, letzt, grund = sym_status(z["key"], st, ltag)
        if status != "ok": out.append(dict(symbol=z["symbol"], typ=z["typ"], name=z["name"], status=status, letzte=letzt, grund=grund))
    return out[:3000]

# ------------------------------------------------------------ Optionen
def opt_zeit(now=None):
    if SIM and "--sim-opt" in sys.argv: return True
    if SIM and "--sim-hist" in sys.argv: return False
    now = now or dt.datetime.now()
    return now.weekday() < 5 and OPT_FENSTER[0] <= now.strftime("%H:%M") < OPT_FENSTER[1]

def optionsdurchlauf(q, nr):
    heute = dt.date.today(); q.basis_starten(); spot, vix = q.basis(); ketten = q.ketten()
    ver = verfaelle_waehlen({k: v["exps"] for k, v in ketten.items()}, heute); au = []
    for kl, e, dte in ver:
        for K, a in strike_auswahl(ketten[kl]["strikes"], spot, dte): au.append((kl, e, K, a, dte))
    log(f"Optionen Durchlauf {nr}: SPX {spot:.2f}, VIX {vix}, {len(ver)} Verfälle, {len(au)} Kontrakte")
    datei = kette_datei(); neu = not os.path.exists(datei); n = 0; t0 = time.time()
    setze(job="Optionen: Durchlauf %d" % nr)
    with LOCK: ST["opt"].update(durchlauf=nr, kontrakte=[0, len(au)])
    with open(datei, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        if neu: w.writerow(OPT_SPALTEN)
        for i in range(0, len(au), BLOCK):
            if ST["stopp"] or not opt_zeit(): break
            while ST["pause"] and not ST["stopp"]: q.pause(1)
            blk = au[i:i + BLOCK]; zeit = dt.datetime.now().isoformat(timespec="seconds")
            with LOCK: ST["opt"]["leitungen"] = len(blk) + 2
            res = q.block([(a[0], a[1], a[2], a[3]) for a in blk])
            for a, r in zip(blk, res):
                if r["bid"] is None and r["ask"] is None and r["last"] is None: continue
                w.writerow([zeit, nr, round(spot, 2), vix if vix is not None else "", a[0], a[1], a[4], a[3], a[2], r["bid"] or "", r["ask"] or "", r["last"] or "",
                            r["volumen"] if r["volumen"] is not None else "", r["oi"] if r["oi"] is not None else "", round(r["tws_iv"], 5) if r["tws_iv"] else "",
                            round(r["tws_delta"], 4) if r["tws_delta"] is not None else "", q.typ]); n += 1
            f.flush()
            with LOCK: ST["opt"]["kontrakte"][0] = min(i + BLOCK, len(au)); ST["opt"]["zeilen_heute"] += sum(1 for r in res if not (r["bid"] is None and r["ask"] is None and r["last"] is None)); ST["letzter_wert"] = time.time(); ST["opt"]["letzte"] = zeit
    with LOCK: ST["opt"]["leitungen"] = 2
    log(f"Optionen Durchlauf {nr} fertig: {n} Zeilen in {time.time() - t0:.0f} s")

def zeilen_heute_zaehlen():
    d = kette_datei()
    if not os.path.exists(d): return 0
    with open(d, "rb") as f: return max(0, sum(1 for _ in f) - 1)

# ------------------------------------------------------------ Hauptschleife (Arbeitsthread)
def arbeiter():
    q = None; os.makedirs(DATEN, exist_ok=True); fertig = False; nr = letzter_durchlauf(kette_datei()); tag = dt.date.today()
    HINWEISE.update(_json_lesen("_hinweise.json")); NAMEN.update(_json_lesen("_namen.json")); TIEFE.update(_json_lesen("_tiefe.json"))
    plan = plan_laden()
    with LOCK: ST["opt"]["zeilen_heute"] = zeilen_heute_zaehlen()
    log("Sammler gestartet,", len(plan), "Werte in der Watchlist, Durchlauf-Nummer geht bei", nr + 1, "weiter")
    while not ST["stopp"]:
        try:
            if ST["aktualisieren"]:
                setze(aktualisieren=False, fehler="")
                with HLOCK: HINWEISE.clear(); _json_schreiben("_hinweise.json", HINWEISE)
                PERM.clear(); plan = plan_laden(); fertig = False; log("Aktualisieren: Watchlist neu gelesen,", len(plan), "Werte, fehlende Kerzen werden nachgeholt")
            if dt.date.today() != tag: tag = dt.date.today(); PERM.clear(); plan = plan_laden(); fertig = False; nr = 0; ST["opt"]["zeilen_heute"] = 0
            if q is None:
                setze(phase="Verbinde mit TWS ..."); q = SimQuelle() if SIM else IBQuelle(); q.verbinden(); setze(verbunden=True, datentyp=q.typ, fehler="")
            if opt_zeit():
                setze(phase="Optionen (Marktdaten-Leitungen für SPX-Kette)"); nr += 1; optionsdurchlauf(q, nr)
                if ST["stopp"]: break
                setze(job="Pause bis zum nächsten Durchlauf"); t_end = time.time() + (0.2 if SIM else PAUSE_MIN * 60)
                while time.time() < t_end and not ST["stopp"] and opt_zeit(): q.pause(2)
                if SIM and nr >= 2: break
            else:
                if hasattr(q, "basis_stoppen"): q.basis_stoppen()
                with LOCK: ST["opt"]["leitungen"] = 0
                if fertig: setze(phase="Warte auf Optionszeit (%s)" % OPT_FENSTER[0], job=""); q.pause(15); continue
                setze(phase="Historie (Tages-, Stunden-, 5-Minuten-Kerzen)"); fertig = historie_phase(q, plan)
                if SIM and fertig and "--sim-bleib" not in sys.argv: break
        except KeyboardInterrupt: break
        except Exception as e:
            log("FEHLER:", repr(e), "- neuer Versuch in 60 s"); setze(verbunden=False, fehler=repr(e)[:200], phase="Fehler, neuer Versuch")
            try: q.trennen()
            except Exception: pass
            q = None; time.sleep(5 if SIM else 60)
    if q: q.trennen()
    setze(phase="Beendet", verbunden=False)

# ------------------------------------------------------------ Statusseite
HTML = """<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Marktsammler v1.2.6</title>
<style>
:root{--bg:#fff;--fg:#1d2330;--mut:#667085;--line:#e3e7ee;--card:#f6f8fb;--ok:#1a7f4b;--bad:#c0332b;--acc:#2b5fd9;--warn:#b7791f}
@media(prefers-color-scheme:dark){:root{--bg:#12151c;--fg:#e8ebf2;--mut:#9aa3b5;--line:#2a3040;--card:#1a1f2b;--ok:#4cc38a;--bad:#ff7a70;--acc:#7da3ff;--warn:#e6b450}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,Segoe UI,sans-serif;padding:16px;max-width:1150px;margin:auto}
h1{font-size:20px;margin:0 0 4px}.sub{color:var(--mut);margin-bottom:14px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px;margin-bottom:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}.k{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.04em}.v{font-size:18px;font-weight:600;margin-top:2px;overflow-wrap:anywhere}
.bar{height:8px;background:var(--line);border-radius:5px;overflow:hidden;margin-top:6px}.bar>i{display:block;height:100%;background:var(--acc);width:0}
.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}.mut{color:var(--mut)}.err{background:var(--bad);color:#fff;padding:10px 12px;border-radius:8px;margin-bottom:12px;display:none}
button{font:inherit;padding:7px 14px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer;margin-right:6px}button:hover{border-color:var(--acc)}button.main{background:var(--acc);color:#fff;border-color:var(--acc)}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:5px 8px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}th{color:var(--mut);font-weight:600}
td.klick{cursor:pointer}td.klick:hover{background:var(--card)}tr.sel td{background:var(--card)}tr.kopf td{background:var(--card);font-weight:600;color:var(--mut);font-size:12px;text-transform:uppercase}
.tw{max-height:360px;overflow:auto;border:1px solid var(--line);border-radius:10px}pre{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px;max-height:220px;overflow:auto;font-size:12px;margin:0}
input{font:inherit;padding:6px 8px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg);width:160px}h2{font-size:15px;margin:16px 0 6px}
</style></head><body>
<h1>Marktsammler v1.2.6</h1><div class="sub" id="sub">lädt ...</div>
<div class="err" id="err"></div>
<div style="margin-bottom:12px"><button class="main" onclick="cmd('aktualisieren')">Aktualisieren</button><button onclick="cmd('pause')" id="bp">Pause</button><button onclick="cmd('stopp')">Beenden</button></div>
<div class="grid">
<div class="card"><div class="k">Verbindung</div><div class="v" id="verb">-</div><div class="k" id="dtyp"></div></div>
<div class="card"><div class="k">Phase</div><div class="v" id="phase">-</div><div class="k" id="job"></div></div>
<div class="card"><div class="k">Letzter neuer Wert</div><div class="v" id="last">-</div></div>
<div class="card"><div class="k">Marktdaten-Leitungen</div><div class="v" id="lein">-</div><div class="bar"><i id="leinb"></i></div></div>
</div>
<div class="grid">
<div class="card"><div class="k">Tageskerzen</div><div class="v" id="hd">-</div><div class="bar"><i id="hdb"></i></div></div>
<div class="card"><div class="k">Stundenkerzen</div><div class="v" id="hh">-</div><div class="bar"><i id="hhb"></i></div></div>
<div class="card"><div class="k">5-Minuten-Kerzen</div><div class="v" id="hm">-</div><div class="bar"><i id="hmb"></i></div></div>
<div class="card"><div class="k">Optionskette heute</div><div class="v" id="op">-</div><div class="bar"><i id="opb"></i></div><div class="k" id="op2"></div></div>
<div class="card"><div class="k">Pause zwischen Abfragen</div><div class="v" id="ps">-</div><div class="k" id="lz"></div></div>
</div>
<h2>Vollständigkeit nach Gruppe und Index (Zelle anklicken: zeigt, was fehlt)</h2>
<div class="tw"><table id="ue"></table></div>
<div id="fe"></div>
<h2>Werte</h2><div><input id="f" placeholder="Filter (z. B. AAPL, DAX)" oninput="rend()"></div>
<div class="tw"><table><thead><tr><th>Wert</th><th>Name</th><th>Gruppe</th><th>Tage bis</th><th>Anzahl</th><th>Stunden bis</th><th>Anzahl</th><th>5 Min bis</th><th>Anzahl</th></tr></thead><tbody id="tb"></tbody></table></div>
<h2>Protokoll</h2><pre id="log"></pre>
<script>
let S=null,SEL=null;const $=i=>document.getElementById(i);
const SN={D:'Tageskerzen',H:'Stundenkerzen',M5:'5-Minuten'};
function esc(x){return String(x==null?'':x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function ago(t){if(!t)return "-";let s=Math.round(Date.now()/1000-t);return s<90?("vor "+s+" s"):s<5400?("vor "+Math.round(s/60)+" min"):("vor "+(s/3600).toFixed(1)+" h")}
function pct(a,b){return b?Math.min(100,100*a/b):0}
async function cmd(c){await fetch('/api/'+c,{method:'POST'});poll()}
function ue(){if(!S)return;let h='<thead><tr><th>Gruppe / Index</th><th>Werte</th><th>Tageskerzen</th><th>Stundenkerzen</th><th>5-Minuten</th></tr></thead><tbody>',kat='';
for(const r of S.uebersicht){if(r.kat!==kat){kat=r.kat;h+=`<tr class="kopf"><td colspan="5">${kat=='g'?'Nach Gruppe':'Nach Index / Untergruppe'}</td></tr>`}
h+=`<tr><td>${esc(r.name)}</td><td>${r.werte}</td>`;
for(const st of ['D','H','M5']){const v=r.stufen[st];if(!v){h+='<td class="mut">-</td>';continue}const f=v[0]-v[1];const cls=f==0?'ok':(v[1]==0?'bad':'warn');const sel=SEL&&SEL.k==r.kat&&SEL.n==r.name&&SEL.s==st?' sel':'';
h+=`<td class="klick ${cls}${sel}" data-k="${r.kat}" data-n="${esc(r.name)}" data-s="${st}">${v[1]} von ${v[0]}${f?' ('+f+' fehlen)':' fertig'}</td>`}h+='</tr>'}
$('ue').innerHTML=h+'</tbody>'}
document.addEventListener('click',e=>{const t=e.target.closest('td.klick');if(!t)return;SEL={k:t.dataset.k,n:t.dataset.n,s:t.dataset.s};fehl()});
async function fehl(){if(!SEL){$('fe').innerHTML='';return}
try{const r=await fetch('/api/fehlend?art='+SEL.k+'&name='+encodeURIComponent(SEL.n)+'&stufe='+SEL.s);const L=await r.json();
let h=`<h2>Fehlend: ${esc(SEL.n)} · ${SN[SEL.s]} (${L.length})</h2>`;
if(!L.length)h+='<div class="ok">Nichts fehlt.</div>';else{h+='<div class="tw"><table><thead><tr><th>Wert</th><th>Name</th><th>Art</th><th>Status</th><th>Letzte Kerze</th><th>Hinweis</th></tr></thead><tbody>';
for(const x of L)h+=`<tr><td>${esc(x.symbol)}</td><td>${esc(x.name)}</td><td>${esc(x.typ)}</td><td class="${x.status=='fehler'?'bad':'warn'}">${x.status=='alt'?'veraltet':x.status=='fehler'?'Problem':'fehlt'}</td><td>${esc(x.letzte)||'-'}</td><td>${esc(x.grund)}</td></tr>`;h+='</tbody></table></div>'}
$('fe').innerHTML=h}catch(e){}}
function rend(){if(!S)return;const f=$('f').value.toUpperCase();let h='';const ks=Object.keys(S.symbole).filter(k=>{const s=S.symbole[k];return !f||k.includes(f)||(s.name||'').toUpperCase().includes(f)||(s.sub||[]).join(' ').toUpperCase().includes(f)}).sort();
for(const k of ks.slice(0,2500)){const s=S.symbole[k],d=s.D||[],o=s.H||[],m=s.M5||[];h+=`<tr><td>${esc(s.symbol||k)}</td><td>${esc(s.name)}</td><td>${esc(s.gruppe)}</td><td>${d[1]||'-'}</td><td>${d[2]||0}</td><td>${(o[1]||'-').slice(0,10)}</td><td>${o[2]||0}</td><td>${(m[1]||'-').slice(0,10)}</td><td>${m[2]||0}</td></tr>`}$('tb').innerHTML=h}
async function poll(){try{const r=await fetch('/api/status');S=await r.json()}catch(e){$('sub').textContent='Statusseite nicht erreichbar (läuft der Sammler?)';$('sub').className='sub bad';return}
$('sub').textContent='Läuft seit '+(S.laufzeit_min)+' min, aktualisiert '+S.uhr;$('sub').className='sub';
$('verb').textContent=S.verbunden?'verbunden':'getrennt';$('verb').className='v '+(S.verbunden?'ok':'bad');$('dtyp').textContent=S.datentyp==1?'Echtzeitdaten':S.datentyp==3?'verzögerte Daten':S.datentyp?('Datentyp '+S.datentyp):'';
$('phase').textContent=S.phase+(S.pause?' (pausiert)':'');$('job').textContent=S.job||'';$('bp').textContent=S.pause?'Fortsetzen':'Pause';
$('last').textContent=ago(S.letzter_wert);const stale=S.letzter_wert&&(Date.now()/1000-S.letzter_wert>900)&&!S.pause&&S.phase.startsWith('Optionen');$('last').className='v '+(stale?'bad':'');
const L=S.opt.leitungen;$('lein').textContent=L+' von '+S.max_leitungen;$('leinb').style.width=pct(L,S.max_leitungen)+'%';
for(const [st,a,b] of [['D','hd','hdb'],['H','hh','hhb'],['M5','hm','hmb']]){const v=S.hist[st];$(a).textContent=v[0]+' von '+v[1]+' Werten';$(b).style.width=pct(v[0],v[1])+'%'}
const K=S.opt.kontrakte;$('op').textContent=S.opt.zeilen_heute+' Zeilen';$('opb').style.width=pct(K[0],K[1])+'%';$('op2').textContent=S.opt.durchlauf?('Durchlauf '+S.opt.durchlauf+': '+K[0]+'/'+K[1]+' Kontrakte, zuletzt '+(S.opt.letzte||'-')):'noch kein Durchlauf heute';
$('ps').textContent=S.pausensek.toFixed(1)+' s';$('lz').textContent=Object.keys(S.laufzeit).map(k=>SN[k]+': '+S.laufzeit[k].anfragen+' Abfragen in '+S.laufzeit[k].sekunden+' s').join(' | ');
const e=$('err');if(S.fehler){e.style.display='block';e.textContent='Fehler: '+S.fehler}else e.style.display='none';
$('log').textContent=S.log.join('\\n');$('log').scrollTop=1e9;ue();rend();fehl()}
poll();setInterval(poll,3000)
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def log_message(s, *a): pass
    def _send(s, code, body, typ):
        b = body.encode("utf-8") if isinstance(body, str) else body
        s.send_response(code); s.send_header("Content-Type", typ); s.send_header("Content-Length", str(len(b))); s.send_header("Cache-Control", "no-store"); s.end_headers(); s.wfile.write(b)
    def do_GET(s):
        u = urllib.parse.urlparse(s.path)
        if u.path == "/api/status":
            with LOCK:
                d = json.loads(json.dumps({k: v for k, v in ST.items() if k != "start"}, default=str)); d["log"] = list(LOGZ[-40:]); d["max_leitungen"] = MAX_LEITUNGEN
                d["laufzeit_min"] = int((time.time() - ST["start"]) / 60); d["uhr"] = dt.datetime.now().strftime("%H:%M:%S"); d["uebersicht"] = uebersicht_bauen()
            s._send(200, json.dumps(d), "application/json")
        elif u.path == "/api/fehlend":
            p = urllib.parse.parse_qs(u.query)
            with LOCK: l = fehlend_liste(p.get("art", ["g"])[0], p.get("name", [""])[0], p.get("stufe", ["D"])[0])
            s._send(200, json.dumps(l), "application/json")
        else: s._send(200, HTML, "text/html; charset=utf-8")
    def do_POST(s):
        if s.path.startswith("/api/pause"): setze(pause=not ST["pause"]); log("Pause" if ST["pause"] else "Fortgesetzt")
        elif s.path.startswith("/api/stopp"): setze(stopp=True); log("Beenden angefordert")
        elif s.path.startswith("/api/aktualisieren"): setze(aktualisieren=True, pause=False); log("Aktualisieren angefordert")
        s._send(200, "{}", "application/json")

def main():
    if BLOCK + 2 > MAX_LEITUNGEN: print("BLOCK + 2 muss kleiner/gleich MAX_LEITUNGEN sein"); sys.exit(1)
    windows_schutz(); os.makedirs(DATEN, exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", HTTP_PORT), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
    log("Statusseite: http://127.0.0.1:%d/  (%s)" % (HTTP_PORT, "SIMULATION" if SIM else "TWS Port %d, Client-ID %d" % (PORT, CLIENT_ID)))
    t = threading.Thread(target=arbeiter, daemon=True); t.start()
    try:
        while t.is_alive(): time.sleep(0.5)
    except KeyboardInterrupt: setze(stopp=True); t.join(5)
    if SIM: time.sleep(0.2)

if __name__ == "__main__": main()
