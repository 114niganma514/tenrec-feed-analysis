"""
Statistical tests on the SQL outputs (writes output/tables/stats_tests.csv).

1. QK vs QB click-through and likes per click: two-proportion z-tests
2. CTR differs by gender: chi-square on clicks vs non-clicks (exposure counts)
3. Age and CTR: Spearman correlation across age bands (code 0 = missing excluded)
4. Feed fatigue: Wilcoxon signed-rank on per-user CTR, first 20 exposures vs exposures 101-200
5. Popularity bias: Spearman correlation between item exposure decile and CTR
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def two_prop(x1, n1, x2, n2):
    p1, p2 = x1 / n1, x2 / n2
    p = (x1 + x2) / (n1 + n2)
    z = (p1 - p2) / np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return p1, p2, z, 2 * stats.norm.sf(abs(z))


def run_tests(out: Path):
    t = lambda n: pd.read_csv(out / "tables" / f"{n}.csv")
    rows = []

    f = t("funnel_by_platform").set_index("platform")
    if {"QK", "QB"} <= set(f.index):
        p1, p2, z, p = two_prop(f.clicks["QK"], f.exposures["QK"], f.clicks["QB"], f.exposures["QB"])
        rows.append(("CTR: QK vs QB (two-proportion z-test)", f"{p1:.2%} vs {p2:.2%}", p, f"z = {z:.0f}"))
        p1, p2, z, p = two_prop(f.likes["QK"], f.clicks["QK"], f.likes["QB"], f.clicks["QB"])
        rows.append(("Likes per click: QK vs QB (two-proportion z-test)", f"{p1:.2%} vs {p2:.2%}", p, f"z = {z:.1f}"))

    g = t("by_gender")
    g = g[g.gender > 0]
    if len(g) >= 2:
        table = np.column_stack([g.clicks, g.exposures - g.clicks])
        chi2, p, _, _ = stats.chi2_contingency(table)
        ctr = g.clicks / g.exposures
        rows.append(("CTR differs by gender code (chi-square)",
                     " vs ".join(f"code {int(c)}: {v:.2%}" for c, v in zip(g.gender, ctr)), p, f"chi2 = {chi2:,.0f}"))

    a = t("by_age")
    a = a[a.age > 0]
    if len(a) >= 3:
        rho, p = stats.spearmanr(a.age, a.clicks / a.exposures)
        rows.append(("Age band vs CTR (Spearman, across bands)", f"{len(a)} bands", p, f"rho = {rho:.2f}"))

    fw = t("fatigue_within_user")
    for plat, d in fw.groupby("platform"):
        if len(d) >= 10:
            w = stats.wilcoxon(d.ctr_early, d.ctr_late)  # two-sided
            rows.append((f"{plat}: same users' CTR, first 20 vs exposures 101-200 (Wilcoxon signed-rank, two-sided)",
                         f"{d.ctr_early.mean():.2%} vs {d.ctr_late.mean():.2%} ({len(d):,} users)", w.pvalue,
                         f"{(d.ctr_late < d.ctr_early).mean():.0%} of users click less later"))

    pdc = t("popularity_deciles")
    rho, p = stats.spearmanr(pdc.decile, pdc.clicks / pdc.exposures)
    rows.append(("Item exposure decile vs CTR (Spearman)", "10 deciles", p, f"rho = {rho:.2f}"))

    res = pd.DataFrame(rows, columns=["test", "compared", "p_value", "effect"])
    res["significant_at_5pct"] = res.p_value < .05
    res.to_csv(out / "tables" / "stats_tests.csv", index=False, encoding="utf-8")
    for r in res.itertuples():
        print(f"  {r.test[:72]:<72} p={r.p_value:.2g}")
    return res


if __name__ == "__main__":
    run_tests(Path(__file__).resolve().parents[1] / "output")
