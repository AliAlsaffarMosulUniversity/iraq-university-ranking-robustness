"""Analysis for: weight sensitivity and national-international agreement in rankings of Iraqi public universities.

Main specification (S1): eight indicators in five axes, equal axis weights, THE entered as the
continuous score rebuilt from pillar scores, SIR overall rank excluded (it is a composite of the
three SIR sub-ranks that are already in the index).
Alternative specifications (S2-S4) restore the SIR overall rank, the THE band midpoint and/or the
weights of the comparison tool, to show how much these choices matter.
Run:  python scripts/analysis.py
"""
import pathlib, re, json
import numpy as np, pandas as pd
from scipy import stats
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT/"results"; FIG = OUT/"figures"; FIG.mkdir(parents=True, exist_ok=True)
SEED, N_SIM = 20261002, 10_000
AXES = ["national", "global", "research", "education", "sustainability"]
W_EQUAL = np.full(5, 0.2)
W_TOOL = np.array([25, 25, 25, 10, 15], float) / 100

df = pd.read_csv(ROOT/"data/universities.csv", encoding="utf-8-sig").set_index("id")
pil = pd.read_csv(ROOT/"data/the_wur_2027_pillars.csv").set_index("id")
W_THE = dict(teaching=.295, research_environment=.29, research_quality=.30, industry=.04, international_outlook=.075)
df["the_score"] = (pil[list(W_THE)] * pd.Series(W_THE)).sum(axis=1)

def band(v):
    if pd.isna(v): return np.nan
    s = str(v).replace(",", "")
    if s in ("NR", "Reporter", ""): return np.nan
    n = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)]
    return np.nan if not n else (n[0] if len(n) == 1 else (n[0] + n[1]) / 2)

# indicator: (series, higher_is_better, axis)
ALL = {
 "iru":       (df["iru2025_score"], True, "national"),
 "the_score": (df["the_score"], True, "global"),
 "the_band":  (df["the_wur_2027"].map(band), False, "global"),
 "qs":        (df["qs_wur_2027"].map(band), False, "global"),
 "sir":       (df["sir2026_overall"].map(band), False, "global"),
 "sir_res":   (df["sir2026_research"].map(band), False, "research"),
 "sir_inn":   (df["sir2026_innovation"].map(band), False, "research"),
 "staff":     (df["students_per_staff_the2027"].map(band), False, "education"),
 "impact":    (df["the_impact_2026"].map(band), False, "sustainability"),
 "sir_soc":   (df["sir2026_societal"].map(band), False, "sustainability"),
}
CORE = ["iru", "qs", "sir_res", "sir_inn", "staff", "impact", "sir_soc"]
SPECS = {
 "S1 main":                 (CORE + ["the_score"], W_EQUAL),
 "S2 + SIR overall":        (CORE + ["the_score", "sir"], W_EQUAL),
 "S3 THE band":             (CORE + ["the_band"], W_EQUAL),
 "S4 tool weights":         (CORE + ["the_score"], W_TOOL),
 "S5 original (v1)":        (CORE + ["the_band", "sir"], W_TOOL),
}

def normalise(ids, inds):
    N = pd.DataFrame(index=ids)
    for k in inds:
        x = ALL[k][0].loc[ids].astype(float); lo, hi = x.min(), x.max()
        z = (x - lo) / (hi - lo); N[k] = z if ALL[k][1] else 1 - z
    return N
def treat(N, how):
    return N if how == "A" else N.fillna(0.0) if how == "B" else N.fillna(N.median())
def axis_scores(N):
    return pd.DataFrame({a: N[[k for k in N if ALL[k][2] == a]].mean(axis=1, skipna=True) for a in AXES})
def wsum(A, W):
    M = ~np.isnan(A); return (W @ np.where(M, A, 0.0).T) / (W @ M.T.astype(float))
def topsis(A, W):
    V = A / np.sqrt((A ** 2).sum(axis=0)); out = np.empty((W.shape[0], A.shape[0]))
    for i, w in enumerate(W):
        X = V * w; dp = np.sqrt(((X - X.max(0)) ** 2).sum(1)); dm = np.sqrt(((X - X.min(0)) ** 2).sum(1)); out[i] = dm / (dp + dm)
    return out
