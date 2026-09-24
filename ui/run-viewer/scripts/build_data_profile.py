"""Sinh src/mock/data_profile.json cho trang "Bối cảnh dữ liệu": phân phối từng cột
trong dữ liệu THÔ (csv vào pipeline) và SAU tiền xử lý (after_P09.parquet).

Chạy bằng Python của ra_causal (cần pandas + pyarrow):
  ../../.venv/bin/python scripts/build_data_profile.py \
      --raw <dirty.csv> --final <interim/<run_id>/after_P09.parquet> \
      --schema ../../configs/schema/canonical.yaml --out src/mock/data_profile.json
"""
import argparse, json
import numpy as np, pandas as pd, yaml

ap = argparse.ArgumentParser()
ap.add_argument("--raw", required=True)
ap.add_argument("--final", required=True)
ap.add_argument("--schema", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()

schema = yaml.safe_load(open(a.schema, encoding="utf-8"))["columns"]
raw = pd.read_csv(a.raw, dtype=str, keep_default_na=False)
final = pd.read_parquet(a.final)
NUM = {"float32", "float64", "int8", "int16"}
BINS = 14


def num_profile(s: pd.Series, n_invalid: int = 0):
    v = s.dropna().astype(float)
    if v.empty:
        return {"kind": "num", "n": int(len(s)), "missing": int(s.isna().sum()), "invalid": n_invalid}
    counts, edges = np.histogram(v, bins=BINS)
    return {
        "kind": "num", "n": int(len(s)), "missing": int(s.isna().sum()) - n_invalid, "invalid": n_invalid,
        "min": float(v.min()), "max": float(v.max()), "median": float(v.median()),
        "hist": counts.tolist(), "edges": [float(edges[0]), float(edges[-1])],
    }


def cat_profile(s: pd.Series):
    s = s.astype(object).where(s.notna(), None)
    vc = s.map(lambda x: "(trống)" if x is None or x == "" else str(x)).value_counts()
    return {
        "kind": "cat", "n": int(len(s)), "missing": int(vc.get("(trống)", 0)),
        "n_unique": int(len(vc)), "top": [[k, int(c)] for k, c in vc.head(8).items()],
    }


out = {"columns": {}}
for col in raw.columns:
    dtype = schema.get(col, {}).get("dtype")
    r = raw[col].replace("", np.nan)
    if dtype in NUM:
        parsed = pd.to_numeric(r, errors="coerce")
        invalid = int((r.notna() & parsed.isna()).sum())
        raw_p = num_profile(parsed, invalid)
        raw_p["missing"] = int(r.isna().sum())
        fin_p = num_profile(pd.to_numeric(final[col], errors="coerce")) if col in final else None
    elif col in ("record_id", "grower_id", "field_id"):
        raw_p = {"kind": "id", "n": int(len(r)), "missing": int(r.isna().sum()), "n_unique": int(r.nunique()),
                 "duplicated": int(r.dropna().duplicated().sum())}
        f = final[col] if col in final else None
        fin_p = None if f is None else {"kind": "id", "n": int(len(f)), "missing": int(f.isna().sum()),
                                         "n_unique": int(f.nunique()), "duplicated": int(f.dropna().duplicated().sum())}
    else:
        raw_p = cat_profile(r)
        fin_p = cat_profile(final[col]) if col in final else None
    out["columns"][col] = {"raw": raw_p, "final": fin_p}

y = pd.to_numeric(final["yield_t_ha"], errors="coerce")
out["dataset"] = {
    "raw": {"rows": int(len(raw)), "cols": int(raw.shape[1]), "growers": int(raw["grower_id"].nunique()),
            "fields": int(raw["field_id"].nunique()),
            "years": [int(pd.to_numeric(raw["year"]).min()), int(pd.to_numeric(raw["year"]).max())],
            "cover_crop_true": int((raw["cover_crop"] == "True").sum())},
    "final": {"rows": int(len(final)), "cols": int(final.shape[1]),
              "treated": int((final["cover_crop"] == True).sum()),  # noqa: E712
              "treatment_missing": int(final["cover_crop"].isna().sum()),
              "y_missing": int(y.isna().sum()), "clusters": int(final["cluster_id"].nunique()),
              "folds": int(final.loc[final["fold_id"] >= 0, "fold_id"].nunique()),
              "dup_record_id": int(final["record_id"].duplicated().sum())},
}
json.dump(out, open(a.out, "w"), ensure_ascii=False, indent=1)
print("ok", len(out["columns"]), "cột", json.dumps(out["dataset"], ensure_ascii=False))
