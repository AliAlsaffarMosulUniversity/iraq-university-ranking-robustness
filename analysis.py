"""Phase 2 analysis.
1. Rank agreement between the national ranking (IRU) and international rankings.
2. Monte Carlo weight sensitivity of a composite index (10,000 weight vectors).
3. Weighted sum vs TOPSIS.
4. Three treatments of "not ranked" values.
Main sample: 35 universities. Sensitivity sample: 37 (adds two university colleges).
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
rng = np.random.default_rng(SEED)

df = pd.read_csv(ROOT/"data/universities.csv", encoding="utf-8-sig").set_index("id")
pil = pd.read_csv(ROOT/"data/the_wur_2027_pillars.csv").set_index("id")

def band(v):
    """Rank band -> number (midpoint; open-ended bands use the lower bound). NR/Reporter/blank -> NaN."""
    if pd.isna(v): return np.nan
    s = str(v).replace(",", "")
    if s in ("NR", "Reporter", ""): return np.nan
    n = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)]
    return np.nan if not n else (n[0] if len(n) == 1 else (n[0] + n[1]) / 2)

# ---- indicator matrix (raw), direction, axis ---------------------------------
IND = {  # name: (column, higher_is_better, axis)
 "iru":        ("iru2025_score", True,  "national"),
 "the":        ("the_wur_2027", False, "global"),
 "qs":         ("qs_wur_2027", False, "global"),
 "sir":        ("sir2026_overall", False, "global"),
 "sir_res":    ("sir2026_research", False, "research"),
 "sir_inn":    ("sir2026_innovation", False, "research"),
 "staff":      ("students_per_staff_the2027", False, "education"),
 "impact":     ("the_impact_2026", False, "sustainability"),
 "sir_soc":    ("sir2026_societal", False, "sustainability"),
}
AXES = ["national", "global", "research", "education", "sustainability"]
BASE_W = np.array([25, 25, 25, 10, 15], float) / 100          # weights used in the comparison app
raw = pd.DataFrame({k: df[c].map(band) for k, (c, _, _) in IND.items()})

W_THE = dict(teaching=.295, research_environment=.29, research_quality=.30, industry=.04, international_outlook=.075)
df["the_score"] = (pil[list(W_THE)] * pd.Series(W_THE)).sum(axis=1)   # continuous THE score rebuilt from pillars

def normalise(R):
    """Min-max to [0,1], 1 = best, computed over observed values only."""
    N = pd.DataFrame(index=R.index, columns=R.columns, dtype=float)
    for k in R:
        x = R[k]; lo, hi = x.min(), x.max()
        z = (x - lo) / (hi - lo) if hi > lo else x * 0 + 1.0
        N[k] = z if IND[k][1] else 1 - z
    return N

def treat(N, how):
    """A = available case (ignore missing, renormalise weights);
       B = penalty (missing = worst observed = 0);  C = neutral (missing = median of observed)."""
    if how == "A": return N
    if how == "B": return N.fillna(0.0)
    if how == "C": return N.fillna(N.median())
    raise ValueError(how)

def axis_scores(N):
    """Mean of available indicators inside each axis -> institutions x axes (NaN if axis fully missing)."""
    return pd.DataFrame({a: N[[k for k in IND if IND[k][2] == a]].mean(axis=1, skipna=True) for a in AXES})

def weighted_sum(A, W):
    """A: n x m axis scores (may hold NaN), W: s x m weights. Returns s x n composite (available-case renormalised)."""
    M = ~np.isnan(A); A0 = np.where(M, A, 0.0)
    num = W @ A0.T; den = W @ M.T.astype(float)
    return num / den

def topsis(A, W):
    """Classic TOPSIS on a complete n x m matrix. Returns s x n closeness."""
    V = A / np.sqrt((A ** 2).sum(axis=0))                      # vector normalisation
    out = np.empty((W.shape[0], A.shape[0]))
    for i, w in enumerate(W):
        X = V * w; best, worst = X.max(axis=0), X.min(axis=0)
        dp = np.sqrt(((X - best) ** 2).sum(axis=1)); dm = np.sqrt(((X - worst) ** 2).sum(axis=1))
        out[i] = dm / (dp + dm)
    return out

def ranks(S):                                                  # 1 = best, per row
    return stats.rankdata(-S, axis=1, method="average")

def run(sample_ids, tag):
    R = raw.loc[sample_ids]; N0 = normalise(R); res = {}
    W_uni = rng.dirichlet(np.ones(len(AXES)), N_SIM)                       # uniform on the simplex
    W_loc = rng.dirichlet(BASE_W * 60, N_SIM)                              # perturbation around the baseline
    base = {}
    for how in "ABC":
        A = axis_scores(treat(N0, how)).to_numpy()
        base[how] = ranks(weighted_sum(A, BASE_W[None, :]))[0]
        for wname, W in (("uniform", W_uni), ("local", W_loc)):
            rk = ranks(weighted_sum(A, W))
            res[(how, wname)] = rk
    # summary table per institution, treatment B (complete matrix) and A
    rows = []
    for how in "ABC":
        rk = res[(how, "uniform")]
        for j, u in enumerate(sample_ids):
            r = rk[:, j]
            rows.append(dict(sample=tag, treatment=how, id=u, baseline_rank=base[how][j], mean_rank=r.mean(),
                             p05=np.percentile(r, 5), p95=np.percentile(r, 95), range90=np.percentile(r, 95) - np.percentile(r, 5),
                             p_top5=(r <= 5).mean(), p_top10=(r <= 10).mean(), modal_rank=stats.mode(np.round(r), keepdims=False).mode))
    summ = pd.DataFrame(rows)
    # global stability metrics
    glob = []
    for (how, wname), rk in res.items():
        b = base[how]
        rho = np.array([stats.spearmanr(b, r)[0] for r in rk[:2000]])
        top1 = pd.Series(np.array(sample_ids)[rk.argmin(axis=1)]).value_counts(normalize=True)
        rng90 = np.percentile(rk, 95, axis=0) - np.percentile(rk, 5, axis=0)
        glob.append(dict(sample=tag, treatment=how, weights=wname, mean_spearman_vs_baseline=rho.mean(), min_spearman=rho.min(),
                         mean_range90=rng90.mean(), max_range90=rng90.max(), n_distinct_rank1=len(top1),
                         rank1_leader=top1.index[0], rank1_share=top1.iloc[0],
                         share_same_top5=np.mean([set(np.argsort(r)[:5]) == set(np.argsort(b)[:5]) for r in rk])))
    glob = pd.DataFrame(glob)
    # agreement between missing-data treatments (baseline weights)
    tr = pd.DataFrame(base, index=sample_ids)
    tr_corr = pd.DataFrame([dict(sample=tag, pair=f"{a}-{b}", spearman=stats.spearmanr(tr[a], tr[b])[0],
                                 kendall=stats.kendalltau(tr[a], tr[b])[0], max_abs_shift=(tr[a] - tr[b]).abs().max(),
                                 mean_abs_shift=(tr[a] - tr[b]).abs().mean()) for a, b in (("A","B"),("A","C"),("B","C"))])
    # TOPSIS vs weighted sum (complete matrices only: treatments B and C)
    tp = []
    for how in "BC":
        A = axis_scores(treat(N0, how)).to_numpy()
        rw, rt = ranks(weighted_sum(A, BASE_W[None, :]))[0], ranks(topsis(A, BASE_W[None, :]))[0]
        Wm = W_uni[:2000]; RW, RT = ranks(weighted_sum(A, Wm)), ranks(topsis(A, Wm))
        rho_mc = np.array([stats.spearmanr(a, b)[0] for a, b in zip(RW, RT)])
        tp.append(dict(sample=tag, treatment=how, spearman_baseline=stats.spearmanr(rw, rt)[0], kendall_baseline=stats.kendalltau(rw, rt)[0],
                       max_abs_shift=np.abs(rw - rt).max(), n_changed=int((rw != rt).sum()), same_top5=set(np.argsort(rw)[:5]) == set(np.argsort(rt)[:5]),
                       mean_spearman_mc=rho_mc.mean(), min_spearman_mc=rho_mc.min()))
        tr[f"topsis_{how}"] = rt
    return summ, glob, tr_corr, pd.DataFrame(tp), tr, res

unis35 = [u for u in df.index if df.loc[u, "type"] == "university"]
all37 = list(df.index)
S35 = run(unis35, "35 universities"); S37 = run(all37, "37 institutions")
pd.concat([S35[0], S37[0]]).round(4).to_csv(OUT/"mc_rank_summary.csv", index=False)
pd.concat([S35[1], S37[1]]).round(4).to_csv(OUT/"mc_stability_metrics.csv", index=False)
pd.concat([S35[2], S37[2]]).round(4).to_csv(OUT/"missing_treatment_agreement.csv", index=False)
pd.concat([S35[3], S37[3]]).round(4).to_csv(OUT/"topsis_vs_weighted_sum.csv", index=False)
S35[4].rename(columns={"A":"wsum_A","B":"wsum_B","C":"wsum_C"}).to_csv(OUT/"baseline_ranks_35.csv")

# ---- 1. rank agreement national vs international -----------------------------
series = {"IRU 2025": df["iru2025_score"], "IRU 2024": df["iru2024_score"], "THE 2027 (rebuilt score)": df["the_score"],
          "THE 2027 (band)": -raw["the"], "SIR overall": -raw["sir"], "SIR research": -raw["sir_res"],
          "SIR innovation": -raw["sir_inn"], "SIR societal": -raw["sir_soc"], "THE Impact 2026": -raw["impact"]}
names = list(series); rows = []
for i, a in enumerate(names):
    for b in names[i+1:]:
        x, y = series[a].loc[unis35], series[b].loc[unis35]; m = x.notna() & y.notna()
        if m.sum() < 6: continue
        rho, p = stats.spearmanr(x[m], y[m]); tau, pt = stats.kendalltau(x[m], y[m])
        # bootstrap CI for rho
        idx = np.flatnonzero(m.to_numpy()); bs = []
        for _ in range(2000):
            s = rng.choice(idx, idx.size)
            r = stats.spearmanr(x.to_numpy()[s], y.to_numpy()[s])[0]
            if not np.isnan(r): bs.append(r)
        rows.append(dict(a=a, b=b, n=int(m.sum()), spearman=rho, p_spearman=p, ci_low=np.percentile(bs, 2.5),
                         ci_high=np.percentile(bs, 97.5), kendall=tau, p_kendall=pt))
corr = pd.DataFrame(rows); corr.round(4).to_csv(OUT/"rank_correlations.csv", index=False)

# presence in international rankings vs national score (does the national ranking separate listed from unlisted?)
pres = []
for k, lab in (("the","THE 2027"),("sir","SIR 2026"),("impact","THE Impact 2026"),("qs","QS 2027")):
    inn = raw.loc[unis35, k].notna(); sc = df.loc[unis35, "iru2025_score"]
    u, p = stats.mannwhitneyu(sc[inn], sc[~inn], alternative="greater")
    pres.append(dict(ranking=lab, n_listed=int(inn.sum()), n_unlisted=int((~inn).sum()), median_iru_listed=sc[inn].median(),
                     median_iru_unlisted=sc[~inn].median(), auc=u / (inn.sum() * (~inn).sum()), p_one_sided=p))
pd.DataFrame(pres).round(4).to_csv(OUT/"presence_vs_national_score.csv", index=False)

# national rank vs composite of international indicators only (removes the national axis)
N35 = normalise(raw.loc[unis35]); intl = {}
for how in "ABC":
    A = axis_scores(treat(N35, how))[AXES[1:]].to_numpy(); w = BASE_W[1:] / BASE_W[1:].sum()
    comp = weighted_sum(A, w[None, :])[0]; ok = ~np.isnan(comp)
    rho, p = stats.spearmanr(df.loc[unis35, "iru2025_score"].to_numpy()[ok], comp[ok])
    intl[how] = dict(n=int(ok.sum()), spearman=round(float(rho), 4), p=float(p))
# year-to-year national stability
x, y = df.loc[unis35, "iru2024_rank"], df.loc[unis35, "iru2025_rank"]
yy = dict(spearman=round(float(stats.spearmanr(x, y)[0]), 4), kendall=round(float(stats.kendalltau(x, y)[0]), 4),
          mean_abs_shift=round(float((x - y).abs().mean()), 2), max_abs_shift=int((x - y).abs().max()),
          biggest_movers={u: int(x[u] - y[u]) for u in (x - y).abs().sort_values(ascending=False).index[:5]})
(OUT/"summary.json").write_text(json.dumps(dict(seed=SEED, n_sim=N_SIM, national_vs_international_composite=intl,
                                                 national_2024_vs_2025=yy), indent=1, ensure_ascii=False))

# ---- figures -----------------------------------------------------------------
plt.rcParams.update({"font.size": 9, "figure.dpi": 150})
rk = S35[5][("B", "uniform")]; order = np.argsort(np.median(rk, axis=0))
SHORT = {"uoitc":"Info. Technology & Comm.","jabir":"Jabir ibn Hayyan","ibnsina":"Ibn Sina","buog":"Basrah Oil and Gas"}
fig, ax = plt.subplots(figsize=(8, 8))
ax.boxplot([rk[:, j] for j in order], vert=False, whis=(5, 95), showfliers=False, widths=.6,
           medianprops=dict(color="black"))
ax.set_yticks(range(1, len(order) + 1)); ax.set_yticklabels([SHORT.get(unis35[j], df.loc[unis35[j], "name_en"].replace("University of ", "").replace(" University", "")) for j in order])
ax.invert_yaxis(); ax.set_xlabel("Rank over 10,000 weight vectors\n(box: quartiles; whiskers: 5th–95th percentile)")
ax.set_title("Rank uncertainty under random axis weights", fontsize=10); fig.tight_layout(); fig.savefig(FIG/"fig1_rank_uncertainty.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(6, 5.2)); m = df.loc[unis35, "the_score"].notna()
ax.scatter(df.loc[unis35, "iru2025_score"][m], df.loc[unis35, "the_score"][m], s=22, color="#1f4e79")
for u in df.loc[unis35][m].index: ax.annotate(u, (df.loc[u, "iru2025_score"], df.loc[u, "the_score"]), fontsize=6.5, xytext=(3, 3), textcoords="offset points")
ax.set_xlabel("IRU 2025 score (national)"); ax.set_ylabel("THE WUR 2027 score rebuilt from pillars"); ax.set_title("National vs international: 23 universities ranked by THE")
fig.tight_layout(); fig.savefig(FIG/"fig2_national_vs_the.png"); plt.close(fig)

tr = S35[4]; fig, ax = plt.subplots(figsize=(6, 7)); o = tr["B"].sort_values().index
for u in o:
    ax.plot([0, 1, 2], [tr.loc[u, "A"], tr.loc[u, "B"], tr.loc[u, "C"]], marker="o", ms=3, lw=.8, color="#555")
    ax.text(-0.05, tr.loc[u, "A"], u, ha="right", va="center", fontsize=6.5)
ax.set_xticks([0, 1, 2]); ax.set_xticklabels(["A: available case", "B: penalty", "C: neutral (median)"]); ax.invert_yaxis()
ax.set_ylabel("Composite rank (baseline weights)"); ax.set_xlim(-.45, 2.1); ax.set_title("Effect of the 'not ranked' treatment on composite rank")
fig.tight_layout(); fig.savefig(FIG/"fig3_missing_treatments.png"); plt.close(fig)
print("done")
