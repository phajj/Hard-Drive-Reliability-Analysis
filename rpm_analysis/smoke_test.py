import csv, io, random, subprocess, sys, tempfile, zipfile, datetime as dt
from pathlib import Path
import pandas as pd
proj = Path(__file__).resolve().parent
tmp = Path(tempfile.mkdtemp(prefix="hddsmoke_")); (tmp/"zips").mkdir()
random.seed(1)
models = {("Hitachi","HMS5C4040ALE640"):5700, ("","ST4000DM000"):5900, ("","WDC WD30EFRX"):5400, ("","HDS5C3030ALA630"):5700,
          ("","ST12000NM0007"):7200, ("HGST","HUH721212ALN604"):7200, ("","TOSHIBA MG07ACA14TA"):7200,
          ("","ST31500541AS"):5900, ("","ST3000DM001"):7200}
drives = []
for (pre, m), rpm in models.items():
    for i in range(600):
        drives.append(dict(sn=f"{m[:4]}{i:05d}", pre=pre, m=m, rpm=rpm, poh=random.randint(0, 30000), alive=True))
start = dt.date(2019,1,1)
for zi, name in enumerate(["data_Q1_2019", "data_Q2_2019"]):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for day in range(60):
            date = start + dt.timedelta(days=zi*60+day)
            cols = ["date","serial_number","model","capacity_bytes","failure","smart_1_raw","smart_9_raw"] + (["smart_999_raw"] if zi else [])
            s = io.StringIO(); w = csv.writer(s); w.writerow(cols)
            for d in drives:
                if not d["alive"]: continue
                d["poh"] += 24
                fail = random.random() < (0.01 if d["m"]=="ST3000DM001" else {5400:0.002, 5700:0.0005, 5900:0.00075, 7200:0.001}[d["rpm"]])
                pre = d["pre"] if not (zi and d["pre"]=="Hitachi") else "HGST"   # name change between zips
                model = f"{pre} {d['m']}".strip()
                row = [date.isoformat(), d["sn"], model, 4000787030016, int(fail), 0, d["poh"] if random.random()>0.01 else ""]
                w.writerow(row + ([""] if zi else []))
                if fail: d["alive"] = False
            zf.writestr(f"{name}/{date}.csv", s.getvalue())
            if day == 0: zf.writestr(f"__MACOSX/{name}/._{date}.csv", b"\x00\x05junk")
    (tmp/"zips"/f"{name}.zip").write_bytes(buf.getvalue())
true_failures = sum(not d["alive"] for d in drives)
py = sys.executable
def run(*a):
    r = subprocess.run([py, str(proj/a[0]), *a[1:]], cwd=tmp, capture_output=True, text=True)
    print(f"$ {' '.join(a)}\n{r.stdout[-2500:]}{r.stderr[-2500:]}"); assert r.returncode == 0
run("process_zips.py", "zips")
run("process_zips.py", "zips")          # re-run should skip both
run("build_drive_table.py")
d = pd.read_parquet(tmp/"drives.parquet")
assert len(d) == 5400, len(d); assert d.failed.sum() == true_failures, (d.failed.sum(), true_failures)
assert d.model.nunique() == 9, d.model.unique()
assert not (tmp/"work"/"data_Q1_2019").exists()
run("list_models.py", "--min-drives", "100")
lab = pd.read_csv(tmp/"models_to_label.csv"); print(lab[["model","drives","rpm_hint"]])
lab["rpm"] = lab["rpm_hint"]; lab.to_csv(tmp/"models_to_label.csv", index=False)
r = subprocess.run([py, str(proj/"list_models.py")], cwd=tmp, capture_output=True, text=True); assert r.returncode != 0
run("sample_by_rpm.py", "--per-class", "1000", "--max-model-share", "0.5", "--latest-model-year", "2019")
r = subprocess.run([py, str(proj/"sample_by_rpm.py"), "--latest-model-year", "2018", "--out", "x.parquet"], cwd=tmp, capture_output=True, text=True)
assert r.returncode != 0 and "No drives left" in r.stdout + r.stderr, "era filter did not drop later models"
smp = pd.read_parquet(tmp/"sample.parquet")
assert not {"ST3000DM001", "WDC WD30EFRX"} & set(smp.model), "default exclusions not applied"
assert sorted(smp.rpm_class.unique()) == ["5700", "5900", "7200"], smp.rpm_class.unique()
import hashlib
sample_ids = pd.read_parquet(tmp/"sample.parquet").serial_number.sort_values()
print("SAMPLE FINGERPRINT:", hashlib.sha1("".join(sample_ids).encode()).hexdigest()[:12])
print("ALL CHECKS PASSED, true failures:", true_failures, "tmp:", tmp)
