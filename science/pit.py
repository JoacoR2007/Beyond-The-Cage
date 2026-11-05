"""Características "punto en el tiempo" (point-in-time) a partir de los CSV de UFCStats.

Regla de oro: las características de una pelea se calculan SOLO con peleas anteriores a su fecha
(las peleas de un mismo evento se procesan juntas y recién después se actualiza el estado).
Así se evita la fuga de información (data leakage) y el backtest es honesto.

build() devuelve:
  fights  : una fila por pelea decisiva (ganador "w" vs perdedor "l") con las características de ambos antes de pelear,
            el cara a cara previo (h2h) y la probabilidad del simulador v1 (el del sitio) recalculada punto en el tiempo (p_heur).
  current : una fila por peleador con su estado actual (características + métricas crudas), útil para clustering y para el sitio.
"""
import csv, datetime as dt, re, unicodedata
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
DIVS = ["FLY", "BW", "FW", "LW", "WW", "MW", "LHW", "HW"]
WC = [("light heavyweight", 6), ("heavyweight", 7), ("flyweight", 0), ("bantamweight", 1), ("featherweight", 2),
      ("lightweight", 3), ("welterweight", 4), ("middleweight", 5)]
FEATURES = ["elo", "wr", "exp", "slpm", "acc", "sapm", "def", "tdavg", "tdacc", "tddef", "sub15", "kd15", "ctrl15",
            "ko_rate", "sub_rate", "finag", "reach", "height", "age", "layoff", "form"]
FWT = [1, .85, .7, .55, .4]

def norm(s):
    s = s.translate(str.maketrans("łøđß", "lodb"))
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()
def key(s): return tuple(sorted(norm(s).split()))
def short(s): t = norm(s).split(); return (t[0], t[-1]) if t else ()
def of(s):
    m = re.match(r"\s*(\d+)\s+of\s+(\d+)", s or ""); return (int(m[1]), int(m[2])) if m else (0, 0)
def mmss(s):
    m = re.match(r"\s*(\d+):(\d+)", s or ""); return int(m[1]) * 60 + int(m[2]) if m else 0
def num(s):
    try: return int(float(s))
    except (TypeError, ValueError): return 0
def wdiv(s):
    s = (s or "").lower()
    return -1 if "women" in s else next((i for n, i in WC if n in s), -1)
def _rows(n): return csv.DictReader(open(RAW / n, encoding="utf-8"))

def load():
    ev_date = {r["EVENT"].strip(): dt.datetime.strptime(r["DATE"].strip(), "%B %d, %Y").date() for r in _rows("ufc_event_details.csv")}
    ids, names = {}, []
    def gid(n):
        k = key(n)
        if k not in ids: ids[k] = len(names); names.append(n)
        return ids[k]
    res = []
    for r in _rows("ufc_fight_results.csv"):
        ev, bout = r["EVENT"].strip(), r["BOUT"].strip()
        if ev not in ev_date or " vs. " not in bout: continue
        a, b = [x.strip() for x in bout.split(" vs. ", 1)]
        rnd, t = num(r["ROUND"]), mmss(r["TIME"])
        res.append(dict(ev=ev, bout=bout, a=a, b=b, ia=gid(a), ib=gid(b), out=r["OUTCOME"].strip(), method=r["METHOD"].strip().upper(),
                        min=((rnd - 1) * 300 + t) / 60 if rnd else 0.0, rnd=rnd, div=wdiv(r["WEIGHTCLASS"])))
    st = defaultdict(dict)
    for r in _rows("ufc_fight_stats.csv"):
        v = st[(r["EVENT"].strip(), r["BOUT"].strip())].setdefault(r["FIGHTER"].strip(), np.zeros(7))
        s, t = of(r["SIG.STR."]), of(r["TD"])
        v += [s[0], s[1], t[0], t[1], num(r["SUB.ATT"]), num(r["KD"]), mmss(r["CTRL"])]
    tott = {}
    for r in _rows("ufc_fighter_tott.csv"): tott.setdefault(key(r["FIGHTER"]), r)
    return ev_date, names, res, st, tott, ids

