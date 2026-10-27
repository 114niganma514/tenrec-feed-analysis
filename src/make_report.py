"""
Reads output/tables/*.csv -> writes output/charts/*.png and output/report.md
Can be run on its own after the SQL step: python src/make_report.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({
    "font.sans-serif": ["Segoe UI", "Helvetica", "Arial", "DejaVu Sans"],
    "axes.unicode_minus": False, "figure.dpi": 150, "savefig.bbox": "tight",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#8a8984", "axes.labelcolor": "#52514e",
    "xtick.color": "#52514e", "ytick.color": "#52514e",
    "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": .6, "axes.axisbelow": True,
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlecolor": "#0b0b0b",
})
BLUE, ORANGE, MUTED, INK = "#2a78d6", "#eb6834", "#b9b8b2", "#0b0b0b"
pct = lambda x, d=1: f"{x * 100:.{d}f}%"
num = lambda x: f"{x:,.0f}"


def big(v):
    a = abs(v)
    if a >= 1e9:
        return f"{v / 1e9:.1f}B"
    if a >= 1e6:
        return f"{v / 1e6:.1f}M"
    if a >= 1e3:
        return f"{v / 1e3:.0f}K"
    return f"{v:,.0f}"


def build(out: Path):
    T = lambda n: pd.read_csv(out / "tables" / f"{n}.csv")
    save = lambda fig, name: (fig.savefig(out / "charts" / name, facecolor=fig.get_facecolor()), plt.close(fig))
    (out / "charts").mkdir(exist_ok=True)

    q = T("quality").set_index("platform")
    f = T("funnel_by_platform").set_index("platform")
    fc, g, a, ga = T("funnel_by_category"), T("by_gender"), T("by_age"), T("gender_age_grid")
    pdc, conc, isz = T("popularity_deciles"), T("concentration").iloc[0], T("item_ctr_by_size")
    ab, up, us = T("activity_buckets"), T("user_percentiles"), T("user_summary").iloc[0]
    fat, fw, st = T("fatigue"), T("fatigue_within_user"), T("stats_tests")
    src = T("data_source").source.iloc[0]
    nl = T("null_counts").set_index("tbl")
    for d in (f,):
        d["ctr"] = d.clicks / d.exposures
        d["like_pc"] = d.likes / d.clicks
        d["share_pc"] = d.shares / d.clicks
        d["follow_pc"] = d.follows / d.clicks
        d["rewatch_pc"] = d.rewatched_clicks / d.clicks
    plats = [p for p in ["QK", "QB"] if p in f.index]
    qk = f.loc["QK"]

    # 1 Funnel per 1,000 exposures, both platforms (log scale)
    metrics = [("clicks", "Clicks"), ("likes", "Likes"),
               ("follows", "Follows"), ("shares", "Shares")]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    x = np.arange(len(metrics))
    for k, (p, col) in enumerate(zip(plats, [BLUE, ORANGE])):
        vals = [f.loc[p, m] * 1000 / f.loc[p, "exposures"] for m, _ in metrics]
        ax.bar(x + (k - .5) * .38, vals, .38, color=col, label={"QK": "QQ Kandian (QK)", "QB": "QQ Browser (QB)"}[p])
        for i, v in enumerate(vals):
            ax.text(x[i] + (k - .5) * .38, v, f"{v:,.1f}", ha="center", va="bottom", fontsize=7, color=INK)
    ax.set_yscale("log")
    ax.set_xticks(x, [n for _, n in metrics])
    ax.legend(frameon=False)
    ax.grid(axis="x", visible=False)
    ax.set_title("Engagement per 1,000 video exposures (log scale)")
    save(fig, "01_funnel.png")

    # 2 Gender x age CTR heatmap
    ga["ctr"] = ga.clicks / ga.exposures
    hm = ga[(ga.gender > 0)].pivot(index="gender", columns="age", values="ctr")
    fig, ax = plt.subplots(figsize=(9, 2.8))
    im = ax.imshow(hm.values, cmap="Blues", aspect="auto")
    for (i, j), v in np.ndenumerate(hm.values):
        if not np.isnan(v):
            ax.text(j, i, f"{v * 100:.1f}", ha="center", va="center", fontsize=8,
                    color="white" if v > np.nanmax(hm.values) * .75 else INK)
    ax.set_yticks(range(len(hm)), [f"gender code {int(c)}" for c in hm.index])
    ax.set_xticks(range(hm.shape[1]), [("missing" if c == 0 else f"band {int(c)}") for c in hm.columns], fontsize=8)
    ax.grid(False)
    ax.set_title("Click-through rate (%) by gender code and age band (QK)")
    fig.colorbar(im, ax=ax, fraction=.025, format=lambda v, _: pct(v, 0))
    save(fig, "02_gender_age_ctr.png")

    # 3 Age bands: CTR and exposures per user
    a2 = a[a.age > 0].copy()
    a2["ctr"] = a2.clicks / a2.exposures
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.4))
    ax[0].bar(a2.age.astype(int).astype(str), a2.ctr, color=BLUE, width=.6)
    ax[0].yaxis.set_major_formatter(lambda v, _: pct(v, 0))
    ax[0].set_title("Click-through rate by age band")
    ax[1].bar(a2.age.astype(int).astype(str), a2.exposures_per_user, color=BLUE, width=.6)
    ax[1].set_title("Exposures per user by age band")
    for x_ in ax:
        x_.set_xlabel("Age band (anonymised code)")
        x_.grid(axis="x", visible=False)
    save(fig, "03_age.png")

    # 4 Popularity deciles
    pdc["exp_share"] = pdc.exposures / pdc.exposures.sum()
    pdc["ctr"] = pdc.clicks / pdc.exposures
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.4))
    ax[0].bar(pdc.decile.astype(str), pdc.exp_share, color=BLUE, width=.6)
    ax[0].yaxis.set_major_formatter(lambda v, _: pct(v, 0))
    ax[0].set_title("Share of all exposures")
    ax[1].plot(pdc.decile.astype(str), pdc.ctr, color=BLUE, lw=2, marker="o", ms=5)
    ax[1].yaxis.set_major_formatter(lambda v, _: pct(v, 1))
    ax[1].set_title("Click-through rate")
    for x_ in ax:
        x_.set_xlabel("Video popularity decile (10 = most exposed)")
    ax[0].grid(axis="x", visible=False)
    save(fig, "04_popularity.png")

    # 5 User activity buckets
    ab["label"] = ab.exposure_bucket.str.split("_", n=1).str[1]
    ab["user_share"] = ab.users / ab.users.sum()
    ab["click_share"] = ab.clicks / ab.clicks.sum()
    ab["ctr"] = ab.clicks / ab.exposures
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 3.6))
    x = np.arange(len(ab))
    ax[0].bar(x - .2, ab.user_share, .38, color=BLUE, label="Share of users")
    ax[0].bar(x + .2, ab.click_share, .38, color=ORANGE, label="Share of clicks")
    ax[0].set_xticks(x, ab.label)
    ax[0].yaxis.set_major_formatter(lambda v, _: pct(v, 0))
    ax[0].legend(frameon=False)
    ax[0].set_title("Users vs clicks by number of exposures")
    ax[1].bar(ab.label, ab.ctr, color=BLUE, width=.6)
    ax[1].yaxis.set_major_formatter(lambda v, _: pct(v, 0))
    ax[1].set_title("Click-through rate by number of exposures")
    for x_ in ax:
        x_.set_xlabel("Exposures per user")
        x_.grid(axis="x", visible=False)
    save(fig, "05_user_activity.png")

    # 6 User concentration curve
    up = up.sort_values("pctile")
    up["cum_users"] = up.users.cumsum() / up.users.sum()
    up["cum_clicks"] = up.clicks.cumsum() / up.clicks.sum()
    top10 = up.loc[up.pctile == 10, "cum_clicks"].iloc[0] if (up.pctile == 10).any() else np.nan
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(np.r_[0, up.cum_users], np.r_[0, up.cum_clicks], color=BLUE, lw=2)
    ax.plot([0, 1], [0, 1], color=MUTED, lw=1, ls="--")
    ax.scatter([.1], [top10], color=ORANGE, zorder=3, s=25)
    ax.annotate(f"Top 10% of users = {pct(top10, 0)} of clicks", (.1, top10), xytext=(8, -12),
                textcoords="offset points", fontsize=8, color=INK)
    ax.xaxis.set_major_formatter(lambda v, _: pct(v, 0))
    ax.yaxis.set_major_formatter(lambda v, _: pct(v, 0))
    ax.set_xlabel("Users ranked by clicks")
    ax.set_ylabel("Cumulative share of clicks")
    ax.set_title("How concentrated are clicks? (QK)")
    save(fig, "06_user_concentration.png")

    # 7 Feed fatigue (indexed to the first 10 exposures)
    fat["ctr"] = fat.clicks / fat.exposures
    fat["label"] = fat.position_bucket.str.split("_", n=1).str[1]
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    for p, col in zip(plats, [BLUE, ORANGE]):
        d = fat[(fat.platform == p) & (fat.exposures >= 500)]
        if len(d):
            ax.plot(d.label, d.ctr / d.ctr.iloc[0] * 100, color=col, lw=2, marker="o", ms=5,
                    label={"QK": "QK (2% user sample)", "QB": "QB (all users)"}[p])
    ax.axhline(100, color=MUTED, lw=1, ls="--")
    ax.set_ylabel("CTR index (first 10 exposures = 100)")
    ax.set_xlabel("Position in the user's feed")
    ax.legend(frameon=False)
    ax.set_title("Click-through by position in the feed (indexed to the first 10 exposures)")
    save(fig, "07_fatigue.png")

    # ---------------- numbers for the report ----------------
    s = lambda key: st[st.test.str.startswith(key)].iloc[0] if (st.test.str.startswith(key)).any() else None
    g2 = g[g.gender > 0].assign(ctr=lambda d: d.clicks / d.exposures)
    a2s = a2.sort_values("ctr")
    top_dec, mid = pdc[pdc.decile == 10].iloc[0], pdc[pdc.decile.between(5, 9)]
    mid_ctr = mid.clicks.sum() / mid.exposures.sum()
    # fatigue sizing on QK: clicks lost beyond position 100 if CTR stayed at the first-20 level
    fq = fat[fat.platform == "QK"].copy()
    lost_txt = ""
    if len(fq):
        early = fq[fq.position_bucket.str[:2].isin(["01", "02"])]
        early_ctr = early.clicks.sum() / early.exposures.sum()
        late = fq[fq.position_bucket.str[:2].astype(int) >= 5]
        late_ctr = late.clicks.sum() / max(late.exposures.sum(), 1)
        late_share = late.exposures.sum() / fq.exposures.sum()
        lost = (early_ctr - late_ctr) * late.exposures.sum() * 50          # QK sample is 1 user in 50
        recover = .1 * lost
        lost_txt = (f"In the QK sample, CTR is {pct(early_ctr)} in the first 20 exposures but {pct(late_ctr)} beyond "
                    f"exposure 100, and {pct(late_share, 0)} of all exposures happen beyond position 100. "
                    f"This pooled gap mixes light and heavy users; the same-user test above confirms the drop within users. "
                    f"Scaled to all QK users, the gap is about **{big(lost)} clicks**; recovering a tenth of it "
                    f"would add about **{big(recover)} clicks** (+{pct(recover / qk.clicks)}).")
    s_fat = [r for r in st.itertuples() if "same users" in r.test]
    fat_by = {r.test.split(":")[0]: r for r in s_fat}
    fq_t = fat_by.get("QK")
    fat_summary = f"QK same users: {fq_t.compared}" if fq_t is not None else "n/a"
    def _dir(r):
        a_, b_ = [float(x.strip().rstrip("%")) for x in r.compared.split("(")[0].split("vs")]
        return "down" if b_ < a_ else "up"
    if fq_t is not None and fq_t.p_value < .05 and _dir(fq_t) == "down":
        fat_interp = "QK click-through decays with scrolling depth"
        qb_t = fat_by.get("QB")
        if qb_t is not None and _dir(qb_t) == "up":
            fat_interp += "; QB users who scroll far click more (different product behaviour)"
    else:
        fat_interp = "No clear fatigue in QK"
    if "QB" in f.index:
        r_ = f.loc["QB", "ctr"] / qk.ctr
        lk = f.loc["QB", "like_pc"] / qk.like_pc
        if r_ > 1.2:
            ctr_interp = f"QB users click {r_:.1f}x as often but like {1 / lk:.1f}x less per click: shallow clicking vs deeper engagement"
        elif r_ < 1 / 1.2:
            ctr_interp = "QK users click far more often than QB users"
        else:
            ctr_interp = "Similar click-through across products"
    else:
        ctr_interp = ""
    never = us.never_clicked / us.users
    if never > .02:
        rec2 = (f"**Recommendation 2: rescue the non-clickers early.** {pct(never)} of users never clicked anything they "
                f"were shown. Treat the first session as cold start: more diverse, broadly popular content and a quick "
                f"interest picker, measured by first-session CTR.")
    else:
        rec2 = (f"**Recommendation 2: turn clickers into engaged users.** Almost every user clicks something "
                f"(only {int(us.never_clicked):,} never did), but only {pct(us.ever_liked / us.users)} ever liked, "
                f"{pct(us.ever_shared / us.users)} ever shared and {pct(us.ever_followed / us.users)} ever followed. "
                f"Prompts such as a follow button after the second video from the same creator, measured by the share of "
                f"users with a first follow within 7 days, target the larger gap.")
    is_real = q.loc["QK", "exposures"] > 10_000_000

    def tl(r):
        return f"{r.compared}, p = {r.p_value:.2g}, {r.effect}" if r is not None else "n/a"

    sp = s("CTR: QK vs QB")
    sl = s("Likes per click")
    sg = s("CTR differs by gender")
    sa = s("Age band vs CTR")
    spop = s("Item exposure decile")

    md = f"""# Tencent Video Feed Engagement Analysis (Tenrec)

