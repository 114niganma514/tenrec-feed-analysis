"""
One-click pipeline for the Tenrec (Tencent) feed project:
extract QK-video.csv and QB-video.csv from Tenrec.zip -> load -> run sql/01-06 -> save every query
result to output/tables/ -> statistical tests -> charts and report.

Usage:
    python src/run_analysis.py                          # finds Tenrec.zip in data/ or the folder above the project
    python src/run_analysis.py --zip "D:/path/Tenrec.zip"
    python src/run_analysis.py --data data/sample --engine sqlite   # synthetic test data

QK-video has ~490M rows: DuckDB is required for the real data (about 15 GB uncompressed, spills to disk).
"""
import argparse
import re
import shutil
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR, OUT = ROOT / "sql", ROOT / "output"
FILES = ["QK-video.csv", "QB-video.csv"]
ZIP_CANDIDATES = [ROOT / "data" / "Tenrec.zip", ROOT.parent / "Tenrec.zip"]
SQL_FILES = ["01_clean.sql", "02_funnel.sql", "03_demographics.sql", "04_content.sql", "05_users.sql",
             "06_sequence.sql"]
COLUMNS = {"user_id": "UINTEGER", "item_id": "UINTEGER", "click": "UTINYINT", "follow": "UTINYINT",
           "like": "UTINYINT", "share": "UTINYINT", "video_category": "TINYINT", "watching_times": "USMALLINT",
           "gender": "UTINYINT", "age": "UTINYINT"}


def find_data(data_arg, zip_arg):
    if data_arg:
        p = Path(data_arg)
        if all((p / f).exists() for f in FILES):
            return p
        raise SystemExit(f"[ERROR] {p} does not contain {FILES}")
    target = ROOT / "data" / "tenrec"
    if all((target / f).exists() for f in FILES):
        return target
    z = Path(zip_arg) if zip_arg else next((c for c in ZIP_CANDIDATES if c.exists()), None)
    if z is None or not z.exists():
        raise SystemExit("[ERROR] Tenrec.zip not found. Download it from the official Tenrec page "
                         "(https://static.qblv.qq.com/qblv/h5/algo-frontend/tenrec_dataset.html) and pass --zip.")
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(z) as zf:
        for info in zf.infolist():
            name = Path(info.filename).name
            if name in FILES and "__MACOSX" not in info.filename and not (target / name).exists():
                print(f"Extracting {name} ({info.file_size / 1e9:.1f} GB) from {z} ...", flush=True)
                tmp = target / (name + ".part")
                done, last = 0, -1
                with zf.open(info) as src, open(tmp, "wb") as dst:
                    while chunk := src.read(64 << 20):
                        dst.write(chunk)
                        done += len(chunk)
                        if info.file_size and done * 10 // info.file_size != last:
                            last = done * 10 // info.file_size
                            print(f"  {done / 1e9:.1f} / {info.file_size / 1e9:.1f} GB", flush=True)
                tmp.replace(target / name)
    missing = [f for f in FILES if not (target / f).exists()]
    if missing:
        raise SystemExit(f"[ERROR] {z} does not contain {missing}")
    return target


