"""Nạp một lượt chạy thật của ra_causal vào dữ liệu mẫu của giao diện.

Chỉ dùng thư viện chuẩn của Python, chạy được trên macOS, Windows, Linux:

  python scripts/import_run.py --run-dir ../../data/out --run-id <run_id>

Ghi đè:
  src/mock/runs.json            <- reports/<run_id>/run_report.json
  src/mock/variable_roles.json  <- processed/<run_id>/data_dictionary.csv (artifact của P08)
Không đụng tới data_profile.json (chạy build_data_profile.py) và content/dataContext.ts
(phần "lỗi cài trong mock" viết tay cho dirty.csv — đổi dữ liệu thì phải sửa tay).
"""
import argparse, csv, json, os

ap = argparse.ArgumentParser()
ap.add_argument("--run-dir", required=True, help="thư mục --output đã truyền cho run_pipeline (vd ../../data/out)")
ap.add_argument("--run-id", required=True, help="tên thư mục lượt chạy, vd 20260924-112145-95668ddd")
a = ap.parse_args()

here = os.path.dirname(os.path.abspath(__file__))
mock = os.path.join(here, "..", "src", "mock")
report_path = os.path.join(a.run_dir, "reports", a.run_id, "run_report.json")
dict_path = os.path.join(a.run_dir, "processed", a.run_id, "data_dictionary.csv")

with open(report_path, encoding="utf-8") as f:
    report = json.load(f)
with open(os.path.join(mock, "runs.json"), "w", encoding="utf-8") as f:
    json.dump({"A": report}, f, ensure_ascii=False, indent=1)


def cell(v: str):
    if v == "":
        return None
    if v in ("True", "False"):
        return v == "True"
    return v


with open(dict_path, encoding="utf-8", newline="") as f:
    rows = [{k: cell(v) for k, v in r.items()} for r in csv.DictReader(f)]
with open(os.path.join(mock, "variable_roles.json"), "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)

print(f"runs.json: {report['run_id']} ({report['status']}, {len(report['steps'])} bước)")
print(f"variable_roles.json: {len(rows)} cột")