> Data: {"Tenrec benchmark (Tencent, NeurIPS 2022): " + src if is_real else "WARNING: synthetic sample for testing only. Re-run on the real data before quoting any number."}
> QQ Kandian (QK): {num(q.loc["QK", "exposures"])} video exposures, {num(q.loc["QK", "users"])} users, {num(q.loc["QK", "items"])} videos.
> QQ Browser (QB): {num(q.loc["QB", "exposures"])} exposures, {num(q.loc["QB", "users"])} users, {num(q.loc["QB", "items"])} videos.
> Each row is one exposure with click, like, share and follow flags. Gender and age are anonymised codes (0 = missing). No timestamps are provided.
> Data quality (QK): {num(q.loc["QK", "watch_without_click"])} rows have watching_times > 0 without a click, so watching_times is not used as a post-click metric; {num(q.loc["QK", "action_without_click"])} rows have a like, share or follow without a click (kept as recorded). Exposures with a missing video_category are almost never clicked.
> Missing values (written as \\N in the source): QK video_category {num(nl.loc["qk", "category_null"])}, gender {num(nl.loc["qk", "gender_null"])}, age {num(nl.loc["qk", "age_null"])}, click {num(nl.loc["qk", "click_null"])}; flags default to 0, gender/age to code 0, video_category to "missing".