def ranks(S): return stats.rankdata(-S, axis=1, method="average")
def rho(a, b): return float(stats.spearmanr(a, b)[0])

def run(ids, inds, w0, seed=SEED):
    rng = np.random.default_rng(seed)
    N0 = normalise(ids, inds); Wg = rng.dirichlet(np.ones(5), N_SIM); Wl = rng.dirichlet(w0 * 60, N_SIM)
    base, sims = {}, {}
    for how in "ABC":
        A = axis_scores(treat(N0, how)).to_numpy()
        base[how] = ranks(wsum(A, w0[None, :]))[0]
        sims[(how, "global")] = ranks(wsum(A, Wg)); sims[(how, "local")] = ranks(wsum(A, Wl))
    return N0, base, sims, Wg

def stability(ids, base, rk):
    r = np.array([rho(base, x) for x in rk[:2000]])
    w90 = np.percentile(rk, 95, 0) - np.percentile(rk, 5, 0)
    top1 = pd.Series(np.array(ids)[rk.argmin(1)]).value_counts(normalize=True)
    b5 = set(np.argsort(base)[:5])
    return dict(mean_rho=r.mean(), min_rho=r.min(), mean_w90=w90.mean(), max_w90=w90.max(), n_rank1=len(top1),
                leader=top1.index[0], leader_share=top1.iloc[0], top5_kept=np.mean([set(np.argsort(x)[:5]) == b5 for x in rk]))

unis35 = [u for u in df.index if df.loc[u, "type"] == "university"]; all37 = list(df.index)
inds, w0 = SPECS["S1 main"]
N0, base, sims, Wg = run(unis35, inds, w0)

# --- per-university summary (main spec)
rows = []
for how in "ABC":
    rk = sims[(how, "global")]
    for j, u in enumerate(unis35):
        r = rk[:, j]; rows.append(dict(treatment=how, id=u, baseline_rank=base[how][j], mean_rank=r.mean(), p05=np.percentile(r, 5),
                                       p95=np.percentile(r, 95), p_top5=(r <= 5).mean(), p_top10=(r <= 10).mean()))
summ = pd.DataFrame(rows); summ.round(4).to_csv(OUT/"mc_rank_summary.csv", index=False)
stab = pd.DataFrame([dict(sample=35, treatment=h, design=d, **stability(unis35, base[h], sims[(h, d)])) for h in "ABC" for d in ("global", "local")])
_, b37, s37, _ = run(all37, inds, w0)
stab = pd.concat([stab, pd.DataFrame([dict(sample=37, treatment="B", design="global", **stability(all37, b37["B"], s37[("B", "global")]))])])
stab.round(4).to_csv(OUT/"mc_stability_metrics.csv", index=False)

# --- treatments
tr = pd.DataFrame(base, index=unis35)
pd.DataFrame([dict(pair=a+"-"+b, spearman=rho(tr[a], tr[b]), kendall=float(stats.kendalltau(tr[a], tr[b])[0]),
                   mean_abs_shift=(tr[a]-tr[b]).abs().mean(), max_abs_shift=(tr[a]-tr[b]).abs().max())
              for a, b in (("A","B"),("A","C"),("B","C"))]).round(4).to_csv(OUT/"missing_treatment_agreement.csv", index=False)
# --- TOPSIS
tp = []
for how in "BC":
    A = axis_scores(treat(N0, how)).to_numpy(); rw, rt = base[how], ranks(topsis(A, w0[None, :]))[0]
    RW, RT = ranks(wsum(A, Wg[:2000])), ranks(topsis(A, Wg[:2000]))
    tp.append(dict(treatment=how, spearman=rho(rw, rt), kendall=float(stats.kendalltau(rw, rt)[0]), max_abs_shift=np.abs(rw-rt).max(),
                   n_changed=int((rw != rt).sum()), same_top5=set(np.argsort(rw)[:5]) == set(np.argsort(rt)[:5]),
                   mean_spearman_mc=np.mean([rho(a, b) for a, b in zip(RW, RT)])))
    tr["topsis_"+how] = rt
