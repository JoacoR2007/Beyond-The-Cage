"""Backtest honesto y entrenamiento del modelo que usa el simulador del sitio.

1. Características punto en el tiempo (pit.py): cada pelea usa solo información anterior a su fecha.
2. Validación hacia adelante (walk-forward): para cada año Y entre TEST_FROM y hoy se entrena con las peleas anteriores a Y
   y se predice Y. Nunca se mezclan fechas.
3. Se comparan: azar, solo Elo, solo récord, solo forma, el simulador v1 del sitio (fórmula a mano) y los modelos entrenados
   (regresión logística y gradient boosting). Métricas: acierto, log loss, Brier, ECE y calibración, con IC95% por bootstrap.
4. Se entrena el modelo final con todo el historial y se exporta data/model.json (lo que lee el sitio) y data/model_report.json.
Uso: python science/train_model.py        Requiere: pandas numpy scikit-learn matplotlib"""
import datetime as dt, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
sys.path.insert(0, str(Path(__file__).parent))
import pit

ROOT = Path(__file__).resolve().parent.parent
TRAIN_START, TEST_FROM, SEED = 2010, 2018, 7
FEATS = pit.FEATURES + ["h2h"]
LABEL = {"elo": "Elo", "wr": "Récord (suavizado)", "exp": "Experiencia (log nº peleas)", "slpm": "Golpes sig./min", "acc": "Precisión de golpes",
         "sapm": "Golpes recibidos/min", "def": "Defensa de golpes", "tdavg": "Derribos/15 min", "tdacc": "Precisión de derribos", "tddef": "Defensa de derribos",
         "sub15": "Sumisiones intentadas/15 min", "kd15": "Caídas (knockdowns)/15 min", "ctrl15": "Control en el suelo", "ko_rate": "% de victorias por KO",
         "sub_rate": "% de victorias por sumisión", "finag": "% de derrotas por finalización", "reach": "Alcance", "height": "Altura", "age": "Edad",
         "layoff": "Inactividad (log días)", "form": "Forma (últimos 5)", "h2h": "Cara a cara previo"}

def design(df):
    return np.c_[df[["w_" + f for f in pit.FEATURES]].values - df[["l_" + f for f in pit.FEATURES]].values, df["h2h"].values]
def fit_lr(X, C):
    s = X.std(0); s[s == 0] = 1
    m = LogisticRegression(C=C, fit_intercept=False, max_iter=3000).fit(np.vstack([X, -X]) / s, np.r_[np.ones(len(X)), np.zeros(len(X))])
    return m, s
lr_p = lambda m, s, X: 1 / (1 + np.exp(-(X / s) @ m.coef_[0]))
def fit_gb(X):
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=.05, max_iter=250, l2_regularization=1.0, min_samples_leaf=50, random_state=0)\
        .fit(np.vstack([X, -X]), np.r_[np.ones(len(X)), np.zeros(len(X))])
gb_p = lambda m, X: (m.predict_proba(X)[:, 1] + 1 - m.predict_proba(-X)[:, 1]) / 2

# p = probabilidad que el modelo le dio al GANADOR real. El modelo es simétrico (p(A,B)=1-p(B,A)), así que esto equivale a orientar al azar.
acc = lambda p: float(np.mean((p > .5) + .5 * (p == .5)))
ll = lambda p: float(-np.mean(np.log(np.clip(p, 1e-6, 1))))
brier = lambda p: float(np.mean((1 - p) ** 2))
def calib(p, bins=10):
    q, y = np.r_[p, 1 - p], np.r_[np.ones(len(p)), np.zeros(len(p))]
    b = np.minimum((q * bins).astype(int), bins - 1)
    rows = [dict(lo=i / bins, hi=(i + 1) / bins, pred=float(q[b == i].mean()), obs=float(y[b == i].mean()), n=int((b == i).sum())) for i in range(bins) if (b == i).any()]
    return rows, float(sum(abs(r["pred"] - r["obs"]) * r["n"] for r in rows) / len(q))
def boot(P, fn, B=1000, ref=None):
    rng = np.random.default_rng(SEED); n = len(P); idx = rng.integers(0, n, (B, n))
    v = np.array([fn(P[i]) - (fn(ref[i]) if ref is not None else 0) for i in idx])
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]