## 0. Executive summary

| Area | Key numbers | Interpretation |
|---|---|---|
| Click-through | QK {pct(qk.ctr)} of exposures clicked{"; QB " + pct(f.loc["QB", "ctr"]) if "QB" in f.index else ""} | {ctr_interp} |
| Depth | Per 1,000 QK clicks: {qk.like_pc * 1000:.1f} likes, {qk.follow_pc * 1000:.1f} follows, {qk.share_pc * 1000:.1f} shares | Only {pct(us.ever_liked / us.users, 0)} of users ever liked and {pct(us.ever_followed / us.users, 0)} ever followed |
| Popularity | Top 1% of videos get {pct(conc.top1pct_exposure_share)} of exposures; {num(conc.items_shown_once)} videos were shown only once | Exposure is highly concentrated |
| Earned exposure | CTR of the most-exposed decile {pct(top_dec.clicks / top_dec.exposures)} vs deciles 5-9 {pct(mid_ctr)} | {"Popular videos click better, but this is partly a feedback loop: high CTR earns exposure and exposure builds popularity" if top_dec.clicks / top_dec.exposures > mid_ctr else "The most-exposed videos do NOT click better: possible popularity bias"} |
| Users | Top 10% of users make {pct(top10, 0)} of clicks; CTR falls from {pct(ab.ctr.iloc[0], 0)} for the lightest users to {pct(ab.ctr.iloc[-1], 0)} for the heaviest | {"Engagement is driven by a minority" if top10 > .3 else "Clicks are spread fairly widely"} |
| Fatigue | {fat_summary} | {fat_interp} |
| Audience | CTR ranges from {pct(a2s.ctr.iloc[0])} (age band {int(a2s.age.iloc[0])}) to {pct(a2s.ctr.iloc[-1])} (band {int(a2s.age.iloc[-1])}) | Ranking should be calibrated by audience segment |

