"""
Generates SYNTHETIC QK-video.csv / QB-video.csv files with the same columns as Tenrec, for testing
the pipeline only. Numbers from this data are meaningless.
Usage: python data/generate_sample.py --users 3000 --out data/sample
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

COLS = ["user_id", "item_id", "click", "follow", "like", "share", "video_category", "watching_times", "gender", "age"]


def make(n_users, n_items, rng, base_ctr, uid0):
    act = rng.lognormal(3.2, .9, n_users).astype(int) + 3
    gender = rng.choice([0, 1, 2], n_users, p=[.05, .55, .40])
    age = rng.choice(range(9), n_users, p=[.05, .05, .15, .2, .2, .15, .1, .06, .04])
    pop = rng.pareto(1.2, n_items) + 1
    pop /= pop.sum()
    item_q = rng.lognormal(0, .5, n_items)
    item_cat = (rng.random(n_items) < .7).astype(int)
    rows = []
    for u in range(n_users):
        n = act[u]
        items = rng.choice(n_items, n, p=pop)
        pos = np.arange(n)
        p_click = np.clip(base_ctr * item_q[items] * (1 + .15 * (gender[u] == 2)) * (1.2 - .04 * age[u])
                          * (1 - .3 * pos / (n + 20)), 0, .95)
        click = (rng.random(n) < p_click).astype(int)
        like = click * (rng.random(n) < .03 * item_q[items])
        share = click * (rng.random(n) < .004)
        follow = click * (rng.random(n) < .006)
        watch = click * (1 + rng.poisson(.25, n))
        rows.append(np.column_stack([np.full(n, uid0 + u), items, click, follow, like, share, item_cat[items], watch,
                                     np.full(n, gender[u]), np.full(n, age[u])]))
    return pd.DataFrame(np.vstack(rows), columns=COLS)


def main(n_users, out, seed):
    rng = np.random.default_rng(seed)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    make(n_users, n_users * 5, rng, .3, 1).to_csv(out / "QK-video.csv", index=False)
    make(n_users // 5, n_users, rng, .12, 3_500_000).to_csv(out / "QB-video.csv", index=False)
    print(f"wrote synthetic Tenrec files -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=3000)
    ap.add_argument("--out", default="data/sample")
    ap.add_argument("--seed", type=int, default=3)
    a = ap.parse_args()
    main(a.users, a.out, a.seed)
