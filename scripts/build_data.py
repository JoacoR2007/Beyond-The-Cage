"""Genera data/fighters.json a partir de data/rankings.json + los CSV de data/raw/.
Estadísticas, récord UFC, alcance y valoraciones 0-99 se calculan con datos reales;
si un peleador tiene pocas peleas, se usan las valoraciones de data/seed_ratings.json.
Uso: python scripts/build_data.py   (solo librería estándar)"""
import bisect, csv, datetime as dt, json, re, unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA, RAW = ROOT / "data", ROOT / "data" / "raw"
DIVS = ["FLY", "BW", "FW", "LW", "WW", "MW", "LHW", "HW"]
MIN_FIGHTS, MIN_MIN, ACTIVE_YEARS = 3, 15, 4

def norm(s):
    s = s.translate(str.maketrans("łøđß", "lodb"))
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()
def key(s): return tuple(sorted(norm(s).split()))
def short(s): t = norm(s).split(); return (t[0], t[-1]) if t else ()
def rows(name): return csv.DictReader(open(RAW / name, encoding="utf-8"))
def of(s):
    m = re.match(r"\s*(\d+)\s+of\s+(\d+)", s or ""); return (int(m[1]), int(m[2])) if m else (0, 0)
def mmss(s):
    m = re.match(r"\s*(\d+):(\d+)", s or ""); return int(m[1]) * 60 + int(m[2]) if m else 0
def num(s):
    try: return int(float(s))          # el CSV trae valores como "1.0"
    except (TypeError, ValueError): return 0

WC = [("light heavyweight", "LHW"), ("heavyweight", "HW"), ("flyweight", "FLY"), ("bantamweight", "BW"),
      ("featherweight", "FW"), ("lightweight", "LW"), ("welterweight", "WW"), ("middleweight", "MW")]
def wcode(s):                                   # categoría masculina de una pelea (None si es femenina, catchweight, etc.)
    s = (s or "").lower()
    return None if "women" in s else next((c for n, c in WC if n in s), None)
def mshort(m):
    m = (m or "").upper(); return "KO/TKO" if m.startswith("KO") else "SUB" if m.startswith("SUB") else "NC" if m.startswith(("COULD", "OVERT")) else m[:3]
dv = defaultdict(lambda: defaultdict(int))     # peleas recientes por categoría de cada peleador

# --- eventos y resultados
events = {r["EVENT"].strip(): dt.datetime.strptime(r["DATE"].strip(), "%B %d, %Y").date() for r in rows("ufc_event_details.csv")}
ref = max(events.values())
bouts, hist = {}, defaultdict(list)          # hist: key -> [(fecha, W/L/D/NC, método)]
for r in rows("ufc_fight_results.csv"):
    ev, bout = r["EVENT"].strip(), r["BOUT"].strip()
    if ev not in events or " vs. " not in bout: continue
    a, b = [x.strip() for x in bout.split(" vs. ", 1)]
    rnd, t = num(r["ROUND"]), mmss(r["TIME"])
    bouts[(ev, bout)] = {"min": ((rnd - 1) * 300 + t) / 60 if rnd else 0, "date": events[ev]}
    oa, _, ob = r["OUTCOME"].strip().partition("/")
    meth = r["METHOD"].strip()
    code = wcode(r.get("WEIGHTCLASS"))
    for who, res in ((a, oa), (b, ob)):
        opp = b if who == a else a
        if res in ("W", "L", "D", "NC"): hist[key(who)].append((events[ev], res, meth, key(opp), opp, rnd))
        if code and events[ev] >= ref.replace(year=ref.year - 3): dv[key(who)][code] += 1
        hist[short(who)] = hist[key(who)]

# --- estadísticas por pelea (suma de rounds)
per = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
for r in rows("ufc_fight_stats.csv"):
    k = (r["EVENT"].strip(), r["BOUT"].strip())
    if k not in bouts: continue
    d = per[k][r["FIGHTER"].strip()]
    d["sl"] += of(r["SIG.STR."])[0]; d["sa"] += of(r["SIG.STR."])[1]
    d["tdl"] += of(r["TD"])[0]; d["tda"] += of(r["TD"])[1]
    d["sub"] += num(r["SUB.ATT"]); d["kd"] += num(r["KD"]); d["ctrl"] += mmss(r["CTRL"])