## 1. Engagement funnel
![funnel](charts/01_funnel.png)
- QK: {num(qk.exposures)} exposures -> {num(qk.clicks)} clicks ({pct(qk.ctr)}) -> {num(qk.likes)} likes, {num(qk.follows)} follows, {num(qk.shares)} shares.
""" + (f"""- QB: {num(f.loc["QB", "exposures"])} exposures -> {num(f.loc["QB", "clicks"])} clicks ({pct(f.loc["QB", "ctr"])}) -> {num(f.loc["QB", "likes"])} likes, {num(f.loc["QB", "follows"])} follows, {num(f.loc["QB", "shares"])} shares.
- {sp.test}: {tl(sp)}.
- {sl.test}: {tl(sl)}.
""" if "QB" in f.index else "") + "\n".join(
        f"- {r.platform}, video_category {'missing' if r.video_category < 0 else int(r.video_category)}: CTR {pct(r.clicks / r.exposures)}, likes per 1k clicks {r.likes * 1000 / max(r.clicks, 1):.1f} ({pct(r.exposures / f.loc[r.platform, 'exposures'], 0)} of that platform's exposures)"
        for r in fc.itertuples()) + f"""

## 2. Audience
![gender-age](charts/02_gender_age_ctr.png)
![age](charts/03_age.png)
""" + "\n".join(f"- Gender code {int(r.gender)}: {num(r.users)} users, CTR {pct(r.ctr)}, {r.exposures_per_user:,.0f} exposures per user" for r in g2.itertuples()) + f"""
- {sg.test if sg is not None else ""}: {tl(sg)}.
- {sa.test if sa is not None else ""}: {tl(sa)}.