def main():
    out = pit.build(); df = out["fights"].sort_values("date").reset_index(drop=True)
    df["y"] = df.date.dt.year; df = df[df.y >= TRAIN_START].reset_index(drop=True)
    X = design(df); k = {f: i for i, f in enumerate(FEATS)}
    one = lambda f: X[:, [k[f]]]
    # --- elegir C con una validación anterior al período de prueba (entrena <2016, valida 2016-2017)
    tr, va = (df.y < TEST_FROM - 2).values, df.y.between(TEST_FROM - 2, TEST_FROM - 1).values
    cs = {C: ll(lr_p(*(lambda m, s: (m, s))(*fit_lr(X[tr], C)), X[va])) for C in (.003, .01, .03, .1, .3, 1)}
    C = min(cs, key=cs.get); print("C elegido:", C, {c: round(v, 4) for c, v in cs.items()})
    # --- validación hacia adelante
    names = ["coin", "elo", "record", "form", "heur", "lr", "gb"]
    P = {n: np.full(len(df), np.nan) for n in names}; P["coin"][:] = .5; P["heur"] = df.p_heur.values.copy()
    for Y in range(TEST_FROM, int(df.y.max()) + 1):
        tr, te = (df.y < Y).values, (df.y == Y).values
        if not te.any(): continue
        for n, cols in (("elo", [k["elo"]]), ("record", [k["wr"]]), ("form", [k["form"]]), ("lr", list(range(len(FEATS))))):
            m, s = fit_lr(X[tr][:, cols], C if n == "lr" else 1.0); P[n][te] = lr_p(m, s, X[te][:, cols])
        P["gb"][te] = gb_p(fit_gb(X[tr]), X[te])
        print("año", Y, "n =", int(te.sum()), "| LR acierto", round(acc(P["lr"][te]), 3), "ll", round(ll(P["lr"][te]), 4), "| v1 ll", round(ll(P["heur"][te]), 4))
    T = (df.y >= TEST_FROM).values; exp = T & ((df.nstw >= 3) & (df.nstl >= 3)).values
    rep = {"generated": dt.date.today().isoformat(), "dataThrough": str(out["dataThrough"]), "testFrom": TEST_FROM, "trainStart": TRAIN_START, "C": C,
           "nTest": int(T.sum()), "nExperienced": int(exp.sum()), "models": {}, "byYear": {}, "calibration": {}}
    for n in names:
        p = P[n][T]; rows, ece = calib(p)
        rep["models"][n] = dict(acc=acc(p), ll=ll(p), brier=brier(p), ece=ece, accCI=boot(p, acc), llCI=boot(p, ll),
                                accExp=acc(P[n][exp]), llExp=ll(P[n][exp]))
        if n in ("lr", "heur", "gb"): rep["calibration"][n] = rows
    rep["diffs"] = {f"{a}_vs_{b}": dict(ll=boot(P[a][T], ll, ref=P[b][T]), acc=boot(P[a][T], acc, ref=P[b][T]))
                    for a, b in (("lr", "coin"), ("lr", "heur"), ("lr", "elo"), ("gb", "lr"), ("heur", "coin"))}
    for Y in sorted(df.y[T].unique()):
        m = (df.y == Y).values; rep["byYear"][int(Y)] = {n: dict(acc=acc(P[n][m]), ll=ll(P[n][m]), n=int(m.sum())) for n in ("coin", "elo", "heur", "lr", "gb")}
    # --- modelo final (todo el historial) y coeficientes
    m, s = fit_lr(X, C)
    rep["coef"] = sorted([dict(f=f, label=LABEL[f], coef=float(m.coef_[0][i]), std=float(s[i])) for i, f in enumerate(FEATS)], key=lambda d: -abs(d["coef"]))
    # --- exportar lo que usa el sitio
    cur = out["current"]; rk = json.load(open(ROOT / "data" / "rankings.json", encoding="utf-8")); al = json.load(open(ROOT / "data" / "aliases.json", encoding="utf-8"))
    nf = len(pit.FEATURES); cv, miss = {}, []
    for d in rk["divisions"].values():
        for f in d:
            nm = al.get(f["n"], f["n"]); i = out["ids"].get(pit.key(nm))
            if i is None:
                i = next((j for j, x in enumerate(out["names"]) if pit.short(x) == pit.short(nm)), None)
            if i is None: miss.append(f["n"]); continue
            cv[f["n"]] = [round(float(v), 4) for v in cur.loc[i, pit.FEATURES].values / s[:nf]]
    use = rep["models"]["lr"]["ll"] < rep["models"]["heur"]["ll"] and rep["models"]["lr"]["ll"] < rep["models"]["coin"]["ll"]
    r = rep["models"]; site = {"version": 1, "use": bool(use), "trainedAt": rep["generated"], "dataThrough": rep["dataThrough"], "features": pit.FEATURES,
                               "c": [round(float(c), 5) for c in m.coef_[0][:nf]], "ch": round(float(m.coef_[0][nf] / s[nf]), 5), "cur": cv,
                               "report": {"n": rep["nTest"], "from": TEST_FROM, "to": int(df.y.max()), "acc": round(r["lr"]["acc"], 4), "ll": round(r["lr"]["ll"], 4),
                                          "brier": round(r["lr"]["brier"], 4), "accHeur": round(r["heur"]["acc"], 4), "llHeur": round(r["heur"]["ll"], 4),
                                          "accElo": round(r["elo"]["acc"], 4), "llCoin": round(r["coin"]["ll"], 4)}}
    (ROOT / "data" / "model.json").write_text(json.dumps(site, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (ROOT / "data" / "model_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n=== Resultados (peleas %d-%d, n=%d) ===" % (TEST_FROM, df.y.max(), rep["nTest"]))
    for n in names: print(f"{n:7s} acierto {r[n]['acc']:.3f} {np.round(r[n]['accCI'], 3)}  log loss {r[n]['ll']:.4f} {np.round(r[n]['llCI'], 4)}  Brier {r[n]['brier']:.4f}  ECE {r[n]['ece']:.3f}")
    print("diferencias (IC95%):", {a: dict(ll=np.round(v["ll"], 4).tolist(), acc=np.round(v["acc"], 3).tolist()) for a, v in rep["diffs"].items()})
    print("usar modelo en el sitio:", use, "| sin match:", miss)
    print("top coeficientes:", [(d["f"], round(d["coef"], 3)) for d in rep["coef"][:8]])
    try: figures(rep)
    except Exception as e: print("figuras:", e)

def figures(rep):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    out = Path(__file__).parent / "figures"; out.mkdir(exist_ok=True)
    plt.rcParams.update({"figure.facecolor": "white", "axes.spines.top": False, "axes.spines.right": False, "font.size": 10})
    fig, ax = plt.subplots(figsize=(5.2, 5)); ax.plot([0, 1], [0, 1], "--", c="#999", label="calibración perfecta")
    for n, c, lb in (("lr", "#d71920", "Modelo (regresión logística)"), ("heur", "#1d4fd7", "Simulador v1 (fórmula a mano)")):
        r = rep["calibration"][n]; ax.plot([x["pred"] for x in r], [x["obs"] for x in r], "o-", c=c, label=lb)
    ax.set(xlabel="Probabilidad predicha", ylabel="Frecuencia observada", title="Calibración (validación hacia adelante)"); ax.legend(frameon=False, fontsize=8); fig.tight_layout(); fig.savefig(out / "calibration.png", dpi=150); plt.close(fig)
    yrs = sorted(rep["byYear"], key=int); fig, ax = plt.subplots(figsize=(6.5, 4))
    for n, c, lb in (("coin", "#999", "Azar"), ("elo", "#888", "Solo Elo"), ("heur", "#1d4fd7", "Simulador v1"), ("lr", "#d71920", "Modelo")):
        ax.plot([int(y) for y in yrs], [rep["byYear"][y][n]["ll"] for y in yrs], "o-", c=c, label=lb)
    ax.set(xlabel="Año evaluado", ylabel="Log loss (menor es mejor)", title="Error por año"); ax.legend(frameon=False, fontsize=8); fig.tight_layout(); fig.savefig(out / "by_year.png", dpi=150); plt.close(fig)
    cf = rep["coef"][:12][::-1]; fig, ax = plt.subplots(figsize=(6.5, 4.4))
    ax.barh([d["label"] for d in cf], [d["coef"] for d in cf], color=["#d71920" if d["coef"] > 0 else "#1d4fd7" for d in cf]); ax.axvline(0, c="#333", lw=.8)
    ax.set(xlabel="Coeficiente estandarizado (efecto sobre la probabilidad de ganar)", title="Qué pesa más en el modelo"); fig.tight_layout(); fig.savefig(out / "coefficients.png", dpi=150); plt.close(fig)

if __name__ == "__main__":
    main()