pd.DataFrame(tp).round(4).to_csv(OUT/"topsis_vs_weighted_sum.csv", index=False)
tr.to_csv(OUT/"baseline_ranks_35.csv")

# --- specification comparison (treatment B)
sp = []; ref = base["B"]
for name, (ii, ww) in SPECS.items():
    _, b, s, _ = run(unis35, ii, ww); st = stability(unis35, b["B"], s[("B", "global")]); stl = stability(unis35, b["B"], s[("B", "local")])
    sp.append(dict(spec=name, rho_with_main=rho(ref, b["B"]), max_shift_vs_main=np.abs(ref - b["B"]).max(), mean_rho_global=st["mean_rho"],
                   mean_w90_global=st["mean_w90"], max_w90_global=st["max_w90"], top5_kept_global=st["top5_kept"], top5_kept_local=stl["top5_kept"],
                   top5=" ".join(np.array(unis35)[np.argsort(b["B"])[:5]])))
pd.DataFrame(sp).round(4).to_csv(OUT/"specification_comparison.csv", index=False)

# --- redundancy among SIR indicators
sirc = pd.DataFrame({k: ALL[k][0].loc[unis35] for k in ("sir", "sir_res", "sir_inn", "sir_soc")}).dropna()
red = {f"sir~{k}": round(rho(sirc["sir"], sirc[k]), 3) for k in ("sir_res", "sir_inn", "sir_soc")}

# --- agreement in order
rng = np.random.default_rng(SEED + 1)
series = {"IRU 2025": df["iru2025_score"], "IRU 2024": df["iru2024_score"], "THE 2027 (rebuilt score)": df["the_score"],
          "SIR overall": -ALL["sir"][0], "SIR research": -ALL["sir_res"][0], "SIR innovation": -ALL["sir_inn"][0],
          "SIR societal": -ALL["sir_soc"][0], "THE Impact 2026": -ALL["impact"][0]}
rows = []; names = list(series)
for i, a in enumerate(names):
    for b in names[i+1:]:
        x, y = series[a].loc[unis35], series[b].loc[unis35]; m = (x.notna() & y.notna()).to_numpy()
        if m.sum() < 6: continue
        r, p = stats.spearmanr(x[m], y[m]); tau, pt = stats.kendalltau(x[m], y[m]); idx = np.flatnonzero(m); bs = []
        for _ in range(2000):
            s_ = rng.choice(idx, idx.size); v = stats.spearmanr(x.to_numpy()[s_], y.to_numpy()[s_])[0]
            if not np.isnan(v): bs.append(v)
        rows.append(dict(a=a, b=b, n=int(m.sum()), spearman=r, p=p, ci_low=np.percentile(bs, 2.5), ci_high=np.percentile(bs, 97.5), kendall=tau))
pd.DataFrame(rows).round(4).to_csv(OUT/"rank_correlations.csv", index=False)
# --- agreement in presence
pres = []
for k, lab in (("the_band","THE 2027"),("sir","SIR 2026"),("impact","THE Impact 2026"),("qs","QS 2027")):
    inn = ALL[k][0].loc[unis35].notna(); sc = df.loc[unis35, "iru2025_score"]; u, p = stats.mannwhitneyu(sc[inn], sc[~inn], alternative="greater")
    pres.append(dict(ranking=lab, listed=int(inn.sum()), unlisted=int((~inn).sum()), med_listed=sc[inn].median(), med_unlisted=sc[~inn].median(),
                     auc=u/(inn.sum()*(~inn).sum()), p=p))
pd.DataFrame(pres).round(4).to_csv(OUT/"presence_vs_national_score.csv", index=False)
# --- national vs international-only composite
intl = {}
for how in "ABC":
    A = axis_scores(treat(N0, how))[AXES[1:]].to_numpy(); c = wsum(A, np.full((1, 4), .25))[0]; ok = ~np.isnan(c)
    intl[how] = dict(n=int(ok.sum()), rho=round(rho(df.loc[unis35, "iru2025_score"].to_numpy()[ok], c[ok]), 3))