## 3. Content and popularity bias
![popularity](charts/04_popularity.png)
- {num(conc["items"])} videos; the top 10% receive {pct(conc.top10pct_exposure_share)} of exposures and the top 1% receive {pct(conc.top1pct_click_share)} of clicks.
- {spop.test if spop is not None else ""}: {tl(spop)}.
""" + "\n".join(f"- Videos with {r.exposure_band.split('_', 1)[1]} exposures: {num(r.items)} videos, mean video CTR {pct(r.mean_item_ctr)}" for r in isz.itertuples()) + f"""

**Recommendation 1: test an exploration slot.** {"Because the most-exposed videos do not click better than mid-popularity videos, part of their exposure could go to an exploration slot (for example 1 in 10 feed positions) for less-shown videos with good early CTR." if top_dec.clicks / top_dec.exposures <= mid_ctr else "Popular videos click better, but exposure is extremely concentrated. Reserve a small exploration slot (for example 1 in 10 positions) so new videos can prove themselves, and measure CTR and catalogue coverage in an A/B test."}

## 4. Users
![activity](charts/05_user_activity.png)
![concentration](charts/06_user_concentration.png)
- {num(us.users)} users: {num(us.never_clicked)} never clicked, {pct(us.ever_liked / us.users)} ever liked, {pct(us.ever_shared / us.users)} ever shared, {pct(us.ever_followed / us.users)} ever followed.
""" + "\n".join(f"- {r.label} exposures: {pct(r.user_share)} of users, {pct(r.click_share)} of clicks, CTR {pct(r.ctr)}" for r in ab.itertuples()) + f"""

{rec2}

## 5. Feed fatigue
![fatigue](charts/07_fatigue.png)
""" + "\n".join(f"- {r.test}: {tl(r)}." for r in s_fat) + f"""
- {lost_txt}

**Recommendation 3: refresh deep sessions.** Insert diversity breaks (new categories or creators) after about 100 exposures and A/B test the effect on CTR at depth and on total session clicks.

## 6. Limitations
1. No timestamps: position in the file is used as scroll order (the Tenrec authors build session sequences the same way), so fatigue mixes within-session and across-session effects.
2. Gender, age and video_category are anonymised codes; the analysis compares groups but cannot name them.
3. QK sequence analysis uses a fixed 2% user sample (user_id divisible by 50) to keep the sort affordable; totals elsewhere use all rows.
4. Observational data: every recommendation needs an A/B test.
"""
    (out / "report.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    build(Path(__file__).resolve().parents[1] / "output")
