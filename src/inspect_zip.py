"""Lists the contents of Tenrec.zip (names, sizes) and the first rows of every CSV inside,
without extracting anything. Output: output/inspect.txt"""
import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = [ROOT / "data" / "Tenrec.zip", ROOT.parent / "Tenrec.zip"]


def main():
    z = next((p for p in CANDIDATES if p.exists()), None)
    out = ROOT / "output"
    out.mkdir(exist_ok=True)
    lines = []
    if z is None:
        lines.append("[ERROR] Tenrec.zip not found in: " + ", ".join(map(str, CANDIDATES)))
    else:
        lines.append(f"zip: {z}  ({z.stat().st_size / 1e9:.2f} GB)")
        with zipfile.ZipFile(z) as zf:
            infos = zf.infolist()
            for i in infos:
                lines.append(f"{i.file_size / 1e6:12,.1f} MB  {i.compress_size / 1e6:10,.1f} MB zipped  {i.filename}")
            for i in infos:
                if i.filename.lower().endswith((".csv", ".txt")) and i.file_size > 0:
                    lines.append(f"\n===== {i.filename} =====")
                    with zf.open(i) as f:
                        txt = io.TextIOWrapper(f, encoding="utf-8", errors="replace")
                        for k in range(6):
                            row = txt.readline()
                            if not row:
                                break
                            lines.append(row.rstrip()[:300])
    (out / "inspect.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