# --- leave-one-out stability of the agreement coefficients (the universities are a census, not a sample)
loo = {}
for b in ("THE 2027 (rebuilt score)", "SIR overall", "THE Impact 2026"):
    xx, yy = series["IRU 2025"].loc[unis35], series[b].loc[unis35]; mm = xx.notna() & yy.notna(); ids = list(xx[mm].index)
    v = [rho(xx[mm].drop(u), yy[mm].drop(u)) for u in ids]
    loo[b] = dict(n=len(ids), full=round(rho(xx[mm], yy[mm]), 3), min=round(min(v), 3), max=round(max(v), 3),
                  most_influential=ids[int(np.argmax(np.abs(np.array(v) - rho(xx[mm], yy[mm]))))])
x, y = df.loc[unis35, "iru2024_rank"], df.loc[unis35, "iru2025_rank"]
(OUT/"summary.json").write_text(json.dumps(dict(seed=SEED, n_sim=N_SIM, sir_redundancy=red, leave_one_out=loo, national_vs_international_composite=intl,
    national_2024_vs_2025=dict(spearman=round(rho(x, y), 3), kendall=round(float(stats.kendalltau(x, y)[0]), 3),
                               mean_abs_shift=round(float((x-y).abs().mean()), 2), max_abs_shift=int((x-y).abs().max()))), indent=1))

# --- figures (600 dpi, no titles inside the image)
plt.rcParams.update({"font.size": 9, "savefig.dpi": 600, "font.family": "DejaVu Sans"})
SHORT = {"uoitc":"Info. Technology & Comm.","jabir":"Jabir ibn Hayyan","ibnsina":"Ibn Sina","buog":"Basrah Oil and Gas"}
lab = lambda u: SHORT.get(u, df.loc[u, "name_en"].replace("University of ", "").replace(" University", ""))
m = df.loc[unis35, "the_score"].notna(); fig, ax = plt.subplots(figsize=(5.6, 4.6))
ax.scatter(df.loc[unis35, "iru2025_score"][m], df.loc[unis35, "the_score"][m], s=20, color="#1f4e79")
for u in df.loc[unis35][m].index: ax.annotate(lab(u), (df.loc[u, "iru2025_score"], df.loc[u, "the_score"]), fontsize=6, xytext=(3, 3), textcoords="offset points")
ax.set_xlabel("IRU 2025 score"); ax.set_ylabel("THE 2027 score rebuilt from pillar scores"); fig.tight_layout(); fig.savefig(FIG/"fig1_national_vs_the.png"); plt.close(fig)
rk = sims[("B", "global")]; o = np.argsort(np.median(rk, 0)); fig, ax = plt.subplots(figsize=(6.8, 7.6))
ax.boxplot([rk[:, j] for j in o], vert=False, whis=(5, 95), showfliers=False, widths=.6, medianprops=dict(color="black"))
ax.set_yticks(range(1, len(o)+1)); ax.set_yticklabels([lab(unis35[j]) for j in o]); ax.invert_yaxis(); ax.set_xlabel("Rank over 10,000 weight vectors")
fig.tight_layout(); fig.savefig(FIG/"fig2_rank_uncertainty.png"); plt.close(fig)
fig, ax = plt.subplots(figsize=(5.4, 6.6))
for u in tr.index:
    ax.plot([0, 1, 2], [tr.loc[u, "A"], tr.loc[u, "B"], tr.loc[u, "C"]], marker="o", ms=3, lw=.8, color="#555")
    ax.text(-0.06, tr.loc[u, "A"], lab(u), ha="right", va="center", fontsize=5.5)
ax.set_xticks([0, 1, 2]); ax.set_xticklabels(["A: available case", "B: penalty", "C: median"]); ax.invert_yaxis(); ax.set_ylabel("Composite rank"); ax.set_xlim(-.95, 2.1)
fig.tight_layout(); fig.savefig(FIG/"fig3_missing_treatments.png"); plt.close(fig)
print("done")