tot = defaultdict(lambda: defaultdict(float))
for k, fs in per.items():
    if len(fs) != 2: continue
    (n1, a), (n2, b) = fs.items()
    if a["sa"] + b["sa"] == 0 or bouts[k]["min"] <= 0: continue
    for me, op, who in ((a, b, n1), (b, a, n2)):
        t = tot[key(who)]
        t["min"] += bouts[k]["min"]; t["n"] += 1; t["last"] = max(t["last"], bouts[k]["date"].toordinal())
        for f in ("sl", "sa", "tdl", "tda", "sub", "kd", "ctrl"): t[f] += me[f]
        for f in ("sl", "sa", "tdl", "tda"): t["o" + f] += op[f]
def div(a, b): return a / b if b else None
def metrics(t, h):
    m = t["min"]; w = [x for x in h if x[1] == "W"]; l = [x for x in h if x[1] == "L"]
    fin = lambda x: re.match(r"(KO|SUB)", x[2].upper()) is not None
    return {"slpm": div(t["sl"], m), "acc": div(t["sl"], t["sa"]), "sapm": div(t["osl"], m),
            "def": None if not t["osa"] else 1 - t["osl"] / t["osa"], "tdavg": div(t["tdl"] * 15, m), "tdacc": div(t["tdl"], t["tda"]),
            "tddef": None if not t["otda"] else 1 - t["otdl"] / t["otda"], "sub": div(t["sub"] * 15, m), "kd15": div(t["kd"] * 15, m),
            "ctrl15": div(t["ctrl"] * 15, m), "ko_rate": div(sum(1 for x in w if x[2].upper().startswith("KO")), len(w)),
            "subwin": div(sum(1 for x in w if x[2].upper().startswith("SUB")), len(w)), "finag": div(sum(1 for x in l if fin(x)), len(l)) if l else 0.0}

# --- población activa POR DIVISIÓN: cada peleador se compara solo con los de su categoría,
# así un peso pesado no tiene más "fuerza" que un mosca solo por pesar más.
limit = ref.toordinal() - ACTIVE_YEARS * 365
prim = {k: max(c, key=c.get) for k, c in dv.items() if c}      # categoría donde pelea últimamente
pop = defaultdict(lambda: defaultdict(list))
for k, t in tot.items():
    if k in prim and t["n"] >= MIN_FIGHTS and t["min"] >= MIN_MIN and t["last"] >= limit:
        for name, v in metrics(t, hist[k]).items():
            if v is not None: pop[prim[k]][name].append(v)
for d in pop.values():
    for v in d.values(): v.sort()
def pc(div, name, v):
    s = pop[div][name]
    if v is None or len(s) < 12: return None
    return (bisect.bisect_left(s, v) + bisect.bisect_right(s, v)) / 2 / len(s)
def wavg(parts):
    parts = [(p, w) for p, w in parts if p is not None]
    return sum(p * w for p, w in parts) / sum(w for _, w in parts) if parts else None
inv = lambda p: None if p is None else 1 - p
def ratings(m, div):
    g = lambda n: pc(div, n, m[n])
    r = [wavg([(g("kd15"), .6), (g("ko_rate"), .4)]),
         wavg([(g("slpm"), .35), (g("acc"), .25), (g("def"), .25), (inv(g("sapm")), .15)]),
         wavg([(g("tdavg"), .35), (g("tdacc"), .15), (g("tddef"), .30), (g("ctrl15"), .20)]),
         wavg([(g("sub"), .6), (g("subwin"), .4)]),
         wavg([(g("def"), .3), (inv(g("sapm")), .3), (g("tddef"), .15), (inv(g("finag")), .25)])]
    # se estira un poco el rango para que los mejores de cada rubro se acerquen a 99
    return [None if x is None else round(40 + 59 * min(1, max(0, .5 + (x - .5) * 1.3))) for x in r]