class Engine:
    def __init__(self, kind: str, db: str):
        self.kind = kind
        if kind == "duckdb":
            import duckdb
            self.con = duckdb.connect(db)
            tmp = Path(db).parent / "duckdb_tmp"
            self.con.execute(f"SET temp_directory='{tmp.as_posix()}'")
        else:
            import sqlite3
            self.con = sqlite3.connect(db)
            self.con.execute("PRAGMA journal_mode=OFF")
            self.con.execute("PRAGMA synchronous=OFF")

    def load_csv(self, name: str, path: Path):
        # "like" is an SQL keyword, so the column is renamed to "alike"
        # Missing values are written as \N in the source files. Flags and demographics default to 0
        # (0 is already the dataset's "missing" code for gender and age); a missing video_category
        # becomes -1 so it can be reported separately. Null counts are kept in table null_counts.
        if self.kind == "duckdb":
            cols = ", ".join(f"'{k}': '{v}'" for k, v in COLUMNS.items())
            self.con.execute(f"""CREATE OR REPLACE TABLE {name}_nulls AS
                SELECT '{name}' AS tbl, COUNT(*) - COUNT(click) AS click_null, COUNT(*) - COUNT("like") AS like_null,
                       COUNT(*) - COUNT(video_category) AS category_null, COUNT(*) - COUNT(gender) AS gender_null,
                       COUNT(*) - COUNT(age) AS age_null, COUNT(*) - COUNT(watching_times) AS watching_null
                FROM read_csv('{path.as_posix()}', header=true, nullstr='\\N', columns={{{cols}}})""")
            self.con.execute(f"""CREATE OR REPLACE TABLE {name} AS
                SELECT user_id, item_id,
                       COALESCE(click, 0) AS click, COALESCE(follow, 0) AS follow, COALESCE("like", 0) AS alike,
                       COALESCE(share, 0) AS share, COALESCE(video_category, -1) AS video_category,
                       COALESCE(watching_times, 0) AS watching_times,
                       COALESCE(gender, 0) AS gender, COALESCE(age, 0) AS age
                FROM read_csv('{path.as_posix()}', header=true, nullstr='\\N', columns={{{cols}}})""")
            return self.con.execute(f"SELECT COUNT(*) FROM {name}").fetchall()[0][0]
        self.con.execute(f"DROP TABLE IF EXISTS {name}")
        n = 0
        nulls = None
        for chunk in pd.read_csv(path, chunksize=1_000_000, na_values=["\\N"]):
            nc = chunk.isna().sum()
            nulls = nc if nulls is None else nulls + nc
            chunk = chunk.fillna({"video_category": -1}).fillna(0).astype(int)
            chunk.rename(columns={"like": "alike"}).to_sql(name, self.con, if_exists="append", index=False)
            n += len(chunk)
        pd.DataFrame([{"tbl": name, "click_null": nulls["click"], "like_null": nulls["like"],
                       "category_null": nulls["video_category"], "gender_null": nulls["gender"],
                       "age_null": nulls["age"], "watching_null": nulls["watching_times"]}]).to_sql(
            f"{name}_nulls", self.con, if_exists="replace", index=False)
        return n

    def run(self, sql: str, fetch: bool):
        if self.kind == "duckdb":
            r = self.con.execute(sql)
            return r.df() if fetch else None
        if fetch:
            return pd.read_sql_query(sql, self.con)
        self.con.execute(sql)
        self.con.commit()


def parse_blocks(path: Path):
    text = path.read_text(encoding="utf-8")
    for part in re.split(r"^-- @name\s+", text, flags=re.M)[1:]:
        name, body = part.split("\n", 1)
        body = "\n".join(l for l in body.splitlines() if not l.strip().startswith("--"))
        yield name.strip(), [s.strip() for s in body.split(";") if s.strip()]


def run_file(eng: Engine, path: Path):
    for name, stmts in parse_blocks(path):
        t = time.time()
        res = None
        for s in stmts:
            res = eng.run(s, fetch=s.lstrip().upper().startswith(("SELECT", "WITH")))
        if res is not None:
            (OUT / "tables").mkdir(parents=True, exist_ok=True)
            res.to_csv(OUT / "tables" / f"{name}.csv", index=False, encoding="utf-8")
        print(f"  {path.name:<20} {name:<22} {time.time() - t:7.1f}s", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None, help="Folder with QK-video.csv and QB-video.csv")
    ap.add_argument("--zip", default=None, help="Path to Tenrec.zip (default: auto-detect)")
    ap.add_argument("--engine", choices=["auto", "duckdb", "sqlite"], default="auto")
    a = ap.parse_args()
    if a.engine == "auto":
        try:
            import duckdb  # noqa: F401
            a.engine = "duckdb"
        except ImportError:
            a.engine = "sqlite"

    folder = find_data(a.data, a.zip)
    real = "sample" not in folder.name
    print(f"Data folder: {folder}\nEngine: {a.engine}", flush=True)
    for sub in ("tables", "charts"):
        shutil.rmtree(OUT / sub, ignore_errors=True)
        (OUT / sub).mkdir(parents=True, exist_ok=True)
    db = OUT / f"tenrec.{a.engine}"
    db.unlink(missing_ok=True)
    eng = Engine(a.engine, str(db))

    t0 = time.time()
    print("[1/4] Load CSV files", flush=True)
    for table, file in [("qk", "QK-video.csv"), ("qb", "QB-video.csv")]:
        t = time.time()
        n = eng.load_csv(table, folder / file)
        print(f"  {file:<16} {n:>14,} rows {time.time() - t:7.1f}s", flush=True)
    pd.DataFrame([{"source": "Tenrec official release (real data)" if real else "synthetic sample"}]).to_csv(
        OUT / "tables" / "data_source.csv", index=False)

    print("[2/4] Analyse (SQL)", flush=True)
    for f in SQL_FILES:
        run_file(eng, SQL_DIR / f)

    print("[3/4] Statistical tests", flush=True)
    sys.path.insert(0, str(Path(__file__).parent))
    from stats_tests import run_tests
    run_tests(OUT)

    print("[4/4] Charts and report", flush=True)
    from make_report import build
    build(OUT)
    print(f"Done in {time.time() - t0:.0f}s -> {OUT}")


if __name__ == "__main__":
    main()