def _inch(s):
    m = re.search(r"(\d+)'\s*(\d+)", s or ""); return int(m[1]) * 12 + int(m[2]) if m else np.nan
def _reach(s):
    m = re.search(r"(\d+(?:\.\d+)?)", s or ""); return float(m[1]) if m else np.nan
def _dob(s):
    try: return dt.datetime.strptime((s or "").strip(), "%b %d, %Y").date().toordinal()
    except ValueError: return np.nan

def build(today=None):
    ev_date, names, res, st, tott, ids = load()
    N = len(names)
    A = {k: np.zeros(N) for k in ("min", "sl", "sa", "osl", "osa", "tdl", "tda", "otdl", "otda", "sub", "kd", "ctrl", "nst", "n", "w", "l", "ko", "sw", "fl")}
    elo = np.full(N, 1500.); last = np.full(N, -1.); ldiv = np.full(N, -1); form = np.zeros(N)
    recent = [[] for _ in range(N)]; beat = [set() for _ in range(N)]
    reach, height, dob = (np.full(N, np.nan) for _ in range(3))
    for k, i in ids.items():
        r = tott.get(k)
        if r: reach[i], height[i], dob[i] = _reach(r["REACH"]), _inch(r["HEIGHT"]), _dob(r["DOB"])
    mreach, mheight = np.nanmean(reach), np.nanmean(height)

    def feats(D):
        mn = A["min"]; tm = max(mn.sum(), 1.)
        mu = dict(slpm=A["sl"].sum() / tm, acc=A["sl"].sum() / max(A["sa"].sum(), 1), de=1 - A["osl"].sum() / max(A["osa"].sum(), 1),
                  td=A["tdl"].sum() / tm, tdacc=A["tdl"].sum() / max(A["tda"].sum(), 1), tddef=1 - A["otdl"].sum() / max(A["otda"].sum(), 1),
                  sub=A["sub"].sum() / tm, kd=A["kd"].sum() / tm, ctrl=A["ctrl"].sum() / 60 / tm)
        c = {"elo": elo, "wr": (A["w"] + 1) / (A["w"] + A["l"] + 2), "exp": np.log1p(A["n"]),
             "slpm": (A["sl"] + 15 * mu["slpm"]) / (mn + 15), "acc": (A["sl"] + 50 * mu["acc"]) / (A["sa"] + 50),
             "sapm": (A["osl"] + 15 * mu["slpm"]) / (mn + 15), "def": (A["osa"] - A["osl"] + 50 * mu["de"]) / (A["osa"] + 50),
             "tdavg": 15 * (A["tdl"] + 30 * mu["td"]) / (mn + 30), "tdacc": (A["tdl"] + 5 * mu["tdacc"]) / (A["tda"] + 5),
             "tddef": (A["otda"] - A["otdl"] + 5 * mu["tddef"]) / (A["otda"] + 5), "sub15": 15 * (A["sub"] + 30 * mu["sub"]) / (mn + 30),
             "kd15": 15 * (A["kd"] + 30 * mu["kd"]) / (mn + 30), "ctrl15": 15 * (A["ctrl"] / 60 + 30 * mu["ctrl"]) / (mn + 30),
             "ko_rate": (A["ko"] + 1.05) / (A["w"] + 3), "sub_rate": (A["sw"] + .45) / (A["w"] + 3), "finag": (A["fl"] + 1) / (A["l"] + 2),
             "reach": np.where(np.isnan(reach), mreach, reach), "height": np.where(np.isnan(height), mheight, height),
             "age": np.where(np.isnan(dob), 29., (D - dob) / 365.25),
             "layoff": np.where(last > 0, np.log1p(np.minimum(D - last, 1095)), np.log1p(240)), "form": form}
        return np.column_stack([c[f] for f in FEATURES])

    def raws():                                   # métricas crudas (sin suavizar), como las del sitio
        with np.errstate(all="ignore"):
            m = A["min"]
            r = dict(slpm=A["sl"] / m, acc=A["sl"] / A["sa"], sapm=A["osl"] / m, de=1 - A["osl"] / A["osa"], tdavg=A["tdl"] * 15 / m,
                     tdacc=A["tdl"] / A["tda"], tddef=1 - A["otdl"] / A["otda"], sub=A["sub"] * 15 / m, kd=A["kd"] * 15 / m,
                     ctrl=A["ctrl"] * 15 / m, ko=A["ko"] / A["w"], sw=A["sw"] / A["w"], fin=np.where(A["l"] > 0, A["fl"] / A["l"], 0.))
        return {k: np.where(np.isfinite(v), v, np.nan) for k, v in r.items()}

    def pct(s, v):
        if len(s) < 12 or not np.isfinite(v): return None
        return (np.searchsorted(s, v, "left") + np.searchsorted(s, v, "right")) / 2 / len(s)
    def wavg(parts):
        parts = [(p, w) for p, w in parts if p is not None]
        return sum(p * w for p, w in parts) / sum(w for _, w in parts) if parts else None
    def rating(i, d, R, pops, active):             # valoraciones 0-99 del sitio (percentiles dentro de la división)
        if not active[i] or d < 0: return None
        g = lambda k: pct(pops[d][k], R[k][i]); inv = lambda p: None if p is None else 1 - p
        comps = [wavg([(g("kd"), .6), (g("ko"), .4)]), wavg([(g("slpm"), .35), (g("acc"), .25), (g("de"), .25), (inv(g("sapm")), .15)]),
                 wavg([(g("tdavg"), .35), (g("tdacc"), .15), (g("tddef"), .30), (g("ctrl"), .20)]), wavg([(g("sub"), .6), (g("sw"), .4)]),
                 wavg([(g("de"), .3), (inv(g("sapm")), .3), (g("tddef"), .15), (inv(g("fin")), .25)])]
        return [70 if x is None else round(40 + 59 * min(1, max(0, .5 + (x - .5) * 1.3))) for x in comps]
    def heuristic(i, j, d, R, pops, active):        # el simulador v1 del sitio, recalculado con datos de antes de la pelea
        di, dj = (d, d) if d >= 0 else (ldiv[i], ldiv[j])
        ra = rating(i, di, R, pops, active) or [70] * 5; rb = rating(j, dj, R, pops, active) or [70] * 5
        g = .5 + abs(ra[2] - rb[2]) / 120
        tot = lambda f, k: .75 * (g * (.6 * f[2] + .4 * f[3]) + (1 - g) * (.6 * f[1] + .4 * f[0])) + .15 * f[4] + 10 * (A["w"][k] / (A["w"][k] + A["l"][k]) if A["w"][k] + A["l"][k] else .5)
        ex = 10 * ((j in beat[i]) - (i in beat[j])) + 7 * (form[i] - form[j])
        if not (np.isnan(reach[i]) or np.isnan(reach[j])): ex += .35 * (reach[i] - reach[j])
        if active[i] and active[j]:
            ex += 2 * ((R["slpm"][i] - R["sapm"][i]) - (R["slpm"][j] - R["sapm"][j])) + .05 * 100 * (R["de"][i] - R["de"][j])
        return 1 / (1 + np.exp(-(tot(ra, i) - tot(rb, j) + ex) / 14))

    by_ev = defaultdict(list)
    for r in res: by_ev[r["ev"]].append(r)
    rows, Fw, Fl = [], [], []
    for ev in sorted(by_ev, key=lambda e: (ev_date[e], e)):
        date = ev_date[ev]; D = date.toordinal()
        F = feats(D); R = raws()
        active = (A["nst"] >= 3) & (A["min"] >= 15) & (last >= D - 4 * 365)
        pops = {}
        for d in {r["div"] for r in by_ev[ev]} | {-1}:
            for dd in ([d] if d >= 0 else range(8)):
                if dd in pops: continue
                m = active & (ldiv == dd)
                pops[dd] = {k: np.sort(v[m & np.isfinite(v)]) for k, v in R.items()}
        for r in by_ev[ev]:
            if r["out"] not in ("W/L", "L/W"): continue
            w, l = (r["ia"], r["ib"]) if r["out"] == "W/L" else (r["ib"], r["ia"])
            rows.append(dict(date=date, ev=ev, div=r["div"], method=r["method"], rnd=r["rnd"], w=names[w], l=names[l], nw=A["n"][w], nl=A["n"][l],
                             nstw=A["nst"][w], nstl=A["nst"][l], h2h=float((l in beat[w]) - (w in beat[l])),
                             p_heur=heuristic(w, l, r["div"], R, pops, active)))
            Fw.append(F[w]); Fl.append(F[l])
        for r in by_ev[ev]:                          # ---- actualizar el estado DESPUÉS de procesar el evento
            i, j, o = r["ia"], r["ib"], r["out"]
            va, vb = st.get((ev, r["bout"]), {}).get(r["a"]), st.get((ev, r["bout"]), {}).get(r["b"])
            if va is not None and vb is not None and va[1] + vb[1] > 0 and r["min"] > 0:
                for x, y, vx, vy in ((i, j, va, vb), (j, i, vb, va)):
                    A["min"][x] += r["min"]; A["nst"][x] += 1
                    A["sl"][x] += vx[0]; A["sa"][x] += vx[1]; A["osl"][x] += vy[0]; A["osa"][x] += vy[1]
                    A["tdl"][x] += vx[2]; A["tda"][x] += vx[3]; A["otdl"][x] += vy[2]; A["otda"][x] += vy[3]
                    A["sub"][x] += vx[4]; A["kd"][x] += vx[5]; A["ctrl"][x] += vx[6]
            if o not in ("W/L", "L/W", "D/D", "NC/NC"): continue
            fin = r["method"].startswith(("KO", "SUB"))
            for x, y, rs in ((i, j, o.split("/")[0]), (j, i, o.split("/")[1])):
                A["n"][x] += 1; last[x] = D
                if r["div"] >= 0: ldiv[x] = r["div"]
                recent[x] = (recent[x] + [(rs, fin)])[-5:]
                form[x] = sum(FWT[k] * ((1 if a == "W" else -1 if a == "L" else 0) * (1 + (.3 if f else 0))) for k, (a, f) in enumerate(reversed(recent[x]))) / 3.5
                if rs == "W":
                    A["w"][x] += 1; A["ko"][x] += r["method"].startswith("KO"); A["sw"][x] += r["method"].startswith("SUB"); beat[x].add(y)
                elif rs == "L":
                    A["l"][x] += 1; A["fl"][x] += fin
            if o in ("W/L", "L/W"):
                w, l = (i, j) if o == "W/L" else (j, i)
            else: w, l = i, j
            e = 1 / (1 + 10 ** ((elo[l] - elo[w]) / 400)); s = 1.0 if o in ("W/L", "L/W") else .5 if o == "D/D" else None
            if s is not None: d = 32 * (s - e); elo[w] += d; elo[l] -= d
    fights = pd.DataFrame(rows)
    fights = pd.concat([fights, pd.DataFrame(np.array(Fw), columns=["w_" + f for f in FEATURES]), pd.DataFrame(np.array(Fl), columns=["l_" + f for f in FEATURES])], axis=1)
    fights["date"] = pd.to_datetime(fights["date"])
    D = (today or dt.date.today()).toordinal()
    Fn, Rn = feats(D), raws()
    cur = pd.DataFrame(Fn, columns=FEATURES); cur.insert(0, "name", names); cur["n"] = A["n"]; cur["nst"] = A["nst"]; cur["min"] = A["min"]
    cur["last"] = [dt.date.fromordinal(int(x)) if x > 0 else None for x in last]; cur["ldiv"] = ldiv
    for k, v in Rn.items(): cur["r_" + k] = v
    return dict(fights=fights, current=cur, names=names, ids=ids, dataThrough=max(ev_date.values()))

if __name__ == "__main__":
    import time; t0 = time.time(); o = build(); f = o["fights"]
    print(f"{len(f)} peleas decisivas · {f.date.min().date()} → {f.date.max().date()} · {time.time() - t0:.0f}s")
    print("peleas con estadísticas de ambos (≥3 previas):", int(((f.nstw >= 3) & (f.nstl >= 3)).sum()))
    print(f.groupby(f.date.dt.year).size().to_string())
    f.to_pickle("/tmp/fights.pkl"); o["current"].to_pickle("/tmp/current.pkl")