# --- altura / alcance / postura
tott = {}
for r in rows("ufc_fighter_tott.csv"):
    tott.setdefault(key(r["FIGHTER"]), r); tott.setdefault(short(r["FIGHTER"]), r)
def inches(s):
    m = re.search(r"(\d+)'\s*(\d+)", s or ""); return int(m[1]) * 12 + int(m[2]) if m else None
def reach(s):
    m = re.search(r"(\d+(?:\.\d+)?)", s or ""); return float(m[1]) if m else None

# --- armado final
rk = json.load(open(DATA / "rankings.json", encoding="utf-8"))
named = {key(n["n"]): n["n"] for d in rk["divisions"].values() for n in d}      # para los cara a cara
seed = json.load(open(DATA / "seed_ratings.json", encoding="utf-8"))
alias = json.load(open(DATA / "aliases.json", encoding="utf-8"))
out, missing, real_n = [], [], 0
def fmt(w, l, d): return f"{w}-{l}" + (f"-{d}" if d else "")
for di, code in enumerate(DIVS):
    for ki, f in enumerate(rk["divisions"][code]):
        name = alias.get(f["n"], f["n"])
        k1, k2 = key(name), short(name)
        kk = k1 if (k1 in tot or k1 in hist or k1 in tott) else k2
        h, t, tt = hist.get(kk, []), tot.get(kk), tott.get(kk) or tott.get(k2)
        if not h and not tt: missing.append(f["n"])
        base = [int(x) for x in re.findall(r"\d+", f["r"])[:3]] + [0, 0, 0]
        w, l, d = base[0], base[1], base[2]
        asof = dt.date.fromisoformat(f.get("asOf", rk["asOf"]))   # fecha del récord base
        for dte, res, *_ in h:
            if dte > asof: w += res == "W"; l += res == "L"; d += res == "D"
        uw, ul, ud = (sum(1 for x in h if x[1] == c) for c in "WLD")
        beat = sorted({named[x[3]] for x in h if x[1] == "W" and x[3] in named and named[x[3]] != f["n"]})
        l5 = [[x[0].isoformat(), x[4], x[1], mshort(x[2]), x[5]] for x in sorted(h, key=lambda x: x[0], reverse=True)[:5]]
        o = {"n": f["n"], "beat": beat, "l5": l5, "c": f["c"], "r": fmt(w, l, d), "s": f["s"], "d": di, "k": ki, "ufc": fmt(uw, ul, ud) if h else None,
             "reach": reach(tt["REACH"]) if tt else None, "height": inches(tt["HEIGHT"]) if tt else None,
             "stance": (tt["STANCE"] or None) if tt else None}
        sd = seed.get(f["n"], [60] * 5)
        isreal = bool(t and t["n"] >= MIN_FIGHTS and t["min"] >= MIN_MIN)
        if isreal:
            m = metrics(t, h); rt = ratings(m, code); real_n += 1
            o.update({"real": True, "fights": int(t["n"]), "slpm": round(m["slpm"], 2), "acc": round(100 * m["acc"]) if m["acc"] is not None else None,
                      "sapm": round(m["sapm"], 2), "def": round(100 * m["def"]) if m["def"] is not None else None,
                      "tdavg": round(m["tdavg"], 2), "tdacc": round(100 * m["tdacc"]) if m["tdacc"] is not None else None,
                      "tddef": round(100 * m["tddef"]) if m["tddef"] is not None else None, "sub": round(m["sub"], 2)})
            sd = [x if x is not None else sd[i] for i, x in enumerate(rt)]
        else: o["real"] = False
        o.update(dict(zip("PSGBR", sd)))
        out.append(o)
json.dump({"updated": dt.date.today().isoformat(), "dataThrough": ref.isoformat(), "rankingsAsOf": rk["asOf"], "fighters": out},
          open(DATA / "fighters.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"{len(out)} peleadores · {real_n} con estadísticas reales · datos hasta {ref}")
if missing: print("No encontrados en el dataset (agregalos a data/aliases.json):", ", ".join(missing))
