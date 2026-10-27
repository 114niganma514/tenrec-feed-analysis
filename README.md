# Tencent Video Feed Engagement Analysis (Tenrec, ~490M exposures)

Analysis of real exposure logs from two Tencent video feeds: **QQ Kandian (QK)** and **QQ Browser (QB)**, from the Tenrec benchmark (NeurIPS 2022). Each row is one video shown to a user, with click, like, share and follow flags. The project builds the exposure -> click -> like/share/follow funnel at the scale of hundreds of millions of rows, compares audiences and products, measures popularity bias, and tests whether click-through decays the further users scroll.

## 1. Business questions

| # | Question | Method | File |
|---|---|---|---|
| Q1 | How much of the feed gets clicked, and how deep does engagement go? QK vs QB? | Funnel per 1,000 exposures, two-proportion z-tests | `sql/02_funnel.sql` |
| Q2 | Which audiences click most? | CTR by gender code and age band, gender x age grid, chi-square, Spearman | `sql/03_demographics.sql` |
| Q3 | Is exposure concentrated, and do the most-shown videos earn it? | Exposure deciles vs CTR, top-1%/10% shares, item CTR by exposure band | `sql/04_content.sql` |
| Q4 | How concentrated is engagement among users? How many never click? | Activity buckets, user concentration curve | `sql/05_users.sql` |
| Q5 | Does click-through fall as users scroll deeper? | CTR by feed position; same-user comparison (Wilcoxon signed-rank) | `sql/06_sequence.sql` |

## 2. Data

- Source: [Tenrec](https://github.com/yuangh-x/2022-NIPS-Tenrec) (Yuan et al., NeurIPS 2022). Download `Tenrec.zip` from the [official page](https://static.qblv.qq.com/qblv/h5/algo-frontend/tenrec_dataset.html) after accepting the licence. Not redistributed here.
- Files used: `QK-video.csv` (15.1 GB) and `QB-video.csv` (77 MB). Columns: `user_id, item_id, click, follow, like, share, video_category, watching_times, gender, age`.
- Notes: `like` is renamed `alike` (SQL keyword); gender, age and video_category are anonymised codes (0 = missing); there are no timestamps, so file order is used as feed order (as the Tenrec authors do for session sequences).
- Data quality checks (`sql/01_clean.sql`): invalid click values, actions without a click, watches without a click, missing demographics.

## 3. How to run

**Windows:** keep `Tenrec.zip` in `data\` or in the folder above this project, then double-click `run_windows.bat`. The first run extracts about 15 GB and processes ~490M rows with DuckDB (roughly 15-40 minutes depending on the machine; needs ~40 GB free disk).

**Command line:**
```bash
pip install duckdb pandas matplotlib scipy
python src/run_analysis.py --zip "path/to/Tenrec.zip"
python data/generate_sample.py && python src/run_analysis.py --data data/sample --engine sqlite   # synthetic test
```

Outputs: `output/tables/*.csv`, `output/charts/*.png` (7 charts), `output/report.md`.

## 4. Project structure

```
data/generate_sample.py     synthetic data with the Tenrec schema (testing only)
src/inspect_zip.py          lists the zip contents and first rows without extracting
sql/01_clean.sql            data quality, user and item tables
sql/02_funnel.sql           exposure -> click -> like/share/follow, QK vs QB
sql/03_demographics.sql     gender and age
sql/04_content.sql          popularity concentration and bias
sql/05_users.sql            user activity and concentration
sql/06_sequence.sql         feed fatigue by position
src/run_analysis.py         extract, load, run SQL, export
src/stats_tests.py          z-tests, chi-square, Spearman, Wilcoxon
src/make_report.py          charts and report
run_windows.bat             one-click runner for Windows
```

## 5. Metric definitions

- **CTR** = clicks / exposures; **likes / shares / follows per click** = action count / clicks
- **Re-watch rate** = clicked exposures with watching_times >= 2 / clicks
- **Popularity decile** = videos split into 10 equal-count groups by number of exposures
- **Feed position** = n-th exposure of a user in file order

## 6. Key findings (real data; full numbers in `output/report.md`)

1. **Feed fatigue is real and large.** For the same QK users, click-through falls from 32.1% in their first 20 exposures to 24.3% at exposures 101-200 (Wilcoxon signed-rank p < 0.001; 67% of users click less later). About 31% of exposures happen beyond position 100; recovering a tenth of the gap is worth about 2.4M clicks (+1.7%).
2. **Two products, two behaviours.** QQ Browser users click 2.4x as often as QQ Kandian users (69.7% vs 28.8% CTR) but like 5.9x less per click: shallow clicking vs deeper engagement.
3. **Exposure is extremely concentrated.** The top 1% of videos get 66% of exposures and 1.3M videos were shown only once; popular videos do click better (39% CTR at 100k+ exposures vs 22% at 100-999), which is partly a feedback loop.
4. **Engagement beyond the click is thin.** Only 32% of users ever liked, 13% ever shared and 9% ever followed, out of 5.0M users who almost all clicked something.
5. **Heavy users click less per exposure.** CTR falls from 44% for the lightest users to 18% for users with 500+ exposures; the top 10% of users make 33% of clicks.

## 7. Limitations
- No timestamps; fatigue mixes within-session and across-session effects
- Demographics and video_category are anonymised codes
- QK position analysis uses a fixed 2% user sample to keep the sort affordable
- Observational data: recommendations need A/B tests
